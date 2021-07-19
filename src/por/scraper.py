from __future__ import annotations

import json
import re

from lxml import html

BLANK_RULE = "|BLANK RULE DUMMY|"

ALPHA = "abcdefghijklmnopqrstuvwxyz"
ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")

TYPES_CHARS = {
    "alpha": ALPHA,
    "roman": ROMAN,
    "disc": "*",
    "none": " ",
}

STRONG = re.compile("</?strong>")
EMPH = re.compile("</?em>")
LIST_ITEM = re.compile("</?li>")
PARA = re.compile("</?p.*?>")  # needed for e.g. 3.12 with <p style=...>
LINK = re.compile("""<a .*?href="(.*?)".*?>(.*?)</a>""")


def chapter_text(content: str) -> str:
    chapter_rules = get_rules(_get_chapter_data(content))

    chapter_title, chapter_intro = chapter_rules.pop(0)
    text = [_emit_chapter_start(chapter_title, chapter_intro)]

    for rule_title, rule_text in chapter_rules:
        text.append(_emit_rule(rule_title, rule_text))

    return "\n\n".join(text)


def _get_chapter_data(content: str) -> dict:
    por_state = _get_state_data(content)
    return por_state["chapters"][por_state["currentChapter"]]


def _get_state_data(page_content: str) -> dict:
    start = page_content.index("window.__INITIAL_STATE__=") + len("window.__INITIAL_STATE__=")
    end = page_content.index(";(function()")
    state = page_content[start:end]
    return json.loads(state)["por"]


def get_rules(chapter_data: dict) -> list[tuple[str, str]]:
    """Get rules from a chapter data blob.

    Arguments:
        chapter_data: chapter data blob

    Returns:
        List of rules as title, text tuples. The first (index 0) is the chapter
        name and introductory text.

    """
    introduction = _get_rule_details(chapter_data)
    rules = (_get_rule_details(rule_data) for rule_data in chapter_data["rules"])

    return [introduction, *rules]


def _get_rule_details(item: dict) -> tuple[str, str]:
    rows = item["content"]["sections"][0]["rows"]
    if not rows:  # intentionally left blank
        return item["title"], BLANK_RULE
    # e.g. 3.51 has 2 controls dicts
    return item["title"], "".join(control["value"] for control in rows[0]["areas"][0]["controls"])


def _emit_chapter_start(title: str, introduction: str) -> str:
    return _emit_titled_block(title, introduction, page_title=True)


def _emit_rule(title: str, text: str) -> str:
    return _emit_titled_block(title, text, page_title=False)


def _emit_titled_block(title: str, text: str, page_title: bool = False) -> str:
    title = title.replace("’", "'").strip()
    underline = ("=" if page_title else "-") * len(title)
    return f"{title}\n{underline}\n{_html_to_rest(text)}"


def _html_to_rest(html_text: str) -> str:
    if html_text == BLANK_RULE:
        return html_text

    # assert count <(p|a|ol|ul|li|em|strong|sup) == count <[a-zA-Z]
    text = (
        " ".join(html_text.replace("\n", "").split())  # normalise whitespace
        .replace("‘", "'").replace("’", "'")  # curly single quotes
        .replace('“', '"').replace('”', '"')  # curly double quotes
        .replace("–", "--")  # en dash
        .replace("½", " 1/2").replace("¾", " 3/4")  # unicode fractions
        .replace("<sup>sv</sup>", ":sup:`sv`")  # scottish variations
    )

    # strong and emphasis
    text = text.replace("<strong><br /></strong>", "<br />").replace("<em><br /></em>", "<br />")
    text = STRONG.sub("**", text)
    text = EMPH.sub("*", text)
    text = (
        text  # run twice to catch extra tags
        .replace("**<br />", "**").replace("<br />**", "**").replace("*<br />", "*").replace("<br />*", "*")
        .replace("**<br />", "**").replace("<br />**", "**").replace("*<br />", "*").replace("<br />*", "*")
    )

    # hyperlinks
    text = LINK.sub(r"`\2 &lt\1&gt`_", text)  # don't use < and > as we split on these later

    # lists
    text = "\n".join(_parse_html_list(tag) for tag in html.fragments_fromstring(text))
    text = LIST_ITEM.sub("", text)

    # <p> tags
    text = PARA.sub("\n", text)  # paragraph

    text = (
        text
        # clean up from para tags
        .replace("\n\n", "\n")
        .strip("\n")
        .replace(" \n*", " *")
        # deal with newlines
        .replace("<br />", "\n")
        .replace("<br>", "\n")  # lxml 'normalises' br tags to without the closing slash
        .replace("\n\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .replace("\n\n\n\n", "\n\n\n")
        .strip("\n")
        # replace with real values
        .replace("&lt", "<").replace("&gt", ">")
        .replace("&amp;", "&")
    )

    return text


def _parse_html_list(tag: html.HtmlElement, indent_level: int = 0) -> str:
    name = tag.tag
    if name not in {"ol", "ul", "li"}:
        return _stringify_element(tag)

    # ordered list
    if name == "ol":
        ordered = True
        list_type = "alpha"
        if "lower-roman" in tag.get("style", ""):
            list_type = "roman"

    # unordered list
    elif name == "ul":
        ordered = False
        list_type = "disc"
        if "none" in tag.get("style", ""):
            list_type = "none"

    # list items
    else:
        raise ValueError("can't have raw li tags!")

    count = 0
    parsed = [""]  # nested lists must be separated by blank lines

    indent = "   " * indent_level  # three spaces per level, ignoring first level
    line_prefix_no_number = indent + "   "
    for el in tag:
        list_char = f"{TYPES_CHARS[list_type][count if ordered else 0] + '.' * ordered: <3}"
        line_prefix = indent + list_char
        count += 1

        if el.text:
            parsed.append(line_prefix + el.text)
            line_prefix = line_prefix_no_number
        for sub in el:
            if sub.tag in {"ol", "ul"}:
                # nested list must be separated by blank lines
                parsed += ["", _parse_html_list(sub, indent_level=indent_level+1), ""]
            elif sub.tag == "br":
                parsed.append("<br />")
            else:
                parsed.append(line_prefix + _stringify_element(sub))
                line_prefix = line_prefix_no_number
            if sub.tail:
                parsed.append(line_prefix + sub.tail.strip())
                line_prefix = line_prefix_no_number
        if el.tail:
            parsed.append(line_prefix + el.tail)

    parsed += [""]  # nested lists must be separated by blank lines
    return "\n".join(parsed)


def _stringify_element(el: html.HtmlElement) -> str:
    # .__copy__() fixes bug with text serialisation (tostring otherwise prints the entire document)
    return html.tostring(el.__copy__(), encoding="unicode").rstrip("\n").strip()


if __name__ == '__main__':
    # from pathlib import Path
    #
    #
    # import requests

    # Path("overview-raw.txt").write_text(requests.get("https://www.scouts.org.uk/por/").content.decode("utf-8"), encoding="utf-8")
    # Path("ch3-raw.txt").write_text(requests.get("https://www.scouts.org.uk/por/3-the-scout-group/").content.decode("utf-8"), encoding="utf-8")

    # with open("overview-raw.txt", "r", encoding="utf-8") as f:
    #     r_text = f.read()
    # pdf_link = html.document_fromstring(r_text).find(".//main")[0][0][0][-1][0].get("href")
    # por_state = _get_state_data(r_text)
    # por_index = por_state["index"]
    # por_intro = por_state["intro"]
    #
    # links = [item["url"] for item in por_index]

    with open("ch3-raw.txt", "r", encoding="utf-8") as f:
        ch3_raw = f.read()
    ch3_text = chapter_text(ch3_raw)
    with open("chapter-3-d.rst", "w", encoding="utf-8") as f:
        f.write(ch3_text)

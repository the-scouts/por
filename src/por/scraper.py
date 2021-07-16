from __future__ import annotations

import json
import re

# blank_rule = [{"areas": [{"controls": [{"value": ""}]}]}]
blank_rule = [{"areas": [{"controls": [{"value": "<BLANK RULE DUMMY>"}]}]}]

STRONG = re.compile("</?strong>")
EMPH = re.compile("</?em>")
LINK = re.compile("""<a .*?href="(.*?)".*?>(.*?)</a>""")
PARA = re.compile("</?p.*?>")  # needed for e.g. 3.12 with <p style=...>
LIST_ITEM = re.compile("""<li .*?>""")


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
        return item["title"], "<BLANK RULE DUMMY>"
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

    # <a> and <p> tags
    text = LINK.sub(r"`\2 &lt\1&gt`_", text)  # don't use < and > as we split on these later
    text = PARA.sub("\n", text).replace("\n\n", "\n").strip("\n")  # paragraph

    # lists
    numbering: list[tuple[bool, str | None]] = []  # tuples are ordered true/false and list type
    parsed = []
    for tag in text.replace("<", "¦<").replace("\n", "¦").split("¦"):  # split to tags and on newlines
        # indent level
        if tag.startswith("<ol"):
            if "lower-roman" in tag:
                numbering.append((True, "i."))
            else:  # elif "lower-alpha" in tag:
                numbering.append((True, "a."))
            parsed.append("")  # nested lists must be separated by blank lines
        elif tag.startswith("<ul"):
            if "none" in tag:
                numbering.append((False, ""))
            else:
                numbering.append((False, "*"))
            parsed.append("")  # nested lists must be separated by blank lines

        # dedent level
        elif tag.startswith("</ol"):
            if (lvl := numbering.pop(-1))[0] is not True:
                raise ValueError(f"list parsing mismatch! {lvl=}")
            parsed.append("")  # nested lists must be separated by blank lines
            if remaining := tag.removeprefix("</ol>").strip():
                indent = "   " * len(numbering)  # three spaces per level
                parsed.append(indent + remaining)
        elif tag.startswith("</ul"):
            if (lvl := numbering.pop(-1))[0] is not False:
                raise ValueError(f"list parsing mismatch! {lvl=}")
            parsed.append("")  # nested lists must be separated by blank lines
            if remaining := tag.removeprefix("</ul>").strip():
                indent = "   " * len(numbering)  # three spaces per level
                parsed.append(indent + remaining)

        # item tags
        elif tag.startswith("<li"):
            is_ordered, list_char = numbering[-1]
            indent = "   " * len(numbering[1:])  # three spaces per level, ignoring first level
            parsed.append(f"{indent}{list_char: <3}{tag.removeprefix('<li>')}")  # try to remove naive <li> tag

        # just add the text:
        elif not tag.startswith("</li"):
            tag = tag.strip()
            if tag.startswith("<br />"):
                parsed.append("<br />")
                tag = tag[6:].lstrip()  # len("<br />") == 6
            if tag:
                indent = "   " * len(numbering)  # three spaces per level
                parsed.append(indent + tag)

    return (
        # clean up left over <li> tags
        LIST_ITEM.sub("", "\n".join(parsed))
        # deal with newlines
        .replace("<br />", "\n")
        .replace("\n\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .strip("\n")
        # replace with real values
        .replace("&lt", "<").replace("&gt", ">")
    )


if __name__ == '__main__':
    # from pathlib import Path
    #
    # from lxml import html
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
    with open("chapter-3.rst", "w", encoding="utf-8") as f:
        f.write(ch3_text)
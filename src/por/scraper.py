from __future__ import annotations

import json
import re

from docutils.core import publish_string
from lxml import html

BLANK_RULE = "BLANK RULE DUMMY"

ALPHA = "abcdefghijklmnopqrstuvwxyz"
ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")

TYPES_CHARS = {
    "arabic": tuple(str(i) for i in range(1, 26)),  # 100 item list is a bit much
    "alpha": ALPHA,
    "roman": ROMAN,
    "disc": "*",
    "none": " ",
}

STRONG = re.compile("<strong>(?P<open> *)|(?P<close> *)</strong>")
EMPH = re.compile("<em>(?P<open> *)|(?P<close> *)</em>")
JUNK_TAGS = re.compile("</?(span|div|u)( .*?)?>")
LIST_ITEM = re.compile("</?li.*?>")
PARA = re.compile("</?p.*?>")  # needed for e.g. 3.12 with <p style=...>
NO_TEXT_LINK = re.compile(r"<a [^>]*>(\s*)</a>")
LINK = re.compile(r"""<a .*?href="(.*?)".*?>(\s*)(.*?)(\s*)</a>""")
NEWLINE = re.compile("\n\n+")


def chapter_text(content: str, tmp_ch: int = -1) -> str:
    chapter_rules = get_rules(_get_chapter_data(content))

    chapter_title, chapter_intro = chapter_rules.pop(0)
    text = [_emit_chapter_start(chapter_title, chapter_intro, tmp_ch=tmp_ch)]

    for i, (rule_title, rule_text) in enumerate(chapter_rules):
        if tmp_ch in {3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15}:  # + POR TAP
            text.append(_emit_rule(f"Rule {tmp_ch}.{i+1} {rule_title}", rule_text, tmp_ch=tmp_ch, tmp_rl=i+1))
        else:
            text.append(_emit_rule(rule_title, rule_text, tmp_ch=tmp_ch, tmp_rl=i+1))

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
    title = item["title"]
    if not item["content"]:
        return title, ""  # e.g. chapter 7 intro
    rows = item["content"]["sections"][0]["rows"]
    if not rows:  # intentionally left blank
        return title, BLANK_RULE
    # e.g. 3.51 has 2 controls dicts, so need to loop & concatenate
    # e.g. 8.1 has a call to action button to Unity, so need to check stringiness
    return title, "".join(control["value"] for control in rows[0]["areas"][0]["controls"] if isinstance(control["value"], str))


def _emit_chapter_start(title: str, introduction: str, tmp_ch: int = -1) -> str:
    return _emit_titled_block(title, introduction, page_title=True, tmp_ch=tmp_ch, tmp_rl=0)


def _emit_rule(title: str, text: str, tmp_ch: int = -1, tmp_rl: int = -1) -> str:
    return _emit_titled_block(title, text, page_title=False, tmp_ch=tmp_ch, tmp_rl=tmp_rl)


def _emit_titled_block(title: str, text: str, page_title: bool = False, tmp_ch: int = -1, tmp_rl: int = -1) -> str:
    title = title.replace("’", "'").strip()
    underline = ("=" if page_title else "-") * len(title)
    return f"{title}\n{underline}\n{_html_to_rest(text, tmp_ch=tmp_ch, tmp_rl=tmp_rl)}"


def _html_to_rest(html_text: str, tmp_ch: int = -1, tmp_rl: int = -1) -> str:
    loc = (tmp_ch, tmp_rl)
    if loc >= (9, 76):
        _a = 1
    if not html_text or html_text == BLANK_RULE:
        return "" if tmp_rl == 0 else BLANK_RULE

    # assert count <(p|a|ol|ul|li|em|strong|sup) == count <[a-zA-Z]
    text = (
        " ".join(html_text.replace("\n", "").split())  # normalise whitespace
        .replace("‘", "'").replace("’", "'")  # curly single quotes
        .replace('“', '"').replace('”', '"')  # curly double quotes
        .replace("–", "--")  # en dash
        .replace("½", " 1/2").replace("¾", " 3/4")  # unicode fractions
        .replace(" <sup>sv</sup>", " :sup:`sv`").replace("<sup>sv</sup>", r"\ :sup:`sv`")  # scottish variations
        .replace(" <sup>SV</sup>", " :sup:`SV`")  # e.g. 5.45(b)
        .replace("<em><sup>SV</sup></em>", r"\ :sup:`SV`")  # e.g. 5.35(a)(vii)
        .replace("<sup>th</sup>", r"\ :sup:`th`")  # e.g. 4.44(f)(iv)
    )

    # clear empty elements
    text = (
        text.replace("<p> </p>", "")
        .replace("<strong> </strong>", "").replace("<em> </em>", "")
        .replace("<u></u>", "").replace("<span></span>", "")
    )

    # strong and emphasis
    text = (
        text.replace("<strong><br /></strong>", "<br />").replace("<em><br /></em>", "<br />")
        .replace("<strong>. </strong>", ". ")  # 4.25(f)(v) special case
        .replace("<em><u>.</u></em>", ". ")  # 9.4(b) special case
        .replace("<em>.</em>", ". ")  # 9.80(a) special case
        .replace("</em><em>", "").replace("</strong><strong>", "")
        .replace("<strong><br />", "<br /><strong>").replace("<br /></strong>", "</strong><br />")
        .replace("<em><br />", "<br /><em>").replace("<br /></em>", "</em><br />")
        # run twice to catch extra tags (e.g. 3.6(a,b,c,d,e))
        .replace("<strong><br />", "<br /><strong>").replace("<br /></strong>", "</strong><br />")
        .replace("<em><br />", "<br /><em>").replace("<br /></em>", "</em><br />")
    )
    text = STRONG.sub(r"\g<open>**\g<close>", text)
    text = EMPH.sub(r"\g<open>*\g<close>", text)
    text = text.replace(" :sup:`sv`**", "** :sup:`sv`")  # can't have nested markup :(
    text = text.replace("*(*", "(")

    # hyperlinks
    text = text.replace('<a href="https://members.scouts.org.uk/fs120013"> <span><u><a href="https://www.scouts.org.uk/volunteers/running-your-section/programme-guidance/general-activity-guidance/joint-activities-with-other-organisations-except-girlguiding/">FS120013 Joint Activities with other organisations</a></u></span>.</a>', ' <a href="https://www.scouts.org.uk/volunteers/running-your-section/programme-guidance/general-activity-guidance/joint-activities-with-other-organisations-except-girlguiding/">FS120013 Joint Activities with other organisations</a>')  # arrrrghhhhh!
    text = NO_TEXT_LINK.sub(r"\1", text)  # orphan links with no visible text
    text = LINK.sub(r"\2`\3 &lt\1&gt`__\4", text)  # don't use < and > as we split on these later

    # all tags to be removed must be explicitly listed
    text = JUNK_TAGS.sub("", text)

    # lists
    text = "\n".join(_parse_html_list(tag) for tag in html.fragments_fromstring(text))
    text = LIST_ITEM.sub("", text)

    text = (
        # <p> tags
        PARA.sub("\n\n", text)
        .replace(" \n*", " *").replace(" \n\n*", " *")
        # replace with real values
        .replace("&amp;", "&").replace("&lt", "<").replace("&gt", ">")
        # deal with line breaks
        .replace("<br />", "\n")
        .replace("<br>", "\n")  # lxml 'normalises' br tags to without the closing slash
    )
    # deal with newlines
    return NEWLINE.sub("\n\n", text).strip("\n")


def _parse_html_list(tag: html.HtmlElement, indent_by: int = 0) -> str:
    name = tag.tag
    if name not in {"ol", "ul", "li"}:
        return _stringify_element(tag)

    # ordered list
    if name == "ol":
        ordered = True
        list_type = "arabic"
        if "list-style-type: lower-alpha" in tag.get("style", "") or tag.get("type") == "a":
            list_type = "alpha"
        elif "list-style-type: lower-roman" in tag.get("style", "") or tag.get("type") == "i":
            list_type = "roman"

    # unordered list
    elif name == "ul":
        ordered = False
        list_type = "disc"
        if "list-style-type: none" in tag.get("style", ""):
            # list_type = "none"
            raise Exception()  # none list doesnt render in rest. flag locations

    # list items
    else:
        raise ValueError("can't have raw li tags!")

    count = 0
    parsed = [""]  # nested lists must be separated by blank lines

    indent = " " * indent_by  # three spaces per level, ignoring first level

    for el in tag:
        list_char = f"{TYPES_CHARS[list_type][count if ordered else 0] + '.' * ordered + ' ': <3}"
        line_prefix = indent + list_char
        new_indent = len(line_prefix)
        line_prefix_no_number = " " * new_indent
        count += 1

        if el.text:
            parsed.append(line_prefix + el.text.strip())
            line_prefix = line_prefix_no_number
        for sub in el:
            if sub.tag in {"ol", "ul"}:
                # nested list must be separated by blank lines
                parsed += ["", _parse_html_list(sub, indent_by=new_indent), ""]
            elif sub.tag == "br":
                parsed.append("<br />")
            elif sub.tag == "p":
                parsed.append("")
                if sub.text:
                    parsed.append(line_prefix + sub.text)
                    line_prefix = line_prefix_no_number
                if sub_subs := "".join(_stringify_element(sub_sub) for sub_sub in sub):
                    parsed.append(line_prefix + sub_subs)
                    line_prefix = line_prefix_no_number
                if sub.tail:
                    parsed.append(line_prefix + sub.tail)
                    line_prefix = line_prefix_no_number
                parsed.append("")
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
    html_text = html.tostring(el.__copy__(), encoding="unicode").rstrip("\n").strip()
    if el.tail and html_text.endswith(f"{el.tail}\n{el.tail}"):
        return html_text.removesuffix(f"\n{el.tail}")
    return html_text


if __name__ == '__main__':
    from pathlib import Path

    # import requests

    # Path("overview-raw.txt").write_text(requests.get("https://www.scouts.org.uk/por/").content.decode("utf-8"), encoding="utf-8")

    # with open("overview-raw.txt", "r", encoding="utf-8") as f:
    #     r_text = f.read()
    # pdf_link = html.document_fromstring(r_text).find(".//main")[0][0][0][-1][0].get("href")
    # por_state = _get_state_data(r_text)
    # por_index = por_state["index"]
    # por_intro = por_state["intro"]

    # links = [item["url"] for item in por_index]
    # for i, link in enumerate(links):
    #     if i == 0 or i == len(links) - 1:
    #         continue  # skip intro and TAP
    #     p = Path(f"ch{i}-raw.txt")
    #     p.write_text(requests.get("https://www.scouts.org.uk" + link).content.decode("utf-8"), encoding="utf-8")

    # chapters = [*range(1, 15+1)]
    chapters = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    for i in chapters:
        raw = Path(f"ch{i}-raw.txt").read_text(encoding="utf-8")
        exp = Path(f"chapter-{i}.exp.rst")  # expected
        out = chapter_text(raw, tmp_ch=i)
        if exp.is_file():
            assert exp.read_text(encoding="utf-8") == out, f"Chapter {i} not equal!"
        Path(f"chapter-{i}.rst").write_text(out, encoding="utf-8")
        rst_source = out
        # rst_source = Path(f"chapter-{i}.rst").read_text(encoding="utf-8")
        Path(f"chapter-{i}.html").write_text(
            publish_string(
                source=rst_source,
                writer_name="html5",
                settings_overrides={"stylesheet_path": "por.css"},  # , "embed_stylesheet": False
            ).decode("utf-8"),
            encoding="utf-8"
        )


# TODO POR typos:
#   ch1 scout promise (extra closing paren)
#   ch1 1.1 (item b used twice)
#   ch2 dev pol (between para 1&2 only has one line break)
#   ch2 dev pol (operations committee)
#   ch2 eq opps (no space before 3.11b link)
#   ch2 eq opps (reasonable adjs -> members area is dead)
#   ch2 eq opps (leaders -> Rule 2 (outdated?))
#   ch2 2.5 (bold enumerated items aren't a list)
#   3.9 (double rule 3.9(l))
#   3.11/12 (types of group should be a Rule)
#   3.17(b) (random 'Sponsored Scout Groups.')
#   3.19(a) (form C2)
#   3.23(b)(iv)(2,3) (subCommittee)
#   3.23(3,4) (should be c,d no?)
#   3.42(a)(i) (maintaining comms - extra line breaks)
#   3.42(a)(i) (nominating the chair - extra line breaks)
#   3.42(b)(i) (a deputy - extra line breaks)
#   3.42(d)(i) (the section leader - extra line breaks)
#   4.1(q/r) (Associate Members too indented)
#   4.5(b) extra line break of the annual census
#   4.9(b) (A, B should be sub-bullets)
#   4.11(i) (activity should have em dash)
#   4.25 (bullets & indentation generally)
#   4.26(c) extra line break (For \n example)
#   4.37(e) (closing paren before sub list)
#   4.44(e) (section ADCs don't include the word "support")
#   4.64(f) extra line break (Committee \n requesting)
#   4.64(f) extra line break (Membership \n Subscription)
#   5.1(p/q) (Associate Members too indented)
#   5.9(i) (activity should have em dash)
#   5.16 (bullets & indentation generally)
#   9.1(f) (please refer to... needs an indent)
#   9.56(c/d/e) (not part of list)

# FIXME not fixable through automatic parser:
#   --- use line block syntax:
#   ch1 scout promise (line breaks in promise not showing)
#   ch1 cub scout promise (line breaks in promise not showing)
#   ch1 cub scout law (line breaks in promise not showing)
#   ch1 beaver scout promise (line breaks in promise not showing)
#   ch1 1.1 (line breaks in promise/laws not showing)
#   --- add manual line break
#   ch2 religious (extra line break after bold)
#   ch6 membership council (line breaks nominated, elected)
#   ch6 membership board (line breaks elected/youth/appointed/attending/right)
#   ch6 national leaders (extra line break after bold)
#   ch6 headquarters (extra line break after bold)
#   ch6 nations (extra line break after bold)
#   3.23(a)(i) (needs a newline after ex officio)
#   --- make bullets sane
#   3.23 all the bullets, generally. e.g. (a)(i) isn't a new list but a literal `i.`
#   4.25 ditto
#   5.16 ditto
#   4.45(c) the sub list is completely detached
#   --- update docutils transformer code for compact lists
#   4.1(a) - <p> tags used, don't need them
#   --- nested inline markup
#   4.25(e/f/i) can't have nested markup (sup inside bold)
#   <u> tags - links etc, chapter 9 (so many (50+) examples in chapter 9)
#   emphasis inside links / vice versa (lots of examples in chapter 9)
#   --- add manual unity callout link thing
#   8.1(e) unity "call to action" box
#   10.20, 10."Uniform Diagrams" -- link to PDF etc, or transclude
#   11.5(i) good service awards "call to action" box


# TODO snags:
#   ---

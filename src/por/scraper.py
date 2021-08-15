from __future__ import annotations

from collections.abc import Iterator
import json
import re

from lxml import html

BLANK_RULE = "BLANK RULE DUMMY"

ALPHA = "abcdefghijklmnopqrstuvwxyz"
ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xiv")

TYPES_CHARS = {
    "arabic": tuple(str(i) for i in range(1, 26)),  # 100 item list is a bit much
    "alpha": ALPHA,
    "roman": ROMAN,
    "disc": "*",
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
    # e.g. 14.7 has multiple rows
    row_controls = (row["areas"][0]["controls"] for row in rows)
    values = (control["value"] for row in row_controls for control in row)
    return title, "".join(value for value in values if isinstance(value, str))


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
    if loc >= (16, 24):
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
    text = text.replace("UK00000922043&gt`__", "UK00000922043&gt`__ ")  # 14.7

    # all tags to be removed must be explicitly listed
    text = JUNK_TAGS.sub("", text)

    # heading four
    text = re.sub("<h4>(.*?)</h4>", lambda match: f"{match[1]}\n{'~'*len(match[1])}", text)

    # lists
    text = "\n".join(_parse_html_constructs(tag) for tag in html.fragments_fromstring(text))
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
    if tmp_ch == 1:
        text = (
            # scout promise
            text.replace("On my honour,", "| On my honour,")
            .replace("\nI promise that", "\n| I promise that")
            .replace("\nto do", "\n| to do")
            .replace("\nto help", "\n| to help")
            .replace("\nand to", "\n| and to")
            # cub law
            .replace("Cub Scouts", "| Cub Scouts")
            .replace("think of", "| think of")
            .replace("and do a", "| and do a")
            # beaver promise
            .replace("I promise to do my best\n", "| I promise to do my best\n")
            .replace("\nto be", "\n| to be")
            # atheist scout promise
            .replace("to uphold", "| to uphold")
            # buddhist scout promise
            .replace("to seek", "| to seek")
            .replace("\nto act ", "\n| to act ")
            # hindu scout promise
            .replace("to follow", "| to follow")
            # muslim scout promise
            .replace("In the name", "| In the name")
        )
    if tmp_ch == 16:
        text = (
            text.replace("in-the-scout-county-sv/>`__ |", "in-the-scout-county-sv/>`__                                     |")
            .replace(", UK Headquarters respectively). |", ", UK Headquarters respectively).                 |")
            .replace("both in membership and actions]. |", "both in membership and actions].                     |")
            .replace(f"policy/>`__.{' '*257}|", f"policy/>`__.{' '*269}|")
            .replace("#5.19>`__ | Yes", "#5.19>`__             | Yes")
            .replace("enquiry.**", "enquiry.** ").replace("#5.19>`__ ", "#5.19>`__")
            .replace("Panel**", "Panel** ").replace("its recommendation. ", "its recommendation.")
            .replace("`__**)* **EXCLUSION -- NO APPEAL** |", "`__**)* **EXCLUSION -- NO APPEAL**             |")
            .replace("civil courts.**EXCLUSION -- NO APPEAL** |", "civil courts.**EXCLUSION -- NO APPEAL**     |")
        )
    # deal with newlines
    return NEWLINE.sub("\n\n", text).strip("\n")


def _parse_html_constructs(tag: html.HtmlElement) -> str:
    name = tag.tag
    if name in {"ol", "ul", "li"}:
        return _parse_html_list(tag)
    if name == "table":
        return _parse_html_table(tag)
    return _stringify_element(tag)


def _parse_html_list(tag: html.HtmlElement, indent_by: int = 0) -> str:
    name = tag.tag

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
            raise Exception()  # none list doesnt render in rest. flag locations

    # list items
    else:
        raise ValueError(f"can't have raw {name} tags!")

    count = 0
    parsed = [""]  # nested lists must be separated by blank lines

    indent = " " * indent_by  # three spaces per level, ignoring first level

    for el in tag:
        list_char = f"{TYPES_CHARS[list_type][count if ordered else 0] + '.' * ordered + ' ': <3}"
        line_prefixes = _line_prefix_generator(indent + list_char)
        new_indent = indent_by + len(list_char)
        count += 1

        if el.text:
            parsed.append(next(line_prefixes) + el.text.strip())
        for sub in el:
            if sub.tag in {"ol", "ul"}:
                # nested list must be separated by blank lines
                parsed += ["", _parse_html_list(sub, indent_by=new_indent), ""]
            elif sub.tag == "br":
                parsed.append("<br />")
            elif sub.tag == "p":
                parsed.append("")
                if sub.text:
                    parsed.append(next(line_prefixes) + sub.text)
                if sub_subs := "".join(_stringify_element(sub_sub) for sub_sub in sub):
                    parsed.append(next(line_prefixes) + sub_subs)
                if sub.tail:
                    parsed.append(next(line_prefixes) + sub.tail)
                parsed.append("")
            else:
                parsed.append(next(line_prefixes) + _stringify_element(sub))
            if sub.tail:
                parsed.append(next(line_prefixes) + sub.tail.strip())
        if el.tail:
            parsed.append(next(line_prefixes) + el.tail)

    parsed += [""]  # nested lists must be separated by blank lines
    return "\n".join(parsed)


def _stringify_element(el: html.HtmlElement) -> str:
    # .__copy__() fixes bug with text serialisation (tostring otherwise prints the entire document)
    html_text = html.tostring(el.__copy__(), encoding="unicode").rstrip("\n").strip()
    if el.tail and html_text.endswith(f"{el.tail}\n{el.tail}"):
        return html_text.removesuffix(f"\n{el.tail}")
    return html_text


def _line_prefix_generator(line_prefix: str) -> Iterator[str]:
    line_prefix_no_number = " " * len(line_prefix)
    yield line_prefix
    while True:
        yield line_prefix_no_number


def _parse_html_table(tag: html.HtmlElement) -> str:
    if len(tag) != 1 or tag[0].tag != "tbody":
        raise NotImplementedError("only implemented single tbody case")

    tbody = tag[0]
    rows = [*tbody]
    has_headers = rows[0][0].tag == "th"
    num_columns = len(rows[0])
    if has_headers:
        headers = [c.text_content() for c in rows[0]]
        body_rows = rows[1:]
    else:
        headers = []
        body_rows = rows

    result: list[list[str | None]] = [[None] * num_columns for _ in range(len(body_rows))]
    for row_num, row in enumerate(body_rows):
        for col_num, cell in enumerate(row):
            cell_text = str(cell.text_content())
            col_span = int(cell.get("colspan", 1))
            while result[row_num][col_num] is not None:
                col_num += 1
            for i in range(row_num, row_num + int(cell.get("rowspan", 1))):
                for j in range(col_num, col_num + col_span):
                    result[i][j] = cell_text

    if has_headers:
        column_max_lengths = [max(len(row[col_num]) for row in (headers, *result)) for col_num in range(num_columns)]
    else:
        column_max_lengths = [max(len(row[col_num]) for row in result) for col_num in range(num_columns)]

    sep_row = "+" + "+".join("-" * (col_length + 2) for col_length in column_max_lengths) + "+\n"
    table_str = "\n\n" + sep_row

    if has_headers:
        sep_row_header = sep_row.replace("-", "=")
        table_str += "|" + "|".join(f" {cell_text: <{col_length}} " for cell_text, col_length in zip(headers, column_max_lengths)) + "|\n" + sep_row_header

    for row_num, row in enumerate(result):
        table_str += "|" + "|".join(f" {cell_text: <{col_length}} " for cell_text, col_length in zip(row, column_max_lengths)) + "|\n" + sep_row

    return table_str + "\n\n"


if __name__ == '__main__':
    from pathlib import Path

    # import requests

    # Path("unprocessed/overview-raw.txt").write_text(requests.get("https://www.scouts.org.uk/por/").content.decode("utf-8"), encoding="utf-8")

    # Path(f"unprocessed/overview-raw.txt").read_text(encoding="utf-8")
    # pdf_link = html.document_fromstring(r_text).find(".//main")[0][0][0][-1][0].get("href")
    # por_state = _get_state_data(r_text)
    # por_index = por_state["index"]
    # por_intro = por_state["intro"]

    # links = [item["url"] for item in por_index]
    # for i, link in enumerate(links):
    #     p = Path(f"unprocessed/ch{i}-raw.txt")
    #     p.write_text(requests.get("https://www.scouts.org.uk" + link).content.decode("utf-8"), encoding="utf-8")

    # chapters = [*range(1, 15+1)]
    chapters = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
    for i in chapters:
        print(f"Processing Chapter {i}")
        raw = Path(f"ch{i}-raw.txt").read_text(encoding="utf-8")
        exp = Path(f"expected/chapter-{i}.exp.rst")  # expected
        out = chapter_text(raw, tmp_ch=i)
        if exp.is_file():
            assert exp.read_text(encoding="utf-8") == out, f"Chapter {i} not equal!"
        Path(f"chapter-{i}.rst").write_text(out, encoding="utf-8")


# FIXME not fixable through automatic parser:
#   --- add manual line break
#   ch2 religious (extra line break after bold)
#   ch6 membership council (line breaks nominated, elected)
#   ch6 membership board (line breaks elected/youth/appointed/attending/right)
#   ch6 national leaders (extra line break after bold)
#   ch6 headquarters (extra line break after bold)
#   ch6 nations (extra line break after bold)
#   3.23(a)(i) (needs a newline after ex officio)
#   14.7(e) nations email addresses
#   --- make bullets sane
#   3.23 all the bullets, generally. e.g. (a)(i) isn't a new list but a literal `i.`
#   4.25 ditto
#   5.16 ditto
#   4.45(c) the sub list is completely detached
#   14.7(d,e) are numbered as (a,b)
#   15.2(d-l) are numbered as (a-i)
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
#   --- add images
#   14.7 protected mark images
#   --- backslash escape
#   15.2 "* Note that the ..." should be a literal asterisk
#   --- fix tables
#   15.2 rowspans don't propagate

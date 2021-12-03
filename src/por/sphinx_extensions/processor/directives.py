from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
from sphinx.util import logging

from por.sphinx_extensions.processor.utils import scottish_variations

if TYPE_CHECKING:
    from sphinx.domains.std import StandardDomain

logger = logging.getLogger("por.directives")


class BlankPart(Directive):
    option_spec = {"add_training_note": directives.flag}

    def run(self):
        if "add_training_note" in self.options:
            return [nodes.emphasis("", f"This rule is intentionally left blank. All adult training requirements are detailed in "),
                    nodes.Text("POR: The Appointment Process")]
        return [nodes.emphasis("", "This rule is intentionally left blank.")]


class FauxHeading:
    """A heading level that is not defined by a string. We need this to work with
    `docutils.parsers.rst.states.RSTState.check_subsection`.

    The important thing is the length can vary, but it is equal to any FauxHeading.
    """

    def __init__(self, length):
        self.length = length

    def __len__(self):
        return self.length

    def __eq__(self, other):
        return isinstance(other, FauxHeading) or other == "-"


class Rule(Directive):
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "blank": directives.flag,  # blank rule
        "unnumbered": directives.flag,  # unnumbered rule
        "sv": directives.unchanged,  # Scottish variation
    }

    def run(self):
        doc_name = Path(self.state.document["source"]).stem
        chapter_name = doc_name.removeprefix("chapter-")

        # running per-document rule number incrementer. Also store line number
        # as each rule directive seemingly gets processed multiple times
        rule_num, line_num = self.state.document.get("rule_number", (0, -1))
        if line_num != self.state_machine.abs_line_number() and "unnumbered" not in self.options:
            rule_num += 1
            self.state.document["rule_number"] = rule_num, self.state_machine.abs_line_number()

        if "unnumbered" in self.options:
            rule_title = self.arguments[0]
            id_text = nodes.make_id(self.arguments[0])
            rule_num = 0
        elif "blank" in self.options:
            rule_title = f"Rule {int(chapter_name)}.{rule_num}"
            id_text = f"{int(chapter_name)}.{rule_num}"
        elif chapter_name.isdigit():
            rule_title = f"Rule {int(chapter_name)}.{rule_num} {self.arguments[0]}"
            id_text = f"{int(chapter_name)}.{rule_num}"
        else:  # TAP (no rule references in the introduction
            rule_title = f"Rule {rule_num} {self.arguments[0]}"
            id_text = f"{rule_num}"

        block_length = 1 + len(self.options)
        messages = []

        # # Parse the body of the directive
        # if self.has_content and len(self.content):
        #     section_body = nodes.container()
        #     block_length += util.nested_parse_with_titles(self.state, self.content, section_body)
        #     messages.append(section_body)

        # keeping track of the level seems to be required if we want to allow
        # nested content. See `docutils.parsers.rst.states.RSTState.new_subsection`
        original_level = self.state.memo.section_level
        self.state.section(
            title=rule_title,
            source="",
            style=FauxHeading(block_length),
            lineno=self.state_machine.abs_line_number(),
            messages=messages,
        )
        self.state.memo.section_level = original_level

        if self.options == {} and self.arguments == []:
            return []

        new_section = self.state.parent.children[-1]  # get last (newly added) section

        if self.options.keys() & {"blank", "sv"}:
            title_node = new_section[0]

            # Handle blank rules
            if "blank" in self.options:
                title_node += nodes.Text(" "), nodes.emphasis("", "This rule is intentionally left blank", classes=["blank-rule"])

            # Handle Scottish variations
            if "sv" in self.options:
                title_node += scottish_variations.node_from_target(self.options["sv"])

        # (re)set section id / anchor
        for key in new_section["names"]:
            self.state.document.nameids.pop(key, None)  # clear old name-id associations
        new_section["names"] = [id_text]
        for key in new_section["ids"]:
            self.state.document.ids.pop(key, None)  # clear old ids
        new_section["ids"] = [id_text]
        self.state.document.ids[id_text] = new_section
        self.state.document.set_name_id_map(new_section, id_text, new_section, explicit=None)

        # add label
        if self.arguments:  # no point doing this if no rule title
            domain: StandardDomain = self.state.document.settings.env.domains["std"]  # type: ignore[assignment]
            label_id = new_section["ids"][0]
            name = "-".join(f"{chapter_name}:{self.arguments[0]}".lower().split())  # normalise spacing

            if name in domain.labels:
                other_doc = self.state.document.settings.env.doc2path(domain.labels[name][0])
                logger.warning(
                    f"duplicate label {name}, other instance in {other_doc}",
                    location=new_section,
                    type="create_rule_labels",
                    subtype=doc_name,
                )

            domain.anonlabels[name] = doc_name, label_id
            domain.labels[name] = doc_name, label_id, str(rule_num or "")

        return []

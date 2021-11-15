from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from sphinx import addnodes
from sphinx.util.docutils import ReferenceRole
from sphinx.errors import SphinxError
from sphinx.util import logging
# from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    from docutils.parsers.rst.states import Inliner

logger = logging.getLogger("por.roles")

POR_URL_TEMPLATE = ""
SCOTTISH_POR_URL = "https://www.scouts.scot/media/2504/scottish-variations-from-the-september-2021-edition-of-the-policy.pdf"


class RuleReference(ReferenceRole):
    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        # create the reference node
        node = addnodes.pending_xref(
            "",
            nodes.Text(self.text),
            refdoc=self.env.docname,
            reftype="rule",
            refwarn=True,
            reftarget="-".join(":".join(self.text.split("!", 2)[:2]).lower().split()),
        )
        self.set_source_info(node)

        return [node], []


class ChapterReference(ReferenceRole):
    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        # determine the target and title for the class. Assumes a flat structure.
        if self.title == "POR-TAP":
            doc_to = "chapter-16"
            link_text = "POR: The Appointment Process"
        elif self.title.isdigit():
            doc_to = f"chapter-{int(self.title)}"
            link_text = f"Chapter {int(self.title)}"  # clean_astext(env.titles[docname])
        else:
            doc_to = self.target
            link_text = f"Chapter {self.title}"

        if doc_to not in self.env.all_docs:
            return [nodes.Text(link_text)], []

        # create the reference node
        doc_from = self.env.docname
        return [nodes.reference('', link_text, internal=True, refuri=self.env.app.builder.get_relative_uri(doc_from, doc_to))], []


def scottish_variations_role(
        _name: str,
        _rawtext: str,
        text: str,
        _lineno: int,
        _inliner: Inliner,
        _options: dict = {},
        _content: list[str] = [],
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    # TODO delete previous space
    return [nodes.superscript("", "", nodes.reference("", "sv", refuri=SCOTTISH_POR_URL + text))], []


def table_role(
    _name: str,
    _rawtext: str,
    text: str,
    _lineno: int,
    _inliner: Inliner,
    _options: dict = {},
    _content: list[str] = [],
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    return [nodes.Text(f"Table {text}")], []


# class Substitutions(SphinxTransform):
#     # run between Sphinx and default substitutions
#     default_priority = 211
#
#     def apply(self, **_kwargs) -> None:
#         for ref in self.document.traverse(nodes.substitution_reference):
#             if ref["refname"] == "sv":
#                 ref.replace_self(nodes.superscript("", "sv"))

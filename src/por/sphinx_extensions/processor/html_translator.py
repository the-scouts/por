from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
import sphinx.writers.html5 as html5


class PORTranslator(html5.HTML5Translator):
    """Custom RST -> HTML translation rules."""

    @staticmethod
    def should_be_compact_paragraph(node: nodes.paragraph) -> bool:
        """Check if paragraph should be compact.

        Omitting <p/> tags around paragraph nodes gives visually compact lists.

        """
        # Never compact paragraphs that are children of document or compound.
        if isinstance(node.parent, (nodes.document, nodes.compound)):
            return False

        # Only first paragraph can be compact (ignoring initial label & invisible nodes)
        first = isinstance(node.parent[0], nodes.label)
        visible_siblings = [child for child in node.parent.children[first:] if not isinstance(child, nodes.Invisible)]
        if visible_siblings[0] is not node:
            return False

        # otherwise, the paragraph should be compact
        return True

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        """Remove <p> tags if possible."""
        if self.should_be_compact_paragraph(node):
            self.context.append("")
        else:
            self.body.append(self.starttag(node, "p", ""))
            self.context.append("</p>\n")

    def depart_paragraph(self, _: nodes.paragraph) -> None:
        """Add corresponding end tag from `visit_paragraph`."""
        self.body.append(self.context.pop())

    def visit_newline_marker(self, node: nodes.Element):
        # newline_marker is defined in custom_nodes.py
        if isinstance(node.parent.parent, nodes.section):
            self.body.append("<br/>")
        else:
            self.body.append(node.astext())  # sidebar contents
        raise nodes.SkipDeparture

    def unknown_visit(self, node: nodes.Node) -> None:
        """No processing for unknown node types."""
        pass

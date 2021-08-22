from __future__ import annotations

from docutils import nodes
from docutils import transforms


class Contents(transforms.Transform):
    """Add TOC placeholder and horizontal rule after title and headers."""

    # Use same priority as docutils.transforms.Contents
    default_priority = 380

    def apply(self) -> None:
        # POR's introduction doesn't have a contents table
        if "chapter" not in self.document["source"]:
            return

        # Create the contents placeholder section
        title = nodes.title("", "", nodes.Text("Chapter Contents"))
        contents_section = nodes.section("", title, names=["contents"])
        self.document.note_implicit_target(contents_section)

        # Add a table of contents builder
        pending = nodes.pending(_ContentsTransform)
        contents_section += pending
        self.document.note_pending(pending)

        # Insert the toc and a horizontal rule after chapter title
        document_nodes = self.document.children[0]
        self.document.children[0][:] = document_nodes[:1] + [contents_section, nodes.transition()] + document_nodes[1:]


class _ContentsTransform(transforms.Transform):
    """Build Table of Contents from document.

    This transform generates a table of contents from the entire document tree.
    Taking titles from `section` nodes, a nested bullet list is created within
    a newly created section entitled "Chapter Contents".

    This transform requires a startnode, which provides the location for the
    generated table of contents and is replaced by the contents section.

    """
    default_priority = 720

    def apply(self) -> None:
        contents = _build_contents(self.document.children[0][3:])  # skip title, contents, and horizontal rule
        if contents:
            self.startnode.replace_self(contents)
        else:
            # if no contents, remove the empty placeholder
            self.startnode.parent.parent.remove(self.startnode.parent)


def _build_contents(node: nodes.Node | list[nodes.Node]) -> nodes.bullet_list | list:
    entries = []
    children = getattr(node, "children", node)

    for section in children:
        if not isinstance(section, nodes.section):
            continue

        title = section[0]
        section_anchor_uri = section['ids'][0]
        title["refid"] = section_anchor_uri  # Add a link to self
        reference = nodes.reference("", "", nodes.Text(title.astext()), refid=section_anchor_uri)

        item = nodes.list_item("", nodes.paragraph("", "", reference))
        item += _build_contents(section)  # recurse to add sub-sections
        entries.append(item)
    if entries:
        return nodes.bullet_list("", *entries)
    return []

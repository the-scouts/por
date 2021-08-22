from pathlib import Path

from docutils import nodes
from docutils import transforms
from docutils import utils
from docutils.parsers.rst import roles
from docutils.parsers.rst import states


class Title(transforms.Transform):
    """Add title and organise document hierarchy."""

    # needs to run before docutils.transforms.frontmatter.DocInfo
    default_priority = 335

    def apply(self) -> None:
        if not isinstance(self.document[0], nodes.field_list):
            return

        header_details = {}

        # Iterate through the header fields, which are the first section of the document
        for field in self.document[0]:
            # Hold details of the attribute's tag against its details
            header_details[field[0].rawsource.strip()] = field[1].rawsource.strip()

        # Create the title string for the chapter
        chapter_raw = header_details["Chapter"]
        title_raw = header_details["Title"]
        try:
            title_text = f"Chapter {int(chapter_raw)} -- {title_raw}"
            # title_text_nodes = [nodes.inline("", f"Chapter {int(chapter_raw)}"), nodes.inline("", title_raw)]
        except ValueError:
            # title_text_nodes = [nodes.inline("", title_raw)]
            title_text = title_raw

        # Generate the title section node and its properties
        title_node = nodes.section("", nodes.title("", title_text), names=["chapter"])

        # Insert the title node as the root element, move children down
        document_children = self.document.children[1:]  # skip field_list
        self.document.children = [title_node]
        title_node.extend(document_children)
        self.document.note_implicit_target(title_node, title_node)

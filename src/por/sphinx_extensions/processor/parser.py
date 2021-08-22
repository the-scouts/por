from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx import parsers

from por.sphinx_extensions.processor.transforms import contents
from por.sphinx_extensions.processor.transforms import title

if TYPE_CHECKING:
    from docutils import transforms


class PORParser(parsers.RSTParser):
    """RST parser with custom transforms."""

    supported = "por",  # for source_suffix in conf.py

    def get_transforms(self) -> list[type[transforms.Transform]]:
        """Use our custom transform rules."""
        return [
            contents.Contents,
            title.Title,
        ]

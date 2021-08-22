"""Sphinx extensions for performant POR processing"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.environment import BuildEnvironment

from por.sphinx_extensions.processor import html_translator
from por.sphinx_extensions.processor import parser
from por.sphinx_extensions.processor import roles

if TYPE_CHECKING:
    from sphinx.application import Sphinx

# Monkeypatch sphinx.environment.BuildEnvironment.collect_relations, as it takes a long time
# and we don't use the parent/next/prev functionality
BuildEnvironment.collect_relations = lambda self: {}


def setup(app: Sphinx) -> dict[str, bool]:
    """Initialize Sphinx extension."""

    # Register plugin logic
    app.add_source_parser(parser.PORParser)  # Add transforms
    app.add_role("rule", roles.RuleReference())  # Transform POR rule references to links
    app.set_translator("html", html_translator.PORTranslator)  # Docutils Node Visitor overrides (html builder)

    # Parallel safety: https://www.sphinx-doc.org/en/master/extdev/index.html#extension-metadata
    return {"parallel_read_safe": True, "parallel_write_safe": True}

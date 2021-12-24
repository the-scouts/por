"""Sphinx extensions for performant POR processing"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docutils.parsers.rst import states
from docutils.parsers.rst.states import Inliner
from docutils import nodes
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment import BuildEnvironment

from por.sphinx_extensions.processor import directives
from por.sphinx_extensions.processor import html_builder
from por.sphinx_extensions.processor import html_translator
from por.sphinx_extensions.processor import parser
from por.sphinx_extensions.processor import roles
from por.sphinx_extensions.processor.transforms import rule_references

if TYPE_CHECKING:
    from sphinx.application import Sphinx

# Monkeypatch sphinx.environment.BuildEnvironment.collect_relations, as it takes a long time
# and we don't use the parent/next/prev functionality
BuildEnvironment.collect_relations = lambda self: {}

# Monkeypatch sphinx.builders.html.StandaloneHTMLBuilder.create_pygments_style_file, as we
# do not use pygments
StandaloneHTMLBuilder.create_pygments_style_file = lambda self: None


# Enable strong emphasis by monkeypatching a bunch of things.
def strong_emphasis_node(_raw_source, text):
    return nodes.strong("", "", nodes.emphasis("", text))


def strong_emphasis(self, match, lineno):
    before, inlines, remaining, sysmessages, endstring = self.inline_obj(match, lineno, pat_strong_emphasis, strong_emphasis_node)
    return before, inlines, remaining, sysmessages


def build_regexp_override(definition, compile=True):
    if definition[0] == "start":
        definition[3].insert(0, r"\*\*\*")
    return _orig_build_regexp(definition, compile)


pat_strong_emphasis = re.compile(r'(?<![\s\x00])(\*\*\*)')
Inliner.dispatch["***"] = strong_emphasis  # type: ignore[assignment]
_orig_build_regexp = states.build_regexp
states.build_regexp = build_regexp_override


def setup(app: Sphinx) -> dict[str, bool]:
    """Initialize Sphinx extension."""

    # Register plugin logic
    app.add_builder(html_builder.FileBuilder, override=True)
    app.add_builder(html_builder.DirectoryBuilder, override=True)
    app.add_source_parser(parser.PORParser)  # Add transforms
    app.add_role("rule", roles.RuleReference())  # Transform POR rule references to links
    app.add_role("sv", roles.scottish_variations_role)  # Scottish variations
    app.add_role("chapter", roles.ChapterReference())  # Chapter
    app.add_role("table", roles.table_role)  # Table
    app.add_directive('body_blank', directives.BlankPart)  # Blank rule
    app.add_directive("rule", directives.Rule)  # Rule directive
    # app.add_transform(roles.Substitutions)  # Custom substitutions

    app.add_post_transform(rule_references.RulesResolver)

    app.set_translator("html", html_translator.PORTranslator)  # Docutils Node Visitor overrides (html builder)
    app.set_translator("dirhtml", html_translator.PORTranslator)  # Docutils Node Visitor overrides (dirhtml builder)

    # Parallel safety: https://www.sphinx-doc.org/en/master/extdev/index.html#extension-metadata
    return {"parallel_read_safe": True, "parallel_write_safe": True}

# TODO 'this chapter' references
# TODO scottish variation -- link to page/sections
# TODO flexbox or something rendering for images (14.7)

# TODO left hand ToC to be accordian of all chapters

# For custom inline roles and directives:
# https://gdal.org/contributing/rst_style.html
# https://github.com/OSGeo/gdal/tree/master/doc/source/_extensions

# TODO term / definition referencing
# https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html#role-term
# https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html#role-dfn

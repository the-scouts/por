from __future__ import annotations

from pathlib import Path

from docutils.core import publish_string
from sphinx.application import Sphinx

PUBLISH_SETTINGS = {
    "stylesheet_path": "por.css",
    "input_encoding": "unicode",
    "output_encoding": "unicode",
    # "embed_stylesheet": False,
}


def render_docutils() -> None:
    for chapter in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16):
        print(f"Processing Chapter {chapter}")
        rst_source = Path(f"sphinx_source/chapter-{chapter}.rst").read_text(encoding="utf-8")
        out_path = Path(f"rendered/chapter-{chapter}.html")

        rendered_html = publish_string(source=rst_source, writer_name="html5", settings_overrides=PUBLISH_SETTINGS)
        out_path.write_text(rendered_html, encoding="utf-8")


def render_sphinx() -> None:
    root_directory = Path().absolute()
    source_directory = root_directory / "sphinx_source"
    conf_directory = root_directory
    build_directory = root_directory / "build"  # synchronise with deploy-gh-pages.yaml -> deploy step
    doctree_directory = build_directory / ".doctrees"

    # builder configuration
    sphinx_builder = "html"
    # sphinx_builder = "linkcheck"

    app = Sphinx(
        source_directory.as_posix(),
        confdir=conf_directory.as_posix(),
        outdir=build_directory.as_posix(),
        doctreedir=doctree_directory.as_posix(),
        buildername=sphinx_builder,
    )
    app.builder.copysource = False  # Prevent unneeded source copying - we link direct to GitHub
    app.builder.search = False  # Disable search
    app.build()


if __name__ == '__main__':
    render_docutils()
    render_sphinx()

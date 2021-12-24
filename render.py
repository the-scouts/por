from __future__ import annotations

import sys
from pathlib import Path

from sphinx.application import Sphinx


def render_sphinx(*, clean: bool = False, sphinx_builder: str = "html") -> int:
    root_directory = Path(__file__).parent
    source_directory = root_directory / "sphinx_source"
    conf_directory = root_directory
    build_directory = root_directory / "render"  # synchronise with deploy-pages.yml -> deploy step
    doctree_directory = build_directory / ".doctrees"

    if clean:
        import shutil

        try:
            shutil.rmtree(build_directory)
        except FileNotFoundError:
            pass

    # builder configuration
    # sphinx_builder = "linkcheck"

    app = Sphinx(
        source_directory.as_posix(),
        confdir=conf_directory.as_posix(),
        outdir=build_directory.as_posix(),
        doctreedir=doctree_directory.as_posix(),
        buildername=sphinx_builder,
    )
    app.build()
    return app.statuscode


if __name__ == '__main__':
    if "ci" in sys.argv[1:]:
        raise SystemExit(render_sphinx(clean=False, sphinx_builder="dirhtml"))
    raise SystemExit(render_sphinx(clean=True))

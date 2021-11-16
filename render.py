from __future__ import annotations

import sys
from pathlib import Path

from docutils.core import publish_string
from sphinx.application import Sphinx
from sphinx.errors import SphinxError


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
    app.builder.copysource = False  # Prevent unneeded source copying
    app.builder.search = False  # Disable search

    try:
        app.build(force_all=True)
    except (SphinxError, KeyboardInterrupt) as exception:
        import sys

        from sphinx.util.console import red  # type: ignore

        if isinstance(exception, KeyboardInterrupt):
            print("\nInterrupted!", file=sys.stderr)
        else:
            print(red(f"\n{exception.category}:") + f"\n{exception}", file=sys.stderr)

        return 2
    return app.statuscode


if __name__ == '__main__':
    if "ci" in sys.argv[1:]:
        raise SystemExit(render_sphinx(clean=False, sphinx_builder="dirhtml"))
    raise SystemExit(render_sphinx(clean=True))

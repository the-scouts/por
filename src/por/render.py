from __future__ import annotations

from pathlib import Path

from docutils.core import publish_string

PUBLISH_SETTINGS = {
    "stylesheet_path": "por.css",
    "input_encoding": "unicode",
    "output_encoding": "unicode",
    # "embed_stylesheet": False,
}

if __name__ == '__main__':
    for chapter in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16):
        print(f"Processing Chapter {chapter}")
        rst_source = Path(f"expected/chapter-{chapter}.exp.rst").read_text(encoding="utf-8")
        out_path = Path(f"rendered/chapter-{chapter}.html")

        rendered_html = publish_string(source=rst_source, writer_name="html5", settings_overrides=PUBLISH_SETTINGS)
        out_path.write_text(rendered_html, encoding="utf-8")

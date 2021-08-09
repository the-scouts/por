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
    chapters = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
    for i in chapters:
        print(f"Processing Chapter {i}")
        rst_source = Path(f"chapter-{i}.exp.rst").read_text(encoding="utf-8")
        out_path = Path(f"chapter-{i}.html")

        rendered_html = publish_string(source=rst_source, writer_name="html5", settings_overrides=PUBLISH_SETTINGS)
        out_path.write_text(rendered_html, encoding="utf-8")

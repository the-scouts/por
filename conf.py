from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent / "src"))

# Project information
project = "POR"
master_doc = "contents"

# Sphinx extension modules as fully qualified strings
extensions = [
    "por.sphinx_extensions",
    "sphinx.ext.githubpages",
]

# The file extensions of source files. Sphinx uses these suffixes as sources.
source_suffix = {
    ".rst": "por",
}

# List of relative patterns to ignore when looking for source files.
exclude_patterns = [
    # Windows:
    "Thumbs.db",
    ".DS_Store",
    # Python:
    "venv",
    "requirements.txt",
    # Sphinx:
    "build",
    "output.txt",  # Link-check output
]

# HTML output settings
html_show_copyright = False
html_show_sphinx = False
html_title = "por.scouts.org.uk"  # Set <title/>

# Theme settings
html_theme_path = ["src/por/sphinx_extensions"]
html_theme = "por_theme"  # The actual theme directory (child of html_theme_path)
html_use_index = False
html_style = ""  # must be defined here or in theme.conf, but is unused
html_permalinks = False  # handled in the Contents transform

templates_path = ['src/por/sphinx_extensions/por_theme/templates']  # Theme template relative paths from `confdir`

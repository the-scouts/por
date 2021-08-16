# Project information
project = "POR"
master_doc = "contents"

# Sphinx extension modules as fully qualified strings
extensions = [
    "sphinx.ext.githubpages",
]

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
html_use_index = False  # Disable index

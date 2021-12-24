from docutils import nodes
from docutils.frontend import OptionParser
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.writers.html import HTMLWriter

from sphinx.builders.dirhtml import DirectoryHTMLBuilder


class FileBuilder(StandaloneHTMLBuilder):
    copysource = False  # Prevent unneeded source copying
    search = False  # Disable search

    # Things we don't use but that need to exist:
    indexer = None
    relations = {}
    _script_files = _css_files = []
    globalcontext = {"script_files": [], "css_files": []}

    def prepare_writing(self, _doc_names: set[str]) -> None:
        self.docwriter = HTMLWriter(self)
        _opt_parser = OptionParser([self.docwriter], defaults=self.env.settings, read_config_files=True)
        self.docsettings = _opt_parser.get_default_values()

    def get_doc_context(self, docname: str, body: str, _metatags: str) -> dict:
        """Collect items for the template context of a page."""
        try:
            title = self.env.longtitles[docname].astext()
        except KeyError:
            title = ""

        # local table of contents
        toc_tree = self.env.tocs[docname].deepcopy()
        for node in toc_tree.traverse(nodes.reference):
            node["refuri"] = node["anchorname"] or '#'  # fix targets
        toc = self.render_partial(toc_tree)["fragment"]

        return {"title": title, "toc": toc, "body": body}


class DirectoryBuilder(FileBuilder):
    # sync all overwritten things from DirectoryHTMLBuilder
    name = DirectoryHTMLBuilder.name
    get_target_uri = DirectoryHTMLBuilder.get_target_uri
    get_outfilename = DirectoryHTMLBuilder.get_outfilename

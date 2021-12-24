
from docutils import nodes


# New-line marker -- marker node to force a new line.
class newline_marker(nodes.Element):  # NoQA
    def astext(self):
        return " \u2013 "  # en dash


nodes.GenericNodeVisitor.visit_newline_marker = nodes._call_default_visit # NoQA
nodes.GenericNodeVisitor.depart_newline_marker = nodes._call_default_departure # NoQA

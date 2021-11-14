
from docutils import nodes

# New-line marker -- marker node to force a new line.
class newline_marker(nodes.Element): pass # NoQA
nodes.GenericNodeVisitor.visit_newline_marker = nodes._call_default_visit # NoQA
nodes.GenericNodeVisitor.depart_newline_marker = nodes._call_default_departure # NoQA

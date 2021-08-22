from docutils import nodes
from sphinx import addnodes
from sphinx.util.docutils import ReferenceRole
from sphinx.util.docutils import SphinxRole

POR_URL_TEMPLATE = ""


class RuleReference(ReferenceRole):
    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        rule_reference = self.target
        inliner = self.inliner

        target_id = f"index-{self.env.new_serialno('index')}"
        index = addnodes.index(entries=[("single", f"POR Rule {rule_reference}", target_id, "", None)])
        target = nodes.target("", "", ids=[target_id])
        inliner.document.note_explicit_target(target)

        try:
            rule_str, _, fragment = rule_reference.partition("#")
            ref_uri = f"{rule_str}"  # TODO work out an actual URI schema
            if fragment:
                ref_uri = f"{ref_uri}#{fragment}"
        except ValueError:
            message = inliner.reporter.error(f"Invalid POR rule number {rule_reference}", line=self.lineno)
            problematic = inliner.problematic(self.rawtext, "", message)
            return [message], [problematic]

        title = self.title if self.has_explicit_title else f"Rule {self.title}"
        reference = nodes.reference("", "", nodes.strong("", title), internal=False, refuri=ref_uri, classes=['por-rule'])
        return [index, target, reference], []

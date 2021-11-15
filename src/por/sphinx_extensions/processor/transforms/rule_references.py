from __future__ import annotations

from typing import Any, Sequence, TYPE_CHECKING

from docutils import nodes
from sphinx import addnodes
from sphinx.transforms import post_transforms
from sphinx.util import logging
from sphinx.util.nodes import find_pending_xref_condition

if TYPE_CHECKING:
    from sphinx.builders import Builder
    from sphinx.domains.std import StandardDomain

logger = logging.getLogger(__name__)


class RulesResolver(post_transforms.SphinxPostTransform):
    """Resolves rule references on doctrees."""

    default_priority = 9  # before sphinx.transforms.post_transforms.ReferencesResolver

    def run(self, **kwargs: Any) -> None:
        for node in self.document.traverse(addnodes.pending_xref):
            if node["reftype"] != "rule":
                continue

            new_node = _resolve_rule_xref(self.env.domains["std"], self.app.builder, node)
            if new_node is not None:
                node.replace_self([new_node])
                continue

            # unhappy path:
            content = _find_pending_xref_condition(node, ("resolved", "*"))
            if content:
                new_nodes = [content[0].deepcopy()]
            else:
                new_nodes = [node[0].deepcopy()]

            if isinstance(node[0], addnodes.pending_xref_condition):
                matched = _find_pending_xref_condition(node, ("*",))
                if matched:
                    new_nodes = matched
                else:
                    logger.warning("Could not determine the fallback text for the cross-reference. Might be a bug.", location=node)

            node.replace_self(new_nodes)


def _find_pending_xref_condition(node: addnodes.pending_xref, conditions: Sequence[str]) -> list[nodes.Node] | None:
    for condition in conditions:
        matched = find_pending_xref_condition(node, condition)
        if matched:
            return matched.children
    else:
        return None


def _resolve_rule_xref(domain: StandardDomain, builder: Builder, node: addnodes.pending_xref) -> nodes.Element | None:
    target: str = node["reftarget"]
    from_doc_name: str = node["refdoc"]
    try:
        doc_name, label_id, rule_num = domain.labels[target]
        raw_source = node.astext()
    except KeyError:
        # no new node found? warn if node wishes to be warned about
        if node.get("refwarn", False):
            msg = "Failed to create a cross reference. A title or caption not found: " if target in domain.anonlabels else "undefined label: "
            logger.warning(msg + node["reftarget"], location=node, type="ref", subtype=node["reftype"])
        return None

    # translate rule title reference to a rule number for display
    try:
        chapter, rule, *extra = raw_source.split("!", 2)
        link_text = f"Rule {chapter}.{rule_num}{''.join(extra)}"
    except ValueError:
        msg = f"Rule reference formatted incorrectly. Chapter and rule are mandatory with optional extra text, separated by !. Got '{self.text}'."
        # if RAISE_INVALID:
        #     err = SphinxError(msg)
        #     err.category = "Invalid rule reference"
        #     raise err from None
        logger.warning(msg)
        link_text = f"Rule {rule_num}"

    new_node = nodes.reference("", link_text, internal=True, classes=['por-rule'])
    if doc_name == from_doc_name:
        new_node["refid"] = label_id
    else:
        new_node["refuri"] = builder.get_relative_uri(from_doc_name, doc_name)
        if label_id:
            new_node["refuri"] += f"#{label_id}"
    return new_node

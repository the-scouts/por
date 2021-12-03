from docutils import nodes

SCOTTISH_POR_URL = "https://www.scouts.scot/media/2504/scottish-variations-from-the-september-2021-edition-of-the-policy.pdf"


def node_from_target(target_text: str, /) -> nodes.superscript:
    return nodes.superscript("", "", nodes.reference("", "sv", refuri=SCOTTISH_POR_URL + target_text))

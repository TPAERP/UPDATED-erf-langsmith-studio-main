from langgraph.constants import Send

from prompts.risk_taxonomy import RISK_TAXONOMY
from schemas import State


def initiate_parallel_web_search(state: State):
    """Assign each risk taxonomy to a web search worker node."""
    _ = state
    return [Send("web_search", {"taxonomy": taxonomy}) for taxonomy in RISK_TAXONOMY]


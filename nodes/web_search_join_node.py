from prompts.risk_taxonomy import RISK_TAXONOMY
from schemas import State


def web_search_join_router(state: State) -> str:
    """Barrier: proceed only after all taxonomy reports are present."""
    expected = len(RISK_TAXONOMY)
    have = len(state.get("taxonomy_reports", []) or [])
    return "verify_sources" if have >= expected else "end"


from schemas import State


def relevance_join_router(state: State) -> str:
    """Barrier: proceed only after all draft risks have relevance validation."""
    drafts = state.get("draft_risks", []) or []
    finalized = state.get("finalized_risks", []) or []
    if drafts and len(finalized) >= len(drafts):
        return "render_report"
    return "end"


def relevance_router(state: State) -> str:
    """Route to relevance assessment if drafts exist, else render directly."""
    drafts = state.get("draft_risks", []) or []
    return "initiate_relevance" if drafts else "render_report"

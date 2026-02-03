from schemas import State


def refinement_join_router(state: State) -> str:
    """Barrier: proceed only after all draft risks have been refined."""
    drafts = state.get("draft_risks", []) or []
    finalized = state.get("finalized_risks", []) or []
    if drafts and len(finalized) >= len(drafts):
        return "render_report"
    return "end"


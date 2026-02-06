from langgraph.types import Send
from schemas import State


def initiate_parallel_relevance(state: State):
    """
    Assign each draft risk to a portfolio relevance assessment worker.
    """
    drafts = state.get("draft_risks", []) or []
    return [Send("assess_portfolio_relevance", {"risk_candidate": draft}) for draft in drafts]

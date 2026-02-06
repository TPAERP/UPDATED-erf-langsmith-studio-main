from langgraph.types import Send
from schemas import *

def initiate_parallel_refinement(state: State):
    """
    Assigns each draft risk to a risk refinement node.
    """
    drafts = state.get("draft_risks", [])
    
    # We use Send(node_name, state_for_node)
    return [Send("refine_single_risk", {"risk_candidate": draft}) for draft in drafts]

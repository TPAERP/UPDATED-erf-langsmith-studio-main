from typing import Any, Dict

from agent.agents.registry import refine_risk_agent
from schemas import RiskExecutionState


def refine_single_risk_node(state: RiskExecutionState) -> Dict[str, Any]:
    """Controller node: delegate single-risk governance refinement loop."""
    refined = refine_risk_agent(state["risk_candidate"])
    return {"finalized_risks": [refined]}

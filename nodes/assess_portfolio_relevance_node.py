from typing import Any, Dict

from agent.agents.registry import relevance_agent
from schemas import RiskExecutionState


def assess_portfolio_relevance_node(state: RiskExecutionState) -> Dict[str, Any]:
    """Controller node: delegate per-risk portfolio relevance assessment."""
    assessed = relevance_agent(state["risk_candidate"])
    return {"finalized_risks": [assessed]}

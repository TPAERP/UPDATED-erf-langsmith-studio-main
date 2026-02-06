from typing import Any, Dict

from langchain_core.messages import AIMessage

from agent.agents.registry import risk_updater_agent
from schemas import State


def risk_updater_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate risk register update workflow."""
    out = risk_updater_agent(state)
    return {
        "risk": out["risk"],
        "messages": [AIMessage(content=out["message"])],
        "attempts": state.get("attempts", 0),
    }

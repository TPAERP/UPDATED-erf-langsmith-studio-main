from typing import Any, Dict

from langchain_core.messages import AIMessage

from agent.agents.registry import add_signposts_agent
from schemas import State


def add_signposts_all_risks_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate signpost generation/evaluation per risk."""
    out = add_signposts_agent(state)
    return {
        "risk": out["risk"],
        "messages": [AIMessage(content=out["message"])],
    }

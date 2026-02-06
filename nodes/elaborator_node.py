from typing import Any, Dict

from langchain_core.messages import AIMessage

from agent.agents.registry import elaborator_agent
from schemas import State


def elaborator_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate Q&A elaboration over current risk register."""
    answer = elaborator_agent(state)
    return {
        "risk": state.get("risk"),
        "messages": [AIMessage(content=answer)],
        "attempts": state.get("attempts", 0),
    }

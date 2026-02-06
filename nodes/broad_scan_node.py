from typing import Any, Dict

from langchain_core.messages import AIMessage

from agent.agents.registry import broad_scan_agent
from schemas import State


def broad_scan_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate broad scan generation to agent."""
    risks = broad_scan_agent(state)
    return {
        "draft_risks": risks,
        "finalized_risks": [],
        "messages": [
            AIMessage(
                content=f"Broad scan generated {len(risks)} candidates. Refining in parallel..."
            )
        ],
    }

from __future__ import annotations

from typing import Any, Dict

from agent.agents.registry import summarize_events_agent
from schemas import State


def summarize_events_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate event-to-risk summarization."""
    draft_risks = summarize_events_agent(state)
    return {"draft_risks": draft_risks}

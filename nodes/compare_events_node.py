from __future__ import annotations

from typing import Any, Dict

from agent.agents.registry import compare_events_agent
from schemas import State


def compare_events_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate cross-taxonomy event consolidation."""
    cleaned_events = compare_events_agent(state)
    return {"event_clusters": cleaned_events}

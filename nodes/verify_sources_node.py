from __future__ import annotations

from typing import Any, Dict

from agent.agents.registry import verify_sources_agent
from schemas import State


def verify_sources_node(state: State) -> Dict[str, Any]:
    """Controller node: delegate source reliability verification."""
    verified_reports = verify_sources_agent(state)
    return {"verified_taxonomy_reports": verified_reports}

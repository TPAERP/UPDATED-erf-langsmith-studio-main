from __future__ import annotations

from typing import Any, Dict

from agent.agents.registry import web_search_agent
from schemas import TaxonomyExecutionState


def web_search_node(state: TaxonomyExecutionState) -> Dict[str, Any]:
    """Controller node: delegate taxonomy web search and brief generation."""
    report = web_search_agent(state)
    return {"taxonomy_reports": [report]}

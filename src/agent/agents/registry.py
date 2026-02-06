from __future__ import annotations

from typing import Any

from agent.agents.workflow_agents import build_workflow_agents

_agents: dict[str, Any] = build_workflow_agents()

router_agent = _agents["router_agent"]
broad_scan_agent = _agents["broad_scan_agent"]
web_search_agent = _agents["web_search_agent"]
verify_sources_agent = _agents["verify_sources_agent"]
compare_events_agent = _agents["compare_events_agent"]
summarize_events_agent = _agents["summarize_events_agent"]
refine_risk_agent = _agents["refine_risk_agent"]
relevance_agent = _agents["relevance_agent"]
render_report_agent = _agents["render_report_agent"]
risk_updater_agent = _agents["risk_updater_agent"]
elaborator_agent = _agents["elaborator_agent"]
add_signposts_agent = _agents["add_signposts_agent"]

__all__ = [
    "router_agent",
    "broad_scan_agent",
    "web_search_agent",
    "verify_sources_agent",
    "compare_events_agent",
    "summarize_events_agent",
    "refine_risk_agent",
    "relevance_agent",
    "render_report_agent",
    "risk_updater_agent",
    "elaborator_agent",
    "add_signposts_agent",
]

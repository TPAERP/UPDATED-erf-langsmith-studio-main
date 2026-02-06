"""Agent package for OOP workflow orchestration."""

from .registry import (
    add_signposts_agent,
    broad_scan_agent,
    compare_events_agent,
    elaborator_agent,
    refine_risk_agent,
    relevance_agent,
    render_report_agent,
    risk_updater_agent,
    router_agent,
    summarize_events_agent,
    verify_sources_agent,
    web_search_agent,
)

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

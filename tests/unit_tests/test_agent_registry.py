from __future__ import annotations

from agent.agents import registry


def test_registry_exposes_expected_singleton_agents():
    names = [
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
    for name in names:
        assert hasattr(registry, name), f"Missing agent: {name}"
        assert callable(getattr(registry, name)), f"Agent not callable: {name}"

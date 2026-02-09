from __future__ import annotations

from typing import Any

from agent.agents.add_signposts_agent import AddSignpostsAgent
from agent.agents.broad_scan_agent import BroadScanAgent
from agent.agents.compare_events_agent import CompareEventsAgent
from agent.agents.elaborator_agent import ElaboratorAgent
from agent.agents.refine_risk_agent import RefineRiskAgent, _refiner_message_builder
from agent.agents.relevance_agent import RelevanceAgent, _append_weak_relevance_note
from agent.agents.render_report_agent import RenderReportAgent
from agent.agents.risk_updater_agent import RiskUpdaterAgent
from agent.agents.router_agent import RouterAgent, _router_message_builder
from agent.agents.summarize_events_agent import SummarizeEventsAgent
from agent.agents.verify_sources_agent import VerifySourcesAgent
from agent.agents.web_search_agent import WebSearchAgent
from agent.agents.workflow_shared import (
    _default_model_name,
    _provider_llm_factory,
    _single_user_message_builder,
    _today_iso_utc,
    _today_long,
)


def build_workflow_agents() -> dict[str, Any]:
    model = _default_model_name()
    llm_factory = _provider_llm_factory
    return {
        "router_agent": RouterAgent(model=model, llm_factory=llm_factory),
        "broad_scan_agent": BroadScanAgent(model=model, llm_factory=llm_factory),
        "web_search_agent": WebSearchAgent(model=model, llm_factory=llm_factory),
        "verify_sources_agent": VerifySourcesAgent(model=model, llm_factory=llm_factory),
        "compare_events_agent": CompareEventsAgent(model=model, llm_factory=llm_factory),
        "summarize_events_agent": SummarizeEventsAgent(
            model=model,
            llm_factory=llm_factory,
        ),
        "refine_risk_agent": RefineRiskAgent(model=model, llm_factory=llm_factory),
        "relevance_agent": RelevanceAgent(model=model, llm_factory=llm_factory),
        "render_report_agent": RenderReportAgent(),
        "risk_updater_agent": RiskUpdaterAgent(model=model, llm_factory=llm_factory),
        "elaborator_agent": ElaboratorAgent(model=model, llm_factory=llm_factory),
        "add_signposts_agent": AddSignpostsAgent(model=model, llm_factory=llm_factory),
    }


__all__ = [
    "RouterAgent",
    "BroadScanAgent",
    "WebSearchAgent",
    "VerifySourcesAgent",
    "CompareEventsAgent",
    "SummarizeEventsAgent",
    "RefineRiskAgent",
    "RelevanceAgent",
    "RenderReportAgent",
    "RiskUpdaterAgent",
    "ElaboratorAgent",
    "AddSignpostsAgent",
    "build_workflow_agents",
]

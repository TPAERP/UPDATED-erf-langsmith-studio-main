from __future__ import annotations

import json
from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.citation_normalization_tool import CitationNormalizationTool
from agent.tools.citation_selection_tool import CitationSelectionTool
from agent.tools.event_to_risk_source_tool import EventToRiskSourceTool
from agent.tools.risk_deduplication_tool import RiskDeduplicationTool
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.scan_prompts import (
    EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_USER_MESSAGE,
)
from schemas import EventRiskDraftOutput


class SummarizeEventsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.source_tool = EventToRiskSourceTool()
        self.citation_tool = CitationSelectionTool()
        self.normalization_tool = CitationNormalizationTool()
        self.deduper = RiskDeduplicationTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[
                self.source_tool,
                self.citation_tool,
                self.normalization_tool,
                self.deduper,
            ],
            output_format=EventRiskDraftOutput,
            system_template=EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(EVENT_PATH_RISKDRAFT_USER_MESSAGE),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        events = list(state.get("event_clusters") or [])
        reports = list(
            state.get("verified_taxonomy_reports")
            or state.get("taxonomy_reports")
            or []
        )
        if not events:
            return []

        source_meta = self.source_tool.run(reports=reports, events=events)
        out = self.base_agent(
            {},
            events_json=json.dumps(events, indent=2),
            sources_block=source_meta["sources_block"],
        )
        risks = list(out.get("risks") or [])

        cleaned: list[dict[str, Any]] = []
        all_urls = list(source_meta.get("all_urls") or [])
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            portfolio_relevance = str(risk.get("portfolio_relevance") or "").strip()
            if portfolio_relevance not in ("High", "Medium", "Low"):
                portfolio_relevance = "Medium"
            portfolio_relevance_rationale = str(
                risk.get("portfolio_relevance_rationale") or ""
            ).strip()
            if not portfolio_relevance_rationale:
                portfolio_relevance_rationale = "Relevance not specified; requires review."

            sources = self.citation_tool.run(
                narrative=str(risk.get("narrative") or "").strip(),
                reasoning=str(risk.get("reasoning_trace") or "").strip(),
                source_pool=all_urls,
            )
            normalized = self.normalization_tool.run(
                risk={
                    "title": str(risk.get("title") or "").strip(),
                    "category": risk.get("category") or [],
                    "narrative": str(risk.get("narrative") or "").strip(),
                    "reasoning_trace": str(risk.get("reasoning_trace") or "").strip(),
                    "audit_log": [],
                    "portfolio_relevance": portfolio_relevance,
                    "portfolio_relevance_rationale": portfolio_relevance_rationale,
                    "sources": sources,
                }
            )
            cleaned.append(normalized)

        return self.deduper.run(risks=cleaned)

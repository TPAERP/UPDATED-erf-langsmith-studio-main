from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.compare_input_formatting_tool import CompareInputFormattingTool
from agent.tools.event_evidence_filter_tool import EventEvidenceFilterTool
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.scan_prompts import COMPARE_EVENTS_SYSTEM_MESSAGE
from schemas import EventClusterOutput


class CompareEventsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.format_tool = CompareInputFormattingTool()
        self.filter_tool = EventEvidenceFilterTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.format_tool, self.filter_tool],
            output_format=EventClusterOutput,
            system_template=COMPARE_EVENTS_SYSTEM_MESSAGE,
            static_context={"taxonomy": RISK_TAXONOMY},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Today: {today}\n\nSources:\n{source_block}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        reports = list(
            state.get("verified_taxonomy_reports")
            or state.get("taxonomy_reports")
            or []
        )
        if not reports:
            return []
        source_block = self.format_tool.run(reports=reports)
        known_urls: set[str] = set()
        for report in reports:
            sources = report.get("reliable_sources") or report.get("sources") or []
            for source in sources:
                url = str(source.get("url") or "").strip()
                if url:
                    known_urls.add(url)
        out = self.base_agent({}, source_block=source_block)
        events = list(out.get("events") or [])
        return self.filter_tool.run(events=events, known_urls=known_urls)

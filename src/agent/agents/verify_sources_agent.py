from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.source_reliability_merge_tool import SourceReliabilityMergeTool
from agent.tools.source_verification_formatting_tool import (
    SourceVerificationFormattingTool,
)
from prompts.scan_prompts import SOURCE_VERIFIER_SYSTEM_MESSAGE
from schemas import SourceReliabilityOutput


class VerifySourcesAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.format_tool = SourceVerificationFormattingTool()
        self.merge_tool = SourceReliabilityMergeTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.format_tool, self.merge_tool],
            output_format=SourceReliabilityOutput,
            system_template=SOURCE_VERIFIER_SYSTEM_MESSAGE,
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Taxonomy: {taxonomy}\n\nSources:\n{source_block}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        reports = list(state.get("taxonomy_reports", []) or [])
        verified_reports: list[dict[str, Any]] = []
        for report in reports:
            sources = list(report.get("sources") or [])
            if not sources:
                verified_reports.append(
                    {
                        **report,
                        "reliable_sources": [],
                        "verification_notes": "No sources to verify.",
                    }
                )
                continue
            source_block = self.format_tool.run(sources=sources)
            out = self.base_agent(
                {},
                taxonomy=str(report.get("taxonomy") or "").strip(),
                source_block=source_block,
            )
            merged = self.merge_tool.run(
                report=report,
                sources=sources,
                assessments=out.get("sources") or [],
            )
            verified_reports.append(merged)
        return verified_reports

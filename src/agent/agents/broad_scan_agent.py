from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import (
    _single_user_message_builder,
    _today_iso_utc,
    _today_long,
)
from agent.tools.conversation_context_tool import ConversationContextTool
from agent.tools.risk_deduplication_tool import RiskDeduplicationTool
from agent.tools.taxonomy_brief_formatting_tool import TaxonomyBriefFormattingTool
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.scan_prompts import (
    BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
    FEW_SHOT_EXAMPLES,
)
from prompts.source_guide import SOURCE_GUIDE
from schemas import BroadScanOutput


class BroadScanAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.conversation_tool = ConversationContextTool()
        self.brief_formatter = TaxonomyBriefFormattingTool()
        self.risk_deduper = RiskDeduplicationTool()
        system_template = "\n\n".join(
            [
                BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
                "{web_briefs_section}",
            ]
        )
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.brief_formatter, self.risk_deduper],
            output_format=BroadScanOutput,
            system_template=system_template,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
                "FEW_SHOT_EXAMPLES": FEW_SHOT_EXAMPLES,
                "web_briefs_section": "",
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder("{user_query}"),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        context = self.conversation_tool.run(messages=state.get("messages", []) or [])
        taxonomy_reports = list(state.get("taxonomy_reports", []) or [])
        briefs: list[str] = []
        for report in taxonomy_reports:
            brief_text = self.brief_formatter.run(
                mode="normalize_brief",
                content=report.get("brief_md") or "",
                taxonomy=report.get("taxonomy") or "",
                today_iso=_today_iso_utc(),
            )
            if brief_text:
                briefs.append(brief_text)

        web_briefs_section = ""
        if briefs:
            web_briefs_section = "\n".join(
                [
                    "--------------------------------------------------------------------",
                    "WEB HORIZON-SCAN BRIEFS (EVIDENCE INPUT)",
                    "--------------------------------------------------------------------",
                    "Use the briefs below as your primary evidence for 'what is happening now'.",
                    "Do NOT invent facts beyond these briefs; if evidence is missing, say so.",
                    "\n\n".join(briefs),
                ]
            )

        out = self.base_agent(
            state,
            user_query=context.get("last_user_query", ""),
            web_briefs_section=web_briefs_section,
        )
        risks = list(out.get("risks") or [])
        return self.risk_deduper.run(risks=risks)

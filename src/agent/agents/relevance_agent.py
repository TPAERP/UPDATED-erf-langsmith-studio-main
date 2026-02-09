from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.audit_trail_tool import AuditTrailTool
from agent.tools.citation_normalization_tool import CitationNormalizationTool
from agent.tools.citation_selection_tool import CitationSelectionTool
from helper_functions import format_risk_md
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.relevance_prompts import (
    PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE,
)
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.source_guide import SOURCE_GUIDE
from schemas import RelevanceReviewOutput, RiskDraft


def _append_weak_relevance_note(narrative: str) -> str:
    note = (
        "Portfolio relevance remains weak after review; treat as lower priority "
        "for this portfolio."
    )
    if note.lower() in narrative.lower():
        return narrative
    if narrative.endswith("."):
        return f"{narrative} {note}"
    return f"{narrative}. {note}"


class RelevanceAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.audit_tool = AuditTrailTool()
        self.citation_tool = CitationSelectionTool()
        self.normalization_tool = CitationNormalizationTool()
        self.assessor = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.citation_tool, self.normalization_tool],
            output_format=RiskDraft,
            system_template=PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Assess portfolio relevance for this risk draft.\n"
                "Prior reviewer feedback: {last_feedback}\n\n"
                "{formatted_risk}"
            ),
        )
        self.reviewer = BaseAgent(
            model=model,
            skills=[self.audit_tool],
            output_format=RelevanceReviewOutput,
            system_template=PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE.replace(
                    "{risk}",
                    "{risk_md}",
                )
            ),
        )

    def __call__(self, risk_candidate: dict[str, Any]) -> dict[str, Any]:
        current = self.audit_tool.run(
            risk=risk_candidate,
            default_audit_log=[],
            default_reasoning_trace="Initial scan selection.",
        )
        max_rounds = 3
        passed = False
        last_feedback = "None"

        for _round in range(1, max_rounds + 1):
            formatted_risk = format_risk_md(current, 0)
            assessed = self.assessor(
                {},
                formatted_risk=formatted_risk,
                last_feedback=last_feedback,
            )
            portfolio_relevance = str(assessed.get("portfolio_relevance") or "").strip()
            if portfolio_relevance not in ("High", "Medium", "Low"):
                portfolio_relevance = "Medium"
            relevance_rationale = str(
                assessed.get("portfolio_relevance_rationale") or ""
            ).strip()
            if not relevance_rationale:
                relevance_rationale = "Relevance not specified; requires review."

            current = {
                **current,
                "portfolio_relevance": portfolio_relevance,
                "portfolio_relevance_rationale": relevance_rationale,
                "reasoning_trace": str(
                    assessed.get("reasoning_trace") or current.get("reasoning_trace") or ""
                ).strip(),
                "sources": assessed.get("sources") or current.get("sources") or [],
            }

            selected_sources = self.citation_tool.run(
                narrative=str(current.get("narrative") or ""),
                reasoning=str(current.get("reasoning_trace") or ""),
                source_pool=current.get("sources") or [],
            )
            current["sources"] = selected_sources
            current = self.normalization_tool.run(risk=current)

            review_out = self.reviewer({}, taxonomy=RISK_TAXONOMY, risk_md=format_risk_md(current, 0))
            if review_out.get("satisfied_with_relevance"):
                current = self.audit_tool.run(
                    risk=current,
                    append_note="Portfolio relevance validated.",
                )
                passed = True
                break

            last_feedback = str(
                review_out.get("feedback")
                or "Relevance assessment requires revision."
            )
            current = self.audit_tool.run(
                risk=current,
                append_note=f"Relevance reviewer feedback: '{last_feedback}'.",
            )

        if not passed:
            current["portfolio_relevance"] = "Low"
            if not current.get("portfolio_relevance_rationale"):
                current["portfolio_relevance_rationale"] = (
                    "Relevance judged weak after review."
                )
            current = self.audit_tool.run(
                risk=current,
                step_title="Feedback & Revisions",
                step_text=(
                    f"Reviewer feedback: {last_feedback}. Marked relevance as Low and "
                    "flagged for de-prioritization."
                ),
            )
            current["narrative"] = _append_weak_relevance_note(
                str(current.get("narrative") or "")
            )
            current = self.audit_tool.run(
                risk=current,
                append_note="Portfolio relevance flagged as weak after review.",
            )
        elif current.get("portfolio_relevance") not in ("High", "Medium", "Low"):
            current["portfolio_relevance"] = "Medium"

        if "Portfolio Relevance" not in str(current.get("reasoning_trace") or ""):
            current = self.audit_tool.run(
                risk=current,
                step_title="Portfolio Relevance",
                step_text=(
                    f"Rated {current['portfolio_relevance']}: "
                    f"{current.get('portfolio_relevance_rationale', '')}"
                ),
            )
        return current

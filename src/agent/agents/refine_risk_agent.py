from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.audit_trail_tool import AuditTrailTool
from agent.tools.citation_normalization_tool import CitationNormalizationTool
from helper_functions import format_risk_md
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.scan_prompts import (
    FEW_SHOT_EXAMPLES,
    PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
    PER_RISK_EVALUATOR_USER_MESSAGE,
    SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
)
from prompts.source_guide import SOURCE_GUIDE
from schemas import PerRiskEvalOutput, RiskDraft


def _refiner_message_builder(
    system_prompt: str,
    _state: dict[str, Any],
    _runtime_context: dict[str, Any],
) -> list[Any]:
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Revise the risk strictly according to the feedback."),
    ]


class RefineRiskAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.audit_tool = AuditTrailTool()
        self.normalize_tool = CitationNormalizationTool()
        self.evaluator = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.normalize_tool],
            output_format=PerRiskEvalOutput,
            system_template=PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                PER_RISK_EVALUATOR_USER_MESSAGE.replace("{risk}", "{risk_md}")
            ),
        )
        self.refiner = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.normalize_tool],
            output_format=RiskDraft,
            system_template=SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
                "FEW_SHOT_EXAMPLES": FEW_SHOT_EXAMPLES,
                "feedback": "",
                "current_risk": "",
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_refiner_message_builder,
        )

    def __call__(self, risk_candidate: dict[str, Any]) -> dict[str, Any]:
        current = self.audit_tool.run(risk=risk_candidate)
        max_rounds = 3
        for _round in range(1, max_rounds + 1):
            formatted_risk = format_risk_md(current, 0)
            eval_out = self.evaluator({}, taxonomy=RISK_TAXONOMY, risk_md=formatted_risk)
            if eval_out.get("satisfied_with_risk"):
                current = self.audit_tool.run(
                    risk=current,
                    append_note="Passed independent governance review.",
                )
                break

            feedback = str(eval_out.get("feedback") or "Risk requires revision.")
            current = self.audit_tool.run(
                risk=current,
                append_note=f"Evaluator Feedback: '{feedback}'.",
            )
            new_draft = self.refiner(
                {},
                feedback=feedback,
                current_risk=formatted_risk,
            )
            if "portfolio_relevance" not in new_draft:
                new_draft["portfolio_relevance"] = current.get("portfolio_relevance", "Medium")
            if "portfolio_relevance_rationale" not in new_draft:
                new_draft["portfolio_relevance_rationale"] = current.get(
                    "portfolio_relevance_rationale",
                    "Relevance not specified; requires review.",
                )
            if "sources" not in new_draft:
                new_draft["sources"] = current.get("sources", [])
            new_draft["audit_log"] = list(current.get("audit_log") or []) + [
                "Narrative refined to address feedback."
            ]
            current = self.normalize_tool.run(risk=new_draft)
        return current

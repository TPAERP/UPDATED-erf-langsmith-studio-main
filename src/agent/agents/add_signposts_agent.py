from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.conversation_context_tool import ConversationContextTool
from agent.tools.signposts import SignpostAssemblyTool
from helper_functions import format_signposts_md
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.signpost_prompts import (
    SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
    SIGNPOST_EVALUATOR_USER_MESSAGE,
    SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
    SIGNPOST_GENERATOR_USER_MESSAGE,
)
from prompts.source_guide import SOURCE_GUIDE
from schemas import SignpostEvalOutput, SignpostPack


class AddSignpostsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.assembly_tool = SignpostAssemblyTool()
        self.generator = BaseAgent(
            model=model,
            skills=[self.assembly_tool],
            output_format=SignpostPack,
            system_template=SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(SIGNPOST_GENERATOR_USER_MESSAGE),
        )
        self.evaluator = BaseAgent(
            model=model,
            skills=[self.assembly_tool],
            output_format=SignpostEvalOutput,
            system_template=SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(SIGNPOST_EVALUATOR_USER_MESSAGE),
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        risk_register = state.get("risk") or {}
        risks = list(risk_register.get("risks") or [])
        if not risks:
            return {
                "risk": risk_register,
                "message": "No finalized risks found. Run scan/refine first.",
            }

        user_context = self.context_tool.run(messages=state.get("messages", []) or [])
        users_query = user_context.get("last_user_query", "")
        final_risks: list[dict[str, Any]] = []
        max_rounds_per_risk = 1

        for risk in risks:
            current_pack: dict[str, Any] | None = None
            for _round in range(1, max_rounds_per_risk + 1):
                if current_pack is None:
                    current_pack = self.generator(
                        {},
                        risk=risk,
                        user_context=users_query,
                        prior_signposts=current_pack,
                        feedback=None,
                    )
                eval_out = self.evaluator(
                    {},
                    taxonomy=RISK_TAXONOMY,
                    risk=risk,
                    signposts=current_pack,
                )
                if eval_out.get("satisfied_with_signposts"):
                    break
                current_pack = self.generator(
                    {},
                    risk=risk,
                    user_context=users_query,
                    prior_signposts=current_pack,
                    feedback=eval_out.get("feedback"),
                )

            final_risk = self.assembly_tool.run(
                risk=risk,
                signposts=(current_pack or {}).get("signposts") or [],
            )
            final_risks.append(final_risk)

        markdown = ["# Final Risk Register (with Signposts)", ""]
        for i, risk in enumerate(final_risks, start=1):
            categories = risk.get("category") or []
            if not isinstance(categories, list):
                categories = [categories]
            markdown.append(f"## Risk {i}: {risk.get('title', '')}")
            markdown.append(f"**Categories:** {', '.join(str(c) for c in categories)}")
            markdown.append("")
            markdown.append("**Narrative**")
            markdown.append(str(risk.get("narrative") or "").strip())
            markdown.append("")
            if risk.get("reasoning_trace"):
                markdown.append(f"_**Analyst Reasoning:** {risk['reasoning_trace']}_")
                markdown.append("")
            markdown.append(format_signposts_md(risk.get("signposts") or []))
            if risk.get("audit_log"):
                log_text = " ".join(str(item) for item in risk["audit_log"])
                markdown.append("")
                markdown.append("> **Governance History:**")
                markdown.append(f"> {log_text}")
            markdown.append("")
            markdown.append("---")
            markdown.append("")

        return {"risk": {"risks": final_risks}, "message": "\n".join(markdown).strip()}

from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.conversation_context_tool import ConversationContextTool
from agent.tools.update_render_tool import UpdateRenderTool
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.source_guide import SOURCE_GUIDE
from prompts.update_prompts import RISK_UPDATER_SYSTEM_MESSAGE
from schemas import RiskUpdateOutput


class RiskUpdaterAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.render_tool = UpdateRenderTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.context_tool, self.render_tool],
            output_format=RiskUpdateOutput,
            system_template=RISK_UPDATER_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "USER REQUEST:\n{users_query}\n\n"
                "EXISTING RISK REGISTER (JSON-like):\n{existing_register}\n\n"
                "Update the register following your instructions."
            ),
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        context = self.context_tool.run(messages=state.get("messages", []) or [])
        users_query = context.get("last_user_query", "")
        existing_register = state.get("risk")
        updated = self.base_agent(
            {},
            users_query=users_query,
            existing_register=existing_register,
        )
        updated_register = {"risks": updated.get("risks") or []}
        final_message = self.render_tool.run(
            risks=updated_register["risks"],
            change_log=updated.get("change_log") or [],
        )
        return {"risk": updated_register, "message": final_message}

from __future__ import annotations

from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.conversation_context_tool import ConversationContextTool
from prompts.reporting_prompts import ELABORATOR_SYSTEM_MESSAGE
from schemas import ElaboratorOutput


class ElaboratorAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.context_tool],
            output_format=ElaboratorOutput,
            system_template=(
                f"{ELABORATOR_SYSTEM_MESSAGE}\n"
                "Return JSON with key 'answer' only."
            ),
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Current risk register (if any):\n{current_register}\n\n"
                "Conversation so far:\n{conversation}\n\n"
                "User question:\n{last_query}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> str:
        context = self.context_tool.run(messages=state.get("messages", []) or [])
        out = self.base_agent(
            {},
            current_register=state.get("risk"),
            conversation=context.get("conversation", ""),
            last_query=context.get("last_user_query", ""),
        )
        return str(out.get("answer") or "").strip()

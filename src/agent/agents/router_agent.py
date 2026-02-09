from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _today_long
from agent.tools.conversation_context_tool import ConversationContextTool
from prompts.router_prompts import ROUTER_SYSTEM_MESSAGE, ROUTER_USER_MESSAGE
from schemas import RouterOutput


def _router_message_builder(
    system_prompt: str,
    _state: dict[str, Any],
    runtime_context: dict[str, Any],
) -> list[Any]:
    user_query = str(runtime_context.get("user_query") or "")
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=ROUTER_USER_MESSAGE.format(user_query=user_query)),
    ]


class RouterAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.conversation_tool = ConversationContextTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.conversation_tool],
            output_format=RouterOutput,
            system_template=ROUTER_SYSTEM_MESSAGE,
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_router_message_builder,
        )

    def __call__(self, state: dict[str, Any]) -> str:
        context = self.conversation_tool.run(messages=state.get("messages", []) or [])
        output = self.base_agent(state, user_query=context.get("last_user_query", ""))
        user_query_type = output.get("user_query_type")
        if user_query_type == "scan":
            return "initiate_web_search"
        if user_query_type == "update":
            return "risk_updater"
        return "elaborator"

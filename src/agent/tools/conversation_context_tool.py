from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import format_conversation, last_human_content


class ConversationContextTool(KwargTool):
    name: str = "conversation_context_tool"
    description: str = "Extracts latest user message and flattened conversation history."

    def _run(self, **kwargs: Any) -> dict[str, str]:
        messages = list(kwargs.get("messages") or [])
        return {
            "last_user_query": last_human_content(messages),
            "conversation": format_conversation(messages),
        }

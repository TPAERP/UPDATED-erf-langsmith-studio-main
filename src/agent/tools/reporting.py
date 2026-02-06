from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import (
    dedupe_risks,
    format_all_risks_md,
    format_conversation,
    last_human_content,
)


class RiskMarkdownRenderTool(KwargTool):
    name: str = "risk_markdown_render_tool"
    description: str = "Renders risk lists as markdown register output."

    def _run(self, **kwargs: Any) -> str:
        risks = list(kwargs.get("risks") or [])
        dedupe = bool(kwargs.get("dedupe", True))
        if dedupe:
            risks = dedupe_risks(risks)
        return format_all_risks_md(risks) if risks else ""


class ConversationContextTool(KwargTool):
    name: str = "conversation_context_tool"
    description: str = "Extracts latest user message and flattened conversation history."

    def _run(self, **kwargs: Any) -> dict[str, str]:
        messages = list(kwargs.get("messages") or [])
        return {
            "last_user_query": last_human_content(messages),
            "conversation": format_conversation(messages),
        }


class UpdateRenderTool(KwargTool):
    name: str = "update_render_tool"
    description: str = "Formats updated risk register plus change log into markdown."

    def _run(self, **kwargs: Any) -> str:
        risks = list(kwargs.get("risks") or [])
        change_log = list(kwargs.get("change_log") or [])
        lines: list[str] = ["# Updated Risk Register", "", format_all_risks_md(risks), "", "# Change Log"]
        for bullet in change_log:
            lines.append(f"- {bullet}")
        return "\n".join(lines).strip()

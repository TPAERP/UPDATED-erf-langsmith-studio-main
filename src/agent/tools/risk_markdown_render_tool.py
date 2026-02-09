from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import dedupe_risks, format_all_risks_md


class RiskMarkdownRenderTool(KwargTool):
    name: str = "risk_markdown_render_tool"
    description: str = "Renders risk lists as markdown register output."

    def _run(self, **kwargs: Any) -> str:
        risks = list(kwargs.get("risks") or [])
        dedupe = bool(kwargs.get("dedupe", True))
        if dedupe:
            risks = dedupe_risks(risks)
        return format_all_risks_md(risks) if risks else ""

from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import format_all_risks_md


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

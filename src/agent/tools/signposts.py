from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class SignpostAssemblyTool(KwargTool):
    name: str = "signpost_assembly_tool"
    description: str = "Assembles finalized risk payloads with generated signposts."

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        risk = dict(kwargs.get("risk") or {})
        signposts = list(kwargs.get("signposts") or [])
        return {
            "title": risk.get("title", ""),
            "category": risk.get("category", []),
            "narrative": risk.get("narrative", ""),
            "signposts": signposts,
            "reasoning_trace": risk.get("reasoning_trace", ""),
            "audit_log": risk.get("audit_log", []),
        }

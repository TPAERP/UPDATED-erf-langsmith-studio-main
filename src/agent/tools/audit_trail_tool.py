from __future__ import annotations

import re
from typing import Any

from agent.tools.base import KwargTool


def _next_step_number(reasoning: str) -> int:
    count = 0
    for line in (reasoning or "").splitlines():
        if re.match(r"^\s*\d+\.\s", line):
            count += 1
    return count + 1


def _append_step(reasoning: str, title: str, text: str) -> str:
    step_number = _next_step_number(reasoning)
    line = f"{step_number}. **{title}**: {text}"
    return f"{reasoning}\n{line}".strip() if reasoning else line


class AuditTrailTool(KwargTool):
    name: str = "audit_trail_tool"
    description: str = (
        "Ensures audit/reasoning defaults and appends governance notes or reasoning steps."
    )

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        risk = dict(kwargs.get("risk") or {})
        defaults = {
            "audit_log": kwargs.get(
                "default_audit_log",
                ["Draft generated during broad horizon scanning."],
            ),
            "reasoning_trace": kwargs.get("default_reasoning_trace", "Initial scan selection."),
            "portfolio_relevance": kwargs.get("default_portfolio_relevance", "Medium"),
            "portfolio_relevance_rationale": kwargs.get(
                "default_portfolio_relevance_rationale",
                "Relevance not specified; requires review.",
            ),
            "sources": kwargs.get("default_sources", []),
        }
        for key, value in defaults.items():
            if key not in risk:
                risk[key] = value if not isinstance(value, list) else list(value)

        append_note = kwargs.get("append_note")
        if append_note:
            risk["audit_log"] = list(risk.get("audit_log") or [])
            risk["audit_log"].append(str(append_note))

        step_title = kwargs.get("step_title")
        step_text = kwargs.get("step_text")
        if step_title and step_text:
            risk["reasoning_trace"] = _append_step(
                str(risk.get("reasoning_trace") or ""),
                str(step_title),
                str(step_text),
            )

        return risk

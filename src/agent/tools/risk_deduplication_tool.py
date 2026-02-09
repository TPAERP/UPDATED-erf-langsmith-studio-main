from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import dedupe_risks


class RiskDeduplicationTool(KwargTool):
    name: str = "risk_deduplication_tool"
    description: str = "Removes duplicate risks using canonicalized fingerprints."

    def _run(self, **kwargs: Any) -> list[dict[str, Any]]:
        risks = list(kwargs.get("risks") or [])
        return dedupe_risks(risks)

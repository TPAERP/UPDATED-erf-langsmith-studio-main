from __future__ import annotations

from typing import Any

from agent.tools.risk_deduplication_tool import RiskDeduplicationTool
from agent.tools.risk_markdown_render_tool import RiskMarkdownRenderTool


class RenderReportAgent:
    def __init__(self) -> None:
        self.deduper = RiskDeduplicationTool()
        self.renderer = RiskMarkdownRenderTool()

    def __call__(self, state: dict[str, Any]) -> str:
        finalized = list(state.get("finalized_risks", []) or [])
        deduped = self.deduper.run(risks=finalized)
        return self.renderer.run(risks=deduped, dedupe=False)

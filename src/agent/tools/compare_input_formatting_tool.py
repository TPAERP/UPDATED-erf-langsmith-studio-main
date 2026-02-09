from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class CompareInputFormattingTool(KwargTool):
    name: str = "compare_input_formatting_tool"
    description: str = "Formats verified taxonomy report sources for event deduplication prompts."

    def _run(self, **kwargs: Any) -> str:
        reports = list(kwargs.get("reports") or [])
        lines: list[str] = []
        for report in reports:
            taxonomy = str(report.get("taxonomy") or "Unknown").strip()
            sources = report.get("reliable_sources") or report.get("sources") or []
            if not sources:
                continue
            lines.append(f"Taxonomy: {taxonomy}")
            for i, source in enumerate(sources, start=1):
                title = str(source.get("title") or "Untitled").strip()
                url = str(source.get("url") or "").strip()
                snippet = str(source.get("snippet") or "").strip()
                published = str(source.get("published") or "").strip()
                reliability = str(source.get("reliability") or "").strip()
                reliability_line = (
                    f"Reliability: {reliability}" if reliability else "Reliability: Unknown"
                )
                lines.append(
                    "\n".join(
                        [
                            f"[{taxonomy}:{i}] {title}",
                            f"URL: {url}",
                            f"Published: {published or 'Unknown'}",
                            reliability_line,
                            f"Snippet: {snippet or 'No snippet'}",
                        ]
                    )
                )
            lines.append("")
        return "\n".join(lines).strip() if lines else "(No sources provided.)"

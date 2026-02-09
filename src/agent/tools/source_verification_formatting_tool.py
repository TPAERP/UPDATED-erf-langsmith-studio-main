from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class SourceVerificationFormattingTool(KwargTool):
    name: str = "source_verification_formatting_tool"
    description: str = "Formats source metadata into numbered verification text blocks."

    def _run(self, **kwargs: Any) -> str:
        sources = list(kwargs.get("sources") or [])
        if not sources:
            return "(No sources provided.)"
        lines: list[str] = []
        for i, source in enumerate(sources, start=1):
            title = str(source.get("title") or "Untitled").strip()
            url = str(source.get("url") or "").strip()
            snippet = str(source.get("snippet") or "").strip()
            published = str(source.get("published") or "").strip()
            lines.append(
                "\n".join(
                    [
                        f"[{i}] {title}",
                        f"URL: {url}",
                        f"Published: {published or 'Unknown'}",
                        f"Snippet: {snippet or 'No snippet'}",
                    ]
                ).strip()
            )
        return "\n\n".join(lines)

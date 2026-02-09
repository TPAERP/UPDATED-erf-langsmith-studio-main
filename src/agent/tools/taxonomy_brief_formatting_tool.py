from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class TaxonomyBriefFormattingTool(KwargTool):
    name: str = "taxonomy_brief_formatting_tool"
    description: str = "Formats search results into source blocks and normalized brief markdown."

    def _run(self, **kwargs: Any) -> str:
        mode = str(kwargs.get("mode") or "sources_block")
        if mode == "normalize_brief":
            content = kwargs.get("content", "")
            taxonomy = str(kwargs.get("taxonomy") or "").strip()
            today_iso = str(kwargs.get("today_iso") or "").strip()
            if isinstance(content, list):
                brief_md = "\n".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                ).strip()
            else:
                brief_md = str(content).strip()
            if brief_md:
                return brief_md
            return f"## {taxonomy} (as of {today_iso})\n\n- No brief generated."

        sources = list(kwargs.get("sources") or [])
        if not sources:
            return "(No results returned.)"
        lines: list[str] = []
        for i, source in enumerate(sources, start=1):
            published = (
                f" ({source.get('published')})" if source.get("published") else ""
            )
            lines.append(
                f"[{i}] {source.get('title', '')}{published}\n"
                f"{source.get('url', '')}\n"
                f"{source.get('snippet', '')}".strip()
            )
        return "\n\n".join(lines)

from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class EventToRiskSourceTool(KwargTool):
    name: str = "event_to_risk_source_tool"
    description: str = "Builds shared source lookup, URL pool, and formatted source block for event-to-risk drafting."

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        reports = list(kwargs.get("reports") or [])
        events = list(kwargs.get("events") or [])
        lookup: dict[str, dict[str, Any]] = {}
        for report in reports:
            sources = report.get("reliable_sources") or report.get("sources") or []
            for source in sources:
                url = str(source.get("url") or "").strip()
                if url and url not in lookup:
                    lookup[url] = source

        all_urls: list[str] = []
        seen_urls: set[str] = set()
        for event in events:
            for url in event.get("evidence_urls") or []:
                if isinstance(url, str) and url and url not in seen_urls:
                    seen_urls.add(url)
                    all_urls.append(url)

        source_lines: list[str] = []
        for i, url in enumerate(all_urls, start=1):
            source = lookup.get(url, {})
            title = str(source.get("title") or "Untitled").strip()
            snippet = str(source.get("snippet") or "").strip()
            published = str(source.get("published") or "").strip()
            reliability = str(source.get("reliability") or "").strip()
            reliability_line = (
                f"Reliability: {reliability}" if reliability else "Reliability: Unknown"
            )
            source_lines.append(
                "\n".join(
                    [
                        f"[{i}] {title}",
                        f"URL: {url}",
                        f"Published: {published or 'Unknown'}",
                        reliability_line,
                        f"Snippet: {snippet or 'No snippet'}",
                    ]
                )
            )

        return {
            "source_lookup": lookup,
            "all_urls": all_urls,
            "sources_block": "\n\n".join(source_lines).strip()
            if source_lines
            else "(No sources provided.)",
        }

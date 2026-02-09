from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class EventEvidenceFilterTool(KwargTool):
    name: str = "event_evidence_filter_tool"
    description: str = "Filters model-produced events to known evidence URLs and normalized fields."

    def _run(self, **kwargs: Any) -> list[dict[str, Any]]:
        events = list(kwargs.get("events") or [])
        known_urls = set(kwargs.get("known_urls") or [])
        cleaned: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            evidence_urls = [
                url
                for url in (event.get("evidence_urls") or [])
                if isinstance(url, str) and url in known_urls
            ]
            cleaned.append(
                {
                    "title": str(event.get("title") or "").strip(),
                    "taxonomy": event.get("taxonomy") or [],
                    "summary": str(event.get("summary") or "").strip(),
                    "evidence_urls": evidence_urls,
                }
            )
        return cleaned

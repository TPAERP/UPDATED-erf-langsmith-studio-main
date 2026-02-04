from __future__ import annotations

from typing import Any, Dict, List

from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage

from models import event_compare_llm
from prompts.system_messages import COMPARE_EVENTS_SYSTEM_MESSAGE
from prompts.risk_taxonomy import RISK_TAXONOMY
from schemas import EventCluster, State, TaxonomyWebReport, WebSearchResult


def _format_sources_for_compare(reports: List[TaxonomyWebReport]) -> str:
    lines: List[str] = []
    for report in reports:
        taxonomy = (report.get("taxonomy") or "Unknown").strip()
        sources = report.get("reliable_sources") or report.get("sources") or []
        if not sources:
            continue
        lines.append(f"Taxonomy: {taxonomy}")
        for i, s in enumerate(sources, start=1):
            title = (s.get("title") or "Untitled").strip()
            url = (s.get("url") or "").strip()
            snippet = (s.get("snippet") or "").strip()
            published = (s.get("published") or "").strip()
            reliability = (s.get("reliability") or "").strip()
            reliability_line = f"Reliability: {reliability}" if reliability else "Reliability: Unknown"
            lines.append(
                "\n".join(
                    [
                        f"[{taxonomy}:{i}] {title}",
                        f"URL: {url}",
                        f"Published: {published or 'Unknown'}",
                        f"{reliability_line}",
                        f"Snippet: {snippet or 'No snippet'}",
                    ]
                )
            )
        lines.append("")
    return "\n".join(lines).strip() if lines else "(No sources provided.)"


def compare_events_node(state: State) -> Dict[str, Any]:
    """
    Compares and consolidates events across taxonomies to remove duplicates.
    """
    reports = state.get("verified_taxonomy_reports") or state.get("taxonomy_reports") or []
    if not reports:
        return {"event_clusters": []}

    today = datetime.now().strftime("%B %d, %Y")
    source_block = _format_sources_for_compare(reports)
    known_urls = set()
    for report in reports:
        sources = report.get("reliable_sources") or report.get("sources") or []
        for s in sources:
            url = (s.get("url") or "").strip()
            if url:
                known_urls.add(url)

    system = COMPARE_EVENTS_SYSTEM_MESSAGE.format(taxonomy=RISK_TAXONOMY, today=today)

    user = f"Today: {today}\n\nSources:\n{source_block}"
    out = event_compare_llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    events = out.get("events") or []

    cleaned_events: List[EventCluster] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        evidence_urls = [
            url for url in (ev.get("evidence_urls") or []) if url in known_urls
        ]
        cleaned_events.append(
            {
                "title": (ev.get("title") or "").strip(),
                "taxonomy": ev.get("taxonomy") or [],
                "summary": (ev.get("summary") or "").strip(),
                "evidence_urls": evidence_urls,
            }
        )

    return {"event_clusters": cleaned_events}

from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from models import source_verifier_llm
from prompts.system_messages import SOURCE_VERIFIER_SYSTEM_MESSAGE
from schemas import State, TaxonomyWebReport, WebSearchResult


def _format_sources_for_verification(sources: List[WebSearchResult]) -> str:
    lines: List[str] = []
    for i, s in enumerate(sources, start=1):
        title = (s.get("title") or "Untitled").strip()
        url = (s.get("url") or "").strip()
        snippet = (s.get("snippet") or "").strip()
        published = (s.get("published") or "").strip()
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
    return "\n\n".join(lines) if lines else "(No sources provided.)"


def verify_sources_node(state: State) -> Dict[str, Any]:
    """
    Verifies reliability of web search sources and annotates reports.
    Produces verified_taxonomy_reports (non-aggregated) for downstream nodes.
    """
    reports = state.get("taxonomy_reports", []) or []
    if not reports:
        return {"verified_taxonomy_reports": []}

    system = SOURCE_VERIFIER_SYSTEM_MESSAGE.format(
        today=datetime.now(timezone.utc).strftime("%B %d, %Y")
    )

    verified_reports: List[TaxonomyWebReport] = []

    for report in reports:
        sources = report.get("sources") or []
        if not sources:
            verified_reports.append(
                {
                    **report,
                    "reliable_sources": [],
                    "verification_notes": "No sources to verify.",
                }
            )
            continue

        source_block = _format_sources_for_verification(sources)
        user = f"Taxonomy: {(report.get('taxonomy') or '').strip()}\n\nSources:\n{source_block}"

        out = source_verifier_llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        assessments = out.get("sources") or []
        by_url = {
            (a.get("url") or "").strip(): a
            for a in assessments
            if (a.get("url") or "").strip()
        }

        updated_sources: List[WebSearchResult] = []
        for s in sources:
            url = (s.get("url") or "").strip()
            assessment = by_url.get(url)
            if assessment:
                updated_sources.append(
                    {
                        **s,
                        "reliability": assessment.get("reliability", "Unknown"),
                        "reliability_rationale": assessment.get("rationale", ""),
                        "source_type": assessment.get("source_type", "Unknown"),
                    }
                )
            else:
                updated_sources.append(
                    {
                        **s,
                        "reliability": "Unknown",
                        "reliability_rationale": "No assessment returned.",
                        "source_type": "Unknown",
                    }
                )

        reliable_sources = [
            s
            for s in updated_sources
            if s.get("reliability") in ("High", "Medium")
        ]
        if not reliable_sources:
            reliable_sources = updated_sources

        notes = f"Reliable sources: {len(reliable_sources)} of {len(updated_sources)}."

        verified_reports.append(
            {
                **report,
                "sources": updated_sources,
                "reliable_sources": reliable_sources,
                "verification_notes": notes,
            }
        )

    return {"verified_taxonomy_reports": verified_reports}

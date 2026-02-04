from __future__ import annotations

from typing import Any, Dict, List
import re
import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from models import event_risk_summarizer_llm
from prompts.system_messages import (
    EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_USER_MESSAGE,
)
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.risk_taxonomy import RISK_TAXONOMY
from schemas import RiskDraft, State, TaxonomyWebReport, WebSearchResult
from helper_functions import normalize_citations_and_sources, dedupe_risks


def _build_source_lookup(reports: List[TaxonomyWebReport]) -> Dict[str, WebSearchResult]:
    lookup: Dict[str, WebSearchResult] = {}
    for report in reports:
        sources = report.get("reliable_sources") or report.get("sources") or []
        for s in sources:
            url = (s.get("url") or "").strip()
            if url and url not in lookup:
                lookup[url] = s
    return lookup


def _format_sources(urls: List[str], lookup: Dict[str, WebSearchResult]) -> str:
    lines: List[str] = []
    for i, url in enumerate(urls, start=1):
        source = lookup.get(url, {})
        title = (source.get("title") or "Untitled").strip()
        snippet = (source.get("snippet") or "").strip()
        published = (source.get("published") or "").strip()
        reliability = (source.get("reliability") or "").strip()
        reliability_line = f"Reliability: {reliability}" if reliability else "Reliability: Unknown"
        lines.append(
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
    return "\n\n".join(lines).strip() if lines else "(No sources provided.)"


def _citation_indices(text: str) -> List[int]:
    if not text:
        return []
    matches = re.findall(r"\[(\d+)\]", text)
    indices: List[int] = []
    for m in matches:
        if m.isdigit():
            indices.append(int(m))
    return sorted(set(indices))


def _select_cited_sources(
    narrative: str,
    reasoning: str,
    source_pool: List[str],
) -> List[str]:
    indices = sorted(set(_citation_indices(narrative) + _citation_indices(reasoning)))
    if not indices:
        return []
    valid_indices = [i for i in indices if 1 <= i <= len(source_pool)]
    return [f"{i}. {source_pool[i - 1]}" for i in valid_indices]


def summarize_events_node(state: State) -> Dict[str, Any]:
    """
    Converts consolidated events into RiskDrafts where each potential path
    becomes its own risk event (title).
    """
    events = state.get("event_clusters") or []
    reports = state.get("verified_taxonomy_reports") or state.get("taxonomy_reports") or []

    if not events:
        return {"draft_risks": []}

    today = datetime.now().strftime("%B %d, %Y")
    lookup = _build_source_lookup(reports)

    all_urls: List[str] = []
    seen_urls = set()
    for ev in events:
        for url in ev.get("evidence_urls") or []:
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_urls.append(url)

    source_block = _format_sources(all_urls, lookup)

    system = EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE.format(
        today=today,
        taxonomy=RISK_TAXONOMY,
        PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
    )
    user = EVENT_PATH_RISKDRAFT_USER_MESSAGE.format(
        events_json=json.dumps(events, indent=2),
        sources_block=source_block,
    )

    out = event_risk_summarizer_llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    if not isinstance(out, dict):
        return {"draft_risks": []}
    risks = out.get("risks") or []

    cleaned: List[RiskDraft] = []
    for r in risks:
        if not isinstance(r, dict):
            continue
        portfolio_relevance = (r.get("portfolio_relevance") or "").strip()
        if portfolio_relevance not in ("High", "Medium", "Low"):
            portfolio_relevance = "Medium"
        portfolio_relevance_rationale = (r.get("portfolio_relevance_rationale") or "").strip()
        if not portfolio_relevance_rationale:
            portfolio_relevance_rationale = "Relevance not specified; requires review."
        sources_pool = all_urls[:]
        normalized_sources = _select_cited_sources(
            (r.get("narrative") or "").strip(),
            (r.get("reasoning_trace") or "").strip(),
            sources_pool,
        )
        cleaned.append(
            normalize_citations_and_sources({
                "title": (r.get("title") or "").strip(),
                "category": r.get("category") or [],
                "narrative": (r.get("narrative") or "").strip(),
                "reasoning_trace": (r.get("reasoning_trace") or "").strip(),
                "audit_log": [],
                "portfolio_relevance": portfolio_relevance,
                "portfolio_relevance_rationale": portfolio_relevance_rationale,
                "sources": normalized_sources,
            })
        )

    cleaned = dedupe_risks(cleaned)
    return {"draft_risks": cleaned}

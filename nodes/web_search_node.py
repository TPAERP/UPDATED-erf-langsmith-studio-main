from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from models import web_query_llm, web_report_llm, web_search_llm
from schemas import TaxonomyExecutionState, TaxonomyWebReport, WebSearchResult


def _find_sources(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, list):
        out: List[Dict[str, Any]] = []
        for item in obj:
            out.extend(_find_sources(item))
        return out

    if isinstance(obj, dict):
        out: List[Dict[str, Any]] = []

        sources = obj.get("sources")
        if isinstance(sources, list) and all(isinstance(s, dict) for s in sources):
            out.extend(sources)

        for value in obj.values():
            out.extend(_find_sources(value))
        return out

    return []


def _extract_web_search_results(message: Any) -> List[WebSearchResult]:
    payload: Any = []

    # 1. Check content first (modern LangChain/OpenAI standard)
    if hasattr(message, "content"):
        payload = message.content
    # 2. Fallbacks for other metadata locations
    elif isinstance(message, dict):
        payload = message
    elif hasattr(message, "response_metadata") and getattr(message, "response_metadata"):
        payload = message.response_metadata
    elif hasattr(message, "additional_kwargs") and getattr(message, "additional_kwargs"):
        payload = message.additional_kwargs

    raw_sources = _find_sources(payload)
    print(f"raw_sources: {raw_sources}")
    results: List[WebSearchResult] = []
    seen_urls = set()
    for s in raw_sources:
        url = (s.get("url") or s.get("link") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        results.append(
            {
                "title": (s.get("title") or s.get("name") or "").strip(),
                "url": url,
                "snippet": (s.get("snippet") or s.get("description") or s.get("text") or "").strip(),
                "published": (s.get("published") or s.get("date") or s.get("published_date") or "").strip(),
            }
        )
    print(f"extract results: {results}")
    return results


def _search(query: str, *, num: int = 4) -> List[WebSearchResult]:
    message = web_search_llm.invoke(query)
    print(f"message: {message}")
    return _extract_web_search_results(message)[:num]


def _plan_queries(taxonomy: str, *, today_iso: str) -> List[str]:
    system = """
        You generate concise web search queries for a horizon-scanning analyst.

        Rules:
        - Focus on developments from the last 7–14 days relative to today's date.
        - Prefer queries that surface specific events (policy decisions, macro releases, conflicts, regulations, outages).
        - Return 1 queries, each <= 12 words.
        - No quotes, no markdown, no commentary.
        """.strip()

    user = f"Taxonomy: {taxonomy}\nToday (UTC): {today_iso}"
    out = web_query_llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    queries = [q.strip() for q in (out.get("queries") or []) if isinstance(q, str) and q.strip()]

    if not queries: # if no queries were generated, use these hard coded queries
        return [
            f"{taxonomy} latest developments",
            f"{taxonomy} policy changes last week",
            f"{taxonomy} market impact recent",
        ]

    # converts to lowercase to check for duplicates, and returns max 5 queries
    deduped: List[str] = []
    seen = set()
    for q in queries:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(q)
    return deduped[:5]


def web_search_node(state: TaxonomyExecutionState) -> Dict[str, Any]:
    """Generate queries + search the web + write a per-taxonomy brief."""
    taxonomy = (state.get("taxonomy") or "").strip()
    generated_at = datetime.now(timezone.utc).isoformat()
    today_iso = generated_at[:10]

    if not taxonomy:
        return {
            "taxonomy_reports": [
                {
                    "taxonomy": "",
                    "queries": [],
                    "sources": [],
                    "brief_md": "No taxonomy provided to web_search node.",
                    "generated_at": generated_at,
                }
            ]
        }

    queries = _plan_queries(taxonomy, today_iso=today_iso)

    # for each of the queries, perform a search function
    sources: List[WebSearchResult] = []
    seen_urls = set()
    for q in queries[:4]:
        for r in _search(q, num=4): 
            url = (r.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(r)
    print(sources)
    source_lines: List[str] = []
    for i, s in enumerate(sources[:20], start=1):
        published = f" ({s['published']})" if s.get("published") else ""
        source_lines.append(f"[{i}] {s['title']}{published}\n{s['url']}\n{s['snippet']}".strip())
    sources_block = "\n\n".join(source_lines) if source_lines else "(No results returned.)"

    report_system = """
        You are writing a concise 'what's happening now' horizon-scan brief for an institutional risk taxonomy.

        Hard rules:
        - Use ONLY the provided search results as evidence; do not fabricate facts.
        - If evidence is thin, say so explicitly.
        - Prefer concrete dates, actors, and actions when present in snippets.
        - Output Markdown with this exact structure:
        1) A single H2 header with the taxonomy and 'as of' date
        2) 4–7 bullets of key developments (one sentence each)
        3) A final short paragraph: 'Assessment:' with 2–3 sentences
        - In each bullet, cite sources using bracket references like [1], [2] that correspond to the numbered list.
        """.strip()

    report_user = f"""
        Taxonomy: {taxonomy}
        As of (UTC): {today_iso}

        Search results:
        {sources_block}
        """.strip()

    report_msg = web_report_llm.invoke([SystemMessage(content=report_system), HumanMessage(content=report_user)])

    content = getattr(report_msg, "content", "")

    if isinstance(content, list):
        # Join all text blocks into a single string
        brief_md = "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block) 
            for block in content
        ).strip()
    else:
        brief_md = str(content).strip()

    if not brief_md:
        brief_md = f"## {taxonomy} (as of {today_iso})\n\n- No brief generated."

    report: TaxonomyWebReport = {
        "taxonomy": taxonomy,
        "queries": queries,
        "sources": sources[:50],
        "brief_md": brief_md,
        "generated_at": generated_at,
    }
    return {"taxonomy_reports": [report]}


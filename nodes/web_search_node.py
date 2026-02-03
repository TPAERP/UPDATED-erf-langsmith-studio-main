import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from models import web_query_llm, web_report_llm
from schemas import TaxonomyExecutionState, TaxonomyWebReport, WebSearchResult


class WebSearchConfigError(RuntimeError):
    pass


def _pick_provider() -> str:
    provider = (os.getenv("WEB_SEARCH_PROVIDER") or "").strip().lower()
    if provider in {"ddg", "duckduckgo", "duckduckgosearch"}:
        return "ddg"
    if provider in {"serper", "brave", "bing"}:
        return provider

    if os.getenv("SERPER_API_KEY"):
        return "serper"
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    if os.getenv("BING_API_KEY"):
        return "bing"
    return "ddg"


def _http_json(
    *,
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
    timeout_s: int = 25,
) -> Dict[str, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _serper_search(query: str, *, num: int = 4, time_range: str = "w") -> List[WebSearchResult]:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise WebSearchConfigError("Missing SERPER_API_KEY for Serper search provider.")

    payload: Dict[str, Any] = {"q": query, "num": num}
    if time_range:
        payload["tbs"] = f"qdr:{time_range}"

    data = _http_json(
        method="POST",
        url="https://google.serper.dev/search",
        headers={"X-API-KEY": api_key},
        body=payload,
    )

    organic = data.get("organic") or []
    out: List[WebSearchResult] = []
    for item in organic[:num]:
        out.append(
            {
                "title": (item.get("title") or "").strip(),
                "url": (item.get("link") or "").strip(),
                "snippet": (item.get("snippet") or "").strip(),
                "published": (item.get("date") or "").strip(),
            }
        )
    return out


def _brave_search(query: str, *, num: int = 4) -> List[WebSearchResult]:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        raise WebSearchConfigError("Missing BRAVE_API_KEY for Brave search provider.")

    qs = urllib.parse.urlencode({"q": query, "count": str(num), "text_decorations": "false"})
    data = _http_json(
        method="GET",
        url=f"https://api.search.brave.com/res/v1/web/search?{qs}",
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        body=None,
    )

    results = (((data.get("web") or {}).get("results")) or [])[:num]
    out: List[WebSearchResult] = []
    for item in results:
        out.append(
            {
                "title": (item.get("title") or "").strip(),
                "url": (item.get("url") or "").strip(),
                "snippet": (item.get("description") or "").strip(),
                "published": (item.get("page_age") or "").strip(),
            }
        )
    return out


def _bing_search(query: str, *, num: int = 4) -> List[WebSearchResult]:
    api_key = os.getenv("BING_API_KEY")
    if not api_key:
        raise WebSearchConfigError("Missing BING_API_KEY for Bing search provider.")

    qs = urllib.parse.urlencode({"q": query, "count": str(num), "mkt": "en-US"})
    data = _http_json(
        method="GET",
        url=f"https://api.bing.microsoft.com/v7.0/search?{qs}",
        headers={"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"},
        body=None,
    )

    results = (data.get("webPages") or {}).get("value") or []
    out: List[WebSearchResult] = []
    for item in results[:num]:
        out.append(
            {
                "title": (item.get("name") or "").strip(),
                "url": (item.get("url") or "").strip(),
                "snippet": (item.get("snippet") or "").strip(),
                "published": (item.get("dateLastCrawled") or "").strip(),
            }
        )
    return out


def _ddg_search(query: str, *, num: int = 4) -> List[WebSearchResult]:
    """
    DuckDuckGo search without API keys.

    Prefers the `duckduckgo_search` library if present; otherwise falls back to
    parsing the DuckDuckGo HTML results page.
    """
    try:
        # Optional dependency; user may not have it installed.
        from duckduckgo_search import DDGS  # type: ignore

        out: List[WebSearchResult] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=num):
                out.append(
                    {
                        "title": (item.get("title") or "").strip(),
                        "url": (item.get("href") or "").strip(),
                        "snippet": (item.get("body") or "").strip(),
                        "published": "",
                    }
                )
        return out
    except Exception:
        pass

    # Fallback: scrape the HTML endpoint (best-effort).
    qs = urllib.parse.urlencode({"q": query})
    url = f"https://duckduckgo.com/html/?{qs}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "text/html",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Very small parser: extract result anchors + snippets.
    import html as _html
    import re

    # Links are typically: <a rel="nofollow" class="result__a" href="...">Title</a>
    link_re = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE)
    snippet_re = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.IGNORECASE)
    tag_re = re.compile(r"<[^>]+>")

    links = link_re.findall(html)
    snippets = snippet_re.findall(html)

    out: List[WebSearchResult] = []
    for i, (href, title_html) in enumerate(links[:num]):
        title = _html.unescape(tag_re.sub("", title_html)).strip()
        snippet = _html.unescape(tag_re.sub("", snippets[i])).strip() if i < len(snippets) else ""
        out.append(
            {
                "title": title,
                "url": href.strip(),
                "snippet": snippet,
                "published": "",
            }
        )
    return out


def _search(query: str, *, num: int = 4) -> List[WebSearchResult]:
    provider = _pick_provider()
    if provider == "ddg":
        return _ddg_search(query, num=num)
    if provider == "serper":
        return _serper_search(query, num=num)
    if provider == "brave":
        return _brave_search(query, num=num)
    if provider == "bing":
        return _bing_search(query, num=num)
    raise WebSearchConfigError(f"Unsupported provider: {provider}")


def _plan_queries(taxonomy: str, *, today_iso: str) -> List[str]:
    system = """
You generate concise web search queries for a horizon-scanning analyst.

Rules:
- Focus on developments from the last 7–14 days relative to today's date.
- Prefer queries that surface specific events (policy decisions, macro releases, conflicts, regulations, outages).
- Return 3 to 5 queries, each <= 12 words.
- No quotes, no markdown, no commentary.
""".strip()

    user = f"Taxonomy: {taxonomy}\nToday (UTC): {today_iso}"
    out = web_query_llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    queries = [q.strip() for q in (out.get("queries") or []) if isinstance(q, str) and q.strip()]

    # Small safety net
    if not queries:
        return [f"{taxonomy} latest developments", f"{taxonomy} policy changes last week", f"{taxonomy} market impact recent"]

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

    try:
        provider = _pick_provider()
        queries = _plan_queries(taxonomy, today_iso=today_iso)
        sources: List[WebSearchResult] = []
        seen_urls = set()

        for q in queries[:4]:
            for r in _search(q, num=4):
                url = (r.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append(r)

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
        brief_md = (getattr(report_msg, "content", None) or "").strip()
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
    except WebSearchConfigError as e:
        return {
            "taxonomy_reports": [
                {
                    "taxonomy": taxonomy,
                    "queries": [],
                    "sources": [],
                    "brief_md": f"## {taxonomy} (as of {today_iso})\n\nWeb search is not configured: {e}",
                    "generated_at": generated_at,
                }
            ]
        }
    except Exception as e:  # pragma: no cover
        hint = (
            "\n\nTip: DuckDuckGo HTML search can be rate-limited; if this keeps failing, "
            "install the optional `duckduckgo-search` package or configure a key-based provider "
            "via `WEB_SEARCH_PROVIDER`."
            if provider == "ddg"
            else ""
        )
        return {
            "taxonomy_reports": [
                {
                    "taxonomy": taxonomy,
                    "queries": [],
                    "sources": [],
                    "brief_md": f"## {taxonomy} (as of {today_iso})\n\nWeb search failed: {type(e).__name__}: {e}{hint}",
                    "generated_at": generated_at,
                }
            ]
        }

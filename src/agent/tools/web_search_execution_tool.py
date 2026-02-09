from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from models import web_search_llm


def _find_sources(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        out: list[dict[str, Any]] = []
        for item in obj:
            out.extend(_find_sources(item))
        return out

    if isinstance(obj, dict):
        out: list[dict[str, Any]] = []
        sources = obj.get("sources")
        if isinstance(sources, list) and all(isinstance(source, dict) for source in sources):
            out.extend(sources)
        for value in obj.values():
            out.extend(_find_sources(value))
        return out

    return []


class WebSearchExecutionTool(KwargTool):
    name: str = "web_search_execution_tool"
    description: str = "Runs web searches and extracts normalized sources and query plans."

    def _run(self, **kwargs: Any) -> list[Any]:
        mode = str(kwargs.get("mode") or "search")
        if mode == "dedupe_queries":
            queries = list(kwargs.get("queries") or [])
            deduped: list[str] = []
            seen: set[str] = set()
            for query in queries:
                query_text = str(query).strip()
                if not query_text:
                    continue
                key = query_text.lower()
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(query_text)
            max_queries = int(kwargs.get("max_queries") or 5)
            return deduped[:max_queries]

        if mode == "extract_sources":
            message = kwargs.get("message")
            payload: Any = []
            if hasattr(message, "content"):
                payload = message.content
            elif isinstance(message, dict):
                payload = message
            elif hasattr(message, "response_metadata") and getattr(
                message, "response_metadata"
            ):
                payload = message.response_metadata
            elif hasattr(message, "additional_kwargs") and getattr(
                message, "additional_kwargs"
            ):
                payload = message.additional_kwargs
            raw_sources = _find_sources(payload)
            return self._normalize_sources(raw_sources, limit=int(kwargs.get("limit") or 20))

        query = str(kwargs.get("query") or "").strip()
        if not query:
            return []
        num = int(kwargs.get("num") or 10)
        client = kwargs.get("search_client") or web_search_llm
        message = client.invoke(query)
        raw_sources = _find_sources(getattr(message, "content", message))
        return self._normalize_sources(raw_sources, limit=num)

    @staticmethod
    def _normalize_sources(
        raw_sources: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for source in raw_sources:
            url = str(source.get("url") or source.get("link") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            normalized.append(
                {
                    "title": str(source.get("title") or source.get("name") or "").strip(),
                    "url": url,
                    "snippet": str(
                        source.get("snippet")
                        or source.get("description")
                        or source.get("text")
                        or ""
                    ).strip(),
                    "published": str(
                        source.get("published")
                        or source.get("date")
                        or source.get("published_date")
                        or ""
                    ).strip(),
                }
            )
            if len(normalized) >= limit:
                break
        return normalized

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("DEEPSEEK_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")

from agent.agents.web_search_agent import WebSearchAgent


class _StubSearchTool:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        mode = kwargs.get("mode")
        if mode == "dedupe_queries":
            raw = list(kwargs.get("queries") or [])
            max_queries = int(kwargs.get("max_queries") or 5)
            out: list[str] = []
            seen: set[str] = set()
            for query in raw:
                text = str(query).strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(text)
                if len(out) >= max_queries:
                    break
            return out

        query = str(kwargs.get("query") or "")
        num = int(kwargs.get("num") or 0)
        return [
            {
                "title": f"{query} result {i}",
                "url": f"https://example.com/{query.replace(' ', '-')}/{i}",
                "snippet": "snippet",
                "published": "",
            }
            for i in range(num)
        ]


class _StubBriefFormatter:
    def __init__(self) -> None:
        self.sources_block_counts: list[int] = []

    def run(self, **kwargs: Any) -> str:
        mode = str(kwargs.get("mode") or "")
        if mode == "sources_block":
            sources = list(kwargs.get("sources") or [])
            self.sources_block_counts.append(len(sources))
            return f"sources={len(sources)}"
        if mode == "normalize_brief":
            return str(kwargs.get("content") or "")
        return ""


def test_web_search_agent_executes_five_queries_with_ten_results_each() -> None:
    agent = WebSearchAgent.__new__(WebSearchAgent)
    search_tool = _StubSearchTool()
    brief_formatter = _StubBriefFormatter()

    agent.search_tool = search_tool
    agent.brief_formatter = brief_formatter
    agent.query_agent = lambda _state, **_kwargs: {  # type: ignore[assignment]
        "queries": ["one", "two", "three"]
    }
    agent.report_agent = lambda _state, **_kwargs: {"brief_md": "brief"}  # type: ignore[assignment]

    out = agent({"taxonomy": "Geopolitical"})

    assert len(out["queries"]) == 5
    search_calls = [call for call in search_tool.calls if "query" in call]
    assert len(search_calls) == 5
    assert all(int(call.get("num") or 0) == 10 for call in search_calls)
    assert len(out["sources"]) == 50
    assert brief_formatter.sources_block_counts[-1] == 50

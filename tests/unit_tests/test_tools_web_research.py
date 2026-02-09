from __future__ import annotations

from types import SimpleNamespace

from agent.tools.web_research import TaxonomyBriefFormattingTool, WebSearchExecutionTool


def test_web_search_execution_tool_dedupes_queries_and_ignores_unknown_kwargs():
    tool = WebSearchExecutionTool()
    out = tool.run(
        mode="dedupe_queries",
        queries=["US CPI release", "us cpi release", "ECB meeting"],
        max_queries=5,
        unexpected_arg=True,
    )
    assert out == ["US CPI release", "ECB meeting"]


def test_web_search_execution_tool_extracts_and_normalizes_sources():
    payload = [
        {
            "sources": [
                {
                    "title": "T1",
                    "url": "https://example.com/a",
                    "snippet": "A",
                    "published": "2026-02-01",
                },
                {
                    "title": "T1 duplicate",
                    "url": "https://example.com/a",
                    "snippet": "A2",
                },
            ]
        }
    ]
    message = SimpleNamespace(content=payload)
    tool = WebSearchExecutionTool()
    out = tool.run(mode="extract_sources", message=message, limit=10, ignored="x")
    assert len(out) == 1
    assert out[0]["url"] == "https://example.com/a"
    assert out[0]["title"] == "T1"


def test_web_search_execution_tool_search_mode_defaults_to_ten_results():
    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def invoke(self, _query, **kwargs):
            self.calls.append(dict(kwargs))
            return SimpleNamespace(
                content=[
                    {
                        "sources": [
                            {
                                "title": f"T{i}",
                                "url": f"https://example.com/{i}",
                                "snippet": "S",
                                "published": "2026-02-01",
                            }
                            for i in range(12)
                        ]
                    }
                ]
            )

    client = _StubClient()
    tool = WebSearchExecutionTool()
    out = tool.run(query="test query", search_client=client)
    assert len(out) == 10
    assert client.calls == [{"stream": False}]


def test_web_search_execution_tool_search_mode_falls_back_when_stream_kwarg_fails():
    class _StubClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def invoke(self, _query, **kwargs):
            self.calls.append(dict(kwargs))
            if kwargs:
                raise TypeError("unexpected keyword argument")
            return SimpleNamespace(
                content=[
                    {
                        "sources": [
                            {
                                "title": f"T{i}",
                                "url": f"https://example.com/{i}",
                                "snippet": "S",
                                "published": "2026-02-01",
                            }
                            for i in range(12)
                        ]
                    }
                ]
            )

    client = _StubClient()
    tool = WebSearchExecutionTool()
    out = tool.run(query="test query", search_client=client)
    assert len(out) == 10
    assert client.calls == [{"stream": False}, {}]


def test_taxonomy_brief_formatting_tool_formats_and_normalizes_brief():
    tool = TaxonomyBriefFormattingTool()
    block = tool.run(
        mode="sources_block",
        sources=[{"title": "Title", "url": "https://example.com", "snippet": "Snippet"}],
    )
    assert "[1] Title" in block
    assert "https://example.com" in block

    normalized = tool.run(
        mode="normalize_brief",
        content="",
        taxonomy="Geopolitical",
        today_iso="2026-02-06",
    )
    assert "## Geopolitical (as of 2026-02-06)" in normalized

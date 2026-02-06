from __future__ import annotations

from agent.tools.event_pipeline import (
    CompareInputFormattingTool,
    EventEvidenceFilterTool,
    EventToRiskSourceTool,
)


def test_compare_input_formatting_tool_formats_sources():
    tool = CompareInputFormattingTool()
    reports = [
        {
            "taxonomy": "Geopolitical",
            "sources": [{"title": "Source A", "url": "https://example.com/a"}],
        }
    ]
    out = tool.run(reports=reports, ignored=True)
    assert "Taxonomy: Geopolitical" in out
    assert "https://example.com/a" in out


def test_event_evidence_filter_tool_keeps_only_known_urls():
    tool = EventEvidenceFilterTool()
    out = tool.run(
        events=[
            {"title": "E1", "taxonomy": ["Geopolitical"], "summary": "s", "evidence_urls": ["u1", "u2"]},
            {"title": "E2", "taxonomy": [], "summary": "", "evidence_urls": ["u3"]},
        ],
        known_urls={"u2", "u3"},
    )
    assert out[0]["evidence_urls"] == ["u2"]
    assert out[1]["evidence_urls"] == ["u3"]


def test_event_to_risk_source_tool_builds_source_pool_and_block():
    tool = EventToRiskSourceTool()
    out = tool.run(
        reports=[
            {"sources": [{"url": "u1", "title": "A", "snippet": "s"}]},
            {"sources": [{"url": "u2", "title": "B", "snippet": "s"}]},
        ],
        events=[{"evidence_urls": ["u2", "u1", "u2"]}],
        unknown=True,
    )
    assert out["all_urls"] == ["u2", "u1"]
    assert "[1]" in out["sources_block"]

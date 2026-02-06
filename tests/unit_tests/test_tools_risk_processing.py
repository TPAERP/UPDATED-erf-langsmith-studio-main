from __future__ import annotations

from agent.tools.risk_processing import (
    AuditTrailTool,
    CitationNormalizationTool,
    CitationSelectionTool,
    RiskDeduplicationTool,
)


def test_citation_selection_tool_selects_cited_entries():
    tool = CitationSelectionTool()
    out = tool.run(
        narrative="This cites [2].",
        reasoning_trace="And this cites [1].",
        source_pool=["1. https://a", "2. https://b"],
        ignored=True,
    )
    assert out == ["1. https://a", "2. https://b"]


def test_citation_normalization_tool_reindexes_sources_and_text():
    tool = CitationNormalizationTool()
    normalized = tool.run(
        risk={
            "title": "R",
            "category": ["Geopolitical"],
            "narrative": "See [5].",
            "reasoning_trace": "Also [5].",
            "sources": ["5. https://example.com"],
        },
    )
    assert normalized["sources"] == ["1. https://example.com"]
    assert "[1]" in normalized["narrative"]


def test_risk_deduplication_tool_removes_duplicates():
    tool = RiskDeduplicationTool()
    risks = [
        {"title": "Same", "category": ["Geopolitical"], "narrative": "N", "sources": []},
        {"title": "Same", "category": ["Geopolitical"], "narrative": "N", "sources": []},
    ]
    deduped = tool.run(risks=risks, unknown=True)
    assert len(deduped) == 1


def test_audit_trail_tool_applies_defaults_and_appends_note():
    tool = AuditTrailTool()
    risk = tool.run(risk={"title": "R"}, append_note="checked")
    assert risk["audit_log"][-1] == "checked"
    assert risk["reasoning_trace"]

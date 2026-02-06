from __future__ import annotations

from agent.tools.source_quality import (
    SourceReliabilityMergeTool,
    SourceVerificationFormattingTool,
)


def test_source_verification_formatting_tool_builds_numbered_block():
    tool = SourceVerificationFormattingTool()
    out = tool.run(
        sources=[
            {
                "title": "Reuters",
                "url": "https://example.com/reuters",
                "snippet": "News",
                "published": "2026-02-01",
            }
        ],
        ignored=True,
    )
    assert "[1] Reuters" in out
    assert "URL: https://example.com/reuters" in out


def test_source_reliability_merge_tool_applies_assessments_and_fallbacks():
    tool = SourceReliabilityMergeTool()
    report = {"taxonomy": "Geopolitical"}
    sources = [
        {"url": "https://example.com/a", "title": "A"},
        {"url": "https://example.com/b", "title": "B"},
    ]
    assessments = [{"url": "https://example.com/a", "reliability": "High", "rationale": "Trusted"}]

    merged = tool.run(report=report, sources=sources, assessments=assessments, extra=1)
    assert merged["sources"][0]["reliability"] == "High"
    assert merged["sources"][1]["reliability"] == "Unknown"
    assert merged["verification_notes"].startswith("Reliable sources:")

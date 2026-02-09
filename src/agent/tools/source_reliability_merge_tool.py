from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool


class SourceReliabilityMergeTool(KwargTool):
    name: str = "source_reliability_merge_tool"
    description: str = "Merges reliability assessments into source records."

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        report = dict(kwargs.get("report") or {})
        sources = list(kwargs.get("sources") or report.get("sources") or [])
        assessments = list(kwargs.get("assessments") or [])
        by_url = {
            str(assessment.get("url") or "").strip(): assessment
            for assessment in assessments
            if str(assessment.get("url") or "").strip()
        }

        updated_sources: list[dict[str, Any]] = []
        for source in sources:
            url = str(source.get("url") or "").strip()
            assessment = by_url.get(url)
            if assessment:
                updated_sources.append(
                    {
                        **source,
                        "reliability": assessment.get("reliability", "Unknown"),
                        "reliability_rationale": assessment.get("rationale", ""),
                        "source_type": assessment.get("source_type", "Unknown"),
                    }
                )
            else:
                updated_sources.append(
                    {
                        **source,
                        "reliability": "Unknown",
                        "reliability_rationale": "No assessment returned.",
                        "source_type": "Unknown",
                    }
                )

        reliable_sources = [
            source
            for source in updated_sources
            if source.get("reliability") in ("High", "Medium")
        ]
        if not reliable_sources:
            reliable_sources = list(updated_sources)

        verification_notes = (
            f"Reliable sources: {len(reliable_sources)} of {len(updated_sources)}."
            if updated_sources
            else "No sources to verify."
        )

        return {
            **report,
            "sources": updated_sources,
            "reliable_sources": reliable_sources,
            "verification_notes": verification_notes,
        }

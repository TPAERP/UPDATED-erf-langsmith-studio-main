from __future__ import annotations

from typing import Any

from agent.tools.base import KwargTool

from helper_functions import normalize_citations_and_sources


class CitationNormalizationTool(KwargTool):
    name: str = "citation_normalization_tool"
    description: str = "Normalizes citation numbering and source indexing in a risk object."

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        risk = dict(kwargs.get("risk") or {})
        return normalize_citations_and_sources(risk)

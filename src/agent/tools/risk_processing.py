from __future__ import annotations

import re
from typing import Any

from agent.tools.base import KwargTool

from helper_functions import dedupe_risks, normalize_citations_and_sources


def _citation_indices(text: str) -> list[int]:
    if not text:
        return []
    matches = re.findall(r"\[(\d+)\]", text)
    indices: list[int] = []
    for match in matches:
        if match.isdigit():
            indices.append(int(match))
    return sorted(set(indices))


def _parse_indexed_sources(sources: list[str]) -> dict[int, str]:
    indexed: dict[int, str] = {}
    for entry in sources:
        if not isinstance(entry, str):
            continue
        parts = entry.split(".", 1)
        if len(parts) != 2:
            continue
        idx_part = parts[0].strip()
        if idx_part.isdigit():
            indexed[int(idx_part)] = parts[1].strip()
    return indexed


def _next_step_number(reasoning: str) -> int:
    count = 0
    for line in (reasoning or "").splitlines():
        if re.match(r"^\s*\d+\.\s", line):
            count += 1
    return count + 1


def _append_step(reasoning: str, title: str, text: str) -> str:
    step_number = _next_step_number(reasoning)
    line = f"{step_number}. **{title}**: {text}"
    return f"{reasoning}\n{line}".strip() if reasoning else line


class CitationSelectionTool(KwargTool):
    name: str = "citation_selection_tool"
    description: str = (
        "Selects and rehydrates only cited sources from narrative/reasoning text."
    )

    def _run(self, **kwargs: Any) -> list[str]:
        narrative = str(kwargs.get("narrative") or "")
        reasoning = str(kwargs.get("reasoning") or kwargs.get("reasoning_trace") or "")
        source_pool = list(kwargs.get("source_pool") or [])
        source_map_input = kwargs.get("source_map") or {}
        source_map = {
            int(key): str(value)
            for key, value in dict(source_map_input).items()
            if str(key).isdigit()
        }

        indices = sorted(set(_citation_indices(narrative) + _citation_indices(reasoning)))
        if not indices:
            return []

        fallback_sources: list[str] = []
        for entry in source_pool:
            if isinstance(entry, str):
                if "." in entry and entry.split(".", 1)[0].strip().isdigit():
                    fallback_sources.append(entry.split(".", 1)[1].strip())
                else:
                    fallback_sources.append(entry.strip())
            else:
                fallback_sources.append(str(entry))

        if not source_map:
            source_map = _parse_indexed_sources(
                [entry for entry in source_pool if isinstance(entry, str)]
            )

        selected: list[str] = []
        for idx in indices:
            if idx in source_map:
                selected.append(f"{idx}. {source_map[idx]}")
            elif 1 <= idx <= len(fallback_sources):
                selected.append(f"{idx}. {fallback_sources[idx - 1]}")
        return selected


class CitationNormalizationTool(KwargTool):
    name: str = "citation_normalization_tool"
    description: str = "Normalizes citation numbering and source indexing in a risk object."

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        risk = dict(kwargs.get("risk") or {})
        return normalize_citations_and_sources(risk)


class RiskDeduplicationTool(KwargTool):
    name: str = "risk_deduplication_tool"
    description: str = "Removes duplicate risks using canonicalized fingerprints."

    def _run(self, **kwargs: Any) -> list[dict[str, Any]]:
        risks = list(kwargs.get("risks") or [])
        return dedupe_risks(risks)


class AuditTrailTool(KwargTool):
    name: str = "audit_trail_tool"
    description: str = (
        "Ensures audit/reasoning defaults and appends governance notes or reasoning steps."
    )

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        risk = dict(kwargs.get("risk") or {})
        defaults = {
            "audit_log": kwargs.get(
                "default_audit_log",
                ["Draft generated during broad horizon scanning."],
            ),
            "reasoning_trace": kwargs.get("default_reasoning_trace", "Initial scan selection."),
            "portfolio_relevance": kwargs.get("default_portfolio_relevance", "Medium"),
            "portfolio_relevance_rationale": kwargs.get(
                "default_portfolio_relevance_rationale",
                "Relevance not specified; requires review.",
            ),
            "sources": kwargs.get("default_sources", []),
        }
        for key, value in defaults.items():
            if key not in risk:
                risk[key] = value if not isinstance(value, list) else list(value)

        append_note = kwargs.get("append_note")
        if append_note:
            risk["audit_log"] = list(risk.get("audit_log") or [])
            risk["audit_log"].append(str(append_note))

        step_title = kwargs.get("step_title")
        step_text = kwargs.get("step_text")
        if step_title and step_text:
            risk["reasoning_trace"] = _append_step(
                str(risk.get("reasoning_trace") or ""),
                str(step_title),
                str(step_text),
            )

        return risk

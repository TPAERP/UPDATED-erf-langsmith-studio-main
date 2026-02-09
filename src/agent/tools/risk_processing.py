"""Compatibility re-exports for risk-processing tools."""

from .audit_trail_tool import AuditTrailTool, _append_step, _next_step_number
from .citation_normalization_tool import CitationNormalizationTool
from .citation_selection_tool import (
    CitationSelectionTool,
    _citation_indices,
    _parse_indexed_sources,
)
from .risk_deduplication_tool import RiskDeduplicationTool

__all__ = [
    "CitationSelectionTool",
    "CitationNormalizationTool",
    "RiskDeduplicationTool",
    "AuditTrailTool",
]

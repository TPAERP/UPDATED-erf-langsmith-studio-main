"""New LangGraph Agent.

This module defines a custom graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.graph import graph as graph


def __getattr__(name: str) -> Any:
    if name == "graph":
        from agent.graph import graph

        return graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["graph"]

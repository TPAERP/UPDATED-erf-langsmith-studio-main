from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool


class KwargTool(BaseTool):
    """Base tool that supports direct kwargs invocation for controller/agent internals."""

    def run(self, tool_input: Any = None, **kwargs: Any) -> Any:  # type: ignore[override]
        payload: dict[str, Any] = {}
        if isinstance(tool_input, dict):
            payload.update(tool_input)
        elif tool_input not in (None, ""):
            payload["tool_input"] = tool_input
        payload.update(kwargs)
        return self._run(**payload)

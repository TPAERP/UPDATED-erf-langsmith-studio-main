from __future__ import annotations

from agent.agents.router_agent import RouterAgent as NewRouterAgent
from agent.agents.workflow_agents import (
    RouterAgent as LegacyRouterAgent,
)
from agent.agents.workflow_agents import build_workflow_agents
from agent.tools.risk_deduplication_tool import (
    RiskDeduplicationTool as NewRiskDeduplicationTool,
)
from agent.tools.risk_processing import (
    RiskDeduplicationTool as LegacyRiskDeduplicationTool,
)


def test_tool_import_compatibility_for_risk_deduplication():
    assert NewRiskDeduplicationTool is LegacyRiskDeduplicationTool


def test_agent_import_compatibility_for_router():
    assert NewRouterAgent is LegacyRouterAgent


def test_workflow_builder_import_is_available():
    assert callable(build_workflow_agents)

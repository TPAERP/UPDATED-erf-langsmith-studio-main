from schemas import State
from agent.agents.registry import router_agent


def router_node(state: State) -> str:
    """Route user request to scan, update, or Q&A workflows."""
    return router_agent(state)

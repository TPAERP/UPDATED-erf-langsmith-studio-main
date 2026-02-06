from langchain_core.messages import AIMessage

from agent.agents.registry import render_report_agent
from schemas import State


def render_report_node(state: State):
    """Controller node: delegate markdown rendering of final risk register."""
    final_md = render_report_agent(state)
    return {"messages": [AIMessage(content=final_md)]}

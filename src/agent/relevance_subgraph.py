from langgraph.graph import StateGraph, START, END

from schemas import State
from nodes.initiate_parallel_relevance_node import initiate_parallel_relevance
from nodes.assess_portfolio_relevance_node import assess_portfolio_relevance_node


def build_relevance_subgraph():
    relevance_builder = StateGraph(State)
    relevance_builder.add_node("initiate_relevance", lambda state: state)
    relevance_builder.add_node(
        "assess_portfolio_relevance",
        assess_portfolio_relevance_node,
    )

    relevance_builder.add_edge(START, "initiate_relevance")
    relevance_builder.add_conditional_edges(
        "initiate_relevance",
        initiate_parallel_relevance,
        ["assess_portfolio_relevance"],
    )
    relevance_builder.add_edge("assess_portfolio_relevance", END)

    return relevance_builder.compile(name="relevance_subgraph")

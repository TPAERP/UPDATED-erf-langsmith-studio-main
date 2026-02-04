from langgraph.graph import StateGraph, START, END

from schemas import State
from nodes.verify_sources_node import verify_sources_node
from nodes.compare_events_node import compare_events_node
from nodes.summarize_events_node import summarize_events_node
from nodes.initiate_parallel_web_search_node import initiate_parallel_web_search
from nodes.web_search_node import web_search_node
from nodes.web_search_join_node import web_search_join_router


def _prepare_scan_state(state: State):
    return {
        # Ensure keys exist before parallel fan-out
        "taxonomy_reports": [],
        "verified_taxonomy_reports": [],
        "event_clusters": [],
        "draft_risks": [],
        "finalized_risks": [],
        "attempts": state.get("attempts", 0),
    }


def build_scan_subgraph():
    scan_builder = StateGraph(State)
    scan_builder.add_node("initiate_web_search", _prepare_scan_state)
    scan_builder.add_node("web_search", web_search_node)
    scan_builder.add_node("web_search_join", lambda state: state)
    scan_builder.add_node("verify_sources", verify_sources_node)
    scan_builder.add_node("compare_events", compare_events_node)
    scan_builder.add_node("summarize_events", summarize_events_node)

    scan_builder.add_edge(START, "initiate_web_search")
    scan_builder.add_conditional_edges(
        "initiate_web_search",
        initiate_parallel_web_search,
        ["web_search"],
    )
    scan_builder.add_edge("web_search", "web_search_join")
    scan_builder.add_conditional_edges(
        "web_search_join",
        web_search_join_router,
        {"verify_sources": "verify_sources", "end": END},
    )
    scan_builder.add_edge("verify_sources", "compare_events")
    scan_builder.add_edge("compare_events", "summarize_events")
    scan_builder.add_edge("summarize_events", END)

    return scan_builder.compile(name="scan_subgraph")

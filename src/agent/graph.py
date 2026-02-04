from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import sys
from pathlib import Path
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")

load_dotenv(override=True)

# Ensure ./src is on the Python import path when this file is loaded directly
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# import prompts
from prompts.system_messages import *
from prompts.portfolio_allocation import *
from prompts.source_guide import *

# import schemas
from schemas import *

# import helper functions
from helper_functions import *

# import nodes
from nodes.router_node import *
from nodes.verify_sources_node import *
from nodes.compare_events_node import *
from nodes.summarize_events_node import *
from nodes.initiate_parallel_relevance_node import *
from nodes.assess_portfolio_relevance_node import *
from nodes.relevance_join_node import *
from nodes.initiate_parallel_web_search_node import *
from nodes.web_search_node import *
from nodes.web_search_join_node import *
from nodes.render_report_node import *
from nodes.risk_updater_node import *
from nodes.elaborator_node import *


# building graph

graph_builder = StateGraph(State)
graph_builder.add_node("router", lambda state: state) # router returns current state

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

graph_builder.add_node("initiate_web_search", _prepare_scan_state)
graph_builder.add_node("verify_sources", verify_sources_node)
graph_builder.add_node("compare_events", compare_events_node)
graph_builder.add_node("summarize_events", summarize_events_node)
graph_builder.add_node("initiate_relevance", lambda state: state)
graph_builder.add_node("assess_portfolio_relevance", assess_portfolio_relevance_node)
graph_builder.add_node("relevance_join", lambda state: state)
graph_builder.add_node("web_search", web_search_node)
graph_builder.add_node("web_search_join", lambda state: state)
graph_builder.add_node("render_report", render_report_node)
graph_builder.add_node("risk_updater", risk_updater_node)
graph_builder.add_node("elaborator", elaborator_node)

graph_builder.add_edge(START, "router")
graph_builder.add_conditional_edges(
    "router",
    router_node,
    {
        "initiate_web_search": "initiate_web_search",
        "risk_updater": "risk_updater",
        "elaborator": "elaborator",
    }
)

graph_builder.add_conditional_edges("initiate_web_search", initiate_parallel_web_search, ["web_search"])
graph_builder.add_edge("web_search", "web_search_join")
graph_builder.add_conditional_edges(
    "web_search_join",
    web_search_join_router,
    {"verify_sources": "verify_sources", "end": END},
)

graph_builder.add_edge("verify_sources", "compare_events")
graph_builder.add_edge("compare_events", "summarize_events")
graph_builder.add_conditional_edges(
    "summarize_events",
    relevance_router,
    {"initiate_relevance": "initiate_relevance", "render_report": "render_report"},
)
graph_builder.add_conditional_edges(
    "initiate_relevance",
    initiate_parallel_relevance,
    ["assess_portfolio_relevance"],
)
graph_builder.add_edge("assess_portfolio_relevance", "relevance_join")
graph_builder.add_conditional_edges(
    "relevance_join",
    relevance_join_router,
    {"render_report": "render_report", "end": END},
)
graph_builder.add_edge("render_report", END)
graph_builder.add_edge("risk_updater", END)
graph_builder.add_edge("elaborator", END)

graph = graph_builder.compile()

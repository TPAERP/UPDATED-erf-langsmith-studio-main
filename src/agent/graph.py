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
from nodes.relevance_join_node import *
from nodes.render_report_node import *
from nodes.risk_updater_node import *
from nodes.elaborator_node import *

from agent.scan_subgraph import build_scan_subgraph
from agent.relevance_subgraph import build_relevance_subgraph


# building graph

graph_builder = StateGraph(State)
graph_builder.add_node("router", lambda state: state)  # router returns current state
graph_builder.add_node("scan_subgraph", build_scan_subgraph())
graph_builder.add_node("relevance_subgraph", build_relevance_subgraph())
graph_builder.add_node("relevance_join", lambda state: state)
graph_builder.add_node("render_report", render_report_node)
graph_builder.add_node("risk_updater", risk_updater_node)
graph_builder.add_node("elaborator", elaborator_node)

graph_builder.add_edge(START, "router")
graph_builder.add_conditional_edges(
    "router",
    router_node,
    {
        "initiate_web_search": "scan_subgraph",
        "risk_updater": "risk_updater",
        "elaborator": "elaborator",
    }
)

graph_builder.add_conditional_edges(
    "scan_subgraph",
    relevance_router,
    {"initiate_relevance": "relevance_subgraph", "render_report": "render_report"},
)
graph_builder.add_edge("relevance_subgraph", "relevance_join")
graph_builder.add_conditional_edges(
    "relevance_join",
    relevance_join_router,
    {"render_report": "render_report", "end": END},
)
graph_builder.add_edge("render_report", END)
graph_builder.add_edge("risk_updater", END)
graph_builder.add_edge("elaborator", END)

graph = graph_builder.compile()

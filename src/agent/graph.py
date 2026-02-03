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
from nodes.broad_scan_node import *
from nodes.initiate_parallel_web_search_node import *
from nodes.web_search_node import *
from nodes.web_search_join_node import *
from nodes.initiate_parallel_refinement_node import *
from nodes.refine_single_risk_node import *
from nodes.refinement_join_node import *
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
        "draft_risks": [],
        "finalized_risks": [],
        "attempts": state.get("attempts", 0),
    }

graph_builder.add_node("initiate_web_search", _prepare_scan_state)
graph_builder.add_node("broad_scan", broad_scan_node)
graph_builder.add_node("web_search", web_search_node)
graph_builder.add_node("web_search_join", lambda state: state)
graph_builder.add_node("refine_single_risk", refine_single_risk_node)
graph_builder.add_node("refinement_join", lambda state: state)
graph_builder.add_node("render_report", render_report_node)
graph_builder.add_node("risk_updater", risk_updater_node)
graph_builder.add_node("elaborator", elaborator_node)

graph_builder.add_edge(START, "router")
graph_builder.add_conditional_edges(
    "router",
    router_node,  # This function returns "broad_scan", "risk_updater", etc.
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
    {"broad_scan": "broad_scan", "end": END},
)

graph_builder.add_conditional_edges("broad_scan", initiate_parallel_refinement, ["refine_single_risk"])
graph_builder.add_edge("refine_single_risk", "refinement_join")
graph_builder.add_conditional_edges(
    "refinement_join",
    refinement_join_router,
    {"render_report": "render_report", "end": END},
)
graph_builder.add_edge("render_report", END)
graph_builder.add_edge("risk_updater", END)
graph_builder.add_edge("elaborator", END)

graph = graph_builder.compile()

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
from nodes.initiate_parallel_refinement_node import *
from nodes.refine_single_risk_node import *
from nodes.render_report_node import *


# building graph

graph_builder = StateGraph(State)
graph_builder.add_node("router", lambda state: state) # router returns current state
graph_builder.add_node("broad_scan", broad_scan_node)
graph_builder.add_node("refine_single_risk", refine_single_risk_node)
graph_builder.add_node("render_report", render_report_node)

graph_builder.add_edge(START, "router")
graph_builder.add_conditional_edges(
    "router",
    router_node,  # This function returns "broad_scan", "risk_updater", etc.
    {
        "broad_scan": "broad_scan",
    }
)

graph_builder.add_conditional_edges("broad_scan", initiate_parallel_refinement,["refine_single_risk"])
graph_builder.add_edge("refine_single_risk", "render_report")
graph_builder.add_edge("render_report", END)

graph = graph_builder.compile()
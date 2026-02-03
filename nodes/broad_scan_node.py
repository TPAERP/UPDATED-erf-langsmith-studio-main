from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from schemas import *
from models import broad_scanner_llm
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")


def broad_scan_node(state: State) -> Dict[str, Any]:
    """
    Performs a broad scan to generate initial risk drafts.
    Uses the broad scanner LLM to generate multiple risk drafts.
    """
    state.setdefault("risk", None)
    state.setdefault("attempts", 0)
    state.setdefault("messages", [])

    taxonomy = ["Geopolitical","Financial","Trade","Macroeconomics","Military conflict","Climate","Technological","Public Health"]

    system = BROAD_RISK_SCANNER_SYSTEM_MESSAGE.format(
        taxonomy=taxonomy,
        PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
        SOURCE_GUIDE=SOURCE_GUIDE,
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
        today=today
    )

    users_query = last_human_content(state["messages"])
    
    out = broad_scanner_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=users_query),
    ])

    # CHANGE: We populate 'draft_risks' instead of the generic 'risk' key
    # We also clear 'finalized_risks' to ensure a fresh start
    return {
        "draft_risks": out["risks"],
        "finalized_risks": [], # Reset output
        "messages": [AIMessage(content=f"Broad scan generated {len(out['risks'])} candidates. Refining in parallel...")],
    }

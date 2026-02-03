from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from prompts.risk_taxonomy import *
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

    taxonomy = RISK_TAXONOMY

    system = BROAD_RISK_SCANNER_SYSTEM_MESSAGE.format(
        taxonomy=taxonomy,
        PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
        SOURCE_GUIDE=SOURCE_GUIDE,
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
        today=today
    )

    taxonomy_reports = state.get("taxonomy_reports", []) or []
    if taxonomy_reports:
        briefs = "\n\n".join([(r.get("brief_md") or "").strip() for r in taxonomy_reports if (r.get("brief_md") or "").strip()])
        if briefs:
            system = "\n\n".join(
                [
                    system,
                    "--------------------------------------------------------------------",
                    "WEB HORIZON-SCAN BRIEFS (EVIDENCE INPUT)",
                    "--------------------------------------------------------------------",
                    "Use the briefs below as your primary evidence for 'what is happening now'.",
                    "Do NOT invent facts beyond these briefs; if evidence is missing, say so.",
                    briefs,
                ]
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

from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from schemas import *
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")


def render_report_node(state: State):
    """
    Renders the final risk register as markdown.
    """
    parts = []

    taxonomy_reports = state.get("taxonomy_reports", []) or []
    if taxonomy_reports:
        parts.append(format_taxonomy_reports_md(taxonomy_reports))

    finalized = state.get("finalized_risks", []) or []
    parts.append(format_all_risks_md(finalized))

    final_md = "\n\n".join([p for p in parts if p.strip()])
    return {"messages": [AIMessage(content=final_md)]}

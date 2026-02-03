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
    final_md = format_all_risks_md(state["finalized_risks"])
    return {"messages": [AIMessage(content=final_md)]}
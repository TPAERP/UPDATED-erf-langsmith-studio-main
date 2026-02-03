from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from schemas import *
from models import risk_updater_llm
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")

def risk_updater_node(state: State) -> Dict[str, Any]:
    state.setdefault("risk", None)
    state.setdefault("attempts", 0)
    state.setdefault("messages", [])

    taxonomy = ["Geopolitical","Financial","Trade","Macroeconomics","Military conflict","Climate","Technological","Public Health"]

    existing_register = state.get("risk")
    users_query = last_human_content(state["messages"])

    risk_updater_system_message = RISK_UPDATER_SYSTEM_MESSAGE.format(
        taxonomy=taxonomy,
        PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
        SOURCE_GUIDE=SOURCE_GUIDE,
        today=today
    )

    updater_user_message = f"""
            USER REQUEST:
            {users_query}

            EXISTING RISK REGISTER (JSON-like):
            {existing_register}

            Update the register following your instructions.
            """.strip()

    updated = risk_updater_llm.invoke([
        SystemMessage(content=risk_updater_system_message),
        HumanMessage(content=updater_user_message),
    ])

    updated_register = {"risks": updated["risks"]}

    md = []
    md.append("# Updated Risk Register\n")
    md.append(format_all_risks_md(updated_register["risks"]))
    md.append("\n# Change Log\n")
    for bullet in updated["change_log"]:
        md.append(f"- {bullet}")
    final_message = "\n".join(md)

    return {
        "risk": updated_register,
        "messages": [AIMessage(content=final_message)],
        "attempts": state.get("attempts", 0),
    }
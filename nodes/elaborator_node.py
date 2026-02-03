from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from schemas import *
from models import elaborator_llm
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")


def elaborator_node(state: State) -> Dict[str, Any]:
    messages = state.get("messages", []) or []
    last_query = last_human_content(messages)
    conversation = format_conversation(messages)
    current_register = state.get("risk")

    system_message = """
        You are conducting professional Q&A about the existing risk register.
        Answer concisely, in an institutional tone. Do not fabricate specifics.
        If the register is missing, say so and suggest running a scan.
        """.strip()

    user_message = f"""
        Current risk register (if any):
        {current_register}

        Conversation so far:
        {conversation}

        User question:
        {last_query}
        """.strip()

    resp = elaborator_llm.invoke([SystemMessage(content=system_message), HumanMessage(content=user_message)])

    return {
        "risk": state.get("risk"),
        "messages": [AIMessage(content=resp.content)],
        "attempts": state.get("attempts", 0),
    }

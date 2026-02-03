from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from helper_functions import *
from prompts.system_messages import *
from models import router_llm

def router_node(state: State) -> str:
    """
    Determines which path to take based on the last user query.
    Returns one of: "initiate_web_search", "risk_updater", "elaborator"
    """
    users_query = last_human_content(state.get("messages", []) or [])

    router_messages = [
        SystemMessage(content=ROUTER_SYSTEM_MESSAGE),
        HumanMessage(content=ROUTER_USER_MESSAGE.format(user_query=users_query)),
    ]
    out = router_llm.invoke(router_messages)

    if out["user_query_type"] == "scan":
        return "initiate_web_search"
    elif out["user_query_type"] == "update":
        return "risk_updater"
    else:
        return "elaborator"

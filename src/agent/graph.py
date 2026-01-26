from typing import Annotated, TypedDict, List, Dict, Any, Optional, Literal, cast
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from pydantic import Field
from dotenv import load_dotenv
import sys
from pathlib import Path

# Ensure ./src is on the Python import path when this file is loaded directly
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.prompts import (
    ROUTER_SYSTEM_MESSAGE,
    ROUTER_USER_MESSAGE,
    BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
    SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
    PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
    PER_RISK_EVALUATOR_USER_MESSAGE,
    RISK_UPDATER_SYSTEM_MESSAGE,
    SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
    SIGNPOST_GENERATOR_USER_MESSAGE,
    SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
    SIGNPOST_EVALUATOR_USER_MESSAGE,
    FEW_SHOT_EXAMPLES 
)

from agent.portfolio_allocation import PORTFOLIO_ALLOCATION
from agent.source_guide import SOURCE_GUIDE

load_dotenv(override=True)

# -----------------------------
# Schemas
# -----------------------------

class RouterOutput(TypedDict):
    user_query_type: Literal["scan", "update", "qna"] = Field(
        description="Whether user wants to scan, update existing register, or do Q&A"
    )

class RiskDraft(TypedDict):
    title: str = Field(description="Name of risk (concise, specific)")
    category: List[str] = Field(description="List of 1 to 3 taxonomy categories for this risk")
    narrative: str = Field(description="~150 word narrative of risk (scenario-based)")
    
    # --- AUDIT TRAIL FIELDS ---
    reasoning_trace: str = Field(
        default="", 
        description="A cohesive narrative paragraph summarizing the analyst's internal reasoning, signal selection, and materiality checks."
    )
    audit_log: List[str] = Field(
        default_factory=list, 
        description="Chronological log of governance events (reviews, rejections, revisions) formatted as narrative sentences."
    )

class BroadScanOutput(TypedDict):
    risks: List[RiskDraft] = Field(description="Draft risks from broad scanner")

class PerRiskEvalOutput(TypedDict):
    satisfied_with_risk: bool = Field(description="Whether this single risk is acceptable")
    feedback: str = Field(description="Actionable feedback if not acceptable (or brief OK note)")

class RiskUpdateOutput(TypedDict):
    risks: List[RiskDraft] = Field(description="Updated risk register")
    change_log: List[str] = Field(description="Bullet list describing what changed and why")

class Signpost(TypedDict):
    description: str = Field(description="Observable, monitorable indicator")
    status: Literal["Low", "Rising", "Elevated"] = Field(description="Low/Rising/Elevated")

class SignpostPack(TypedDict):
    signposts: List[Signpost] = Field(description="Exactly 3 signposts with status")

class SignpostEvalOutput(TypedDict):
    satisfied_with_signposts: bool = Field(description="Whether signposts are acceptable")
    feedback: str = Field(description="Actionable feedback if not acceptable")


class RiskFinal(TypedDict):
    title: str
    category: str
    narrative: str
    signposts: List[Signpost]
    # Pass audit trail to final output
    reasoning_trace: str
    audit_log: List[str]

class State(TypedDict):
    risk: Optional[BroadScanOutput]
    messages: Annotated[List[BaseMessage], add_messages]
    attempts: int

# -----------------------------
# LLMs
# -----------------------------

llm = "openai"  # "deepseek" or "openai"
if llm == "openai":
    model = "gpt-4o-mini"
    router_llm = ChatOpenAI(model=model).with_structured_output(RouterOutput)
    broad_scanner_llm = ChatOpenAI(model=model).with_structured_output(BroadScanOutput)
    specific_scanner_llm = ChatOpenAI(model=model).with_structured_output(RiskDraft)
    per_risk_evaluator_llm = ChatOpenAI(model=model).with_structured_output(PerRiskEvalOutput)
    signpost_generator_llm = ChatOpenAI(model=model).with_structured_output(SignpostPack)
    signpost_evaluator_llm = ChatOpenAI(model=model).with_structured_output(SignpostEvalOutput)
    risk_updater_llm = ChatOpenAI(model=model).with_structured_output(RiskUpdateOutput)
    elaborator_llm = ChatOpenAI(model=model)
elif llm == "deepseek":
    model = "deepseek-chat"
    router_llm = ChatDeepSeek(model=model).with_structured_output(RouterOutput)
    broad_scanner_llm = ChatDeepSeek(model=model).with_structured_output(BroadScanOutput)
    specific_scanner_llm = ChatDeepSeek(model=model).with_structured_output(RiskDraft)
    per_risk_evaluator_llm = ChatDeepSeek(model=model).with_structured_output(PerRiskEvalOutput)
    signpost_generator_llm = ChatDeepSeek(model=model).with_structured_output(SignpostPack)
    signpost_evaluator_llm = ChatDeepSeek(model=model).with_structured_output(SignpostEvalOutput)
    risk_updater_llm = ChatDeepSeek(model=model).with_structured_output(RiskUpdateOutput)
    elaborator_llm = ChatDeepSeek(model=model)  





# -----------------------------
# Helpers
# -----------------------------

def last_human_content(messages: List[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return cast(str, m.content)
    return ""

def format_risk_md(r: RiskDraft, i: int) -> str:
    categories = r["category"] if isinstance(r["category"], list) else [r["category"]]
    categories_str = ", ".join(categories)
    
    # Format Audit Trail as a narrative blockquote
    audit_section = ""
    if r.get("audit_log"):
        # Join as a single paragraph block
        audit_text = " ".join(r["audit_log"])
        audit_section += f"\n> **Governance History:**\n> {audit_text}\n"
    
    # Format Reasoning Trace as an italicized note
    reasoning_section = ""
    if r.get("reasoning_trace"):
        reasoning_section += f"\n_**Analyst Reasoning:** {r['reasoning_trace']}_\n"

    return "\n".join([
        f"## Risk {i}: {r['title']}",
        f"**Categories:** {categories_str}",
        "",
        "**Narrative**",
        r["narrative"].strip(),
        reasoning_section,
        audit_section,
        "",
        "---",
        ""
    ])

def format_all_risks_md(risks: List[RiskDraft]) -> str:
    md = ["# Risk Register\n"]
    for i, r in enumerate(risks, start=1):
        md.append(format_risk_md(r, i))
    return "\n".join(md)

def format_signposts_md(signposts: List[Signpost]) -> str:
    lines = ["**Signposts (3)**"]
    for sp in signposts:
        lines.append(f"- {sp['description']} — **{sp['status']}**")
    return "\n".join(lines)

def format_conversation(messages: List[Any]) -> str:
    conversation = "Conversation history:\n\n"
    for message in messages:
        if isinstance(message, HumanMessage):
            conversation += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            conversation += f"Assistant: {message.content}\n"
    return conversation

# -----------------------------
# Router
# -----------------------------

def router_node(state: State) -> str:
    users_query = last_human_content(state["messages"])

    router_messages = [
        SystemMessage(content=ROUTER_SYSTEM_MESSAGE),
        HumanMessage(content=ROUTER_USER_MESSAGE.format(user_query=users_query)),
    ]
    out = router_llm.invoke(router_messages)

    if out["user_query_type"] == "scan":
        return "broad_scan"
    elif out["user_query_type"] == "update":
        return "risk_updater"
    else:
        return "elaborator"

# -----------------------------
# Broad scan (no signposts)
# -----------------------------

def broad_scan_node(state: State) -> Dict[str, Any]:
    state.setdefault("risk", None)
    state.setdefault("attempts", 0)
    state.setdefault("messages", [])

    taxonomy = ["Geopolitical","Financial","Trade","Macroeconomics","Military conflict","Climate","Technological","Public Health"]

    system = BROAD_RISK_SCANNER_SYSTEM_MESSAGE.format(
        taxonomy=taxonomy,
        PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
        SOURCE_GUIDE=SOURCE_GUIDE,
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES
    )

    users_query = last_human_content(state["messages"])
    user_msg = f"User request / context (may be empty):\n{users_query}".strip()

    out = broad_scanner_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user_msg),
    ])

    return {
        "risk": out,
        "messages": [AIMessage(content=f"Broad scan produced {len(out['risks'])} draft risks. Refining each risk now...")],
        "attempts": state.get("attempts", 0),
    }

# -----------------------------
# Per-risk refinement loop (evaluator <-> specific scanner)
# -----------------------------

def refine_all_risks_node(state: State) -> Dict[str, Any]:
    state.setdefault("risk", None)
    state.setdefault("attempts", 0)
    state.setdefault("messages", [])

    if not state.get("risk") or not state["risk"].get("risks"):
        return {
            "messages": [AIMessage(content="No risks found to refine. Try running a scan first.")],
            "risk": state.get("risk"),
        }

    taxonomy = ["Geopolitical","Financial","Trade","Macroeconomics","Military conflict","Climate","Technological","Public Health"]

    max_rounds_per_risk = 4  # guardrail
    refined: List[RiskDraft] = []

    for idx, draft in enumerate(state["risk"]["risks"], start=1):
        current = draft
        
        # Initialize audit log with a narrative sentence if empty
        if "audit_log" not in current:
            current["audit_log"] = ["Draft generated during broad horizon scanning."]
        if "reasoning_trace" not in current:
            current["reasoning_trace"] = "Initial scan selection."

        for round_i in range(1, max_rounds_per_risk + 1):
            # 1) Evaluate single risk
            eval_system = PER_RISK_EVALUATOR_SYSTEM_MESSAGE.format(
                PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
                SOURCE_GUIDE=SOURCE_GUIDE,
            )
            eval_user = PER_RISK_EVALUATOR_USER_MESSAGE.format(
                taxonomy=taxonomy,
                risk=current,
            )

            eval_out = per_risk_evaluator_llm.invoke([
                SystemMessage(content=eval_system),
                HumanMessage(content=eval_user),
            ])

            if eval_out["satisfied_with_risk"]:
                # Log success as a narrative sentence
                current["audit_log"].append("Passed independent governance review.")
                break

            # 2) If not satisfied -> revise single risk
            # Log failure as a narrative sentence
            current["audit_log"].append(f"Independent evaluator flagged deficiencies: '{eval_out['feedback']}'.")

            spec_system = SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE.format(
                taxonomy=taxonomy,
                PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
                SOURCE_GUIDE=SOURCE_GUIDE,
                feedback=eval_out["feedback"],
                current_risk=current,
                FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES
            )

            users_query = last_human_content(state["messages"])
            spec_user = f"Revise the risk accordingly. User context:\n{users_query}".strip()

            new_draft = specific_scanner_llm.invoke([
                SystemMessage(content=spec_system),
                HumanMessage(content=spec_user),
            ])
            
            # 3) Merge Metadata
            # Append narrative revision note
            update_note = "Narrative refined to address evaluator feedback."
            new_draft["audit_log"] = current["audit_log"] + [update_note]
            
            current = new_draft

        refined.append(current)

    final_md = format_all_risks_md(refined)

    return {
        "risk": {"risks": refined},
        "messages": [AIMessage(content=final_md)],
        "attempts": state.get("attempts", 0),
    }

def add_signposts_all_risks_node(state: State) -> Dict[str, Any]:
    """
    Takes state['risk'] and returns {'risks': [RiskFinal...]} with signposts.
    Preserves audit trails.
    """
    state.setdefault("risk", None)
    state.setdefault("messages", [])

    if not state.get("risk") or not state["risk"].get("risks"):
        return {
            "messages": [AIMessage(content="No finalized risks found. Run scan/refine first.")],
            "risk": state.get("risk"),
        }

    taxonomy = ["Geopolitical","Financial","Trade","Macroeconomics","Military conflict","Climate","Technological","Public Health"]
    max_rounds_per_risk = 1
    final_risks: List[RiskFinal] = []

    for idx, risk in enumerate(state["risk"]["risks"], start=1):
        current_pack: Optional[SignpostPack] = None

        for round_i in range(1, max_rounds_per_risk + 1):
            # 1) Generate signposts
            gen_system = SIGNPOST_GENERATOR_SYSTEM_MESSAGE.format(
                taxonomy=taxonomy,
                PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
                SOURCE_GUIDE=SOURCE_GUIDE,
            )

            users_query = last_human_content(state["messages"])
            gen_user = SIGNPOST_GENERATOR_USER_MESSAGE.format(
                risk=risk,
                user_context=users_query,
                prior_signposts=current_pack,
                feedback=None,
            )

            if current_pack is None:
                current_pack = signpost_generator_llm.invoke([
                    SystemMessage(content=gen_system),
                    HumanMessage(content=gen_user),
                ])

            # 2) Evaluate signposts
            eval_system = SIGNPOST_EVALUATOR_SYSTEM_MESSAGE.format(
                PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
                SOURCE_GUIDE=SOURCE_GUIDE,
            )
            eval_user = SIGNPOST_EVALUATOR_USER_MESSAGE.format(
                taxonomy=taxonomy,
                risk=risk,
                signposts=current_pack,
            )

            eval_out = signpost_evaluator_llm.invoke([
                SystemMessage(content=eval_system),
                HumanMessage(content=eval_user),
            ])

            if eval_out["satisfied_with_signposts"]:
                break

            # 3) If rejected: regenerate
            regen_user = SIGNPOST_GENERATOR_USER_MESSAGE.format(
                risk=risk,
                user_context=users_query,
                prior_signposts=current_pack,
                feedback=eval_out["feedback"],
            )

            current_pack = signpost_generator_llm.invoke([
                SystemMessage(content=gen_system),
                HumanMessage(content=regen_user),
            ])

        # Finalize risk (Include Audit Data)
        final_risks.append({
            "title": risk["title"],
            "category": risk["category"],
            "narrative": risk["narrative"],
            "signposts": current_pack["signposts"] if current_pack else [],
            "reasoning_trace": risk.get("reasoning_trace", ""),
            "audit_log": risk.get("audit_log", [])
        })

    # Render output
    md = ["# Final Risk Register (with Signposts)\n"]
    for i, r in enumerate(final_risks, start=1):
        categories = r["category"] if isinstance(r["category"], list) else [r["category"]]
        categories_str = ", ".join(categories)
        md.append(f"## Risk {i}: {r['title']}")
        md.append(f"**Categories:** {categories_str}\n")
        md.append("**Narrative**")
        md.append(r["narrative"].strip() + "\n")
        
        # Display Audit info in final output
        if r.get("reasoning_trace"):
            md.append(f"_**Analyst Reasoning:** {r['reasoning_trace']}_")
        
        md.append(format_signposts_md(r["signposts"]))
        
        if r.get("audit_log"):
             # Join as paragraph
             log_text = " ".join(r["audit_log"])
             md.append(f"\n> **Governance History:**\n> {log_text}")
                 
        md.append("\n---\n")

    return {
        "risk": {"risks": final_risks},
        "messages": [AIMessage(content="\n".join(md))],
    }


# -----------------------------
# Risk updater
# -----------------------------

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

# -----------------------------
# QnA node
# -----------------------------

def elaborator_node(state: State) -> Dict[str, Any]:
    last_query = last_human_content(state["messages"])
    conversation = format_conversation(state["messages"])
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

# -----------------------------
# Build graph
# -----------------------------

graph_builder = StateGraph(State)

graph_builder.add_node("router", lambda state: state)
graph_builder.add_edge(START, "router")
graph_builder.add_node("broad_scan", broad_scan_node)
graph_builder.add_node("refine_all_risks", refine_all_risks_node)
# graph_builder.add_node("add_signposts_all_risks", add_signposts_all_risks_node)
graph_builder.add_node("risk_updater", risk_updater_node)
graph_builder.add_node("elaborator", elaborator_node)

graph_builder.add_conditional_edges(
    "router",
    router_node,
    {
        "broad_scan": "broad_scan",
        "risk_updater": "risk_updater",
        "elaborator": "elaborator",
    }
)

# broad_scan -> refine_all_risks -> add_signposts_all_risks -> END
graph_builder.add_edge("broad_scan", "refine_all_risks")
#graph_builder.add_edge("refine_all_risks", "add_signposts_all_risks")
graph_builder.add_edge("refine_all_risks", END)
#graph_builder.add_edge("add_signposts_all_risks", END)

# update -> end
graph_builder.add_edge("risk_updater", END)

# qna -> end
graph_builder.add_edge("elaborator", END)

memory = MemorySaver()
graph = graph_builder.compile()
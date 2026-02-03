from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from schemas import *
from models import signpost_evaluator_llm
from models import signpost_generator_llm
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")


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
                today=today
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
                today=today
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
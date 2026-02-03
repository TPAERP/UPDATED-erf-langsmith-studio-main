from prompts.system_messages import *
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.system_messages import *
from prompts.risk_taxonomy import *
from schemas import *
from models import per_risk_evaluator_llm
from models import specific_scanner_llm
from helper_functions import *
from datetime import datetime
today = datetime.now().strftime("%B %d, %Y")

taxonomy = RISK_TAXONOMY

def refine_single_risk_node(state: RiskExecutionState) -> Dict[str, Any]:
    """
    Processes a SINGLE risk entirely independently.
    Runs the Refiner <-> Evaluator loop for this specific item.
    """
    current = state["risk_candidate"]
    
    # Initialize audit trail if missing
    if "audit_log" not in current:
        current["audit_log"] = ["Draft generated during broad horizon scanning."]
    if "reasoning_trace" not in current:
        current["reasoning_trace"] = "Initial scan selection."

    max_rounds = 3  # Configurable

    for round_i in range(1, max_rounds + 1):
        # 1. Helper to format markdown for the LLM
        # (Using a simplified index '0' since we are isolated here)
        formatted_risk = format_risk_md(current, 0) 

        # 2. Evaluate
        eval_system = PER_RISK_EVALUATOR_SYSTEM_MESSAGE.format(
            PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
            SOURCE_GUIDE=SOURCE_GUIDE,
            today=today
        )
        eval_user = PER_RISK_EVALUATOR_USER_MESSAGE.format(
            taxonomy=taxonomy,
            risk=formatted_risk,
        )

        eval_out = per_risk_evaluator_llm.invoke([
            SystemMessage(content=eval_system),
            HumanMessage(content=eval_user),
        ])

        # 3. Decision Logic
        if eval_out["satisfied_with_risk"]:
            current["audit_log"].append("Passed independent governance review.")
            break # Exit loop, risk is done
        
        # 4. Revise if failed
        current["audit_log"].append(f"Evaluator Feedback: '{eval_out['feedback']}'.")
        
        spec_system = SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE.format(
            taxonomy=taxonomy,
            PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
            SOURCE_GUIDE=SOURCE_GUIDE,
            feedback=eval_out["feedback"],
            current_risk=formatted_risk,
            FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
            today=today
        )
        
        # Note: In a parallel node, we don't easily have access to the full conversation history 
        # unless we pass it in. Usually, the risk context + feedback is enough.
        spec_user = "Revise the risk strictly according to the feedback."

        new_draft = specific_scanner_llm.invoke([
            SystemMessage(content=spec_system),
            HumanMessage(content=spec_user),
        ])
        
        # Merge Audit Logs
        new_draft["audit_log"] = current["audit_log"] + ["Narrative refined to address feedback."]
        current = new_draft

    # RETURN: We return a dictionary that updates the Main State.
    # Because 'finalized_risks' is Annotated with operator.add, this list is APPENDED to the main state.
    return {"finalized_risks": [current]}
from prompts.system_messages import *
from langchain_core.messages import SystemMessage, HumanMessage
from prompts.source_guide import *
from prompts.portfolio_allocation import *
from prompts.risk_taxonomy import *
from schemas import *
from models import relevance_assessor_llm, relevance_reviewer_llm
from helper_functions import *
import re
from datetime import datetime

today = datetime.now().strftime("%B %d, %Y")
taxonomy = RISK_TAXONOMY


def _append_weak_relevance_note(narrative: str) -> str:
    note = (
        "Portfolio relevance remains weak after review; treat as lower priority "
        "for this portfolio."
    )
    if note.lower() in narrative.lower():
        return narrative
    if narrative.endswith("."):
        return f"{narrative} {note}"
    return f"{narrative}. {note}"


def _next_step_number(reasoning: str) -> int:
    count = 0
    for line in (reasoning or "").splitlines():
        if line.strip().startswith(tuple(f"{i}." for i in range(1, 100))):
            count += 1
    return count + 1


def _append_step(reasoning: str, title: str, text: str) -> str:
    step_num = _next_step_number(reasoning)
    step_line = f"{step_num}. **{title}**: {text}"
    if reasoning:
        return f"{reasoning}\n{step_line}"
    return step_line


def _citation_indices(text: str) -> List[int]:
    if not text:
        return []
    matches = re.findall(r"\[(\d+)\]", text)
    indices: List[int] = []
    for m in matches:
        if m.isdigit():
            indices.append(int(m))
    return sorted(set(indices))


def _parse_indexed_sources(sources: List[str]) -> Dict[int, str]:
    indexed: Dict[int, str] = {}
    for entry in sources:
        if not isinstance(entry, str):
            continue
        parts = entry.split(".", 1)
        if len(parts) != 2:
            continue
        idx_part = parts[0].strip()
        if not idx_part.isdigit():
            continue
        indexed[int(idx_part)] = parts[1].strip()
    return indexed


def _select_cited_sources(
    narrative: str,
    reasoning: str,
    source_map: Dict[int, str],
    fallback_sources: List[str],
) -> List[str]:
    indices = sorted(set(_citation_indices(narrative) + _citation_indices(reasoning)))
    if not indices:
        return []
    sources: List[str] = []
    for idx in indices:
        if idx in source_map:
            sources.append(f"{idx}. {source_map[idx]}")
        elif 1 <= idx <= len(fallback_sources):
            sources.append(f"{idx}. {fallback_sources[idx - 1]}")
    return sources


def assess_portfolio_relevance_node(state: RiskExecutionState) -> Dict[str, Any]:
    """
    Assesses and validates portfolio relevance for a SINGLE risk draft.
    """
    current = state["risk_candidate"]

    if "audit_log" not in current:
        current["audit_log"] = []
    if "reasoning_trace" not in current:
        current["reasoning_trace"] = "Initial scan selection."

    max_rounds = 3

    passed = False
    last_feedback = "None"
    source_pool = current.get("sources") or []
    source_map = _parse_indexed_sources(source_pool)
    fallback_sources = [entry.split(".", 1)[-1].strip() if isinstance(entry, str) and "." in entry else entry for entry in source_pool]
    for _round_i in range(1, max_rounds + 1):
        formatted_risk = format_risk_md(current, 0)

        assessor_system = PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE.format(
            PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
            SOURCE_GUIDE=SOURCE_GUIDE,
            today=today,
        )
        assessor_user = (
            "Assess portfolio relevance for this risk draft.\n"
            f"Prior reviewer feedback: {last_feedback}\n\n"
            f"{formatted_risk}"
        )

        assessed = relevance_assessor_llm.invoke(
            [SystemMessage(content=assessor_system), HumanMessage(content=assessor_user)]
        )

        portfolio_relevance = (assessed.get("portfolio_relevance") or "").strip()
        if portfolio_relevance not in ("High", "Medium", "Low"):
            portfolio_relevance = "Medium"
        portfolio_relevance_rationale = (assessed.get("portfolio_relevance_rationale") or "").strip()
        if not portfolio_relevance_rationale:
            portfolio_relevance_rationale = "Relevance not specified; requires review."

        current = {
            **current,
            "portfolio_relevance": portfolio_relevance,
            "portfolio_relevance_rationale": portfolio_relevance_rationale,
            "reasoning_trace": (assessed.get("reasoning_trace") or current.get("reasoning_trace") or "").strip(),
            "sources": assessed.get("sources") or current.get("sources") or [],
        }
        normalized_sources = _select_cited_sources(
            current.get("narrative", ""),
            current.get("reasoning_trace", ""),
            source_map,
            fallback_sources,
        )
        current["sources"] = normalized_sources

        reviewer_system = PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE.format(
            PORTFOLIO_ALLOCATION=PORTFOLIO_ALLOCATION,
            today=today,
        )
        reviewer_user = PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE.format(
            taxonomy=taxonomy,
            risk=format_risk_md(current, 0),
        )

        review_out = relevance_reviewer_llm.invoke(
            [SystemMessage(content=reviewer_system), HumanMessage(content=reviewer_user)]
        )

        if review_out.get("satisfied_with_relevance"):
            current["audit_log"].append("Portfolio relevance validated.")
            passed = True
            break

        feedback = review_out.get("feedback") or "Relevance assessment requires revision."
        last_feedback = feedback
        current["audit_log"].append(f"Relevance reviewer feedback: '{feedback}'.")

    if not passed:
        current["portfolio_relevance"] = "Low"
        if not current.get("portfolio_relevance_rationale"):
            current["portfolio_relevance_rationale"] = "Relevance judged weak after review."
        current["reasoning_trace"] = _append_step(
            current.get("reasoning_trace", ""),
            "Feedback & Revisions",
            f"Reviewer feedback: {last_feedback}. Marked relevance as Low and flagged for de-prioritization.",
        )
        current["narrative"] = _append_weak_relevance_note(current.get("narrative", ""))
        current["audit_log"].append("Portfolio relevance flagged as weak after review.")
    elif not current.get("portfolio_relevance") in ("High", "Medium", "Low"):
        current["portfolio_relevance"] = "Medium"
    if "Portfolio Relevance" not in (current.get("reasoning_trace") or ""):
        current["reasoning_trace"] = _append_step(
            current.get("reasoning_trace", ""),
            "Portfolio Relevance",
            f"Rated {current['portfolio_relevance']}: {current.get('portfolio_relevance_rationale','')}",
        )

    return {"finalized_risks": [current]}

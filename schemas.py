from typing import Annotated, TypedDict, List, Dict, Any, Optional, Literal, cast
from pydantic import Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langgraph.graph.message import add_messages
import operator

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
        description="Strict numbered list (1., 2., 3...) detailing the step-by-step derivation of the risk."
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

class WebQueryPlan(TypedDict):
    queries: List[str] = Field(description="List of web search queries to run")


class WebSearchResult(TypedDict):
    title: str = Field(description="Result title")
    url: str = Field(description="Result URL")
    snippet: str = Field(description="Result snippet/description")
    published: str = Field(description="Published date if available, else empty string")


class TaxonomyWebReport(TypedDict):
    taxonomy: str = Field(description="Risk taxonomy category")
    queries: List[str] = Field(description="Queries executed for this taxonomy")
    sources: List[WebSearchResult] = Field(description="Flattened list of search results used")
    brief_md: str = Field(description="Markdown brief summarizing what is happening now")
    generated_at: str = Field(description="ISO timestamp when generated")


class State(TypedDict, total=False):
    # Existing structured register (used by updater/Q&A flows)
    risk: Dict[str, Any]

    # Drafts (input) vs finalized (output)
    draft_risks: List[RiskDraft]

    # operator.add ensures that when parallel nodes return a list,
    # they are appended to this master list rather than overwriting it.
    finalized_risks: Annotated[List[RiskDraft], operator.add]

    # Parallel web research (one report per taxonomy)
    taxonomy_reports: Annotated[List[TaxonomyWebReport], operator.add]

    messages: Annotated[List[BaseMessage], add_messages]
    attempts: int

# This is the "Sub-State" passed to each parallel worker
class RiskExecutionState(TypedDict):
    risk_candidate: RiskDraft


class TaxonomyExecutionState(TypedDict):
    taxonomy: str

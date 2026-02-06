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
    title: str = Field(description="Potential risk event/path (concise, specific)")
    category: List[str] = Field(description="List of 1 to 3 taxonomy categories for this risk")
    narrative: str = Field(description="~150 word narrative of risk (scenario-based)")
    portfolio_relevance: Literal["High", "Medium", "Low"] = Field(
        description="Portfolio relevance rating"
    )
    portfolio_relevance_rationale: str = Field(
        description="Short rationale tied to portfolio allocation and transmission"
    )
    sources: List[str] = Field(
        description="List of cited sources, prefixed with their citation index (e.g., '12. https://...')"
    )
    
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


class RelevanceReviewOutput(TypedDict):
    satisfied_with_relevance: bool = Field(description="Whether portfolio relevance is acceptable")
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


class WebBriefOutput(TypedDict):
    brief_md: str = Field(description="Markdown brief for a taxonomy")


class ElaboratorOutput(TypedDict):
    answer: str = Field(description="Answer text for risk register Q&A")


class WebSearchResultBase(TypedDict):
    title: str = Field(description="Result title")
    url: str = Field(description="Result URL")
    snippet: str = Field(description="Result snippet/description")
    published: str = Field(description="Published date if available, else empty string")


class WebSearchResult(WebSearchResultBase, total=False):
    reliability: Literal["High", "Medium", "Low", "Unknown"] = Field(
        description="Assessed reliability of the source"
    )
    reliability_rationale: str = Field(
        description="Brief rationale for the reliability label"
    )
    source_type: str = Field(
        description="Source type such as official, major newsroom, trade press, think tank, blog, aggregator"
    )


class SourceReliability(TypedDict):
    url: str = Field(description="Source URL")
    reliability: Literal["High", "Medium", "Low", "Unknown"] = Field(
        description="Reliability label"
    )
    rationale: str = Field(description="Brief rationale for the label")
    source_type: str = Field(description="Source type classification")


class SourceReliabilityOutput(TypedDict):
    sources: List[SourceReliability] = Field(description="Reliability labels per source")


class EventCluster(TypedDict):
    title: str = Field(description="Consolidated event title")
    taxonomy: List[str] = Field(description="Relevant taxonomy categories")
    summary: str = Field(description="1-2 sentence event summary with timing")
    evidence_urls: List[str] = Field(description="List of supporting source URLs")


class EventClusterOutput(TypedDict):
    events: List[EventCluster] = Field(description="Merged, deduplicated events")


class EventRiskDraftOutput(TypedDict):
    risks: List[RiskDraft] = Field(
        description="RiskDrafts derived from consolidated events and paths"
    )


class TaxonomyWebReportBase(TypedDict):
    taxonomy: str = Field(description="Risk taxonomy category")
    queries: List[str] = Field(description="Queries executed for this taxonomy")
    sources: List[WebSearchResult] = Field(description="Flattened list of search results used")
    brief_md: str = Field(description="Markdown brief summarizing what is happening now")
    generated_at: str = Field(description="ISO timestamp when generated")


class TaxonomyWebReport(TaxonomyWebReportBase, total=False):
    reliable_sources: List[WebSearchResult] = Field(
        description="Subset of sources deemed reliable"
    )
    verification_notes: str = Field(description="Brief verification summary")


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
    verified_taxonomy_reports: List[TaxonomyWebReport]
    event_clusters: List[EventCluster]

    messages: Annotated[List[BaseMessage], add_messages]
    attempts: int

# This is the "Sub-State" passed to each parallel worker
class RiskExecutionState(TypedDict):
    risk_candidate: RiskDraft


class TaxonomyExecutionState(TypedDict):
    taxonomy: str

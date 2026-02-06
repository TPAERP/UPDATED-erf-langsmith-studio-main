from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from agent.agents.base_agent import BaseAgent
from agent.tools.event_pipeline import (
    CompareInputFormattingTool,
    EventEvidenceFilterTool,
    EventToRiskSourceTool,
)
from agent.tools.reporting import (
    ConversationContextTool,
    RiskMarkdownRenderTool,
    UpdateRenderTool,
)
from agent.tools.risk_processing import (
    AuditTrailTool,
    CitationNormalizationTool,
    CitationSelectionTool,
    RiskDeduplicationTool,
)
from agent.tools.signposts import SignpostAssemblyTool
from agent.tools.source_quality import (
    SourceReliabilityMergeTool,
    SourceVerificationFormattingTool,
)
from agent.tools.web_research import TaxonomyBriefFormattingTool, WebSearchExecutionTool
from helper_functions import format_risk_md, format_signposts_md
from models import DEEPSEEK_MODEL, LLM_PROVIDER, OPENAI_MODEL
from prompts.portfolio_allocation import PORTFOLIO_ALLOCATION
from prompts.relevance_prompts import (
    PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE,
)
from prompts.reporting_prompts import ELABORATOR_SYSTEM_MESSAGE
from prompts.risk_taxonomy import RISK_TAXONOMY
from prompts.router_prompts import ROUTER_SYSTEM_MESSAGE, ROUTER_USER_MESSAGE
from prompts.scan_prompts import (
    BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
    COMPARE_EVENTS_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_USER_MESSAGE,
    FEW_SHOT_EXAMPLES,
    PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
    PER_RISK_EVALUATOR_USER_MESSAGE,
    SOURCE_VERIFIER_SYSTEM_MESSAGE,
    SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
)
from prompts.signpost_prompts import (
    SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
    SIGNPOST_EVALUATOR_USER_MESSAGE,
    SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
    SIGNPOST_GENERATOR_USER_MESSAGE,
)
from prompts.source_guide import SOURCE_GUIDE
from prompts.update_prompts import RISK_UPDATER_SYSTEM_MESSAGE
from schemas import (
    BroadScanOutput,
    ElaboratorOutput,
    EventClusterOutput,
    EventRiskDraftOutput,
    PerRiskEvalOutput,
    RelevanceReviewOutput,
    RiskDraft,
    RiskUpdateOutput,
    RouterOutput,
    SignpostEvalOutput,
    SignpostPack,
    SourceReliabilityOutput,
    WebBriefOutput,
    WebQueryPlan,
)


def _today_long() -> str:
    return datetime.now().strftime("%B %d, %Y")


def _today_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _provider_llm_factory(model: str) -> Any:
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(model=model, use_responses_api=True)
    return ChatDeepSeek(model=model)


def _default_model_name() -> str:
    return OPENAI_MODEL if LLM_PROVIDER == "openai" else DEEPSEEK_MODEL


def _router_message_builder(
    system_prompt: str,
    _state: dict[str, Any],
    runtime_context: dict[str, Any],
) -> list[Any]:
    user_query = str(runtime_context.get("user_query") or "")
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=ROUTER_USER_MESSAGE.format(user_query=user_query)),
    ]


def _single_user_message_builder(user_template: str) -> Any:
    def _builder(
        system_prompt: str,
        _state: dict[str, Any],
        runtime_context: dict[str, Any],
    ) -> list[Any]:
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_template.format(**runtime_context)),
        ]

    return _builder


def _refiner_message_builder(
    system_prompt: str,
    _state: dict[str, Any],
    _runtime_context: dict[str, Any],
) -> list[Any]:
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Revise the risk strictly according to the feedback."),
    ]


class RouterAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.conversation_tool = ConversationContextTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.conversation_tool],
            output_format=RouterOutput,
            system_template=ROUTER_SYSTEM_MESSAGE,
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_router_message_builder,
        )

    def __call__(self, state: dict[str, Any]) -> str:
        context = self.conversation_tool.run(messages=state.get("messages", []) or [])
        output = self.base_agent(state, user_query=context.get("last_user_query", ""))
        user_query_type = output.get("user_query_type")
        if user_query_type == "scan":
            return "initiate_web_search"
        if user_query_type == "update":
            return "risk_updater"
        return "elaborator"


class BroadScanAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.conversation_tool = ConversationContextTool()
        self.brief_formatter = TaxonomyBriefFormattingTool()
        self.risk_deduper = RiskDeduplicationTool()
        system_template = "\n\n".join(
            [
                BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
                "{web_briefs_section}",
            ]
        )
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.brief_formatter, self.risk_deduper],
            output_format=BroadScanOutput,
            system_template=system_template,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
                "FEW_SHOT_EXAMPLES": FEW_SHOT_EXAMPLES,
                "web_briefs_section": "",
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder("{user_query}"),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        context = self.conversation_tool.run(messages=state.get("messages", []) or [])
        taxonomy_reports = list(state.get("taxonomy_reports", []) or [])
        briefs: list[str] = []
        for report in taxonomy_reports:
            brief_text = self.brief_formatter.run(
                mode="normalize_brief",
                content=report.get("brief_md") or "",
                taxonomy=report.get("taxonomy") or "",
                today_iso=_today_iso_utc(),
            )
            if brief_text:
                briefs.append(brief_text)

        web_briefs_section = ""
        if briefs:
            web_briefs_section = "\n".join(
                [
                    "--------------------------------------------------------------------",
                    "WEB HORIZON-SCAN BRIEFS (EVIDENCE INPUT)",
                    "--------------------------------------------------------------------",
                    "Use the briefs below as your primary evidence for 'what is happening now'.",
                    "Do NOT invent facts beyond these briefs; if evidence is missing, say so.",
                    "\n\n".join(briefs),
                ]
            )

        out = self.base_agent(
            state,
            user_query=context.get("last_user_query", ""),
            web_briefs_section=web_briefs_section,
        )
        risks = list(out.get("risks") or [])
        return self.risk_deduper.run(risks=risks)


class WebSearchAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.search_tool = WebSearchExecutionTool()
        self.brief_formatter = TaxonomyBriefFormattingTool()
        self.query_agent = BaseAgent(
            model=model,
            skills=[self.search_tool],
            output_format=WebQueryPlan,
            system_template=(
                "You generate concise web search queries for a horizon-scanning analyst.\n\n"
                "Rules:\n"
                "- Focus on developments from the last 7-14 days relative to today's date.\n"
                "- Prefer queries that surface specific events (policy decisions, macro releases, conflicts, regulations, outages).\n"
                "- Return 1 to 5 queries, each <= 12 words.\n"
                "- No quotes, no markdown, no commentary.\n"
                "- Return JSON with key 'queries'."
            ),
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Taxonomy: {taxonomy}\nToday (UTC): {today_iso}"
            ),
        )
        self.report_agent = BaseAgent(
            model=model,
            skills=[self.brief_formatter],
            output_format=WebBriefOutput,
            system_template=(
                "You write concise horizon-scan markdown briefs for an institutional risk taxonomy.\n"
                "Use ONLY provided search results, avoid fabrication, and cite sources like [1], [2].\n"
                "Return JSON with key 'brief_md' only."
            ),
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Taxonomy: {taxonomy}\nAs of (UTC): {today_iso}\n\nSearch results:\n{sources_block}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        taxonomy = str(state.get("taxonomy") or "").strip()
        generated_at = datetime.now(timezone.utc).isoformat()
        today_iso = generated_at[:10]

        if not taxonomy:
            return {
                "taxonomy": "",
                "queries": [],
                "sources": [],
                "brief_md": "No taxonomy provided to web_search node.",
                "generated_at": generated_at,
            }

        query_out = self.query_agent({}, taxonomy=taxonomy, today_iso=today_iso)
        queries = self.search_tool.run(
            mode="dedupe_queries",
            queries=query_out.get("queries") or [],
            max_queries=5,
        )
        if not queries:
            queries = [
                f"{taxonomy} latest developments",
                f"{taxonomy} policy changes last week",
                f"{taxonomy} market impact recent",
            ]

        sources: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for query in queries[:4]:
            query_results = self.search_tool.run(query=query, num=4)
            for result in query_results:
                url = str(result.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append(result)

        sources_block = self.brief_formatter.run(mode="sources_block", sources=sources[:20])
        report_out = self.report_agent(
            {},
            taxonomy=taxonomy,
            today_iso=today_iso,
            sources_block=sources_block,
        )
        brief_md = self.brief_formatter.run(
            mode="normalize_brief",
            content=report_out.get("brief_md", ""),
            taxonomy=taxonomy,
            today_iso=today_iso,
        )

        return {
            "taxonomy": taxonomy,
            "queries": queries,
            "sources": sources[:50],
            "brief_md": brief_md,
            "generated_at": generated_at,
        }


class VerifySourcesAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.format_tool = SourceVerificationFormattingTool()
        self.merge_tool = SourceReliabilityMergeTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.format_tool, self.merge_tool],
            output_format=SourceReliabilityOutput,
            system_template=SOURCE_VERIFIER_SYSTEM_MESSAGE,
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Taxonomy: {taxonomy}\n\nSources:\n{source_block}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        reports = list(state.get("taxonomy_reports", []) or [])
        verified_reports: list[dict[str, Any]] = []
        for report in reports:
            sources = list(report.get("sources") or [])
            if not sources:
                verified_reports.append(
                    {
                        **report,
                        "reliable_sources": [],
                        "verification_notes": "No sources to verify.",
                    }
                )
                continue
            source_block = self.format_tool.run(sources=sources)
            out = self.base_agent(
                {},
                taxonomy=str(report.get("taxonomy") or "").strip(),
                source_block=source_block,
            )
            merged = self.merge_tool.run(
                report=report,
                sources=sources,
                assessments=out.get("sources") or [],
            )
            verified_reports.append(merged)
        return verified_reports


class CompareEventsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.format_tool = CompareInputFormattingTool()
        self.filter_tool = EventEvidenceFilterTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.format_tool, self.filter_tool],
            output_format=EventClusterOutput,
            system_template=COMPARE_EVENTS_SYSTEM_MESSAGE,
            static_context={"taxonomy": RISK_TAXONOMY},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Today: {today}\n\nSources:\n{source_block}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        reports = list(
            state.get("verified_taxonomy_reports")
            or state.get("taxonomy_reports")
            or []
        )
        if not reports:
            return []
        source_block = self.format_tool.run(reports=reports)
        known_urls: set[str] = set()
        for report in reports:
            sources = report.get("reliable_sources") or report.get("sources") or []
            for source in sources:
                url = str(source.get("url") or "").strip()
                if url:
                    known_urls.add(url)
        out = self.base_agent({}, source_block=source_block)
        events = list(out.get("events") or [])
        return self.filter_tool.run(events=events, known_urls=known_urls)


class SummarizeEventsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.source_tool = EventToRiskSourceTool()
        self.citation_tool = CitationSelectionTool()
        self.normalization_tool = CitationNormalizationTool()
        self.deduper = RiskDeduplicationTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[
                self.source_tool,
                self.citation_tool,
                self.normalization_tool,
                self.deduper,
            ],
            output_format=EventRiskDraftOutput,
            system_template=EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(EVENT_PATH_RISKDRAFT_USER_MESSAGE),
        )

    def __call__(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        events = list(state.get("event_clusters") or [])
        reports = list(
            state.get("verified_taxonomy_reports")
            or state.get("taxonomy_reports")
            or []
        )
        if not events:
            return []

        source_meta = self.source_tool.run(reports=reports, events=events)
        out = self.base_agent(
            {},
            events_json=json.dumps(events, indent=2),
            sources_block=source_meta["sources_block"],
        )
        risks = list(out.get("risks") or [])

        cleaned: list[dict[str, Any]] = []
        all_urls = list(source_meta.get("all_urls") or [])
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            portfolio_relevance = str(risk.get("portfolio_relevance") or "").strip()
            if portfolio_relevance not in ("High", "Medium", "Low"):
                portfolio_relevance = "Medium"
            portfolio_relevance_rationale = str(
                risk.get("portfolio_relevance_rationale") or ""
            ).strip()
            if not portfolio_relevance_rationale:
                portfolio_relevance_rationale = "Relevance not specified; requires review."

            sources = self.citation_tool.run(
                narrative=str(risk.get("narrative") or "").strip(),
                reasoning=str(risk.get("reasoning_trace") or "").strip(),
                source_pool=all_urls,
            )
            normalized = self.normalization_tool.run(
                risk={
                    "title": str(risk.get("title") or "").strip(),
                    "category": risk.get("category") or [],
                    "narrative": str(risk.get("narrative") or "").strip(),
                    "reasoning_trace": str(risk.get("reasoning_trace") or "").strip(),
                    "audit_log": [],
                    "portfolio_relevance": portfolio_relevance,
                    "portfolio_relevance_rationale": portfolio_relevance_rationale,
                    "sources": sources,
                }
            )
            cleaned.append(normalized)

        return self.deduper.run(risks=cleaned)


class RefineRiskAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.audit_tool = AuditTrailTool()
        self.normalize_tool = CitationNormalizationTool()
        self.evaluator = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.normalize_tool],
            output_format=PerRiskEvalOutput,
            system_template=PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                PER_RISK_EVALUATOR_USER_MESSAGE.replace("{risk}", "{risk_md}")
            ),
        )
        self.refiner = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.normalize_tool],
            output_format=RiskDraft,
            system_template=SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
                "FEW_SHOT_EXAMPLES": FEW_SHOT_EXAMPLES,
                "feedback": "",
                "current_risk": "",
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_refiner_message_builder,
        )

    def __call__(self, risk_candidate: dict[str, Any]) -> dict[str, Any]:
        current = self.audit_tool.run(risk=risk_candidate)
        max_rounds = 3
        for _round in range(1, max_rounds + 1):
            formatted_risk = format_risk_md(current, 0)
            eval_out = self.evaluator({}, taxonomy=RISK_TAXONOMY, risk_md=formatted_risk)
            if eval_out.get("satisfied_with_risk"):
                current = self.audit_tool.run(
                    risk=current,
                    append_note="Passed independent governance review.",
                )
                break

            feedback = str(eval_out.get("feedback") or "Risk requires revision.")
            current = self.audit_tool.run(
                risk=current,
                append_note=f"Evaluator Feedback: '{feedback}'.",
            )
            new_draft = self.refiner(
                {},
                feedback=feedback,
                current_risk=formatted_risk,
            )
            if "portfolio_relevance" not in new_draft:
                new_draft["portfolio_relevance"] = current.get("portfolio_relevance", "Medium")
            if "portfolio_relevance_rationale" not in new_draft:
                new_draft["portfolio_relevance_rationale"] = current.get(
                    "portfolio_relevance_rationale",
                    "Relevance not specified; requires review.",
                )
            if "sources" not in new_draft:
                new_draft["sources"] = current.get("sources", [])
            new_draft["audit_log"] = list(current.get("audit_log") or []) + [
                "Narrative refined to address feedback."
            ]
            current = self.normalize_tool.run(risk=new_draft)
        return current


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


class RelevanceAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.audit_tool = AuditTrailTool()
        self.citation_tool = CitationSelectionTool()
        self.normalization_tool = CitationNormalizationTool()
        self.assessor = BaseAgent(
            model=model,
            skills=[self.audit_tool, self.citation_tool, self.normalization_tool],
            output_format=RiskDraft,
            system_template=PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Assess portfolio relevance for this risk draft.\n"
                "Prior reviewer feedback: {last_feedback}\n\n"
                "{formatted_risk}"
            ),
        )
        self.reviewer = BaseAgent(
            model=model,
            skills=[self.audit_tool],
            output_format=RelevanceReviewOutput,
            system_template=PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE.replace(
                    "{risk}",
                    "{risk_md}",
                )
            ),
        )

    def __call__(self, risk_candidate: dict[str, Any]) -> dict[str, Any]:
        current = self.audit_tool.run(
            risk=risk_candidate,
            default_audit_log=[],
            default_reasoning_trace="Initial scan selection.",
        )
        max_rounds = 3
        passed = False
        last_feedback = "None"

        for _round in range(1, max_rounds + 1):
            formatted_risk = format_risk_md(current, 0)
            assessed = self.assessor(
                {},
                formatted_risk=formatted_risk,
                last_feedback=last_feedback,
            )
            portfolio_relevance = str(assessed.get("portfolio_relevance") or "").strip()
            if portfolio_relevance not in ("High", "Medium", "Low"):
                portfolio_relevance = "Medium"
            relevance_rationale = str(
                assessed.get("portfolio_relevance_rationale") or ""
            ).strip()
            if not relevance_rationale:
                relevance_rationale = "Relevance not specified; requires review."

            current = {
                **current,
                "portfolio_relevance": portfolio_relevance,
                "portfolio_relevance_rationale": relevance_rationale,
                "reasoning_trace": str(
                    assessed.get("reasoning_trace") or current.get("reasoning_trace") or ""
                ).strip(),
                "sources": assessed.get("sources") or current.get("sources") or [],
            }

            selected_sources = self.citation_tool.run(
                narrative=str(current.get("narrative") or ""),
                reasoning=str(current.get("reasoning_trace") or ""),
                source_pool=current.get("sources") or [],
            )
            current["sources"] = selected_sources
            current = self.normalization_tool.run(risk=current)

            review_out = self.reviewer({}, taxonomy=RISK_TAXONOMY, risk_md=format_risk_md(current, 0))
            if review_out.get("satisfied_with_relevance"):
                current = self.audit_tool.run(
                    risk=current,
                    append_note="Portfolio relevance validated.",
                )
                passed = True
                break

            last_feedback = str(
                review_out.get("feedback")
                or "Relevance assessment requires revision."
            )
            current = self.audit_tool.run(
                risk=current,
                append_note=f"Relevance reviewer feedback: '{last_feedback}'.",
            )

        if not passed:
            current["portfolio_relevance"] = "Low"
            if not current.get("portfolio_relevance_rationale"):
                current["portfolio_relevance_rationale"] = (
                    "Relevance judged weak after review."
                )
            current = self.audit_tool.run(
                risk=current,
                step_title="Feedback & Revisions",
                step_text=(
                    f"Reviewer feedback: {last_feedback}. Marked relevance as Low and "
                    "flagged for de-prioritization."
                ),
            )
            current["narrative"] = _append_weak_relevance_note(
                str(current.get("narrative") or "")
            )
            current = self.audit_tool.run(
                risk=current,
                append_note="Portfolio relevance flagged as weak after review.",
            )
        elif current.get("portfolio_relevance") not in ("High", "Medium", "Low"):
            current["portfolio_relevance"] = "Medium"

        if "Portfolio Relevance" not in str(current.get("reasoning_trace") or ""):
            current = self.audit_tool.run(
                risk=current,
                step_title="Portfolio Relevance",
                step_text=(
                    f"Rated {current['portfolio_relevance']}: "
                    f"{current.get('portfolio_relevance_rationale', '')}"
                ),
            )
        return current


class RenderReportAgent:
    def __init__(self) -> None:
        self.deduper = RiskDeduplicationTool()
        self.renderer = RiskMarkdownRenderTool()

    def __call__(self, state: dict[str, Any]) -> str:
        finalized = list(state.get("finalized_risks", []) or [])
        deduped = self.deduper.run(risks=finalized)
        return self.renderer.run(risks=deduped, dedupe=False)


class RiskUpdaterAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.render_tool = UpdateRenderTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.context_tool, self.render_tool],
            output_format=RiskUpdateOutput,
            system_template=RISK_UPDATER_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "USER REQUEST:\n{users_query}\n\n"
                "EXISTING RISK REGISTER (JSON-like):\n{existing_register}\n\n"
                "Update the register following your instructions."
            ),
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        context = self.context_tool.run(messages=state.get("messages", []) or [])
        users_query = context.get("last_user_query", "")
        existing_register = state.get("risk")
        updated = self.base_agent(
            {},
            users_query=users_query,
            existing_register=existing_register,
        )
        updated_register = {"risks": updated.get("risks") or []}
        final_message = self.render_tool.run(
            risks=updated_register["risks"],
            change_log=updated.get("change_log") or [],
        )
        return {"risk": updated_register, "message": final_message}


class ElaboratorAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.base_agent = BaseAgent(
            model=model,
            skills=[self.context_tool],
            output_format=ElaboratorOutput,
            system_template=(
                f"{ELABORATOR_SYSTEM_MESSAGE}\n"
                "Return JSON with key 'answer' only."
            ),
            static_context={},
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(
                "Current risk register (if any):\n{current_register}\n\n"
                "Conversation so far:\n{conversation}\n\n"
                "User question:\n{last_query}"
            ),
        )

    def __call__(self, state: dict[str, Any]) -> str:
        context = self.context_tool.run(messages=state.get("messages", []) or [])
        out = self.base_agent(
            {},
            current_register=state.get("risk"),
            conversation=context.get("conversation", ""),
            last_query=context.get("last_user_query", ""),
        )
        return str(out.get("answer") or "").strip()


class AddSignpostsAgent:
    def __init__(self, model: str, llm_factory: Any) -> None:
        self.context_tool = ConversationContextTool()
        self.assembly_tool = SignpostAssemblyTool()
        self.generator = BaseAgent(
            model=model,
            skills=[self.assembly_tool],
            output_format=SignpostPack,
            system_template=SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
            static_context={
                "taxonomy": RISK_TAXONOMY,
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(SIGNPOST_GENERATOR_USER_MESSAGE),
        )
        self.evaluator = BaseAgent(
            model=model,
            skills=[self.assembly_tool],
            output_format=SignpostEvalOutput,
            system_template=SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
            static_context={
                "PORTFOLIO_ALLOCATION": PORTFOLIO_ALLOCATION,
                "SOURCE_GUIDE": SOURCE_GUIDE,
            },
            today_provider=_today_long,
            llm_factory=llm_factory,
            message_builder=_single_user_message_builder(SIGNPOST_EVALUATOR_USER_MESSAGE),
        )

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        risk_register = state.get("risk") or {}
        risks = list(risk_register.get("risks") or [])
        if not risks:
            return {
                "risk": risk_register,
                "message": "No finalized risks found. Run scan/refine first.",
            }

        user_context = self.context_tool.run(messages=state.get("messages", []) or [])
        users_query = user_context.get("last_user_query", "")
        final_risks: list[dict[str, Any]] = []
        max_rounds_per_risk = 1

        for risk in risks:
            current_pack: dict[str, Any] | None = None
            for _round in range(1, max_rounds_per_risk + 1):
                if current_pack is None:
                    current_pack = self.generator(
                        {},
                        risk=risk,
                        user_context=users_query,
                        prior_signposts=current_pack,
                        feedback=None,
                    )
                eval_out = self.evaluator(
                    {},
                    taxonomy=RISK_TAXONOMY,
                    risk=risk,
                    signposts=current_pack,
                )
                if eval_out.get("satisfied_with_signposts"):
                    break
                current_pack = self.generator(
                    {},
                    risk=risk,
                    user_context=users_query,
                    prior_signposts=current_pack,
                    feedback=eval_out.get("feedback"),
                )

            final_risk = self.assembly_tool.run(
                risk=risk,
                signposts=(current_pack or {}).get("signposts") or [],
            )
            final_risks.append(final_risk)

        markdown = ["# Final Risk Register (with Signposts)", ""]
        for i, risk in enumerate(final_risks, start=1):
            categories = risk.get("category") or []
            if not isinstance(categories, list):
                categories = [categories]
            markdown.append(f"## Risk {i}: {risk.get('title', '')}")
            markdown.append(f"**Categories:** {', '.join(str(c) for c in categories)}")
            markdown.append("")
            markdown.append("**Narrative**")
            markdown.append(str(risk.get("narrative") or "").strip())
            markdown.append("")
            if risk.get("reasoning_trace"):
                markdown.append(f"_**Analyst Reasoning:** {risk['reasoning_trace']}_")
                markdown.append("")
            markdown.append(format_signposts_md(risk.get("signposts") or []))
            if risk.get("audit_log"):
                log_text = " ".join(str(item) for item in risk["audit_log"])
                markdown.append("")
                markdown.append("> **Governance History:**")
                markdown.append(f"> {log_text}")
            markdown.append("")
            markdown.append("---")
            markdown.append("")

        return {"risk": {"risks": final_risks}, "message": "\n".join(markdown).strip()}


def build_workflow_agents() -> dict[str, Any]:
    model = _default_model_name()
    llm_factory = _provider_llm_factory
    return {
        "router_agent": RouterAgent(model=model, llm_factory=llm_factory),
        "broad_scan_agent": BroadScanAgent(model=model, llm_factory=llm_factory),
        "web_search_agent": WebSearchAgent(model=model, llm_factory=llm_factory),
        "verify_sources_agent": VerifySourcesAgent(model=model, llm_factory=llm_factory),
        "compare_events_agent": CompareEventsAgent(model=model, llm_factory=llm_factory),
        "summarize_events_agent": SummarizeEventsAgent(
            model=model,
            llm_factory=llm_factory,
        ),
        "refine_risk_agent": RefineRiskAgent(model=model, llm_factory=llm_factory),
        "relevance_agent": RelevanceAgent(model=model, llm_factory=llm_factory),
        "render_report_agent": RenderReportAgent(),
        "risk_updater_agent": RiskUpdaterAgent(model=model, llm_factory=llm_factory),
        "elaborator_agent": ElaboratorAgent(model=model, llm_factory=llm_factory),
        "add_signposts_agent": AddSignpostsAgent(model=model, llm_factory=llm_factory),
    }

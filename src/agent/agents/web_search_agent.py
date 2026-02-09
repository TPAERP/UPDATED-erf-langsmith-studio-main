from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent.agents.base_agent import BaseAgent
from agent.agents.workflow_shared import _single_user_message_builder, _today_long
from agent.tools.taxonomy_brief_formatting_tool import TaxonomyBriefFormattingTool
from agent.tools.web_search_execution_tool import WebSearchExecutionTool
from schemas import WebBriefOutput, WebQueryPlan


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
                "- Return exactly 5 queries, each <= 12 words.\n"
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

    @staticmethod
    def _fallback_queries(taxonomy: str) -> list[str]:
        return [
            f"{taxonomy} latest developments",
            f"{taxonomy} policy changes last week",
            f"{taxonomy} market impact recent",
            f"{taxonomy} regulatory updates recent",
            f"{taxonomy} major incidents past week",
            f"{taxonomy} official statements latest",
            f"{taxonomy} central bank and macro updates",
            f"{taxonomy} supply chain disruptions recent",
        ]

    def _ensure_five_queries(self, taxonomy: str, raw_queries: list[Any]) -> list[str]:
        queries = self.search_tool.run(
            mode="dedupe_queries",
            queries=raw_queries,
            max_queries=5,
        )
        if len(queries) >= 5:
            return queries[:5]

        seen = {str(query).strip().lower() for query in queries}
        for candidate in self._fallback_queries(taxonomy):
            key = candidate.strip().lower()
            if key in seen:
                continue
            queries.append(candidate)
            seen.add(key)
            if len(queries) >= 5:
                break
        return queries[:5]

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
        queries = self._ensure_five_queries(
            taxonomy=taxonomy,
            raw_queries=query_out.get("queries") or [],
        )

        sources: list[dict[str, Any]] = []
        for query in queries:
            query_results = self.search_tool.run(query=query, num=10)
            sources.extend(query_results)

        sources_block = self.brief_formatter.run(mode="sources_block", sources=sources)
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
            "sources": sources,
            "brief_md": brief_md,
            "generated_at": generated_at,
        }

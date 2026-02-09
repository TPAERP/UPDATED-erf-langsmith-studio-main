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

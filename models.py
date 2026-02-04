import os

from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from schemas import *

LLM_PROVIDER = "deepseek" # openai or deepseek
OPENAI_MODEL = "gpt-4o-mini"
DEEPSEEK_MODEL = "deepseek-chat"

OPENAI_WEB_SEARCH_TOOL = {"type": "web_search"}


if LLM_PROVIDER == "openai":
    base_llm = ChatOpenAI(model=OPENAI_MODEL, use_responses_api=True)

    router_llm = base_llm.with_structured_output(RouterOutput)
    broad_scanner_llm = base_llm.with_structured_output(BroadScanOutput)
    specific_scanner_llm = base_llm.with_structured_output(RiskDraft)
    per_risk_evaluator_llm = base_llm.with_structured_output(PerRiskEvalOutput)
    relevance_assessor_llm = base_llm.with_structured_output(RiskDraft)
    relevance_reviewer_llm = base_llm.with_structured_output(RelevanceReviewOutput)
    signpost_generator_llm = base_llm.with_structured_output(SignpostPack)
    signpost_evaluator_llm = base_llm.with_structured_output(SignpostEvalOutput)
    risk_updater_llm = base_llm.with_structured_output(RiskUpdateOutput)
    elaborator_llm = base_llm

    source_verifier_llm = base_llm.with_structured_output(SourceReliabilityOutput)
    event_compare_llm = base_llm.with_structured_output(EventClusterOutput)
    event_risk_summarizer_llm = base_llm.with_structured_output(EventRiskDraftOutput)

    web_query_llm = base_llm.with_structured_output(WebQueryPlan)
    web_report_llm = base_llm
    web_search_llm = base_llm.bind_tools(
        [OPENAI_WEB_SEARCH_TOOL],
        tool_choice="required",
        include=["web_search_call.action.sources"],
    )
elif LLM_PROVIDER == "deepseek":
    base_llm = ChatDeepSeek(model=DEEPSEEK_MODEL)

    router_llm = base_llm.with_structured_output(RouterOutput)
    broad_scanner_llm = base_llm.with_structured_output(BroadScanOutput)
    specific_scanner_llm = base_llm.with_structured_output(RiskDraft)
    per_risk_evaluator_llm = base_llm.with_structured_output(PerRiskEvalOutput)
    relevance_assessor_llm = base_llm.with_structured_output(RiskDraft)
    relevance_reviewer_llm = base_llm.with_structured_output(RelevanceReviewOutput)
    signpost_generator_llm = base_llm.with_structured_output(SignpostPack)
    signpost_evaluator_llm = base_llm.with_structured_output(SignpostEvalOutput)
    risk_updater_llm = base_llm.with_structured_output(RiskUpdateOutput)
    elaborator_llm = base_llm

    source_verifier_llm = base_llm.with_structured_output(SourceReliabilityOutput)
    event_compare_llm = base_llm.with_structured_output(EventClusterOutput)
    event_risk_summarizer_llm = base_llm.with_structured_output(EventRiskDraftOutput)

    web_query_llm = base_llm.with_structured_output(WebQueryPlan)
    web_report_llm = ChatOpenAI(model=OPENAI_MODEL, use_responses_api=True).bind_tools(
        [OPENAI_WEB_SEARCH_TOOL],
        tool_choice="required",
        include=["web_search_call.action.sources"],
    )
    web_search_llm = ChatOpenAI(model=OPENAI_MODEL, use_responses_api=True).bind_tools(
        [OPENAI_WEB_SEARCH_TOOL],
        tool_choice="required",
        include=["web_search_call.action.sources"],
    )
else:
    raise ValueError(f"Unsupported LLM_PROVIDER={LLM_PROVIDER!r}. Use 'openai' or 'deepseek'.")

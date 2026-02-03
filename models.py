from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from schemas import *

llm = "deepseek"  # "deepseek" or "openai"

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
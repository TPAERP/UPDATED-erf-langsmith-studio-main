from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from models import DEEPSEEK_MODEL, LLM_PROVIDER, OPENAI_MODEL


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

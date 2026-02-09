from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

LLM_PROVIDER = "deepseek"  # openai or deepseek
OPENAI_MODEL = "gpt-4o-mini"
DEEPSEEK_MODEL = "deepseek-chat"

OPENAI_WEB_SEARCH_TOOL = {"type": "web_search"}


def _validate_provider() -> None:
    if LLM_PROVIDER not in {"openai", "deepseek"}:
        raise ValueError(
            f"Unsupported LLM_PROVIDER={LLM_PROVIDER!r}. Use 'openai' or 'deepseek'."
        )


@lru_cache(maxsize=1)
def get_web_search_llm() -> Any:
    """Build and cache the OpenAI web-search bound client lazily."""
    _validate_provider()
    return ChatOpenAI(model=OPENAI_MODEL, use_responses_api=True).bind_tools(
        [OPENAI_WEB_SEARCH_TOOL],
        tool_choice="required",
        include=["web_search_call.action.sources"],
    )

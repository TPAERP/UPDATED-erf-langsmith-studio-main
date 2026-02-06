from __future__ import annotations

from string import Formatter
from typing import Any, Callable, Mapping, Sequence

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import BaseMessage, SystemMessage

from schemas import State

LLMFactory = Callable[[str], Any]
MessageBuilder = Callable[
    [str, Mapping[str, Any], Mapping[str, Any]],
    list[BaseMessage],
]


def _default_message_builder(
    system_prompt: str,
    state: Mapping[str, Any],
    _runtime_context: Mapping[str, Any],
) -> list[BaseMessage]:
    history = list(state.get("messages", []) or [])
    return [SystemMessage(content=system_prompt), *history]


class BaseAgent:
    """Reusable LLM-backed agent with tool binding and structured output."""

    def __init__(
        self,
        model: str,
        skills: Sequence[Any],
        output_format: Any,
        system_template: str,
        static_context: Mapping[str, Any],
        today_provider: Callable[[], str],
        llm_factory: LLMFactory | None = None,
        message_builder: MessageBuilder | None = None,
    ) -> None:
        self.model = model
        self.skills = list(skills)
        self.output_format = output_format
        self.system_template = system_template
        self.static_context = dict(static_context)
        self.today_provider = today_provider
        self.llm_factory = llm_factory or self._default_llm_factory
        self.message_builder = message_builder or _default_message_builder
        self._validate_template_keys()
        self.llm = self.llm_factory(self.model)
        self.agent_executor = self.llm.bind_tools(self.skills).with_structured_output(
            self.output_format
        )

    @staticmethod
    def _default_llm_factory(model: str) -> ChatDeepSeek:
        return ChatDeepSeek(model=model)

    def _validate_template_keys(self) -> None:
        template_keys = {
            field_name
            for _, field_name, _, _ in Formatter().parse(self.system_template)
            if field_name
        }
        missing = sorted(
            key
            for key in template_keys
            if key != "today" and key not in self.static_context
        )
        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(
                f"Missing template keys in static_context for {self.__class__.__name__}: "
                f"{missing_str}"
            )

    def __call__(self, state: State | Mapping[str, Any], **runtime_context: Any) -> Any:
        state_copy = dict(state or {})
        merged_context = {**self.static_context, **runtime_context}
        merged_context.setdefault("today", self.today_provider())
        system_prompt = self.system_template.format(**merged_context)
        messages = self.message_builder(system_prompt, state_copy, merged_context)
        return self.agent_executor.invoke(messages)

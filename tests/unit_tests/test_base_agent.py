from __future__ import annotations

from copy import deepcopy

import pytest

from agent.agents.base_agent import BaseAgent


class _FakeExecutor:
    def __init__(self) -> None:
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return {"ok": True, "messages_len": len(messages)}


class _FakeLLM:
    def __init__(self) -> None:
        self.bound_tools = None
        self.output_format = None
        self.executor = _FakeExecutor()

    def bind_tools(self, skills):
        self.bound_tools = list(skills)
        return self

    def with_structured_output(self, output_format):
        self.output_format = output_format
        return self.executor


def _fake_llm_factory(_model: str):
    return _FakeLLM()


def test_base_agent_formats_system_prompt_and_invokes_executor():
    agent = BaseAgent(
        model="fake-model",
        skills=[],
        output_format=dict,
        system_template="Today is {today}. Portfolio: {portfolio}.",
        static_context={"portfolio": "balanced"},
        today_provider=lambda: "January 01, 2026",
        llm_factory=_fake_llm_factory,
    )

    state = {"messages": []}
    out = agent(state)

    assert out["ok"] is True
    assert out["messages_len"] == 1
    assert "January 01, 2026" in agent.agent_executor.last_messages[0].content
    assert "balanced" in agent.agent_executor.last_messages[0].content


def test_base_agent_does_not_mutate_input_state_messages():
    agent = BaseAgent(
        model="fake-model",
        skills=[],
        output_format=dict,
        system_template="Portfolio: {portfolio}",
        static_context={"portfolio": "balanced"},
        today_provider=lambda: "January 01, 2026",
        llm_factory=_fake_llm_factory,
    )
    state = {
        "messages": [{"type": "human", "content": "hello"}],
        "attempts": 1,
    }
    snapshot = deepcopy(state)
    agent(state)
    assert state == snapshot


def test_base_agent_raises_when_template_keys_missing_from_static_context():
    with pytest.raises(ValueError) as exc:
        BaseAgent(
            model="fake-model",
            skills=[],
            output_format=dict,
            system_template="Missing key: {missing_key}",
            static_context={},
            today_provider=lambda: "January 01, 2026",
            llm_factory=_fake_llm_factory,
        )
    assert "missing_key" in str(exc.value)

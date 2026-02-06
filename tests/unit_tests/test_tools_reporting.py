from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from agent.tools.reporting import (
    ConversationContextTool,
    RiskMarkdownRenderTool,
    UpdateRenderTool,
)


def test_conversation_context_tool_extracts_last_user_and_history():
    tool = ConversationContextTool()
    out = tool.run(messages=[AIMessage(content="a"), HumanMessage(content="b")], ignored=1)
    assert out["last_user_query"] == "b"
    assert "User: b" in out["conversation"]


def test_risk_markdown_render_tool_renders_register():
    tool = RiskMarkdownRenderTool()
    out = tool.run(
        risks=[
            {
                "title": "Risk A",
                "category": ["Geopolitical"],
                "narrative": "Narrative",
                "sources": [],
            }
        ],
        dedupe=True,
    )
    assert "# Risk Register" in out
    assert "Risk A" in out


def test_update_render_tool_formats_change_log():
    tool = UpdateRenderTool()
    out = tool.run(
        risks=[
            {
                "title": "Risk A",
                "category": ["Geopolitical"],
                "narrative": "Narrative",
                "sources": [],
            }
        ],
        change_log=["Updated title"],
    )
    assert "# Updated Risk Register" in out
    assert "- Updated title" in out

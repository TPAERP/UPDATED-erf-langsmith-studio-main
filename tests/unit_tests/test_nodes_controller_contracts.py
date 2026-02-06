from __future__ import annotations

from langchain_core.messages import AIMessage

from nodes.add_signposts_all_risks_node import add_signposts_all_risks_node
from nodes.assess_portfolio_relevance_node import assess_portfolio_relevance_node
from nodes.broad_scan_node import broad_scan_node
from nodes.compare_events_node import compare_events_node
from nodes.elaborator_node import elaborator_node
from nodes.refine_single_risk_node import refine_single_risk_node
from nodes.render_report_node import render_report_node
from nodes.risk_updater_node import risk_updater_node
from nodes.router_node import router_node
from nodes.summarize_events_node import summarize_events_node
from nodes.verify_sources_node import verify_sources_node
from nodes.web_search_node import web_search_node


def test_router_node_contract(monkeypatch):
    monkeypatch.setattr("nodes.router_node.router_agent", lambda _state: "risk_updater")
    assert router_node({"messages": []}) == "risk_updater"


def test_broad_scan_node_contract(monkeypatch):
    monkeypatch.setattr("nodes.broad_scan_node.broad_scan_agent", lambda _state: [{"title": "R"}])
    out = broad_scan_node({"messages": []})
    assert "draft_risks" in out
    assert "finalized_risks" in out
    assert isinstance(out["messages"][0], AIMessage)


def test_web_search_and_verify_source_node_contracts(monkeypatch):
    monkeypatch.setattr(
        "nodes.web_search_node.web_search_agent",
        lambda _state: {"taxonomy": "Geo", "queries": [], "sources": [], "brief_md": "", "generated_at": "now"},
    )
    search_out = web_search_node({"taxonomy": "Geo"})
    assert "taxonomy_reports" in search_out

    monkeypatch.setattr(
        "nodes.verify_sources_node.verify_sources_agent",
        lambda _state: [{"taxonomy": "Geo", "sources": []}],
    )
    verify_out = verify_sources_node({"taxonomy_reports": []})
    assert "verified_taxonomy_reports" in verify_out


def test_compare_and_summarize_node_contracts(monkeypatch):
    monkeypatch.setattr(
        "nodes.compare_events_node.compare_events_agent",
        lambda _state: [{"title": "E", "taxonomy": [], "summary": "", "evidence_urls": []}],
    )
    compare_out = compare_events_node({"verified_taxonomy_reports": []})
    assert "event_clusters" in compare_out

    monkeypatch.setattr(
        "nodes.summarize_events_node.summarize_events_agent",
        lambda _state: [{"title": "R", "category": [], "narrative": ""}],
    )
    summarize_out = summarize_events_node({"event_clusters": []})
    assert "draft_risks" in summarize_out


def test_refine_relevance_render_contracts(monkeypatch):
    monkeypatch.setattr(
        "nodes.refine_single_risk_node.refine_risk_agent",
        lambda _risk: {"title": "R", "category": [], "narrative": ""},
    )
    refined = refine_single_risk_node({"risk_candidate": {"title": "r"}})
    assert "finalized_risks" in refined

    monkeypatch.setattr(
        "nodes.assess_portfolio_relevance_node.relevance_agent",
        lambda _risk: {"title": "R", "category": [], "narrative": ""},
    )
    assessed = assess_portfolio_relevance_node({"risk_candidate": {"title": "r"}})
    assert "finalized_risks" in assessed

    monkeypatch.setattr("nodes.render_report_node.render_report_agent", lambda _state: "markdown")
    rendered = render_report_node({"finalized_risks": []})
    assert isinstance(rendered["messages"][0], AIMessage)
    assert rendered["messages"][0].content == "markdown"


def test_updater_elaborator_signpost_node_contracts(monkeypatch):
    monkeypatch.setattr(
        "nodes.risk_updater_node.risk_updater_agent",
        lambda _state: {"risk": {"risks": []}, "message": "updated"},
    )
    out = risk_updater_node({"messages": [], "attempts": 0})
    assert out["risk"] == {"risks": []}
    assert isinstance(out["messages"][0], AIMessage)
    assert out["attempts"] == 0

    monkeypatch.setattr("nodes.elaborator_node.elaborator_agent", lambda _state: "answer")
    qna_out = elaborator_node({"messages": [], "attempts": 2})
    assert qna_out["messages"][0].content == "answer"
    assert qna_out["attempts"] == 2

    monkeypatch.setattr(
        "nodes.add_signposts_all_risks_node.add_signposts_agent",
        lambda _state: {"risk": {"risks": []}, "message": "signposted"},
    )
    signpost_out = add_signposts_all_risks_node({"risk": {"risks": []}})
    assert signpost_out["risk"] == {"risks": []}
    assert signpost_out["messages"][0].content == "signposted"

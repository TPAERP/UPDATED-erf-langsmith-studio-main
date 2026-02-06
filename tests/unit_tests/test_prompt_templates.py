from __future__ import annotations

from prompts.relevance_prompts import (
    PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE,
    PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE,
)
from prompts.router_prompts import ROUTER_SYSTEM_MESSAGE, ROUTER_USER_MESSAGE
from prompts.scan_prompts import (
    BROAD_RISK_SCANNER_SYSTEM_MESSAGE,
    COMPARE_EVENTS_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE,
    EVENT_PATH_RISKDRAFT_USER_MESSAGE,
    FEW_SHOT_EXAMPLES,
    PER_RISK_EVALUATOR_SYSTEM_MESSAGE,
    PER_RISK_EVALUATOR_USER_MESSAGE,
    SOURCE_VERIFIER_SYSTEM_MESSAGE,
    SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE,
)
from prompts.signpost_prompts import (
    SIGNPOST_EVALUATOR_SYSTEM_MESSAGE,
    SIGNPOST_EVALUATOR_USER_MESSAGE,
    SIGNPOST_GENERATOR_SYSTEM_MESSAGE,
    SIGNPOST_GENERATOR_USER_MESSAGE,
)
from prompts.update_prompts import RISK_UPDATER_SYSTEM_MESSAGE


def test_router_templates_format():
    assert ROUTER_SYSTEM_MESSAGE
    assert "User last message:" in ROUTER_USER_MESSAGE.format(user_query="scan now")


def test_scan_templates_format():
    assert BROAD_RISK_SCANNER_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        FEW_SHOT_EXAMPLES=FEW_SHOT_EXAMPLES,
        today="February 06, 2026",
    )
    assert SPECIFIC_RISK_SCANNER_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        FEW_SHOT_EXAMPLES="few-shot",
        feedback="revise",
        current_risk="risk markdown",
        today="February 06, 2026",
    )
    assert PER_RISK_EVALUATOR_SYSTEM_MESSAGE.format(
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        today="February 06, 2026",
    )
    assert PER_RISK_EVALUATOR_USER_MESSAGE.format(taxonomy=["Geopolitical"], risk="risk")
    assert SOURCE_VERIFIER_SYSTEM_MESSAGE.format(today="February 06, 2026")
    assert COMPARE_EVENTS_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        today="February 06, 2026",
    )
    assert EVENT_PATH_RISKDRAFT_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        PORTFOLIO_ALLOCATION="portfolio",
        today="February 06, 2026",
    )
    assert EVENT_PATH_RISKDRAFT_USER_MESSAGE.format(
        events_json="[]",
        sources_block="sources",
    )


def test_relevance_update_and_signpost_templates_format():
    assert PORTFOLIO_RELEVANCE_ASSESSOR_SYSTEM_MESSAGE.format(
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        today="February 06, 2026",
    )
    assert PORTFOLIO_RELEVANCE_REVIEWER_SYSTEM_MESSAGE.format(
        PORTFOLIO_ALLOCATION="portfolio",
        today="February 06, 2026",
    )
    assert PORTFOLIO_RELEVANCE_REVIEWER_USER_MESSAGE.format(
        taxonomy=["Geopolitical"],
        risk="risk",
    )
    assert RISK_UPDATER_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        today="February 06, 2026",
    )
    assert SIGNPOST_GENERATOR_SYSTEM_MESSAGE.format(
        taxonomy=["Geopolitical"],
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        today="February 06, 2026",
    )
    assert SIGNPOST_GENERATOR_USER_MESSAGE.format(
        risk="risk",
        user_context="context",
        prior_signposts="none",
        feedback="none",
    )
    assert SIGNPOST_EVALUATOR_SYSTEM_MESSAGE.format(
        PORTFOLIO_ALLOCATION="portfolio",
        SOURCE_GUIDE="sources",
        today="February 06, 2026",
    )
    assert SIGNPOST_EVALUATOR_USER_MESSAGE.format(
        taxonomy=["Geopolitical"],
        risk="risk",
        signposts="signposts",
    )

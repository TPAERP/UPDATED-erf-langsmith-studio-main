import pytest

from agent import graph

pytestmark = pytest.mark.anyio


def test_graph_compiles_for_local_smoke() -> None:
    assert graph is not None


@pytest.mark.langsmith
async def test_agent_simple_passthrough() -> None:
    inputs = {"changeme": "some_val"}
    res = await graph.ainvoke(inputs)
    assert res is not None

import asyncio

import pytest

from orqmesh import LangGraphAdapter


class FakeGraph:
    def __init__(self, result):
        self.result = result
        self.received = None

    async def ainvoke(self, input, config=None):
        self.received = (input, config)
        return self.result


def test_langgraph_adapter_passes_input_and_config():
    graph = FakeGraph({"records": [{"document_id": "DOC-1"}]})
    adapter = LangGraphAdapter(graph)

    result = asyncio.run(adapter.ainvoke({"request_id": "REQ-1"}, {"tags": ["test"]}))

    assert result == {"records": [{"document_id": "DOC-1"}]}
    assert graph.received == ({"request_id": "REQ-1"}, {"tags": ["test"]})


def test_langgraph_adapter_rejects_non_mapping_output():
    adapter = LangGraphAdapter(FakeGraph("unexpected"))

    with pytest.raises(TypeError, match="must return a mapping"):
        asyncio.run(adapter.ainvoke({}))
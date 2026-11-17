"""Small dependency-free adapter for invoking async LangGraph runnables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from orqmesh.models import JSONMapping


class AsyncGraphRunnable(Protocol):
    """Structural interface implemented by LangGraph async runnables."""

    async def ainvoke(
        self,
        input: Mapping[str, object],
        config: Mapping[str, object] | None = None,
    ) -> object:
        """Invoke a compiled async graph."""
        ...


class LangGraphAdapter:
    """Invoke a compiled LangGraph with JSON-like input and validate its output.

    LangGraph remains an optional application dependency. The adapter does not
    own model clients, graph state, callbacks, or checkpointers; callers inject
    their compiled graph and choose which safe input/output fields to persist.
    """

    def __init__(self, graph: AsyncGraphRunnable) -> None:
        self._graph = graph

    async def ainvoke(
        self,
        input_data: JSONMapping,
        config: Mapping[str, object] | None = None,
    ) -> JSONMapping:
        """Run the graph and require a mapping result."""
        if config is None:
            result = await self._graph.ainvoke(input_data)
        else:
            result = await self._graph.ainvoke(input_data, config=config)
        if not isinstance(result, Mapping):
            raise TypeError("LangGraph runnable must return a mapping")
        return cast(JSONMapping, dict(result))
"""Explicitly registered tools and agents with per-agent allowlists."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from orqmesh.models import JSONMapping, JSONValue

ToolHandler = Callable[[JSONMapping], JSONValue]


@dataclass(frozen=True, slots=True)
class Tool:
    """A named callable exposed through a registry."""

    name: str
    handler: ToolHandler
    description: str = ""


class ToolRegistry:
    """Registry that only executes explicitly registered tool names."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if not tool.name.strip():
            raise ValueError("Tool names cannot be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def invoke(self, name: str, arguments: JSONMapping) -> JSONValue:
        try:
            tool = self._tools[name]
        except KeyError as error:
            raise KeyError(f"Tool {name!r} is not registered") from error
        return tool.handler(arguments)

    def names(self) -> tuple[str, ...]:
        """Return the registered tool names in registration order."""
        return tuple(self._tools)


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Agent input and the constrained tool-call capability it receives."""

    input: JSONMapping
    _registry: ToolRegistry
    _allowed_tools: frozenset[str]

    def call_tool(self, name: str, arguments: JSONMapping) -> JSONValue:
        if name not in self._allowed_tools:
            raise PermissionError(f"Agent is not allowed to call tool {name!r}")
        return self._registry.invoke(name, arguments)


AgentHandler = Callable[[AgentContext], JSONMapping]


@dataclass(frozen=True, slots=True)
class Agent:
    """Small framework-neutral agent wrapper with explicit tool permissions."""

    name: str
    handler: AgentHandler
    allowed_tools: frozenset[str] = frozenset()

    def run(self, input_data: JSONMapping, registry: ToolRegistry) -> JSONMapping:
        unknown = self.allowed_tools.difference(registry.names())
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Agent {self.name!r} references unregistered tools: {names}")
        context = AgentContext(input_data, registry, self.allowed_tools)
        result = self.handler(context)
        if not isinstance(result, Mapping):
            raise TypeError("Agent handler must return a mapping")
        return dict(result)
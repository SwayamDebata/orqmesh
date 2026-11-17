import pytest

from orqmesh import Agent, Tool, ToolRegistry


def test_agent_can_call_only_allowlisted_tools():
    registry = ToolRegistry([Tool("lookup", lambda arguments: {"found": arguments["key"]})])
    agent = Agent(
        name="lookup-agent",
        allowed_tools=frozenset({"lookup"}),
        handler=lambda context: {"result": context.call_tool("lookup", {"key": "record-1"})},
    )

    assert agent.run({}, registry) == {"result": {"found": "record-1"}}


def test_agent_cannot_call_unallowlisted_tool():
    registry = ToolRegistry([Tool("dangerous", lambda arguments: "executed")])
    agent = Agent(
        name="restricted-agent",
        handler=lambda context: {"result": context.call_tool("dangerous", {})},
    )

    with pytest.raises(PermissionError, match="not allowed"):
        agent.run({}, registry)


def test_duplicate_tool_registration_is_rejected():
    registry = ToolRegistry([Tool("lookup", lambda arguments: None)])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Tool("lookup", lambda arguments: None))

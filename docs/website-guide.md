# Orqmesh documentation

> **Status:** Alpha. Licensed under Apache-2.0. Examples are not production-ready. Source: https://github.com/SwayamDebata/orqmesh. Package: https://pypi.org/project/orqmesh/

## Overview

Orqmesh helps Python developers compose steps, application-owned tools, and human decisions into controlled workflows. It is designed to be infrastructure-neutral: the core does not require a cloud provider, model framework, or third-party runtime dependency. Applications choose their own business rules, credentials, clients, and execution environment.

Orqmesh is an SDK, not a hosted service. It does not provide an LLM, document extraction, an authentication server, a user interface, or a built-in enterprise integration platform. Optional thin adapters can call client objects supplied by the application.

### Where it can help

- Coordinate application-defined processing steps in a predictable order.
- Pause a workflow to request a human decision, then resume after approval.
- Explicitly register callable tools and specify which names an agent can invoke through its context.
- Wrap asynchronous application services or compatible graph invocations in workflow steps.
- Prototype with local JSON checkpoints using synthetic, non-sensitive data.

These are capability examples, not claims that the SDK guarantees compliance, handles any domain automatically, or is safe for production side effects.

## Requirements and installation

- Python 3.11 or later.
- The package declares no mandatory third-party runtime dependencies. Your application must independently install and configure any integration libraries it uses.
- Install the current prerelease with `python -m pip install "orqmesh==0.1.0b1"`.

For local development in PowerShell, from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

Install the published prerelease with `python -m pip install "orqmesh==0.1.0b1"`.

## Core concepts

| Concept | Current behavior |
| --- | --- |
| `Workflow` / `WorkflowStep` | Execute named synchronous steps sequentially. |
| `AsyncWorkflow` / `AsyncWorkflowStep` | Await named asynchronous steps sequentially. |
| `StepContext` | Provides the run ID, input mapping, and outputs of completed steps. Treat nested values as application-owned data; this is not a deep-immutable or isolated view. |
| `WorkflowState` | Holds run status, input, step outputs, next step, pending review, review records, and failure text. |
| `CheckpointStore` | Synchronous `load(run_id)` and `save(state)` protocol. Async workflows call these in worker threads. |
| `JsonFileCheckpointStore` | Local development store that writes JSON and atomically replaces a file for each run. |
| `ReviewRequest` / `ReviewDecision` | A step can pause for review; a caller records approval or rejection. |
| `ToolRegistry` / `Agent` | Registers synchronous tools and restricts calls through `AgentContext.call_tool()` to an agent's allowlist. |

Workflow inputs and outputs must be JSON-serializable. Do not store credentials, document contents, personal data, access tokens, or provider clients in checkpoints. The SDK cannot automatically identify or redact secrets.

## Quickstart: a sequential workflow

This standalone example uses only synthetic input and the standard-library temporary directory. A real application would choose an appropriate checkpoint store and run ID.

```python
from tempfile import TemporaryDirectory

from orqmesh import JsonFileCheckpointStore, Workflow, WorkflowStep


def prepare(context):
    return {"item_id": context.input["item_id"], "status": "ready"}


def summarize(context):
    return {"message": "Prepared " + str(context.outputs["prepare"]["item_id"])}


workflow = Workflow(
    "prepare-item",
    [WorkflowStep("prepare", prepare), WorkflowStep("summarize", summarize)],
)

with TemporaryDirectory() as directory:
    store = JsonFileCheckpointStore(directory)
    state = workflow.run("example-001", {"item_id": "demo"}, store)
    print(state.status.value)  # completed
    print(state.outputs["summarize"])  # {'message': 'Prepared demo'}
```

Each step receives a `StepContext` and returns a mapping or `ReviewRequest`. Step names must be nonempty and unique. Starting an existing run ID raises an error. For the file store, use a 1–128 character identifier beginning with a letter or digit and containing only letters, digits, underscores, dots, and hyphens.

## Human review

A workflow can pause at a step that returns `ReviewRequest`. The request is saved in `pending_review`; no later step runs until an application supplies a decision. In this example the reviewer is simulated—not authenticated.

```python
from tempfile import TemporaryDirectory

from orqmesh import (
    JsonFileCheckpointStore,
    ReviewDecision,
    ReviewRequest,
    RunStatus,
    Workflow,
    WorkflowStep,
)


def request_review(context):
    return ReviewRequest({"item_id": context.input["item_id"], "reason": "demo"})


def finish(context):
    review = context.outputs["review"]["review"]
    return {"decision": review["decision"]}


workflow = Workflow(
    "review-item",
    [WorkflowStep("review", request_review), WorkflowStep("finish", finish)],
)

with TemporaryDirectory() as directory:
    store = JsonFileCheckpointStore(directory)
    state = workflow.run("review-001", {"item_id": "demo"}, store)
    assert state.status is RunStatus.WAITING_REVIEW
    state = workflow.resume(state.run_id, ReviewDecision.APPROVED, "demo-reviewer", store)
    assert state.status is RunStatus.COMPLETED
```

Use `ReviewDecision.REJECTED` to end the run as `rejected` without executing later steps. The consuming application must authenticate and authorize reviewers, enforce tenancy and concurrency, and implement an audit policy. The SDK does not provide these controls.

## Asynchronous workflows

`AsyncWorkflow` awaits async step handlers and uses the existing synchronous checkpoint interface via `asyncio.to_thread()`. This prevents a normal blocking store call from occupying the event loop, but it does not make the store distributed, concurrent, or natively asynchronous.

```python
import asyncio
from tempfile import TemporaryDirectory

from orqmesh import AsyncWorkflow, AsyncWorkflowStep, JsonFileCheckpointStore


async def prepare(context):
    await asyncio.sleep(0)  # stand-in for an application-owned async operation
    return {"item_id": context.input["item_id"], "status": "ready"}


async def main():
    workflow = AsyncWorkflow("async-demo", [AsyncWorkflowStep("prepare", prepare)])
    with TemporaryDirectory() as directory:
        state = await workflow.run(
            "async-001", {"item_id": "demo"}, JsonFileCheckpointStore(directory)
        )
        print(state.status.value)  # completed


asyncio.run(main())  # In an existing async application, await main() instead.
```

Use `await workflow.resume(...)` for async review resumption. Do not call `asyncio.run()` inside an already-running event loop. Async steps still run in order; branching, fan-out, and automatic retries are not implemented.

## Tools and agent permissions

Tools are synchronous callables that accept a JSON mapping and return a JSON-compatible value. An agent's handler receives an `AgentContext` and can call registered names in its allowlist:

```python
from orqmesh import Agent, Tool, ToolRegistry

registry = ToolRegistry([
    Tool("lookup", lambda args: {"found": args["key"]}, "Synthetic lookup"),
])
agent = Agent(
    name="example",
    allowed_tools=frozenset({"lookup"}),
    handler=lambda context: {"result": context.call_tool("lookup", {"key": "demo"})},
)
print(agent.run({}, registry))  # {'result': {'found': 'demo'}}
```

This is an application programming convention, not a sandbox, identity provider, or security boundary against untrusted Python code. The callable receives a context backed by a registry; do not run untrusted agent handlers or rely on private attributes as access control. The application must enforce permissions at the service/tool boundary.

## Integration adapters

- `LangGraphAdapter` invokes an injected object with an async `ainvoke()` method and checks that its result is a mapping. The application constructs and owns the graph, model, tools, and provider credentials. Nested values are not automatically validated or converted to JSON.
- `AzureBlobStore` uses an injected async Blob service client to read a complete blob into memory.
- `AzureCosmosRepository` wraps an injected async Cosmos container for basic upsert and query operations.
- `AzureContentUnderstandingAdapter` offloads a supplied synchronous client's submit/poll operations to worker threads.

These adapters are thin, tested with fakes, and **not certified against specific real provider versions**. Install and configure provider libraries in your application, check their actual APIs, manage client lifetimes, and perform non-production contract tests before use. Orqmesh does not implement Azure OpenAI model invocation, timeouts for these adapters, automatic retry policies, or secret management. See [architecture](architecture.md).

## State, failures, and operations

A normal lifecycle is `running` → `waiting_review` → `running` → `completed`; a rejection ends as `rejected`. A step exception is saved as `failed` and re-raised. Async cancellation is marked failed when possible and re-raised. Exception messages may be persisted verbatim; sanitize them before they reach the runtime.

`JsonFileCheckpointStore` is for local experimentation. It does not encrypt data or guarantee atomic run creation, transactional review decisions, distributed locking, compare-and-set, or multi-worker coordination. A crash can happen between an external side effect and saving the checkpoint. Replaying a step can therefore duplicate that side effect. Production use requires an independently designed, concurrency-safe store, idempotent downstream operations, identity/authorization, audit, retention, recovery, and a security assessment.

Keep workflow definitions stable when resuming. Current checkpoints do not carry a workflow identity or definition version, and `resume()` does not validate that the loaded checkpoint belongs to a particular workflow definition. Concurrent or accidental use of the same run ID across workflows is unsafe.

## Example and development resources

The repository includes a synthetic [document review example](../examples/document_review.py). The review request and input include document content, so only use test data with the local store. The example's caller decides whether review is needed; it does not analyze documents or call an LLM.

- [Architecture](architecture.md)
- [Contributing](../CONTRIBUTING.md)
- [Security](../SECURITY.md)

## Roadmap — not yet implemented

Candidate work includes versioned/concurrent checkpointing, recovery and idempotency patterns, model-provider abstractions, async tools, retry and timeout policies, branching and parallelism, secure review integrations, observability and audit hooks, and provider-version contract tests. These are proposals, not delivery commitments.

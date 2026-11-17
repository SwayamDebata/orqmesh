# Orqmesh

Orqmesh is an early-stage Python SDK for composing controlled agent workflows. Its core is infrastructure-neutral and has no mandatory third-party runtime dependencies.

> **Status:** Alpha prototype, not production-ready. Released under the Apache License 2.0. Source: [github.com/SwayamDebata/orqmesh](https://github.com/SwayamDebata/orqmesh).

## Available today

- Typed sequential synchronous and asynchronous workflows.
- JSON checkpoint interface and local-file implementation.
- Human-review pause, approval, rejection, and resume.
- Explicit tool registry and per-agent tool allowlists.
- Thin, injected-client adapters for LangGraph and selected Azure services, tested with fakes.
- A synthetic, domain-neutral document-review example demonstrating workflow composition.

## Limitations

The SDK does not yet provide distributed checkpointing, atomic concurrent run coordination, branching, retries, side-effect idempotency, Azure OpenAI model adapters, application authentication, or a full audit/observability system. Local checkpoint files are unencrypted and unsuitable for sensitive data. Service adapters are not yet certified against real provider SDK versions. Consult [architecture](docs/architecture.md) before integrating.

## Getting started

Requires Python 3.11 or later. From a development environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python examples/document_review.py
```

The example uses synthetic data and simulates approval without publishing or modifying a document.
`build_document_review_workflow()` accepts a `document` object containing nonempty
`document_id`, `title`, and `content` strings and a boolean `requires_review`. The caller
chooses whether review is required; the workflow does not analyze the content. Documents
without review are automatically approved. Documents requiring review pause for approval
or rejection; rejection stops the workflow without a final result. Successful runs produce
`finalize_document` output with `status`, `document_id`, `title`, and `approval`.
The input and review payload, including document content, are stored in checkpoints, so use
synthetic, non-sensitive data with the local store.

```python
from orqmesh import JsonFileCheckpointStore, Workflow, WorkflowStep

workflow = Workflow(
    "example",
    [WorkflowStep("prepare", lambda context: {"message": "ready"})],
)
state = workflow.run("run-001", {}, JsonFileCheckpointStore(".checkpoints"))
print(state.status.value, state.outputs)
```

Use a new run ID for each run. Never put credentials or sensitive data in checkpoints.

## Documentation

- [Website-ready user guide and examples](docs/website-guide.md)
- [Architecture and implementation status](docs/architecture.md)
- [GitHub setup, package publishing, and release checklist](docs/publishing.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Licensing and release

Orqmesh is released under the Apache License 2.0. See [LICENSE](LICENSE). No package is automatically uploaded by CI.

# Architecture and implementation status

Orqmesh is a Python SDK for composing infrastructure-neutral agent workflows. It is an early prototype, not a fully featured agent platform.

## Implemented boundaries

- **Contracts:** `WorkflowState`, `WorkflowStep`, `StepContext`, `ReviewRequest`, and `ReviewDecision` describe the current execution and review lifecycle.
- **Orchestration:** `Workflow` and `AsyncWorkflow` execute named steps sequentially and persist state at step and review boundaries. The async runner offloads synchronous checkpoint store operations to worker threads.
- **Tools and agents:** `ToolRegistry` registers callables and `Agent` applies an explicit per-agent allowlist. This is a programming boundary, not a sandbox or authorization system.
- **Persistence:** `CheckpointStore` is the synchronous persistence seam. `JsonFileCheckpointStore` atomically replaces local JSON files, but provides no encryption, distributed locking, compare-and-set, or multi-worker coordination.
- **Optional integration seams:** `LangGraphAdapter` invokes an injected asynchronous graph. The Azure Blob, Cosmos, and Content Understanding wrappers accept injected clients and do not manage credentials or client lifecycle. Tests use fakes; actual provider versions and live services are not certified.

## Review lifecycle

A workflow starts as `running`. Steps can return a `ReviewRequest`, persisting a `waiting_review` state. Approval records a reviewer and advances to the following step; rejection ends the run as `rejected`; successful completion becomes `completed`. Step failures are saved as `failed` and re-raised. The application must enforce reviewer identity and permissions.

## Safety and limitations

The local checkpoint store is intended for development. It must not be used to store secrets or sensitive business data. The runner does not offer cross-process locking, atomic run creation or resume, retries, automatic restart recovery, branching, fan-out, or idempotent external side effects. An exception message can be persisted in a checkpoint; callers must ensure exceptions do not expose sensitive information.

A step may perform side effects before its checkpoint is saved. An interruption can leave an external operation completed but the workflow state incomplete. Applications must implement appropriate idempotency and recovery before using the SDK with real external actions. Local JSON checkpoints and tool allowlists alone are not production security controls.

## Future work

- Versioned checkpoint schemas and conditional updates for a production persistence backend.
- Explicit retry, cancellation, recovery, timeout, branching, and bounded-concurrency semantics.
- Model-provider and optional framework adapters with compatibility tests.
- Secure identity and policy integration, audit events, redaction, and observability hooks.
- Additional generic examples, contract tests, and documented API stability guarantees.

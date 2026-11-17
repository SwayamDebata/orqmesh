# Changelog

All notable changes will be documented here. Until an initial public release is authorized and published, entries describe development snapshots rather than published distributions.

## Unreleased — 0.1.0b1 candidate

- Infrastructure-neutral synchronous and asynchronous sequential workflow APIs.
- Local JSON checkpoint store and human-review pause/resume contracts.
- Explicit tool registration and per-agent tool allowlists.
- Thin injected-client wrappers for a LangGraph-style runnable and selected Azure services, tested with fakes.
- Synthetic document-review example and developer documentation.
- Released under the Apache License 2.0. Source: https://github.com/SwayamDebata/orqmesh

### Known limitations

This prototype is not production-ready. Local checkpoints are unencrypted and lack multi-worker coordination. The runtime has no automatic retries, distributed recovery, side-effect idempotency, branching, authentication, or full observability system. Azure/provider compatibility has not been validated against a version matrix or live services.

# Orqmesh project guidance

- Build a Python SDK, not a chatbot or web application.
- Keep the core runtime infrastructure-neutral and framework-independent.
- Preserve explicit boundaries for tools, agent permissions, workflow state, and human review.
- Keep public APIs typed, documented, and covered by focused tests.
- Checkpoint data must be JSON-serializable; do not persist secrets or credentials.
- Be explicit in docs about implemented behavior versus roadmap items.
- Use `pytest` for tests and `ruff check .` for linting; require Python 3.11+.
- Treat Orqmesh as a provisional name pending availability and trademark checks.

# Contributing to Orqmesh

Thank you for your interest. Orqmesh is released under the Apache License 2.0. Contributions sent to this project are accepted under that same license.

Open an issue or pull request at https://github.com/SwayamDebata/orqmesh.

## Development workflow

1. Use Python 3.11 or later in a virtual environment.
2. Install the project with its development extra.
3. Add focused tests for behavior changes; keep public APIs typed and documented.
4. Run `python -m pytest` and `python -m ruff check .` before proposing changes.
5. Keep the core infrastructure-neutral; integrations should use explicit boundaries and deterministic fakes in tests.
6. Never add credentials, private records, or sensitive data to source, logs, test fixtures, checkpoints, or documentation.

"""Checkpoint storage contracts and a local atomic JSON implementation."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

from orqmesh.models import WorkflowState


class CheckpointStore(Protocol):
    """Persistence interface used by the workflow engine."""

    def load(self, run_id: str) -> WorkflowState | None:
        """Load a run snapshot, or return ``None`` if it does not exist."""
        ...

    def save(self, state: WorkflowState) -> None:
        """Persist a run snapshot."""
        ...


class JsonFileCheckpointStore:
    """Store workflow snapshots as atomically replaced local JSON files."""

    _SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, run_id: str) -> Path:
        if not self._SAFE_ID.fullmatch(run_id) or run_id in {".", ".."}:
            raise ValueError("run_id must be a safe 1-128 character identifier")
        return self.directory / f"{run_id}.json"

    def load(self, run_id: str) -> WorkflowState | None:
        path = self._path_for(run_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as checkpoint_file:
            data = json.load(checkpoint_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid checkpoint document for run {run_id!r}")
        return WorkflowState.from_dict(data)

    def save(self, state: WorkflowState) -> None:
        path = self._path_for(state.run_id)
        serialized = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory, delete=False
            ) as checkpoint_file:
                temporary_path = checkpoint_file.name
                checkpoint_file.write(serialized)
                checkpoint_file.flush()
                os.fsync(checkpoint_file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
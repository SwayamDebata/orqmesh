"""Typed data contracts shared by the Orqmesh runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONMapping: TypeAlias = dict[str, JSONValue]


class RunStatus(StrEnum):
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ReviewRequest:
    """A request to pause a workflow until a person makes a decision."""

    payload: JSONMapping


@dataclass(slots=True)
class WorkflowState:
    """JSON-serializable durable snapshot of one workflow run."""

    run_id: str
    status: RunStatus
    input: JSONMapping
    outputs: dict[str, JSONMapping] = field(default_factory=dict)
    next_step: int = 0
    pending_review: JSONMapping | None = None
    reviews: list[JSONMapping] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> JSONMapping:
        """Convert this snapshot to a JSON-compatible dictionary."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "input": self.input,
            "outputs": self.outputs,
            "next_step": self.next_step,
            "pending_review": self.pending_review,
            "reviews": self.reviews,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowState:
        """Restore a snapshot from a JSON-decoded dictionary."""
        return cls(
            run_id=str(data["run_id"]),
            status=RunStatus(str(data["status"])),
            input=data["input"],  # type: ignore[arg-type]
            outputs=data.get("outputs", {}),  # type: ignore[arg-type]
            next_step=int(data.get("next_step", 0)),
            pending_review=data.get("pending_review"),  # type: ignore[arg-type]
            reviews=data.get("reviews", []),  # type: ignore[arg-type]
            error=data.get("error"),  # type: ignore[arg-type]
        )
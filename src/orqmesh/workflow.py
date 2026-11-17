"""Sequential workflow orchestration with durable human-review pauses."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from orqmesh.checkpoints import CheckpointStore
from orqmesh.models import (
    JSONMapping,
    JSONValue,
    ReviewDecision,
    ReviewRequest,
    RunStatus,
    WorkflowState,
)


@dataclass(frozen=True, slots=True)
class StepContext:
    """Read-only view of inputs and outputs available to a workflow step."""

    run_id: str
    input: JSONMapping
    outputs: Mapping[str, JSONMapping]


StepHandler = Callable[[StepContext], Mapping[str, JSONValue] | ReviewRequest]


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """Named unit of workflow logic."""

    name: str
    run: StepHandler


class Workflow:
    """Execute named steps, persisting after each step and review boundary."""

    def __init__(self, name: str, steps: list[WorkflowStep]) -> None:
        if not name.strip():
            raise ValueError("Workflow name cannot be empty")
        if not steps:
            raise ValueError("A workflow must contain at least one step")
        names = [step.name for step in steps]
        if any(not step_name.strip() for step_name in names):
            raise ValueError("Workflow step names cannot be empty")
        if len(names) != len(set(names)):
            raise ValueError("Workflow step names must be unique")
        self.name = name
        self.steps = tuple(steps)

    def run(
        self, run_id: str, input_data: JSONMapping, store: CheckpointStore
    ) -> WorkflowState:
        """Start a new run and advance until completion or human review."""
        if store.load(run_id) is not None:
            raise ValueError(f"A run with id {run_id!r} already exists")
        state = WorkflowState(run_id=run_id, status=RunStatus.RUNNING, input=dict(input_data))
        store.save(state)
        return self._advance(state, store)

    def resume(
        self,
        run_id: str,
        decision: ReviewDecision,
        reviewer: str,
        store: CheckpointStore,
        comment: str | None = None,
    ) -> WorkflowState:
        """Record a human decision and continue or reject a paused run."""
        if not reviewer.strip():
            raise ValueError("reviewer cannot be empty")
        state = store.load(run_id)
        if state is None:
            raise KeyError(f"No checkpoint found for run {run_id!r}")
        if state.status is not RunStatus.WAITING_REVIEW or state.pending_review is None:
            raise ValueError(f"Run {run_id!r} is not waiting for human review")

        pending = state.pending_review
        step_name = str(pending["step"])
        review: JSONMapping = {
            "step": step_name,
            "decision": decision.value,
            "reviewer": reviewer,
            "comment": comment,
            "request": pending["payload"],
        }
        state.reviews.append(review)
        state.outputs[step_name] = {"review": review}
        state.pending_review = None
        state.next_step += 1

        if decision is ReviewDecision.REJECTED:
            state.status = RunStatus.REJECTED
            store.save(state)
            return state

        state.status = RunStatus.RUNNING
        store.save(state)
        return self._advance(state, store)

    def _advance(self, state: WorkflowState, store: CheckpointStore) -> WorkflowState:
        try:
            while state.next_step < len(self.steps):
                step = self.steps[state.next_step]
                context = StepContext(state.run_id, state.input, dict(state.outputs))
                outcome = step.run(context)
                if isinstance(outcome, ReviewRequest):
                    state.status = RunStatus.WAITING_REVIEW
                    state.pending_review = {
                        "step": step.name,
                        "payload": outcome.payload,
                    }
                    store.save(state)
                    return state
                if not isinstance(outcome, Mapping):
                    raise TypeError(f"Step {step.name!r} must return a mapping or ReviewRequest")
                state.outputs[step.name] = dict(outcome)
                state.next_step += 1
                store.save(state)

            state.status = RunStatus.COMPLETED
            store.save(state)
            return state
        except Exception as error:
            state.status = RunStatus.FAILED
            state.error = f"{type(error).__name__}: {error}"
            store.save(state)
            raise
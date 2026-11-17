"""Async sequential workflow orchestration with durable human-review pauses."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
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
from orqmesh.workflow import StepContext

AsyncStepHandler = Callable[
    [StepContext], Awaitable[Mapping[str, JSONValue] | ReviewRequest]
]


@dataclass(frozen=True, slots=True)
class AsyncWorkflowStep:
    """Named asynchronous unit of workflow logic."""

    name: str
    run: AsyncStepHandler


class AsyncWorkflow:
    """Execute async steps sequentially and persist each state transition.

    The checkpoint backend follows the existing synchronous ``CheckpointStore``
    protocol. Calls are delegated to a worker thread so local or blocking storage
    does not block the application's event loop. A durable, concurrency-safe async
    backend is a separate adapter concern.
    """

    def __init__(self, name: str, steps: list[AsyncWorkflowStep]) -> None:
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

    async def run(
        self, run_id: str, input_data: JSONMapping, store: CheckpointStore
    ) -> WorkflowState:
        """Start a run and advance until completion or human review."""
        if await asyncio.to_thread(store.load, run_id) is not None:
            raise ValueError(f"A run with id {run_id!r} already exists")
        state = WorkflowState(run_id=run_id, status=RunStatus.RUNNING, input=dict(input_data))
        await self._save(store, state)
        return await self._advance(state, store)

    async def resume(
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
        state = await asyncio.to_thread(store.load, run_id)
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
            await self._save(store, state)
            return state

        state.status = RunStatus.RUNNING
        await self._save(store, state)
        return await self._advance(state, store)

    async def _save(self, store: CheckpointStore, state: WorkflowState) -> None:
        await asyncio.to_thread(store.save, state)

    async def _advance(self, state: WorkflowState, store: CheckpointStore) -> WorkflowState:
        try:
            while state.next_step < len(self.steps):
                step = self.steps[state.next_step]
                context = StepContext(state.run_id, state.input, dict(state.outputs))
                outcome = await step.run(context)
                if isinstance(outcome, ReviewRequest):
                    state.status = RunStatus.WAITING_REVIEW
                    state.pending_review = {
                        "step": step.name,
                        "payload": outcome.payload,
                    }
                    await self._save(store, state)
                    return state
                if not isinstance(outcome, Mapping):
                    raise TypeError(f"Step {step.name!r} must return a mapping or ReviewRequest")
                state.outputs[step.name] = dict(outcome)
                state.next_step += 1
                await self._save(store, state)

            state.status = RunStatus.COMPLETED
            await self._save(store, state)
            return state
        except Exception as error:
            state.status = RunStatus.FAILED
            state.error = f"{type(error).__name__}: {error}"
            await self._save(store, state)
            raise
        except asyncio.CancelledError:
            state.status = RunStatus.FAILED
            state.error = "CancelledError: workflow execution was cancelled"
            await self._save(store, state)
            raise
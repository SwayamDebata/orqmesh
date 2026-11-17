import asyncio

import pytest

from orqmesh import (
    AsyncWorkflow,
    AsyncWorkflowStep,
    JsonFileCheckpointStore,
    ReviewDecision,
    ReviewRequest,
    RunStatus,
)


def test_async_workflow_pauses_and_resumes_after_checkpoint_reload(tmp_path):
    async def prepare(context):
        await asyncio.sleep(0)
        return {"value": context.input["value"]}

    async def request_review(context):
        return ReviewRequest({"value": context.outputs["prepare"]["value"]})

    async def finish(context):
        return {"status": "ready", "review": context.outputs["request_review"]["review"]}

    workflow = AsyncWorkflow(
        "async-review",
        [
            AsyncWorkflowStep("prepare", prepare),
            AsyncWorkflowStep("request_review", request_review),
            AsyncWorkflowStep("finish", finish),
        ],
    )

    async def exercise():
        paused = await workflow.run("async-1", {"value": 99}, JsonFileCheckpointStore(tmp_path))
        assert paused.status is RunStatus.WAITING_REVIEW

        completed = await workflow.resume(
            paused.run_id,
            ReviewDecision.APPROVED,
            "finance-reviewer",
            JsonFileCheckpointStore(tmp_path),
        )
        assert completed.status is RunStatus.COMPLETED
        assert completed.outputs["finish"]["status"] == "ready"
        assert completed.reviews[0]["reviewer"] == "finance-reviewer"

    asyncio.run(exercise())


def test_async_workflow_rejection_does_not_run_posting_step(tmp_path):
    posting_calls = []

    async def request_review(context):
        return ReviewRequest({"candidate_count": 2})

    async def post(context):
        posting_calls.append(context.run_id)
        return {"posted": True}

    workflow = AsyncWorkflow(
        "async-reject",
        [AsyncWorkflowStep("review", request_review), AsyncWorkflowStep("post", post)],
    )

    async def exercise():
        paused = await workflow.run("async-reject-1", {}, JsonFileCheckpointStore(tmp_path))
        rejected = await workflow.resume(
            paused.run_id,
            ReviewDecision.REJECTED,
            "finance-reviewer",
            JsonFileCheckpointStore(tmp_path),
        )
        assert rejected.status is RunStatus.REJECTED

    asyncio.run(exercise())
    assert posting_calls == []


def test_async_workflow_persists_failure_and_reraises(tmp_path):
    async def broken_step(context):
        raise RuntimeError("service unavailable")

    workflow = AsyncWorkflow("async-failure", [AsyncWorkflowStep("call_service", broken_step)])
    store = JsonFileCheckpointStore(tmp_path)

    async def exercise():
        with pytest.raises(RuntimeError, match="service unavailable"):
            await workflow.run("async-failure-1", {}, store)

    asyncio.run(exercise())
    failed = store.load("async-failure-1")
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error == "RuntimeError: service unavailable"
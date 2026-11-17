from orqmesh import (
    JsonFileCheckpointStore,
    ReviewDecision,
    ReviewRequest,
    RunStatus,
    Workflow,
    WorkflowStep,
)


def test_review_checkpoint_can_resume_after_reloading_store(tmp_path):
    store = JsonFileCheckpointStore(tmp_path)
    workflow = Workflow(
        "review-flow",
        [
            WorkflowStep("prepare", lambda context: {"value": context.input["value"]}),
            WorkflowStep(
                "approve",
                lambda context: ReviewRequest(
                    {"value": context.outputs["prepare"]["value"]}
                ),
            ),
            WorkflowStep("finish", lambda context: {"result": "done"}),
        ],
    )

    paused = workflow.run("run-1", {"value": 42}, store)
    assert paused.status is RunStatus.WAITING_REVIEW
    assert paused.next_step == 1
    assert paused.pending_review == {"step": "approve", "payload": {"value": 42}}

    restored_store = JsonFileCheckpointStore(tmp_path)
    completed = workflow.resume(
        "run-1", ReviewDecision.APPROVED, "reviewer-1", restored_store
    )
    assert completed.status is RunStatus.COMPLETED
    assert completed.outputs["finish"] == {"result": "done"}
    assert completed.reviews[0]["reviewer"] == "reviewer-1"


def test_rejected_review_stops_workflow(tmp_path):
    store = JsonFileCheckpointStore(tmp_path)
    workflow = Workflow(
        "review-flow",
        [WorkflowStep("approve", lambda context: ReviewRequest({"risk": "high"})),
         WorkflowStep("must_not_run", lambda context: {"unexpected": True})],
    )
    paused = workflow.run("run-rejected", {}, store)

    rejected = workflow.resume(
        paused.run_id, ReviewDecision.REJECTED, "reviewer-2", store, "Insufficient evidence"
    )
    assert rejected.status is RunStatus.REJECTED
    assert "must_not_run" not in rejected.outputs


def test_checkpoint_store_rejects_path_traversal(tmp_path):
    store = JsonFileCheckpointStore(tmp_path)
    try:
        store.load("../outside")
    except ValueError as error:
        assert "safe" in str(error)
    else:
        raise AssertionError("unsafe run id should be rejected")

import pytest

from orqmesh import JsonFileCheckpointStore, ReviewDecision, RunStatus
from orqmesh.examples.document_review import build_document_review_workflow


def test_document_without_review_completes_automatically(tmp_path):
    workflow = build_document_review_workflow()
    state = workflow.run(
        "automatic",
        {
            "document": {
                "document_id": " DOC-1 ",
                "title": " Example ",
                "content": " Synthetic content. ",
                "requires_review": False,
            }
        },
        JsonFileCheckpointStore(tmp_path),
    )

    assert state.status is RunStatus.COMPLETED
    assert state.pending_review is None
    assert state.reviews == []
    assert state.outputs["validate_document"] == {
        "document_id": "DOC-1",
        "title": "Example",
        "content": "Synthetic content.",
        "requires_review": False,
    }
    assert state.outputs["review_document"] == {
        "decision": "auto_approved",
        "reason": "review_not_required",
    }
    assert state.outputs["finalize_document"] == {
        "status": "ready",
        "document_id": "DOC-1",
        "title": "Example",
        "approval": "auto_approved",
    }


def test_document_review_approval_resumes_from_checkpoint(tmp_path):
    workflow = build_document_review_workflow()
    document = {
        "document_id": "DOC-2",
        "title": "Example",
        "content": "Synthetic content.",
        "requires_review": True,
    }
    paused = workflow.run("approval", {"document": document}, JsonFileCheckpointStore(tmp_path))

    assert paused.status is RunStatus.WAITING_REVIEW
    assert paused.pending_review == {
        "step": "review_document",
        "payload": {"reason": "review_requested", "document": document},
    }
    assert "finalize_document" not in paused.outputs

    completed = workflow.resume(
        paused.run_id, ReviewDecision.APPROVED, "reviewer", JsonFileCheckpointStore(tmp_path)
    )
    assert completed.status is RunStatus.COMPLETED
    assert completed.pending_review is None
    assert completed.reviews[0]["decision"] == "approved"
    assert completed.reviews[0]["reviewer"] == "reviewer"
    assert completed.outputs["finalize_document"] == {
        "status": "ready",
        "document_id": "DOC-2",
        "title": "Example",
        "approval": "approved",
    }


def test_document_review_rejection_does_not_finalize(tmp_path):
    workflow = build_document_review_workflow()
    store = JsonFileCheckpointStore(tmp_path)
    paused = workflow.run(
        "rejection",
        {
            "document": {
                "document_id": "DOC-3",
                "title": "Example",
                "content": "Synthetic content.",
                "requires_review": True,
            }
        },
        store,
    )
    assert paused.status is RunStatus.WAITING_REVIEW

    rejected = workflow.resume(
        paused.run_id, ReviewDecision.REJECTED, "reviewer", store, "Not approved"
    )
    assert rejected.status is RunStatus.REJECTED
    assert rejected.pending_review is None
    assert rejected.reviews[0]["decision"] == "rejected"
    assert rejected.reviews[0]["comment"] == "Not approved"
    assert "finalize_document" not in rejected.outputs
    assert store.load(rejected.run_id).status is RunStatus.REJECTED


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (None, "document.*object"),
        ({"title": "Example", "content": "Text", "requires_review": False}, "document_id"),
        (
            {"document_id": "DOC", "title": " ", "content": "Text", "requires_review": False},
            "title",
        ),
        (
            {"document_id": "DOC", "title": "Example", "content": 1, "requires_review": False},
            "content",
        ),
        ({"document_id": "DOC", "title": "Example", "content": "Text"}, "requires_review"),
        (
            {"document_id": "DOC", "title": "Example", "content": "Text", "requires_review": 1},
            "requires_review",
        ),
    ],
)
def test_invalid_document_is_rejected(tmp_path, document, message):
    workflow = build_document_review_workflow()
    store = JsonFileCheckpointStore(tmp_path)

    with pytest.raises(ValueError, match=message):
        workflow.run("invalid", {"document": document}, store)
    assert store.load("invalid").status is RunStatus.FAILED
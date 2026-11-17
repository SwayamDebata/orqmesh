"""Run the document review example from the repository root."""

# ruff: noqa: I001

from uuid import uuid4

from orqmesh import JsonFileCheckpointStore, ReviewDecision, RunStatus
from orqmesh.examples.document_review import build_document_review_workflow


def main() -> None:
    """Run a synthetic document through a simulated human approval."""
    workflow = build_document_review_workflow()
    document = {
        "document_id": "DOC-2048",
        "title": "Example document",
        "content": "Synthetic content for a workflow demonstration.",
        "requires_review": True,
    }
    store = JsonFileCheckpointStore(".checkpoints")
    state = workflow.run(f"document-demo-{uuid4().hex}", {"document": document}, store)
    print(f"Initial status: {state.status.value}")

    if state.status is RunStatus.WAITING_REVIEW:
        print(f"Human review required: {state.pending_review}")
        state = workflow.resume(
            state.run_id,
            ReviewDecision.APPROVED,
            reviewer="demo-reviewer",
            comment="Example only: simulated approval.",
            store=store,
        )

    print(f"Final status: {state.status.value}")
    print(f"Final result: {state.outputs.get('finalize_document')}")


if __name__ == "__main__":
    main()
"""A deterministic document workflow demonstrating approval checkpoints."""

from __future__ import annotations

from collections.abc import Mapping

from orqmesh.models import JSONValue, ReviewRequest
from orqmesh.workflow import StepContext, Workflow, WorkflowStep


def build_document_review_workflow() -> Workflow:
    """Build a workflow using the caller's explicit human-review flag.

    Input must contain a ``document`` object with nonempty ``document_id``,
    ``title``, and ``content`` strings and a boolean ``requires_review``.
    The workflow does not inspect content to determine whether review is needed.
    """

    def validate_document(context: StepContext) -> dict[str, JSONValue]:
        document = context.input.get("document")
        if not isinstance(document, Mapping):
            raise ValueError("input must include a 'document' object")

        document_id = document.get("document_id")
        title = document.get("title")
        content = document.get("content")
        if not all(
            isinstance(value, str) and value.strip() for value in (document_id, title, content)
        ):
            raise ValueError("document_id, title, and content must be nonempty strings")
        requires_review = document.get("requires_review")
        if not isinstance(requires_review, bool):
            raise ValueError("requires_review must be a boolean")

        assert isinstance(document_id, str)
        assert isinstance(title, str)
        assert isinstance(content, str)
        return {
            "document_id": document_id.strip(),
            "title": title.strip(),
            "content": content.strip(),
            "requires_review": requires_review,
        }

    def review_document(context: StepContext) -> dict[str, JSONValue] | ReviewRequest:
        document = context.outputs["validate_document"]
        if document["requires_review"]:
            return ReviewRequest(payload={"reason": "review_requested", "document": document})
        return {"decision": "auto_approved", "reason": "review_not_required"}

    def finalize_document(context: StepContext) -> dict[str, JSONValue]:
        document = context.outputs["validate_document"]
        review = context.outputs["review_document"]
        decision = review.get("decision")
        review_record = review.get("review")
        if decision is None and isinstance(review_record, Mapping):
            decision = review_record.get("decision")
        if decision not in {"approved", "auto_approved"}:
            raise ValueError("document has no approval decision")
        return {
            "status": "ready",
            "document_id": document["document_id"],
            "title": document["title"],
            "approval": decision,
        }

    return Workflow(
        name="document_review",
        steps=[
            WorkflowStep("validate_document", validate_document),
            WorkflowStep("review_document", review_document),
            WorkflowStep("finalize_document", finalize_document),
        ],
    )
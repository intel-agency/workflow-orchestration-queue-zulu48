"""Tests for WorkItem model."""

import pytest
from pydantic import ValidationError

from sentinel.models import TaskType, WorkItem, WorkItemStatus


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_plan_exists(self) -> None:
        """Test that PLAN task type exists."""
        assert TaskType.PLAN == "PLAN"

    def test_task_type_implement_exists(self) -> None:
        """Test that IMPLEMENT task type exists."""
        assert TaskType.IMPLEMENT == "IMPLEMENT"

    def test_task_type_values(self) -> None:
        """Test all TaskType values."""
        values = {t.value for t in TaskType}
        assert values == {"PLAN", "IMPLEMENT"}


class TestWorkItemStatus:
    """Tests for WorkItemStatus enum."""

    def test_queued_status(self) -> None:
        """Test QUEUED status."""
        assert WorkItemStatus.QUEUED == "QUEUED"

    def test_in_progress_status(self) -> None:
        """Test IN_PROGRESS status."""
        assert WorkItemStatus.IN_PROGRESS == "IN_PROGRESS"

    def test_blocked_status(self) -> None:
        """Test BLOCKED status."""
        assert WorkItemStatus.BLOCKED == "BLOCKED"

    def test_review_status(self) -> None:
        """Test REVIEW status."""
        assert WorkItemStatus.REVIEW == "REVIEW"

    def test_completed_status(self) -> None:
        """Test COMPLETED status."""
        assert WorkItemStatus.COMPLETED == "COMPLETED"

    def test_cancelled_status(self) -> None:
        """Test CANCELLED status."""
        assert WorkItemStatus.CANCELLED == "CANCELLED"

    def test_all_statuses_defined(self) -> None:
        """Test all expected statuses are defined."""
        expected = {
            "QUEUED",
            "IN_PROGRESS",
            "BLOCKED",
            "REVIEW",
            "COMPLETED",
            "CANCELLED",
        }
        actual = {s.value for s in WorkItemStatus}
        assert actual == expected


class TestWorkItem:
    """Tests for WorkItem model."""

    def test_create_work_item_with_required_fields(self) -> None:
        """Test creating a WorkItem with only required fields."""
        item = WorkItem(
            id="42",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Implement feature X",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
        )

        assert item.id == "42"
        assert item.source_url == "https://github.com/owner/repo/issues/42"
        assert item.context_body == "Implement feature X"
        assert item.target_repo_slug == "owner/repo"
        assert item.task_type == TaskType.IMPLEMENT
        assert item.status == WorkItemStatus.QUEUED  # Default
        assert item.metadata == {}  # Default

    def test_create_work_item_with_all_fields(self) -> None:
        """Test creating a WorkItem with all fields."""
        item = WorkItem(
            id="123",
            source_url="https://github.com/owner/repo/issues/123",
            context_body="Plan the architecture",
            target_repo_slug="owner/repo",
            task_type=TaskType.PLAN,
            status=WorkItemStatus.IN_PROGRESS,
            metadata={
                "issue_node_id": "I_kwDOABC123",
                "labels": ["enhancement"],
            },
        )

        assert item.id == "123"
        assert item.status == WorkItemStatus.IN_PROGRESS
        assert item.metadata["issue_node_id"] == "I_kwDOABC123"
        assert item.metadata["labels"] == ["enhancement"]

    def test_work_item_with_integer_id(self) -> None:
        """Test WorkItem accepts integer ID."""
        item = WorkItem(
            id=42,
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
        )

        assert item.id == 42

    def test_work_item_default_status_is_queued(self) -> None:
        """Test that default status is QUEUED."""
        item = WorkItem(
            id="1",
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
        )

        assert item.status == WorkItemStatus.QUEUED

    def test_work_item_default_metadata_is_empty_dict(self) -> None:
        """Test that default metadata is an empty dict."""
        item = WorkItem(
            id="1",
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
        )

        assert item.metadata == {}
        assert isinstance(item.metadata, dict)

    def test_work_item_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="1",
                # missing source_url
                context_body="Test",
                target_repo_slug="owner/repo",
                task_type=TaskType.IMPLEMENT,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_url",) for e in errors)

    def test_work_item_invalid_target_repo_slug_raises_error(self) -> None:
        """Test that invalid repo slug format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="1",
                source_url="https://github.com/owner/repo/issues/1",
                context_body="Test",
                target_repo_slug="invalid-repo-slug",  # Missing /
                task_type=TaskType.IMPLEMENT,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("target_repo_slug",) for e in errors)

    def test_work_item_accepts_valid_repo_slug(self) -> None:
        """Test that valid repo slug format is accepted."""
        item = WorkItem(
            id="1",
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
        )

        assert item.target_repo_slug == "owner/repo"

    def test_work_item_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="1",
                source_url="https://github.com/owner/repo/issues/1",
                context_body="Test",
                target_repo_slug="owner/repo",
                task_type=TaskType.IMPLEMENT,
                extra_field="not allowed",  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extra_field",) for e in errors)

    def test_work_item_model_copy(self) -> None:
        """Test that model_copy creates a proper copy."""
        original = WorkItem(
            id="1",
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
        )

        updated = original.model_copy(update={"status": WorkItemStatus.IN_PROGRESS})

        assert original.status == WorkItemStatus.QUEUED
        assert updated.status == WorkItemStatus.IN_PROGRESS

    def test_work_item_json_serialization(self) -> None:
        """Test JSON serialization of WorkItem."""
        item = WorkItem(
            id="42",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Test content",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
        )

        json_str = item.model_dump_json()
        assert '"id":"42"' in json_str or '"id": 42' in json_str
        assert '"task_type":"IMPLEMENT"' in json_str
        assert '"status":"QUEUED"' in json_str

    def test_work_item_dict_export(self) -> None:
        """Test dict export of WorkItem."""
        item = WorkItem(
            id="42",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Test content",
            target_repo_slug="owner/repo",
            task_type=TaskType.PLAN,
            status=WorkItemStatus.IN_PROGRESS,
        )

        data = item.model_dump()

        assert data["id"] == "42"
        assert data["task_type"] == TaskType.PLAN or data["task_type"] == "PLAN"
        assert data["status"] == WorkItemStatus.IN_PROGRESS or data["status"] == "IN_PROGRESS"

    def test_work_item_with_complex_metadata(self) -> None:
        """Test WorkItem with complex metadata."""
        metadata = {
            "issue_node_id": "I_kwDOABC123",
            "labels": ["bug", "priority-high", "area:auth"],
            "nested": {"key": "value"},
            "numbers": [1, 2, 3],
        }

        item = WorkItem(
            id="42",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            metadata=metadata,
        )

        assert item.metadata == metadata
        assert item.metadata["nested"]["key"] == "value"

    def test_work_item_enum_values_in_json(self) -> None:
        """Test that enum values are serialized as strings in JSON."""
        item = WorkItem(
            id="1",
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.PLAN,
            status=WorkItemStatus.REVIEW,
        )

        data = item.model_dump()

        # With use_enum_values=True, enums should be serialized as their values
        assert data["task_type"] in (TaskType.PLAN, "PLAN")
        assert data["status"] in (WorkItemStatus.REVIEW, "REVIEW")

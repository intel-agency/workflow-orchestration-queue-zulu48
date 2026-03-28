"""Tests for orchestrator_sentinel."""

import pytest

from src.models.work_item import WorkItem, WorkItemStatus, TaskType


class TestSentinelHelpers:
    """Tests for sentinel helper functions."""

    def test_work_item_status_transitions(self):
        """Test that status enum values match expected labels."""
        assert WorkItemStatus.QUEUED.value == "agent:queued"
        assert WorkItemStatus.IN_PROGRESS.value == "agent:in-progress"
        assert WorkItemStatus.SUCCESS.value == "agent:success"
        assert WorkItemStatus.ERROR.value == "agent:error"
        assert WorkItemStatus.INFRA_FAILURE.value == "agent:infra-failure"

    def test_task_type_enum(self):
        """Test task type enum values."""
        assert TaskType.PLAN.value == "plan"
        assert TaskType.IMPLEMENT.value == "implement"


class TestEnvironmentValidation:
    """Tests for environment validation."""

    def test_missing_token_detection(self, monkeypatch):
        """Test that missing GITHUB_TOKEN is detected."""
        from src.orchestrator_sentinel import validate_environment

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")

        with pytest.raises(SystemExit):
            validate_environment()

    def test_placeholder_detection(self, monkeypatch):
        """Test that placeholder tokens are detected."""
        from src.orchestrator_sentinel import validate_environment

        monkeypatch.setenv("GITHUB_TOKEN", "YOUR_TOKEN_HERE")
        monkeypatch.setenv("GITHUB_REPO", "owner/repo")

        with pytest.raises(SystemExit):
            validate_environment()

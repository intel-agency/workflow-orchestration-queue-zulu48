"""Tests for work_item model."""

import pytest

from src.models.work_item import (
    TaskType,
    WorkItem,
    WorkItemStatus,
    scrub_secrets,
)


class TestWorkItem:
    """Tests for WorkItem model."""

    def test_create_work_item(self):
        """Test creating a basic work item."""
        item = WorkItem(
            id="123",
            issue_number=1,
            source_url="https://github.com/owner/repo/issues/1",
            context_body="Test context",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
        )

        assert item.id == "123"
        assert item.issue_number == 1
        assert item.status == WorkItemStatus.QUEUED

    def test_work_item_with_metadata(self):
        """Test work item with optional metadata."""
        item = WorkItem(
            id="456",
            issue_number=2,
            source_url="https://github.com/owner/repo/issues/2",
            context_body="Test",
            target_repo_slug="owner/repo",
            task_type=TaskType.PLAN,
            status=WorkItemStatus.IN_PROGRESS,
            node_id="I_123",
            metadata={"custom": "value"},
        )

        assert item.node_id == "I_123"
        assert item.metadata["custom"] == "value"


class TestScrubSecrets:
    """Tests for credential scrubbing."""

    def test_scrub_github_pat(self):
        """Test GitHub PAT scrubbing."""
        text = "Token: ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        result = scrub_secrets(text)
        assert "ghp_" not in result
        assert "[REDACTED]" in result

    def test_scrub_openai_key(self):
        """Test OpenAI API key scrubbing."""
        text = "API Key: sk-abcdefghijklmnopqrstuvwxyz123456"
        result = scrub_secrets(text)
        assert "sk-" not in result
        assert "[REDACTED]" in result

    def test_scrub_bearer_token(self):
        """Test Bearer token scrubbing."""
        text = "Authorization: Bearer abc123xyz789"
        result = scrub_secrets(text)
        assert "Bearer abc" not in result

    def test_preserve_normal_text(self):
        """Test that normal text is preserved."""
        text = "This is a normal log message without secrets"
        result = scrub_secrets(text)
        assert result == text

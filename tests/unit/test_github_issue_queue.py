"""Tests for GitHubIssueQueue implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from sentinel.models import TaskType, WorkItem, WorkItemStatus
from sentinel.providers.github import GitHubIssueQueue
from sentinel.providers.github.issue_queue import (
    LABEL_TO_STATUS,
    STATUS_TO_LABEL,
    GitHubAPIError,
    ItemNotFoundError,
)


class TestStatusLabelMappings:
    """Tests for status-label mapping constants."""

    def test_all_statuses_have_label_mappings(self) -> None:
        """Test that all WorkItemStatus values have corresponding labels."""
        for status in WorkItemStatus:
            assert status in STATUS_TO_LABEL, f"Missing label for {status}"

    def test_all_labels_have_status_mappings(self) -> None:
        """Test that all labels have corresponding statuses."""
        for status, label in STATUS_TO_LABEL.items():
            assert label in LABEL_TO_STATUS, f"Missing status for label {label}"
            assert LABEL_TO_STATUS[label] == status

    def test_label_format(self) -> None:
        """Test that all labels follow the orchestration: prefix pattern."""
        for label in STATUS_TO_LABEL.values():
            assert label.startswith("orchestration:"), f"Label {label} missing prefix"


class TestGitHubIssueQueueInit:
    """Tests for GitHubIssueQueue initialization."""

    def test_init_with_token(self) -> None:
        """Test initialization with explicit token."""
        queue = GitHubIssueQueue(repo="owner/repo", token="test-token")

        assert queue.repo == "owner/repo"
        assert queue.token == "test-token"
        assert queue.api_base == "https://api.github.com"

    def test_init_with_env_token(self) -> None:
        """Test initialization with token from environment."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env-token"}, clear=True):
            queue = GitHubIssueQueue(repo="owner/repo")
            assert queue.token == "env-token"

    def test_init_with_gh_token_env(self) -> None:
        """Test initialization with GH_TOKEN from environment."""
        with patch.dict(os.environ, {"GH_TOKEN": "gh-env-token"}, clear=True):
            queue = GitHubIssueQueue(repo="owner/repo")
            assert queue.token == "gh-env-token"

    def test_init_github_token_takes_precedence(self) -> None:
        """Test that GITHUB_TOKEN takes precedence over GH_TOKEN."""
        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "github-token", "GH_TOKEN": "gh-token"},
            clear=True,
        ):
            queue = GitHubIssueQueue(repo="owner/repo")
            assert queue.token == "github-token"

    def test_init_explicit_token_overrides_env(self) -> None:
        """Test that explicit token overrides environment."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env-token"}, clear=True):
            queue = GitHubIssueQueue(repo="owner/repo", token="explicit-token")
            assert queue.token == "explicit-token"

    def test_init_custom_api_base(self) -> None:
        """Test initialization with custom API base URL."""
        queue = GitHubIssueQueue(
            repo="owner/repo",
            token="test-token",
            api_base="https://github.enterprise.com/api/v3",
        )
        assert queue.api_base == "https://github.enterprise.com/api/v3"

    def test_init_api_base_trailing_slash_removed(self) -> None:
        """Test that trailing slash is removed from API base."""
        queue = GitHubIssueQueue(
            repo="owner/repo",
            token="test-token",
            api_base="https://api.github.com/",
        )
        assert queue.api_base == "https://api.github.com"

    def test_init_invalid_repo_format_raises_error(self) -> None:
        """Test that invalid repo format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repo format"):
            GitHubIssueQueue(repo="invalid-repo", token="test-token")

    def test_init_missing_token_raises_error(self) -> None:
        """Test that missing token raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GitHub token is required"):
                GitHubIssueQueue(repo="owner/repo")

    def test_init_repo_with_multiple_slashes_raises_error(self) -> None:
        """Test that repo with multiple slashes raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repo format"):
            GitHubIssueQueue(repo="owner/repo/extra", token="test-token")


class TestGitHubIssueQueueFetchQueuedItems:
    """Tests for fetch_queued_items method."""

    @pytest.fixture
    def queue(self) -> GitHubIssueQueue:
        """Create a GitHubIssueQueue instance for testing."""
        return GitHubIssueQueue(repo="owner/repo", token="test-token")

    @pytest.fixture
    def mock_issue_response(self) -> list[dict]:
        """Create a mock issue response."""
        return [
            {
                "number": 42,
                "html_url": "https://github.com/owner/repo/issues/42",
                "body": "Implement feature X",
                "labels": [
                    {"name": "orchestration:ready"},
                    {"name": "enhancement"},
                ],
                "node_id": "I_kwDOABC123",
                "title": "Feature X Implementation",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "user": {"login": "developer"},
            },
            {
                "number": 43,
                "html_url": "https://github.com/owner/repo/issues/43",
                "body": "Plan the architecture",
                "labels": [
                    {"name": "orchestration:ready"},
                    {"name": "task-type:plan"},
                ],
                "node_id": "I_kwDOABC456",
                "title": "Architecture Planning",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "user": {"login": "architect"},
            },
        ]

    def test_fetch_queued_items_success(
        self,
        queue: GitHubIssueQueue,
        mock_issue_response: list[dict],
    ) -> None:
        """Test successful fetch of queued items."""
        with patch.object(queue, "_make_request", return_value=mock_issue_response):
            items = queue.fetch_queued_items()

            assert len(items) == 2
            assert items[0].id == "42"
            assert items[0].status == WorkItemStatus.QUEUED
            assert items[0].task_type == TaskType.IMPLEMENT
            assert items[1].task_type == TaskType.PLAN

    def test_fetch_queued_items_filters_pull_requests(
        self,
        queue: GitHubIssueQueue,
        mock_issue_response: list[dict],
    ) -> None:
        """Test that pull requests are filtered out."""
        mock_issue_response.append(
            {
                "number": 44,
                "html_url": "https://github.com/owner/repo/pull/44",
                "body": "This is a PR",
                "labels": [{"name": "orchestration:ready"}],
                "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/44"},
            }
        )

        with patch.object(queue, "_make_request", return_value=mock_issue_response):
            items = queue.fetch_queued_items()

            # Should only have 2 items (PR filtered out)
            assert len(items) == 2
            assert all(item.id != "44" for item in items)

    def test_fetch_queued_items_empty_response(self, queue: GitHubIssueQueue) -> None:
        """Test handling of empty response."""
        with patch.object(queue, "_make_request", return_value=[]):
            items = queue.fetch_queued_items()
            assert items == []

    def test_fetch_queued_items_metadata_populated(
        self,
        queue: GitHubIssueQueue,
        mock_issue_response: list[dict],
    ) -> None:
        """Test that metadata is properly populated."""
        with patch.object(queue, "_make_request", return_value=mock_issue_response[:1]):
            items = queue.fetch_queued_items()

            assert len(items) == 1
            assert items[0].metadata["issue_node_id"] == "I_kwDOABC123"
            assert items[0].metadata["title"] == "Feature X Implementation"
            assert items[0].metadata["user"] == "developer"

    def test_fetch_queued_items_api_error(self, queue: GitHubIssueQueue) -> None:
        """Test that API errors are properly raised."""
        with patch.object(
            queue,
            "_make_request",
            side_effect=GitHubAPIError("API Error", status_code=500),
        ), pytest.raises(GitHubAPIError):
            queue.fetch_queued_items()

    def test_fetch_queued_items_correct_params(self, queue: GitHubIssueQueue) -> None:
        """Test that correct API parameters are used."""
        mock_request = MagicMock(return_value=[])
        with patch.object(queue, "_make_request", mock_request):
            queue.fetch_queued_items()

            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "/repos/owner/repo/issues" in call_args[0][1]
            params = call_args[1]["params"]
            assert params["state"] == "open"
            assert params["labels"] == "orchestration:ready"


class TestGitHubIssueQueueUpdateItemStatus:
    """Tests for update_item_status method."""

    @pytest.fixture
    def queue(self) -> GitHubIssueQueue:
        """Create a GitHubIssueQueue instance for testing."""
        return GitHubIssueQueue(repo="owner/repo", token="test-token")

    @pytest.fixture
    def work_item(self) -> WorkItem:
        """Create a sample WorkItem for testing."""
        return WorkItem(
            id="42",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Test item",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
            metadata={"labels": ["orchestration:ready", "enhancement"]},
        )

    @pytest.fixture
    def mock_issue_response(self) -> dict:
        """Create a mock issue response."""
        return {
            "number": 42,
            "labels": [
                {"name": "orchestration:ready"},
                {"name": "enhancement"},
            ],
        }

    def test_update_item_status_success(
        self,
        queue: GitHubIssueQueue,
        work_item: WorkItem,
        mock_issue_response: dict,
    ) -> None:
        """Test successful status update."""
        with patch.object(queue, "_make_request", return_value=mock_issue_response):
            updated = queue.update_item_status(work_item, WorkItemStatus.IN_PROGRESS)

            assert updated.status == WorkItemStatus.IN_PROGRESS
            assert STATUS_TO_LABEL[WorkItemStatus.IN_PROGRESS] in updated.metadata["labels"]
            assert STATUS_TO_LABEL[WorkItemStatus.QUEUED] not in updated.metadata["labels"]

    def test_update_item_status_preserves_original(
        self,
        queue: GitHubIssueQueue,
        work_item: WorkItem,
        mock_issue_response: dict,
    ) -> None:
        """Test that original item is not modified."""
        original_status = work_item.status
        original_labels = work_item.metadata["labels"].copy()

        with patch.object(queue, "_make_request", return_value=mock_issue_response):
            updated = queue.update_item_status(work_item, WorkItemStatus.COMPLETED)

            # Original should be unchanged
            assert work_item.status == original_status
            assert work_item.metadata["labels"] == original_labels

            # Updated should have new status
            assert updated.status == WorkItemStatus.COMPLETED

    def test_update_item_status_not_found(
        self,
        queue: GitHubIssueQueue,
        work_item: WorkItem,
    ) -> None:
        """Test handling of item not found error."""
        with patch.object(
            queue,
            "_make_request",
            side_effect=GitHubAPIError("Not found", status_code=404),
        ), pytest.raises(ItemNotFoundError):
            queue.update_item_status(work_item, WorkItemStatus.IN_PROGRESS)

    def test_update_item_status_preserves_non_status_labels(
        self,
        queue: GitHubIssueQueue,
        work_item: WorkItem,
    ) -> None:
        """Test that non-status labels are preserved."""
        mock_response = {
            "number": 42,
            "labels": [
                {"name": "orchestration:ready"},
                {"name": "enhancement"},
                {"name": "priority-high"},
            ],
        }

        with patch.object(queue, "_make_request", return_value=mock_response):
            updated = queue.update_item_status(work_item, WorkItemStatus.IN_PROGRESS)

            assert "enhancement" in updated.metadata["labels"]
            assert "priority-high" in updated.metadata["labels"]

    def test_update_item_status_all_statuses(
        self,
        queue: GitHubIssueQueue,
        work_item: WorkItem,
        mock_issue_response: dict,
    ) -> None:
        """Test updating to all possible statuses."""
        for status in WorkItemStatus:
            with patch.object(queue, "_make_request", return_value=mock_issue_response):
                updated = queue.update_item_status(work_item, status)
                assert updated.status == status


class TestGitHubAPIError:
    """Tests for GitHubAPIError exception."""

    def test_error_with_message(self) -> None:
        """Test error with just a message."""
        error = GitHubAPIError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.status_code is None
        assert error.response is None

    def test_error_with_status_code(self) -> None:
        """Test error with status code."""
        error = GitHubAPIError("Not found", status_code=404)
        assert error.status_code == 404

    def test_error_with_response(self) -> None:
        """Test error with response object."""
        mock_response = MagicMock()
        error = GitHubAPIError("Server error", status_code=500, response=mock_response)
        assert error.response == mock_response


class TestMakeRequest:
    """Tests for _make_request method."""

    @pytest.fixture
    def queue(self) -> GitHubIssueQueue:
        """Create a GitHubIssueQueue instance for testing."""
        return GitHubIssueQueue(repo="owner/repo", token="test-token")

    def test_make_request_success(self, queue: GitHubIssueQueue) -> None:
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123}

        with patch("requests.request", return_value=mock_response):
            result = queue._make_request("GET", "/test")

            assert result == {"id": 123}

    def test_make_request_error_response(self, queue: GitHubIssueQueue) -> None:
        """Test handling of error response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json.return_value = {}

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(GitHubAPIError) as exc_info:
                queue._make_request("GET", "/test")

            assert exc_info.value.status_code == 404

    def test_make_request_includes_headers(self, queue: GitHubIssueQueue) -> None:
        """Test that request includes proper headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch("requests.request") as mock_request:
            mock_request.return_value = mock_response
            queue._make_request("GET", "/test")

            headers = mock_request.call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test-token"
            assert "Accept" in headers

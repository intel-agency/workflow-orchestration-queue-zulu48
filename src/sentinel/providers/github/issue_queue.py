"""GitHub Issues implementation of the IWorkQueue interface.

This module provides the GitHubIssueQueue class that implements the
IWorkQueue interface using the GitHub REST API for issue operations.
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import requests

from ...interfaces.work_queue import IWorkQueue
from ...models.work_item import TaskType, WorkItem, WorkItemStatus

logger = logging.getLogger(__name__)


# Status to GitHub label mappings
STATUS_TO_LABEL: dict[WorkItemStatus, str] = {
    WorkItemStatus.QUEUED: "orchestration:ready",
    WorkItemStatus.IN_PROGRESS: "orchestration:in-progress",
    WorkItemStatus.BLOCKED: "orchestration:blocked",
    WorkItemStatus.REVIEW: "orchestration:review",
    WorkItemStatus.COMPLETED: "orchestration:completed",
    WorkItemStatus.CANCELLED: "orchestration:cancelled",
}

# Label to status mappings (reverse)
LABEL_TO_STATUS: dict[str, WorkItemStatus] = {v: k for k, v in STATUS_TO_LABEL.items()}

# Task type to label mappings
TASK_TYPE_LABELS: dict[TaskType, str] = {
    TaskType.PLAN: "task-type:plan",
    TaskType.IMPLEMENT: "task-type:implement",
}


class GitHubIssueQueue(IWorkQueue):
    """GitHub Issues implementation of the IWorkQueue interface.

    This class provides a concrete implementation of IWorkQueue that uses
    the GitHub REST API to manage work items as GitHub Issues.

    Attributes:
        repo: Repository in 'owner/repo' format.
        token: GitHub personal access token for authentication.
        api_base: Base URL for GitHub API (defaults to github.com).

    Example:
        ```python
        queue = GitHubIssueQueue(
            repo="owner/repo",
            token="ghp_xxxxxxxxxxxx"
        )

        # Fetch queued items
        items = queue.fetch_queued_items()

        # Update status
        updated = queue.update_item_status(items[0], WorkItemStatus.IN_PROGRESS)
        ```
    """

    def __init__(
        self,
        repo: str,
        token: str | None = None,
        api_base: str = "https://api.github.com",
    ) -> None:
        """Initialize the GitHub Issue Queue.

        Args:
            repo: Repository in 'owner/repo' format.
            token: GitHub personal access token. If not provided, will attempt
                   to read from GITHUB_TOKEN or GH_TOKEN environment variable.
            api_base: Base URL for GitHub API. Defaults to github.com API.
                      Use 'https://api.github.enterprise.com' for GitHub Enterprise.

        Raises:
            ValueError: If repo is not in 'owner/repo' format or token is not available.
        """
        if "/" not in repo or repo.count("/") != 1:
            raise ValueError(f"Invalid repo format '{repo}'. Expected 'owner/repo'.")

        self.repo = repo
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.api_base = api_base.rstrip("/")

        if not self.token:
            raise ValueError(
                "GitHub token is required. Provide it via the 'token' parameter "
                "or set the GITHUB_TOKEN or GH_TOKEN environment variable."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """Make an HTTP request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.).
            endpoint: API endpoint (without base URL).
            **kwargs: Additional arguments passed to requests.

        Returns:
            JSON response (can be dict, list, or other JSON types).

        Raises:
            GitHubAPIError: If the API request fails.
        """
        url = f"{self.api_base}{endpoint}"
        headers = self._get_headers()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=30,
            **kwargs,
        )

        if response.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error: {response.status_code} - {response.text}",
                status_code=response.status_code,
                response=response,
            )

        return response.json()

    def _issue_to_work_item(self, issue: dict[str, Any]) -> WorkItem:
        """Convert a GitHub issue to a WorkItem.

        Args:
            issue: GitHub issue dictionary from API response.

        Returns:
            WorkItem representation of the issue.
        """
        labels = [label["name"] for label in issue.get("labels", [])]

        # Determine status from labels
        status = WorkItemStatus.QUEUED
        for label in labels:
            if label in LABEL_TO_STATUS:
                status = LABEL_TO_STATUS[label]
                break

        # Determine task type from labels
        task_type = TaskType.IMPLEMENT  # Default
        for label in labels:
            if label.startswith("task-type:"):
                if label == TASK_TYPE_LABELS[TaskType.PLAN]:
                    task_type = TaskType.PLAN
                break

        # Extract target repo from issue body or use current repo
        body = issue.get("body") or ""
        target_repo = self.repo  # Default to current repo

        # Look for target repo in body (could be extracted from structured content)
        # For now, we use the current repo as default

        return WorkItem(
            id=str(issue["number"]),
            source_url=issue["html_url"],
            context_body=body,
            target_repo_slug=target_repo,
            task_type=task_type,
            status=status,
            metadata={
                "issue_node_id": issue.get("node_id"),
                "title": issue.get("title"),
                "labels": labels,
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
                "user": issue.get("user", {}).get("login"),
            },
        )

    def _get_status_label(self, status: WorkItemStatus) -> str:
        """Get the GitHub label for a given status."""
        return STATUS_TO_LABEL.get(status, STATUS_TO_LABEL[WorkItemStatus.QUEUED])

    def fetch_queued_items(self) -> list[WorkItem]:
        """Fetch all work items that are queued and ready for processing.

        Retrieves GitHub issues with the 'orchestration:ready' label that
        are open and ready to be processed.

        Returns:
            A list of WorkItem objects representing the queued work items.

        Raises:
            GitHubAPIError: If the GitHub API request fails.
        """
        logger.info(f"Fetching queued items from {self.repo}")

        try:
            # Fetch issues with orchestration:ready label
            params = {
                "state": "open",
                "labels": STATUS_TO_LABEL[WorkItemStatus.QUEUED],
                "per_page": 100,
                "sort": "created",
                "direction": "asc",
            }

            issues = cast(
                list[dict[str, Any]],
                self._make_request("GET", f"/repos/{self.repo}/issues", params=params),
            )

            work_items = []
            for issue in issues:
                # Skip pull requests (they have pull_request key)
                if "pull_request" in issue:
                    continue

                try:
                    work_item = self._issue_to_work_item(issue)
                    work_items.append(work_item)
                except Exception as e:
                    logger.warning(f"Failed to convert issue {issue.get('number')}: {e}")
                    continue

            logger.info(f"Found {len(work_items)} queued work items")
            return work_items

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to fetch queued items: {e}") from e

    def update_item_status(self, item: WorkItem, status: WorkItemStatus) -> WorkItem:
        """Update the status of a work item in the queue.

        Updates the GitHub issue's labels to reflect the new status.
        Removes the old status label and adds the new one.

        Args:
            item: The work item to update.
            status: The new status to set for the work item.

        Returns:
            The updated WorkItem with the new status reflected.

        Raises:
            GitHubAPIError: If the GitHub API request fails.
            ItemNotFoundError: If the issue cannot be found.
        """
        logger.info(f"Updating item {item.id} status to {status}")

        issue_number = int(item.id)
        new_label = self._get_status_label(status)

        try:
            # Get current issue to retrieve existing labels
            issue = self._make_request("GET", f"/repos/{self.repo}/issues/{issue_number}")

            current_labels = [label["name"] for label in issue.get("labels", [])]

            # Remove old status labels and add new one
            updated_labels = [label for label in current_labels if label not in LABEL_TO_STATUS]
            updated_labels.append(new_label)

            # Update the issue
            self._make_request(
                "PATCH",
                f"/repos/{self.repo}/issues/{issue_number}",
                json={"labels": updated_labels},
            )

            # Return updated work item with deep copy to avoid mutating original
            updated_item = item.model_copy(deep=True)
            updated_item.status = status

            # Update metadata with new labels
            updated_item.metadata["labels"] = updated_labels

            logger.info(f"Successfully updated item {item.id} to status {status}")
            return updated_item

        except GitHubAPIError as e:
            if e.status_code == 404:
                raise ItemNotFoundError(f"Issue {item.id} not found in {self.repo}") from e
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to update item status: {e}") from e


class GitHubAPIError(Exception):
    """Exception raised when GitHub API requests fail."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: requests.Response | None = None,
    ) -> None:
        """Initialize the GitHub API error.

        Args:
            message: Error message.
            status_code: HTTP status code from the response.
            response: The raw requests Response object.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ItemNotFoundError(Exception):
    """Exception raised when a work item cannot be found in the queue."""

    pass


class QueueConnectionError(Exception):
    """Exception raised when unable to connect to the queue provider."""

    pass


class QueueAuthenticationError(Exception):
    """Exception raised when authentication with the provider fails."""

    pass

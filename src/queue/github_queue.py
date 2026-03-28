"""GitHub Issues queue implementation."""

import asyncio
import logging
import os
import random
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from src.models.work_item import WorkItem, WorkItemStatus, TaskType

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("SENTINEL_POLL_INTERVAL", "60"))
MAX_BACKOFF = int(os.getenv("SENTINEL_MAX_BACKOFF", "960"))
SENTINEL_BOT_LOGIN = os.getenv("SENTINEL_BOT_LOGIN", "")


class ITaskQueue(ABC):
    """Abstract interface for task queue operations."""

    @abstractmethod
    async def fetch_queued_items(self) -> List[WorkItem]:
        """Fetch all items currently in the queue."""
        pass

    @abstractmethod
    async def claim_task(self, item: WorkItem) -> bool:
        """Attempt to claim a task. Returns True if successful."""
        pass

    @abstractmethod
    async def update_status(self, item: WorkItem, status: WorkItemStatus) -> bool:
        """Update the status of a work item."""
        pass

    @abstractmethod
    async def add_comment(self, item: WorkItem, body: str) -> bool:
        """Add a comment to a work item."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection."""
        pass


class GitHubQueue(ITaskQueue):
    """
    GitHub Issues-based task queue implementation.

    Uses GitHub Issues with labels as a distributed task queue.
    Implements assign-then-verify pattern for concurrency control.
    """

    def __init__(self, token: str, repo: str):
        """
        Initialize the GitHub queue.

        Args:
            token: GitHub API token
            repo: Repository in format "owner/repo"
        """
        self.token = token
        self.repo = repo
        self.owner, self.repo_name = repo.split("/", 1)
        self.base_url = "https://api.github.com"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_queued_items(self) -> List[WorkItem]:
        """
        Fetch all issues with the agent:queued label.

        Returns:
            List of WorkItems representing queued issues
        """
        client = await self._get_client()
        url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues"
        params = {
            "labels": "agent:queued",
            "state": "open",
            "per_page": 100,
        }

        response = await client.get(url, params=params)
        response.raise_for_status()
        issues = response.json()

        work_items = []
        for issue in issues:
            item = WorkItem(
                id=str(issue["id"]),
                issue_number=issue["number"],
                source_url=issue["html_url"],
                context_body=issue.get("body", "") or "",
                target_repo_slug=self.repo,
                task_type=TaskType.IMPLEMENT,
                status=WorkItemStatus.QUEUED,
                node_id=issue.get("node_id"),
                metadata={"title": issue.get("title", "")},
            )
            work_items.append(item)

        return work_items

    async def claim_task(self, item: WorkItem) -> bool:
        """
        Attempt to claim a task using assign-then-verify pattern.

        1. Attempt to assign SENTINEL_BOT_LOGIN to the issue
        2. Re-fetch the issue
        3. Verify the bot is in the assignees list

        Args:
            item: The work item to claim

        Returns:
            True if claim was successful, False otherwise
        """
        if not SENTINEL_BOT_LOGIN:
            logger.warning("SENTINEL_BOT_LOGIN not set, skipping distributed lock")
            return True

        client = await self._get_client()

        try:
            assign_url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{item.issue_number}/assignees"
            await client.post(assign_url, json={"assignees": [SENTINEL_BOT_LOGIN]})

            verify_url = (
                f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{item.issue_number}"
            )
            response = await client.get(verify_url)
            response.raise_for_status()
            issue = response.json()

            assignee_logins = [a["login"] for a in issue.get("assignees", [])]
            if SENTINEL_BOT_LOGIN not in assignee_logins:
                logger.info(f"Task {item.issue_number} claimed by another sentinel")
                return False

            logger.info(f"Successfully claimed task {item.issue_number}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to claim task {item.issue_number}: {e}")
            return False

    async def update_status(self, item: WorkItem, status: WorkItemStatus) -> bool:
        """
        Update the status of a work item by swapping labels.

        Args:
            item: The work item to update
            status: The new status

        Returns:
            True if update was successful
        """
        client = await self._get_client()
        url = (
            f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{item.issue_number}/labels"
        )

        try:
            response = await client.delete(url)
            if response.status_code not in (200, 204):
                pass

            add_url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{item.issue_number}/labels"
            await client.post(add_url, json={"labels": [status.value]})

            logger.info(f"Updated task {item.issue_number} to {status.value}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update status for task {item.issue_number}: {e}")
            return False

    async def add_comment(self, item: WorkItem, body: str) -> bool:
        """
        Add a comment to a work item.

        Args:
            item: The work item to comment on
            body: The comment body

        Returns:
            True if comment was added successfully
        """
        from src.models.work_item import scrub_secrets

        client = await self._get_client()
        url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{item.issue_number}/comments"

        scrubbed_body = scrub_secrets(body)

        try:
            await client.post(url, json={"body": scrubbed_body})
            logger.info(f"Added comment to task {item.issue_number}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to add comment to task {item.issue_number}: {e}")
            return False


async def run_with_backoff(
    coro, base_interval: int = POLL_INTERVAL, max_backoff: int = MAX_BACKOFF
):
    """
    Run a coroutine with jittered exponential backoff on failure.

    Args:
        coro: The coroutine to run
        base_interval: Base polling interval in seconds
        max_backoff: Maximum backoff time in seconds
    """
    current_backoff = base_interval

    while True:
        try:
            result = await coro
            current_backoff = base_interval
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429):
                jitter = random.uniform(0, 0.1 * current_backoff)
                wait_time = min(current_backoff + jitter, max_backoff)
                logger.warning(f"Rate limited, backing off for {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                current_backoff = min(current_backoff * 2, max_backoff)
            else:
                raise

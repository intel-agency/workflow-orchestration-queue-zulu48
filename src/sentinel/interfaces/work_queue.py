"""Abstract base class for work queue interfaces.

This module defines the IWorkQueue abstract base class that specifies
the interface for provider-agnostic queue operations.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from ..models.work_item import WorkItem, WorkItemStatus


class IWorkQueue(ABC):
    """Abstract base class defining the interface for work queue operations.

    This interface provides a provider-agnostic way to interact with different
    queue backends (GitHub Issues, Linear, Jira, etc.). Concrete implementations
    should map provider-specific APIs to these interface methods.

    Methods:
        fetch_queued_items: Retrieve all work items that are ready for processing.
        update_item_status: Update the status of a specific work item.

    Example:
        ```python
        class GitHubIssueQueue(IWorkQueue):
            def __init__(self, repo: str, token: str):
                self.repo = repo
                self.token = token

            def fetch_queued_items(self) -> list[WorkItem]:
                # Implementation using GitHub REST API
                ...

            def update_item_status(self, item: WorkItem, status: WorkItemStatus) -> WorkItem:
                # Implementation using GitHub REST API
                ...
        ```
    """

    @abstractmethod
    def fetch_queued_items(self) -> list[WorkItem]:
        """Fetch all work items that are queued and ready for processing.

        This method should retrieve work items from the underlying queue provider
        that are in a state ready to be processed (e.g., GitHub issues with
        specific labels like 'orchestration:ready').

        Returns:
            A list of WorkItem objects representing the queued work items.
            Returns an empty list if no items are queued.

        Raises:
            QueueConnectionError: If unable to connect to the queue provider.
            QueueAuthenticationError: If authentication with the provider fails.

        Example:
            ```python
            queue = GitHubIssueQueue(repo="owner/repo", token="ghp_xxx")
            items = queue.fetch_queued_items()
            for item in items:
                print(f"Processing: {item.id} - {item.context_body[:50]}")
            ```
        """
        ...

    @abstractmethod
    def update_item_status(self, item: WorkItem, status: WorkItemStatus) -> WorkItem:
        """Update the status of a work item in the queue.

        This method should update the work item's status in the underlying
        provider (e.g., by changing GitHub issue labels) and return the
        updated work item.

        Args:
            item: The work item to update.
            status: The new status to set for the work item.

        Returns:
            The updated WorkItem with the new status reflected.

        Raises:
            ItemNotFoundError: If the work item cannot be found in the queue.
            QueueConnectionError: If unable to connect to the queue provider.
            QueueAuthenticationError: If authentication with the provider fails.

        Example:
            ```python
            queue = GitHubIssueQueue(repo="owner/repo", token="ghp_xxx")
            item = queue.fetch_queued_items()[0]
            updated = queue.update_item_status(item, WorkItemStatus.IN_PROGRESS)
            print(f"Status updated to: {updated.status}")
            ```
        """
        ...


class IWorkQueueProtocol(Protocol):
    """Protocol version of IWorkQueue for structural subtyping.

    This protocol allows any class that implements the required methods
    to be treated as an IWorkQueue, even if it doesn't explicitly inherit
    from IWorkQueue.

    Use IWorkQueue (ABC) for explicit inheritance and IWorkQueueProtocol
    for structural type checking.
    """

    def fetch_queued_items(self) -> list[WorkItem]:
        """Fetch all work items that are queued and ready for processing."""
        ...

    def update_item_status(self, item: WorkItem, status: WorkItemStatus) -> WorkItem:
        """Update the status of a work item in the queue."""
        ...

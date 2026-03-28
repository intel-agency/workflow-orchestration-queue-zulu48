"""Work Item model for Sentinel queue system.

This module defines the WorkItem Pydantic model and related enums for
representing standardized work items across different queue providers.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Enumeration of task types for work items."""

    PLAN = "PLAN"
    """Planning task - analysis, design, or documentation work."""

    IMPLEMENT = "IMPLEMENT"
    """Implementation task - coding, configuration, or deployment work."""


class WorkItemStatus(str, Enum):
    """Enumeration of work item statuses mapping to GitHub labels.

    These statuses correspond to common workflow states and can be mapped
    to provider-specific status representations (e.g., GitHub labels).
    """

    QUEUED = "QUEUED"
    """Item is queued and waiting to be processed."""

    IN_PROGRESS = "IN_PROGRESS"
    """Item is currently being worked on."""

    BLOCKED = "BLOCKED"
    """Item is blocked and cannot proceed."""

    REVIEW = "REVIEW"
    """Item is under review."""

    COMPLETED = "COMPLETED"
    """Item has been completed successfully."""

    CANCELLED = "CANCELLED"
    """Item has been cancelled and will not be processed."""


class WorkItem(BaseModel):
    """Unified Pydantic model representing a standardized work item.

    This model provides a provider-agnostic representation of work items
    that can be used across different queue providers (GitHub, Linear, Jira, etc.).

    Attributes:
        id: Unique identifier for the work item (string or integer).
        source_url: URL of the original source (e.g., GitHub issue URL).
        context_body: The main content/context of the work item.
        target_repo_slug: Target repository in format 'owner/repo'.
        task_type: Type of task (PLAN or IMPLEMENT).
        status: Current status of the work item.
        metadata: Flexible dictionary for provider-specific data (e.g., GitHub node_id).

    Example:
        ```python
        work_item = WorkItem(
            id="12345",
            source_url="https://github.com/owner/repo/issues/42",
            context_body="Implement user authentication",
            target_repo_slug="owner/repo",
            task_type=TaskType.IMPLEMENT,
            status=WorkItemStatus.QUEUED,
            metadata={"issue_node_id": "I_kwDOABC123"}
        )
        ```
    """

    id: str | int = Field(
        ...,
        description="Unique identifier for the work item",
        examples=["12345", "GH-42", 12345],
    )
    source_url: str = Field(
        ...,
        description="URL of the original source (e.g., GitHub issue URL)",
        examples=["https://github.com/owner/repo/issues/42"],
    )
    context_body: str = Field(
        ...,
        description="The main content/context of the work item",
        examples=["Implement user authentication with OAuth2"],
    )
    target_repo_slug: str = Field(
        ...,
        description="Target repository in format 'owner/repo'",
        pattern=r"^[^/]+/[^/]+$",
        examples=["owner/repo"],
    )
    task_type: TaskType = Field(
        ...,
        description="Type of task (PLAN or IMPLEMENT)",
    )
    status: WorkItemStatus = Field(
        default=WorkItemStatus.QUEUED,
        description="Current status of the work item",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible dictionary for provider-specific data (e.g., GitHub node_id)",
        examples=[
            {"issue_node_id": "I_kwDOABC123", "labels": ["bug", "priority-high"]}
        ],
    )

    model_config = {
        "frozen": False,
        "extra": "forbid",
        "use_enum_values": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "42",
                    "source_url": "https://github.com/owner/repo/issues/42",
                    "context_body": "Implement user authentication with OAuth2",
                    "target_repo_slug": "owner/repo",
                    "task_type": "IMPLEMENT",
                    "status": "QUEUED",
                    "metadata": {"issue_node_id": "I_kwDOABC123"},
                }
            ]
        },
    }

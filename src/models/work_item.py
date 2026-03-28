"""Unified data models for workflow-orchestration-queue."""

from enum import Enum
from typing import Any, Dict, Optional
import re

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Type of work item."""

    PLAN = "plan"
    IMPLEMENT = "implement"


class WorkItemStatus(str, Enum):
    """Status of a work item, maps to GitHub labels."""

    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"


class WorkItem(BaseModel):
    """Unified work item representation used by both Sentinel and Notifier."""

    id: str = Field(..., description="Unique identifier for the work item")
    issue_number: int = Field(..., description="GitHub issue number")
    source_url: str = Field(..., description="URL to the source issue")
    context_body: str = Field(..., description="Body/context of the work item")
    target_repo_slug: str = Field(..., description="Target repository (owner/repo)")
    task_type: TaskType = Field(..., description="Type of task")
    status: WorkItemStatus = Field(..., description="Current status")
    node_id: Optional[str] = Field(None, description="GitHub node ID for GraphQL operations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


SECRET_PATTERNS = [
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
    (r"ghs_[a-zA-Z0-9]{36}", "GitHub Server Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"github_pat_[a-zA-Z0-9]{22,}", "GitHub Fine-grained PAT"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer Token"),
]


def scrub_secrets(text: str) -> str:
    """
    Remove sensitive credential patterns from text.

    Args:
        text: The text to scrub

    Returns:
        Text with secrets replaced by [REDACTED]
    """
    for pattern, _ in SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text

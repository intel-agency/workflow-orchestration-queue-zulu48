"""Pydantic models for parsing GitHub webhook payloads."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user."""

    login: str
    id: int
    node_id: Optional[str] = None
    avatar_url: Optional[str] = None


class GitHubRepository(BaseModel):
    """GitHub repository."""

    id: int
    name: str
    full_name: str
    owner: GitHubUser
    html_url: str


class GitHubLabel(BaseModel):
    """GitHub label."""

    id: int
    name: str
    color: str
    description: Optional[str] = None


class GitHubIssue(BaseModel):
    """GitHub issue."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    user: GitHubUser
    labels: List[GitHubLabel] = Field(default_factory=list)
    repository: Optional[GitHubRepository] = None
    node_id: Optional[str] = None


class GitHubComment(BaseModel):
    """GitHub issue/PR comment."""

    id: int
    body: Optional[str] = None
    user: GitHubUser
    html_url: str


class GitHubPullRequest(BaseModel):
    """GitHub pull request."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    user: GitHubUser
    head_ref: Optional[str] = None
    base_ref: Optional[str] = None
    node_id: Optional[str] = None


class GitHubWebhookPayload(BaseModel):
    """Base GitHub webhook payload."""

    action: Optional[str] = None
    repository: Optional[GitHubRepository] = None
    sender: Optional[GitHubUser] = None


class IssueWebhookPayload(GitHubWebhookPayload):
    """GitHub issues webhook payload."""

    issue: Optional[GitHubIssue] = None


class IssueCommentWebhookPayload(GitHubWebhookPayload):
    """GitHub issue_comment webhook payload."""

    issue: Optional[GitHubIssue] = None
    comment: Optional[GitHubComment] = None


class PullRequestWebhookPayload(GitHubWebhookPayload):
    """GitHub pull_request webhook payload."""

    pull_request: Optional[GitHubPullRequest] = None

"""Notifier Service - FastAPI webhook receiver for GitHub events."""

import hashlib
import hmac
import logging
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel

from src.models.github_events import IssueWebhookPayload
from src.queue.github_queue import GitHubQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

app = FastAPI(
    title="workflow-orchestration-queue Notifier",
    description="Webhook receiver for GitHub events",
    version="0.1.0",
)


def validate_environment():
    """Validate required environment variables at startup."""
    required = ["WEBHOOK_SECRET", "GITHUB_TOKEN", "GITHUB_REPO"]
    missing = [v for v in required if not os.getenv(v)]

    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)

    placeholder_patterns = ["YOUR_", "CHANGE_ME", "placeholder", "your_webhook_secret"]
    for var in required:
        value = os.getenv(var, "")
        for pattern in placeholder_patterns:
            if pattern.lower() in value.lower():
                logger.error(f"Environment variable {var} appears to be a placeholder")
                sys.exit(1)

    logger.info("Environment validation passed")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header.

    Args:
        payload: Raw request body bytes
        signature: Value of X-Hub-Signature-256 header
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not signature.startswith("sha256="):
        return False

    expected = signature[7:]
    computed = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, computed)


@app.on_event("startup")
async def startup_event():
    """Validate environment on startup."""
    validate_environment()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "notifier"}


@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """
    Handle GitHub webhook events.

    Validates HMAC signature, parses the event, and queues work items.
    """
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(payload_bytes, signature, WEBHOOK_SECRET):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()
    action = payload.get("action", "")

    logger.info(f"Received {event_type}.{action} event")

    if event_type == "issues" and action == "opened":
        return await handle_issue_opened(payload)

    return {"status": "acknowledged", "event": event_type, "action": action}


async def handle_issue_opened(payload: dict) -> dict:
    """
    Handle newly opened issues.

    Applies agent:queued label if the issue matches patterns.
    """
    issue = payload.get("issue", {})
    title = issue.get("title", "")
    body = issue.get("body", "") or ""

    should_queue = False

    plan_patterns = ["[Application Plan]", "[Plan]", "[Epic]"]
    for pattern in plan_patterns:
        if pattern in title:
            should_queue = True
            break

    if not should_queue:
        bug_patterns = ["[Bug]", "[Bugfix]", "bug:", "fix:"]
        for pattern in bug_patterns:
            if pattern.lower() in title.lower():
                should_queue = True
                break

    if should_queue:
        queue = GitHubQueue(token=GITHUB_TOKEN, repo=GITHUB_REPO)
        try:
            issue_number = issue.get("number")

            add_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/labels"
            await queue._get_client().post(add_url, json={"labels": ["agent:queued"]})

            logger.info(f"Queued issue #{issue_number}: {title}")

            return {"status": "queued", "issue_number": issue_number}
        finally:
            await queue.close()

    return {"status": "ignored", "reason": "No matching pattern"}


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "workflow-orchestration-queue Notifier",
        "version": "0.1.0",
        "docs": "/docs",
    }


def main():
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

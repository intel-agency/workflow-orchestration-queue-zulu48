"""Orchestrator Sentinel - Background polling and task execution service."""

import asyncio
import logging
import os
import random
import signal
import subprocess
import sys
from datetime import datetime
from typing import Optional

from src.models.work_item import WorkItem, WorkItemStatus
from src.queue.github_queue import GitHubQueue, POLL_INTERVAL, MAX_BACKOFF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
HEARTBEAT_INTERVAL = int(os.getenv("SENTINEL_HEARTBEAT_INTERVAL", "300"))
SUBPROCESS_TIMEOUT = int(os.getenv("SENTINEL_SUBPROCESS_TIMEOUT", "5700"))
DEVCONTAINER_SCRIPT = os.getenv("DEVCONTAINER_SCRIPT", "./scripts/devcontainer-opencode.sh")

_shutdown_requested = False
_sentinel_id = os.getenv("SENTINEL_ID", f"sentinel-{os.getpid()}")


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, requesting graceful shutdown...")
    _shutdown_requested = True


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def validate_environment():
    """Validate required environment variables."""
    required = ["GITHUB_TOKEN", "GITHUB_REPO"]
    missing = [v for v in required if not os.getenv(v)]

    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)

    placeholder_patterns = ["YOUR_", "CHANGE_ME", "placeholder"]
    for var in required:
        value = os.getenv(var, "")
        for pattern in placeholder_patterns:
            if pattern in value:
                logger.error(f"Environment variable {var} appears to be a placeholder")
                sys.exit(1)

    logger.info("Environment validation passed")


async def run_shell_command(
    command: str, timeout: int = SUBPROCESS_TIMEOUT
) -> tuple[int, str, str]:
    """
    Run a shell command with timeout.

    Args:
        command: The command to run
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    logger.info(f"Running command: {command}")

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        process.kill()
        logger.error(f"Command timed out after {timeout}s: {command}")
        return (-1, "", f"Command timed out after {timeout}s")


async def heartbeat_loop(queue: GitHubQueue, item: WorkItem, start_time: datetime):
    """
    Post heartbeat comments at regular intervals.

    Args:
        queue: The GitHub queue instance
        item: The work item being processed
        start_time: When processing started
    """
    while not _shutdown_requested:
        await asyncio.sleep(HEARTBEAT_INTERVAL)

        elapsed = (datetime.now() - start_time).total_seconds()
        minutes = int(elapsed // 60)

        body = f"**[Heartbeat]** {_sentinel_id} still working... ({minutes} minutes elapsed)"
        await queue.add_comment(item, body)
        logger.info(f"Posted heartbeat for task {item.issue_number}")


async def process_task(queue: GitHubQueue, item: WorkItem) -> bool:
    """
    Process a single work item.

    Args:
        queue: The GitHub queue instance
        item: The work item to process

    Returns:
        True if processing succeeded
    """
    start_time = datetime.now()
    heartbeat_task = asyncio.create_task(heartbeat_loop(queue, item, start_time))

    try:
        await queue.update_status(item, WorkItemStatus.IN_PROGRESS)
        await queue.add_comment(item, f"**{_sentinel_id}** is starting work on this task.")

        up_cmd = f"{DEVCONTAINER_SCRIPT} up"
        exit_code, stdout, stderr = await run_shell_command(up_cmd, timeout=300)

        if exit_code != 0:
            logger.error(f"Failed to bring up environment: {stderr}")
            await queue.update_status(item, WorkItemStatus.INFRA_FAILURE)
            await queue.add_comment(
                item,
                f"**Infrastructure Error**\n\n```\n{stderr[-2000:]}\n```",
            )
            return False

        prompt = item.context_body
        prompt_cmd = f'{DEVCONTAINER_SCRIPT} prompt "{prompt}"'
        exit_code, stdout, stderr = await run_shell_command(prompt_cmd)

        if exit_code != 0:
            logger.error(f"Prompt execution failed: {stderr}")
            await queue.update_status(item, WorkItemStatus.ERROR)
            await queue.add_comment(
                item,
                f"**Execution Error**\n\n```\n{stderr[-2000:]}\n```",
            )
            return False

        await queue.update_status(item, WorkItemStatus.SUCCESS)
        await queue.add_comment(item, f"**{_sentinel_id}** completed work successfully.")

        stop_cmd = f"{DEVCONTAINER_SCRIPT} stop"
        await run_shell_command(stop_cmd, timeout=60)

        return True

    except Exception as e:
        logger.exception(f"Error processing task {item.issue_number}")
        await queue.update_status(item, WorkItemStatus.ERROR)
        await queue.add_comment(item, f"**Error**: {str(e)}")
        return False

    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


async def run_forever(queue: GitHubQueue):
    """
    Main polling loop.

    Args:
        queue: The GitHub queue instance
    """
    global _shutdown_requested
    current_backoff = POLL_INTERVAL

    while not _shutdown_requested:
        try:
            logger.info("Polling for queued tasks...")
            items = await queue.fetch_queued_items()

            if items:
                logger.info(f"Found {len(items)} queued task(s)")
                current_backoff = POLL_INTERVAL

                for item in items:
                    if _shutdown_requested:
                        break

                    if await queue.claim_task(item):
                        await process_task(queue, item)
            else:
                logger.debug("No queued tasks found")

            await asyncio.sleep(current_backoff)

        except Exception as e:
            logger.exception("Error in polling loop")

            jitter = random.uniform(0, 0.1 * current_backoff)
            wait_time = min(current_backoff + jitter, MAX_BACKOFF)
            logger.warning(f"Backing off for {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            current_backoff = min(current_backoff * 2, MAX_BACKOFF)


async def main():
    """Main entry point."""
    import random  # noqa: F401 - used by run_forever

    validate_environment()

    queue = GitHubQueue(token=GITHUB_TOKEN, repo=GITHUB_REPO)

    logger.info(f"Starting Sentinel {_sentinel_id}")
    logger.info(f"Monitoring repository: {GITHUB_REPO}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")

    try:
        await run_forever(queue)
    finally:
        await queue.close()
        logger.info("Sentinel shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())

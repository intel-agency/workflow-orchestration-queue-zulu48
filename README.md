# workflow-orchestration-queue (OS-APOW)

A headless agentic orchestration platform that transforms GitHub Issues into autonomous execution orders.

## Overview

workflow-orchestration-queue enables AI-driven development without human-in-the-loop intervention. The system uses a 4-pillar architecture:

- **The Ear (Notifier)** - FastAPI webhook receiver for GitHub events
- **The State (Queue)** - GitHub Issues as distributed state (Markdown-as-a-Database)
- **The Brain (Sentinel)** - Background polling service with shell-bridge execution
- **The Hands (Worker)** - Isolated DevContainer for AI agent execution

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- GitHub CLI (`gh`) authenticated
- GitHub App or PAT with appropriate scopes

### Installation

```bash
# Install dependencies with uv
uv sync --dev

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### Running

```bash
# Start the notifier service
uv run uvicorn src.notifier_service:app --reload

# Start the sentinel (in another terminal)
uv run python -m src.orchestrator_sentinel
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

## Project Structure

```
workflow-orchestration-queue/
├── src/
│   ├── notifier_service.py     # FastAPI webhook receiver
│   ├── orchestrator_sentinel.py # Background polling service
│   ├── models/
│   │   ├── work_item.py        # Unified data model
│   │   └── github_events.py    # Webhook payload schemas
│   └── queue/
│       └── github_queue.py     # GitHub Issues queue
├── tests/                      # Test suite
├── scripts/                    # Shell bridge scripts
├── plan_docs/                  # Planning documents
└── .github/workflows/          # CI/CD pipelines
```

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API token |
| `GITHUB_REPO` | Target repository (owner/repo) |
| `WEBHOOK_SECRET` | HMAC secret for webhook validation |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTINEL_BOT_LOGIN` | - | Bot account login for task claiming |
| `SENTINEL_POLL_INTERVAL` | 60 | Polling interval in seconds |
| `SENTINEL_HEARTBEAT_INTERVAL` | 300 | Heartbeat comment interval |
| `SENTINEL_SUBPROCESS_TIMEOUT` | 5700 | Max task execution time |

## Development

### Testing

```bash
# Run all tests
uv run pytest tests -v

# Run with coverage
uv run pytest tests -v --cov=src --cov-report=term-missing
```

### Linting

```bash
# Run ruff linter
uv run ruff check src tests

# Format code
uv run ruff format src tests
```

### Type Checking

```bash
uv run mypy src
```

## Documentation

- [Architecture Guide](plan_docs/architecture.md)
- [Tech Stack](plan_docs/tech-stack.md)
- [Development Plan](plan_docs/OS-APOW%20Development%20Plan%20v4.2.md)
- [Implementation Spec](plan_docs/OS-APOW%20Implementation%20Specification%20v1.2.md)

## License

MIT License - see [LICENSE](LICENSE) for details.

# Tech Stack: workflow-orchestration-queue (OS-APOW)

## Runtime & Language

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Primary language for orchestrator, API, and system logic |
| PowerShell Core (pwsh) | 7.x | Shell bridge scripts, auth synchronization |
| Bash | 5.x | DevContainer lifecycle scripts |

## Web Framework

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | latest | High-performance async web framework for webhook receiver |
| Uvicorn | latest | ASGI server for production deployment |
| Pydantic | latest | Data validation and settings management |

## HTTP & Networking

| Component | Version | Purpose |
|-----------|---------|---------|
| HTTPX | latest | Async HTTP client for GitHub API calls |
| hmac (stdlib) | - | Webhook signature verification |

## Package Management

| Component | Version | Purpose |
|-----------|---------|---------|
| uv | 0.10.9+ | Rust-based Python package manager |
| pip (fallback) | - | Legacy package installer |

## Containerization

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.x | Multi-container orchestration |
| DevContainers | - | Reproducible development environment |

## Agent Runtime

| Component | Version | Purpose |
|-----------|---------|---------|
| opencode CLI | 1.2.24+ | AI agent runtime |
| GLM-5 (zai-coding-plan/glm-5) | - | Primary LLM model |

## MCP Servers

| Component | Purpose |
|-----------|---------|
| @modelcontextprotocol/server-sequential-thinking | Structured reasoning |
| @modelcontextprotocol/server-memory | Knowledge graph persistence |

## Development Tools

| Component | Purpose |
|-----------|---------|
| ruff | Python linter/formatter |
| pytest | Testing framework |
| mypy | Static type checking |

## Version Control

| Component | Purpose |
|-----------|---------|
| Git | Version control |
| GitHub CLI (gh) | Repository operations |
| GitHub Actions | CI/CD pipelines |

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| GITHUB_TOKEN | Yes | GitHub API authentication |
| GH_ORCHESTRATION_AGENT_TOKEN | Yes | Org-level PAT for orchestrator |
| ZHIPU_API_KEY | Yes | ZhipuAI model access |
| WEBHOOK_SECRET | Yes | HMAC signature verification |
| GITHUB_REPO | Yes | Target repository (owner/repo) |
| SENTINEL_BOT_LOGIN | Yes | Bot account login for task claiming |

## Notes

- All dependencies managed via `pyproject.toml` with `uv.lock` for reproducibility
- No .NET required (despite DevContainer including .NET SDK for template compatibility)
- Connection pooling via single `httpx.AsyncClient` instance

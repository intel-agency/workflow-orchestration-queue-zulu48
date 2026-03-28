# Architecture: workflow-orchestration-queue (OS-APOW)

## System Overview

workflow-orchestration-queue is a headless agentic orchestration platform that transforms GitHub Issues into autonomous execution orders. The system operates without human-in-the-loop intervention, using a 4-pillar architecture.

## 4-Pillar Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub (External)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Issues    │  │   Labels    │  │  Projects   │  │  Webhooks   │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
└─────────┼────────────────┼────────────────┼────────────────┼───────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE EAR (Notifier)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Webhook Receiver                                        │   │
│  │  - HMAC SHA256 signature validation                              │   │
│  │  - Event triaging and WorkItem manifest generation               │   │
│  │  - Queue initialization (apply agent:queued label)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE STATE (Queue)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  GitHub Issues as Database (Markdown-as-a-Database)              │   │
│  │  - agent:queued → agent:in-progress → agent:success/error        │   │
│  │  - Assignees as distributed lock                                 │   │
│  │  - Comments for heartbeat and error reporting                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE BRAIN (Sentinel)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  orchestrator_sentinel.py                                        │   │
│  │  - Polling loop (60s interval, jittered backoff)                 │   │
│  │  - Assign-then-verify task claiming                              │   │
│  │  - Shell-bridge execution via devcontainer-opencode.sh           │   │
│  │  - Heartbeat coroutine (5 min intervals)                         │   │
│  │  - Graceful shutdown (SIGTERM/SIGINT)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        THE HANDS (Worker)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DevContainer + opencode CLI                                     │   │
│  │  - Isolated Docker environment                                   │   │
│  │  - Resource constraints (2 CPUs, 4GB RAM)                        │   │
│  │  - Ephemeral credentials                                         │   │
│  │  - LLM-driven code generation                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. The Ear (Work Event Notifier)

**File:** `src/notifier_service.py`

**Responsibilities:**
- Secure webhook ingestion at `/webhooks/github`
- HMAC SHA256 signature validation
- Event parsing and triaging
- WorkItem manifest generation
- Queue initialization (apply `agent:queued` label)

**Key Interfaces:**
- `POST /webhooks/github` - GitHub webhook endpoint
- `GET /health` - Health check endpoint
- `GET /docs` - Swagger/OpenAPI documentation

### 2. The State (Work Queue)

**Implementation:** GitHub Issues + Labels

**State Machine:**
```
agent:queued → agent:in-progress → agent:success
                    │
                    └──→ agent:error
                    └──→ agent:infra-failure
                    └──→ agent:stalled-budget
```

**Concurrency Control:**
- Assign-then-verify pattern using GitHub Assignees
- `SENTINEL_BOT_LOGIN` identifies the bot account

### 3. The Brain (Sentinel Orchestrator)

**File:** `src/orchestrator_sentinel.py`

**Responsibilities:**
- Polling loop with jittered exponential backoff
- Task claiming via assign-then-verify
- Shell-bridge execution via `devcontainer-opencode.sh`
- Heartbeat posting (every 5 minutes)
- Credential scrubbing before public output
- Graceful shutdown handling

**Key Functions:**
- `run_forever()` - Main polling loop
- `claim_task()` - Assign-then-verify locking
- `process_task()` - Shell-bridge execution
- `_heartbeat_loop()` - Background heartbeat coroutine

### 4. The Hands (Opencode Worker)

**Environment:** DevContainer

**Responsibilities:**
- Execute agent instructions from `local_ai_instruction_modules/`
- Generate and modify code
- Run tests and validation
- Create pull requests

## Data Model

### WorkItem (src/models/work_item.py)

```python
class TaskType(Enum):
    PLAN = "plan"
    IMPLEMENT = "implement"

class WorkItemStatus(Enum):
    QUEUED = "agent:queued"
    IN_PROGRESS = "agent:in-progress"
    SUCCESS = "agent:success"
    ERROR = "agent:error"
    INFRA_FAILURE = "agent:infra-failure"
    STALLED_BUDGET = "agent:stalled-budget"

class WorkItem(BaseModel):
    id: str
    issue_number: int
    source_url: str
    context_body: str
    target_repo_slug: str
    task_type: TaskType
    status: WorkItemStatus
    node_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

### Credential Scrubbing

```python
def scrub_secrets(text: str) -> str:
    """Remove sensitive patterns from text."""
    patterns = [
        r'ghp_[a-zA-Z0-9]{36}',      # GitHub PAT
        r'ghs_[a-zA-Z0-9]{36}',      # GitHub Server Token
        r'gho_[a-zA-Z0-9]{36}',      # GitHub OAuth Token
        r'github_pat_[a-zA-Z0-9]{22}', # GitHub Fine-grained PAT
        r'sk-[a-zA-Z0-9]{20,}',      # OpenAI API Key
        r'Bearer\s+[a-zA-Z0-9\-._~+/]+=*', # Bearer tokens
    ]
    for pattern in patterns:
        text = re.sub(pattern, '[REDACTED]', text)
    return text
```

## Security Architecture

### Network Isolation
- Worker containers in dedicated Docker network
- No access to host network or metadata endpoints

### Credential Management
- Ephemeral credentials (environment variables only)
- Never written to disk in container
- Credential scrubbing for all public output

### Webhook Security
- HMAC SHA256 signature validation
- Reject requests with invalid/missing signatures (401)

## Architecture Decision Records (ADRs)

### ADR-07: Shell-Bridge Execution
**Decision:** Orchestrator interacts with worker exclusively via `devcontainer-opencode.sh`
**Rationale:** Ensures environment parity with human developers
**Consequence:** Python code remains lightweight; shell scripts handle container complexity

### ADR-08: Polling-First Resiliency
**Decision:** Polling as primary discovery; webhooks as optimization
**Rationale:** Self-healing on restart; no lost events during downtime
**Consequence:** Higher latency (60s poll interval) but guaranteed delivery

### ADR-09: Provider-Agnostic Interface
**Decision:** ITaskQueue abstraction for queue operations
**Rationale:** Enable future provider swapping (Linear, Notion, etc.)
**Consequence:** Slight abstraction overhead; future flexibility

## File Structure

```
workflow-orchestration-queue/
├── pyproject.toml
├── uv.lock
├── src/
│   ├── __init__.py
│   ├── notifier_service.py
│   ├── orchestrator_sentinel.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── work_item.py
│   │   └── github_events.py
│   └── queue/
│       ├── __init__.py
│       └── github_queue.py
├── tests/
│   ├── __init__.py
│   ├── test_sentinel.py
│   ├── test_notifier.py
│   └── test_models.py
├── scripts/
│   ├── devcontainer-opencode.sh
│   ├── gh-auth.ps1
│   └── update-remote-indices.ps1
└── local_ai_instruction_modules/
    └── *.md
```

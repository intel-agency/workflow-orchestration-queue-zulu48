# Workflow Execution Plan: project-setup

**Generated:** 2026-03-28
**Workflow:** project-setup
**Repository:** intel-agency/workflow-orchestration-queue-zulu48

---

## 1. Overview

This workflow execution plan covers the `project-setup` dynamic workflow for the **workflow-orchestration-queue (OS-APOW)** project.

**Project Description:**
workflow-orchestration-queue is a headless agentic orchestration platform that transforms GitHub Issues into autonomous execution orders. The system uses a 4-pillar architecture (Ear/State/Brain/Hands) to enable AI-driven development without human-in-the-loop intervention.

**Workflow Purpose:**
Initialize the repository from its seeded template state into a fully configured project ready for Phase 1 implementation.

**Total Assignments:** 6 main + 1 pre-script + 2 post-assignment events (repeated)

---

## 2. Project Context Summary

### Key Facts

| Aspect | Details |
|--------|---------|
| **Project Name** | workflow-orchestration-queue (OS-APOW) |
| **Repository** | intel-agency/workflow-orchestration-queue-zulu48 |
| **Type** | Template-based AI orchestration system |
| **Primary Language** | Python 3.12+ |
| **Frameworks** | FastAPI, Pydantic, HTTPX, uv |
| **Containerization** | Docker, DevContainers |
| **State Model** | GitHub Issues as database (Markdown-as-a-Database) |
| **Architecture** | 4 pillars: Ear (Notifier), State (Queue), Brain (Sentinel), Hands (Worker) |

### Technology Stack

- **Runtime:** Python 3.12+
- **Web Framework:** FastAPI + Uvicorn
- **Validation:** Pydantic
- **HTTP Client:** HTTPX (async)
- **Package Manager:** uv (Rust-based)
- **Containerization:** Docker, Docker Compose, DevContainers
- **Agent Runtime:** opencode CLI with GLM-5 model

### Special Constraints

1. **Action SHA Pinning:** All GitHub Actions MUST be pinned to specific commit SHAs
2. **Validation Required:** Run `./scripts/validate.ps1 -All` before any commit/push
3. **Template Placeholders:** Repository was seeded from template; all placeholders already replaced
4. **Self-Bootstrapping:** System designed to build itself after Phase 0 seeding

### Known Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| GitHub API Rate Limiting | High | Use GitHub App tokens (5,000 req/hr); implement backoff |
| LLM Hallucination/Looping | High | Max steps timeout; cost guardrails |
| Concurrency Collisions | Medium | Assign-then-verify pattern for task claiming |
| CI Check Failures | Medium | 3-attempt remediation loop before escalation |

---

## 3. Assignment Execution Plan

### Pre-Script Event

| Field | Content |
|-------|---------|
| **Assignment** | `create-workflow-plan`: Create Workflow Execution Plan |
| **Goal** | Produce a project-specific workflow execution plan before other assignments begin |
| **Key Acceptance Criteria** | - Dynamic workflow fully read and traced<br>- All plan_docs/ read and summarized<br>- Workflow execution plan committed to plan_docs/workflow-plan.md<br>- Stakeholder approval obtained |
| **Project-Specific Notes** | This assignment. Plan docs include detailed architecture, development plan, implementation spec, plan review, and simplification report. |
| **Prerequisites** | None (first step) |
| **Dependencies** | None |
| **Risks / Challenges** | None - planning only |
| **Events** | None |

---

### Assignment 1: init-existing-repository

| Field | Content |
|-------|---------|
| **Assignment** | `init-existing-repository`: Initiate Existing Repository |
| **Goal** | Set up the repository with labels, project board, branch protection, and initial PR |
| **Key Acceptance Criteria** | - New branch `dynamic-workflow-project-setup` created<br>- Branch protection ruleset imported<br>- GitHub Project created with columns<br>- Labels imported from .github/.labels.json<br>- Workspace/devcontainer files renamed<br>- PR created from branch to main |
| **Project-Specific Notes** | Repository already seeded from template. Branch protection ruleset at `.github/protected-branches_ruleset.json`. Labels at `.github/.labels.json`. |
| **Prerequisites** | GitHub auth with `repo`, `project`, `read:project`, `read:user`, `user:email`, `administration:write` scopes |
| **Dependencies** | None (first main assignment) |
| **Risks / Challenges** | - Ruleset import requires `administration:write` scope<br>- PR creation requires at least one commit<br>- Project creation may require org permissions |
| **Events** | **Post:** validate-assignment-completion, report-progress |

**Output Variables:**
- `$pr_num`: PR number for use in pr-approval-and-merge

---

### Assignment 2: create-app-plan

| Field | Content |
|-------|---------|
| **Assignment** | `create-app-plan`: Create Application Plan |
| **Goal** | Create comprehensive application plan documented as a GitHub issue |
| **Key Acceptance Criteria** | - Application template analyzed<br>- Plan documented in GitHub issue using template<br>- Milestones created and linked<br>- Issue added to GitHub Project<br>- Labels applied (planning, documentation) |
| **Project-Specific Notes** | Plan docs already exist: Development Plan v4.2, Architecture Guide v3.2, Implementation Spec v1.2, Plan Review, Simplification Report. These should be synthesized into the application plan issue. |
| **Prerequisites** | init-existing-repository completed (labels, project board exist) |
| **Dependencies** | Labels from Assignment 1 |
| **Risks / Challenges** | - Extensive plan docs require synthesis<br>- Must not implement code - planning only |
| **Events** | **Pre:** gather-context<br>**Post:** validate-assignment-completion, report-progress<br>**On Failure:** recover-from-error |

**Output Variables:**
- `$plan_issue_num`: Issue number for the application plan (used in post-script)

---

### Assignment 3: create-project-structure

| Field | Content |
|-------|---------|
| **Assignment** | `create-project-structure`: Create Project Structure |
| **Goal** | Create actual project scaffolding: solution structure, Docker, CI/CD, docs |
| **Key Acceptance Criteria** | - Solution/project structure created<br>- Dockerfile and docker-compose.yml created<br>- CI/CD pipeline structure established<br>- Documentation structure created<br>- Repository summary document created<br>- All GitHub Actions SHA-pinned |
| **Project-Specific Notes** | Python project using uv. Structure should follow Implementation Spec §Project Structure. Key files: pyproject.toml, src/notifier_service.py, src/orchestrator_sentinel.py, src/models/, src/queue/. |
| **Prerequisites** | create-app-plan completed (plan exists to guide structure) |
| **Dependencies** | Application plan issue |
| **Risks / Challenges** | - Must use `COPY src/` before `uv pip install -e .` in Dockerfile<br>- Healthcheck must use Python stdlib (no curl)<br>- All actions must be SHA-pinned |
| **Events** | **Post:** validate-assignment-completion, report-progress |

---

### Assignment 4: create-agents-md-file

| Field | Content |
|-------|---------|
| **Assignment** | `create-agents-md-file`: Create AGENTS.md File |
| **Goal** | Create AGENTS.md at repository root for AI coding agent context |
| **Key Acceptance Criteria** | - AGENTS.md exists at repository root<br>- Contains project overview, setup commands, structure, code style<br>- All listed commands validated by running them<br>- File committed and pushed |
| **Project-Specific Notes** | Complements existing AGENTS.md from template. Must be updated for OS-APOW specifics: uv commands, FastAPI, Docker, Sentinel/Notifier architecture. |
| **Prerequisites** | create-project-structure completed (commands exist to validate) |
| **Dependencies** | Project structure with working commands |
| **Risks / Challenges** | Commands must be validated - may reveal issues in project structure |
| **Events** | **Post:** validate-assignment-completion, report-progress |

---

### Assignment 5: debrief-and-document

| Field | Content |
|-------|---------|
| **Assignment** | `debrief-and-document`: Debrief and Document Learnings |
| **Goal** | Create comprehensive debriefing report capturing learnings and improvements |
| **Key Acceptance Criteria** | - Detailed report created following template<br>- All deviations from assignments documented<br>- Report reviewed and approved<br>- Execution trace saved to debrief-and-document/trace.md |
| **Project-Specific Notes** | Should capture: validation script issues, CI check results, any deviations from plan docs, plan-impacting findings for subsequent phases. |
| **Prerequisites** | All prior assignments completed |
| **Dependencies** | All prior assignment outputs |
| **Risks / Challenges** | Must capture ALL deviations - no silent skipping |
| **Events** | **Post:** validate-assignment-completion, report-progress |

---

### Assignment 6: pr-approval-and-merge

| Field | Content |
|-------|---------|
| **Assignment** | `pr-approval-and-merge`: Pull Request Approval and Merge |
| **Goal** | Complete PR approval, resolve all comments, merge, and clean up |
| **Key Acceptance Criteria** | - All CI checks pass (with up to 3 remediation attempts)<br>- Code review delegated to code-reviewer (not self-review)<br>- All review comments resolved via GraphQL<br>- Stakeholder approval obtained<br>- PR merged<br>- Source branch deleted<br>- Related issues closed |
| **Project-Specific Notes** | Receives `$pr_num` from init-existing-repository. This is automated setup PR - self-approval acceptable per workflow spec. |
| **Prerequisites** | All prior assignments completed, `$pr_num` available |
| **Dependencies** | `$pr_num` from Assignment 1 |
| **Risks / Challenges** | - CI failures may require multiple fix cycles<br>- Must follow ai-pr-comment-protocol.md exactly<br>- Must commit all changes before merge |
| **Events** | **Post:** validate-assignment-completion, report-progress |

**Input Variables:**
- `$pr_num`: From init-existing-repository

**Output Variables:**
- `result`: "merged" | "pending" | "failed"

---

## 4. Sequencing Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROJECT-SETUP WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

[PRE-SCRIPT]
    │
    ▼
┌─────────────────────┐
│ create-workflow-plan │ ─────► plan_docs/workflow-plan.md
└─────────────────────┘
    │
    ▼
[MAIN ASSIGNMENTS]
    │
    ├─► ┌──────────────────────────┐
    │   │ init-existing-repository  │ ─────► Branch, Labels, Project, PR
    │   └──────────────────────────┘
    │            │
    │            ▼
    │   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   │ validate-assignment     │ ─►│ report-progress         │
    │   └─────────────────────────┘   └─────────────────────────┘
    │            │
    ├─► ┌──────────────────────────┐
    │   │ create-app-plan          │ ─────► Plan Issue, Milestones
    │   └──────────────────────────┘
    │            │
    │            ▼
    │   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   │ validate-assignment     │ ─►│ report-progress         │
    │   └─────────────────────────┘   └─────────────────────────┘
    │            │
    ├─► ┌──────────────────────────┐
    │   │ create-project-structure │ ─────► Source, Docker, CI/CD
    │   └──────────────────────────┘
    │            │
    │            ▼
    │   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   │ validate-assignment     │ ─►│ report-progress         │
    │   └─────────────────────────┘   └─────────────────────────┘
    │            │
    ├─► ┌──────────────────────────┐
    │   │ create-agents-md-file    │ ─────► AGENTS.md
    │   └──────────────────────────┘
    │            │
    │            ▼
    │   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   │ validate-assignment     │ ─►│ report-progress         │
    │   └─────────────────────────┘   └─────────────────────────┘
    │            │
    ├─► ┌──────────────────────────┐
    │   │ debrief-and-document     │ ─────► Debrief Report, Trace
    │   └──────────────────────────┘
    │            │
    │            ▼
    │   ┌─────────────────────────┐   ┌─────────────────────────┐
    │   │ validate-assignment     │ ─►│ report-progress         │
    │   └─────────────────────────┘   └─────────────────────────┘
    │            │
    └─► ┌──────────────────────────┐
        │ pr-approval-and-merge    │ ─────► Merged PR, Closed Issues
        └──────────────────────────┘
                    │
                    ▼
        ┌─────────────────────────┐   ┌─────────────────────────┐
        │ validate-assignment     │ ─►│ report-progress         │
        └─────────────────────────┘   └─────────────────────────┘
                    │
                    ▼
[POST-SCRIPT]
    │
    ▼
┌───────────────────────────────────┐
│ Apply orchestration:plan-approved │ ─────► Plan Issue Labeled
│ to application plan issue         │
└───────────────────────────────────┘
```

---

## 5. Variable Flow

| Variable | Produced By | Consumed By |
|----------|-------------|-------------|
| `$pr_num` | init-existing-repository | pr-approval-and-merge |
| `$plan_issue_num` | create-app-plan | post-script (label application) |

---

## 6. Open Questions

1. **GitHub App Token Scope:** Does the current `GH_ORCHESTRATION_AGENT_TOKEN` have `administration:write` scope for branch protection ruleset import? If not, the ruleset import step will fail.

2. **Project Board Permissions:** Does the authenticated account have permission to create organization-level projects, or should this be a user-level project?

3. **Plan Issue Number Tracking:** The post-script requires locating the application plan issue. Should this be captured as `$plan_issue_num` during create-app-plan, or should post-script search for it by label?

---

## 7. Critical Rules Reminder

1. **Action SHA Pinning:** All GitHub Actions workflows MUST pin actions to specific commit SHAs (e.g., `uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1`)

2. **Validation Before Commit:** Run `./scripts/validate.ps1 -All` before any commit/push. Fix all failures before proceeding.

3. **No Self-Review for Code:** pr-approval-and-merge must delegate code review to `code-reviewer` subagent (though self-approval is acceptable for this automated setup PR per workflow spec).

4. **Commit Before Merge:** All changes must be committed and pushed to the PR branch before merge attempt.

---

## 8. Approval

**Plan Status:** ⏳ Pending Approval

**Stakeholder Approval Required:** Yes - this plan must be approved before proceeding with main assignments.

---

*Plan prepared by Orchestrator Agent*
*Date: 2026-03-28*

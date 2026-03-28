---
file: AGENTS.md
description: Project instructions for coding agents
scope: repository
---

<instructions>
  <purpose>
    <summary>
      GitHub Actions-based AI orchestration system. On GitHub events (issues, PR comments, reviews),
      the `orchestrator-agent` workflow assembles a structured prompt, spins up a devcontainer,
      and runs `opencode --agent Orchestrator` to delegate work to specialist sub-agents in `.opencode/agents/`.
    </summary>
  </purpose>

  <template_usage>
    <summary>
      This repository is a **GitHub template repo** (`intel-agency/workflow-orchestration-queue-zulu48`).
      New project repositories are created from it using automation scripts in the
      `nam20485/workflow-launch2` repo. The scripts clone this template, seed plan docs,
      replace template placeholders, and push — producing a ready-to-go AI-orchestrated repo.
    </summary>

    <template-clone-instances>
      Once the template has been cloned into a new instance, this file must be updated to match the new repo's specifics (e.g., name, links, instructions). 
    </template-clone-instances>

    <creation_workflow>
      <step>1. Run `./scripts/create-repo-from-slug.ps1 -Slug &lt;project-slug&gt; -Yes` from the `workflow-launch2` repo.</step>
      <step>2. That delegates to `./scripts/create-repo-with-plan-docs.ps1` which:
        - Creates a new GitHub repo from this template via `gh repo create --template intel-agency/workflow-orchestration-queue-zulu48`
        - Generates a random suffix for the repo name (e.g., `project-slug-bravo84`)
        - Creates repo secrets (`GEMINI_API_KEY`) and variables (`VERSION_PREFIX`)
        - Clones the new repo locally
        - Copies plan docs from `./plan_docs/&lt;slug&gt;/` into the clone's `plan_docs/` directory
        - Replaces all template placeholders (`workflow-orchestration-queue-zulu48` → new repo name, `intel-agency` → new owner)
        - Commits and pushes the seeded repo
      </step>
      <step>3. On push, the clone's `validate` workflow runs CI (lint, scan, tests, devcontainer build) and the `publish-docker` workflow builds and pushes the base Docker image to GHCR.</step>
      <step>4. On successful `publish-docker` completion, the `prebuild-devcontainer` workflow is triggered (via `workflow_run`) to build and push the prebuilt devcontainer image. Together, `publish-docker` → `prebuild-devcontainer` form the devcontainer prebuild caching pipeline that the `orchestrator-agent` workflow relies on to quickly spin up devcontainers.</step>
    </creation_workflow>

    <template_design_constraints>
      <rule>Template placeholders (`workflow-orchestration-queue-zulu48`, `intel-agency`) in file contents and paths are replaced by the creation script. Keep them consistent.</rule>
      <rule>The `validate` workflow must tolerate fresh clones where no prebuilt GHCR devcontainer image exists yet (fallback build from Dockerfile + image aliasing).</rule>
      <rule>The `plan_docs/` directory contains external-generated documents seeded at clone time. Exclude it from strict linting (markdown lint, etc.).</rule>
      <rule>The consumer `.devcontainer/devcontainer.json` references a prebuilt GHCR image. On fresh clones the image won't exist until `publish-docker` and `prebuild-devcontainer` workflows complete their first run.</rule>
    </template_design_constraints>

    <automation_scripts>
      <entry><repo>nam20485/workflow-launch2</repo><path>scripts/create-repo-from-slug.ps1</path><description>Entry point — takes a slug, resolves plan docs dir, delegates to create-repo-with-plan-docs.ps1</description></entry>
      <entry><repo>nam20485/workflow-launch2</repo><path>scripts/create-repo-with-plan-docs.ps1</path><description>Full pipeline: repo create, clone, seed docs, placeholder replace, commit, push</description></entry>
    </automation_scripts>
  </template_usage>

  <tech_stack>
    <item>opencode CLI — agent runtime (`opencode --model zai-coding-plan/glm-5 --agent Orchestrator`)</item>
    <item>ZhipuAI GLM models via `ZHIPU_API_KEY`</item>
    <item>GitHub Actions + devcontainers/ci — workflow trigger, runner, reproducible container</item>
    <item>.NET SDK 10 + Aspire + Avalonia templates, Bun, uv (all in devcontainer)</item>
    <item>MCP servers: `@modelcontextprotocol/server-sequential-thinking`, `@modelcontextprotocol/server-memory`</item>
  </tech_stack>

  <repository_map>
    <!-- Workflows -->
    <entry><path>.github/workflows/orchestrator-agent.yml</path><description>Primary workflow — assembles prompt, logs into GHCR, runs opencode in devcontainer</description></entry>
    <entry><path>.github/workflows/prompts/orchestrator-agent-prompt.md</path><description>Prompt template with `__EVENT_DATA__` placeholder (sed-substituted at runtime)</description></entry>
    <entry><path>.github/workflows/publish-docker.yml</path><description>Builds Dockerfile, pushes to GHCR with branch-latest and branch-&lt;VERSION_PREFIX.run_number&gt; tags</description></entry>
    <entry><path>.github/workflows/prebuild-devcontainer.yml</path><description>Layers devcontainer Features on published Docker image (triggered by workflow_run)</description></entry>
    <!-- Agent definitions -->
    <entry><path>.opencode/agents/orchestrator.md</path><description>Orchestrator — coordinates specialists, never writes code directly</description></entry>
    <entry><path>.opencode/agents/</path><description>All specialist agents (developer, code-reviewer, planner, devops-engineer, github-expert, etc.)</description></entry>
    <entry><path>.opencode/commands/</path><description>Reusable command prompts (orchestrate-new-project, grind-pr-reviews, fix-failing-workflows, etc.)</description></entry>
    <entry><path>.opencode/opencode.json</path><description>opencode config — MCP server definitions</description></entry>
    <!-- Devcontainer -->
    <entry><path>.github/.devcontainer/Dockerfile</path><description>Devcontainer image — .NET SDK, Bun, uv, opencode CLI (build context for publish-docker)</description></entry>
    <entry><path>.github/.devcontainer/devcontainer.json</path><description>Build-time devcontainer config (Dockerfile + Features: node, python, gh CLI)</description></entry>
    <entry><path>.devcontainer/devcontainer.json</path><description>Consumer devcontainer — pulls prebuilt GHCR image, forwards port 4096, and auto-starts `opencode serve` on container start</description></entry>
    <entry><path>scripts/start-opencode-server.sh</path><description>Guarded `opencode serve` bootstrapper used by the devcontainer lifecycle and workflow attach path</description></entry>
    <entry><path>scripts/run-devcontainer-orchestrator.sh</path><description>One-shot script: brings up the devcontainer, ensures the opencode server is running, and executes the orchestrator agent. Used by the workflow and can be invoked directly locally.</description></entry>
    <!-- Tests -->
    <entry><path>test/</path><description>Shell-based tests: devcontainer build, tool availability, prompt assembly</description></entry>

    <opencode_server>
      <summary>
        The consumer devcontainer auto-starts `opencode serve` through `scripts/start-opencode-server.sh`.
        The server listens on port `4096` by default so host or in-container clients can attach with
        `opencode run --attach http://127.0.0.1:4096 ...` (or the forwarded host port when connecting from outside the container).
      </summary>
    </opencode_server>
    <entry><path>test/fixtures/</path><description>Sample webhook payloads for local testing</description></entry>
    <!-- Remote instructions -->
    <entry><path>local_ai_instruction_modules/</path><description>Local instruction modules (development rules, workflows, delegation, terminal commands)</description></entry>
  </repository_map>

  <instruction_source>
    <repository>
      <name>nam20485/agent-instructions</name>
      <branch>main</branch>
    </repository>
    <guidance>
      Remote instructions are the single source of truth. Fetch from raw URLs:
      replace `github.com/` with `raw.githubusercontent.com/` and remove `blob/`.
      Core instructions: `https://raw.githubusercontent.com/nam20485/agent-instructions/main/ai_instruction_modules/ai-core-instructions.md`
    </guidance>
    <modules>
      <module type="core" required="true" link="https://github.com/nam20485/agent-instructions/blob/main/ai_instruction_modules/ai-core-instructions.md">Core Instructions</module>
      <module type="local" required="true" path="local_ai_instruction_modules">Local AI Instructions</module>
      <module type="local" required="true" path="local_ai_instruction_modules/ai-dynamic-workflows.md">Dynamic Workflow Orchestration</module>
      <module type="local" required="true" path="local_ai_instruction_modules/ai-workflow-assignments.md">Workflow Assignments</module>
      <module type="local" required="true" path="local_ai_instruction_modules/ai-development-instructions.md">Development Instructions</module>
      <module type="optional" path="local_ai_instruction_modules/ai-terminal-commands.md">Terminal Commands</module>
    </modules>
  </instruction_source>

  <environment_setup>
    <secrets>
      <item>`ZHIPU_API_KEY` — ZhipuAI model access; set in repo Settings → Secrets.</item>
      <item>`KIMI_CODE_ORCHESTRATOR_AGENT_API_KEY` — Kimi (Moonshot) model access; set in repo Settings → Secrets.</item>
      <item>`GH_ORCHESTRATION_AGENT_TOKEN` — org-level PAT with scopes: repo, workflow, project, read:org. Required for orchestrator execution. No fallback to `GITHUB_TOKEN`.</item>
      <item>`GITHUB_TOKEN` — provided automatically by Actions; used only for GHCR login (image pull).</item>
    </secrets>
    <devcontainer_cache>
      Image at `ghcr.io/${{ github.repository }}/devcontainer`. `publish-docker.yml` builds the raw Dockerfile;
      `prebuild-devcontainer.yml` layers Features. Login via `docker/login-action` with `GITHUB_TOKEN`.
      Set repo variable `VERSION_PREFIX` (e.g., `1.0`) for versioned tags emitted by both image publishing workflows.
    </devcontainer_cache>
  </environment_setup>

  <testing>
    <guidance>Tests are shell scripts in `test/`. Run directly with `bash`.</guidance>
    <commands>
      <command>All tests: `bash test/test-devcontainer-build.sh && bash test/test-devcontainer-tools.sh && bash test/test-prompt-assembly.sh`</command>
      <command>Prompt changes: `bash test/test-prompt-assembly.sh`</command>
      <command>Dockerfile changes: `bash test/test-devcontainer-tools.sh`</command>
    </commands>
    <guidance>Add new fixture payloads to `test/fixtures/` when testing new event types.</guidance>
  </testing>

  <coding_conventions>
    <rule>Keep changes minimal and targeted.</rule>
    <rule>Do not hardcode secrets/tokens. When writing tests for credential-scrubbing or secret-detection utilities, use obviously synthetic values that will not trigger `gitleaks` (e.g., `FAKE-KEY-FOR-TESTING-00000000`). Never use prefixes that match real provider formats (`sk-`, `ghp_`, `ghs_`, `AKIA`, etc.) in test fixtures.</rule>
    <rule>Preserve the `__EVENT_DATA__` placeholder in `orchestrator-agent-prompt.md`.</rule>
    <rule>Keep orchestrator delegation-depth ≤2 and "never write code directly" constraint.</rule>
    <rule>Pin ALL GitHub Actions by full SHA to the latest release — no tag or branch references (`@v4`, `@main`). Format: `uses: owner/action@<full-40-char-SHA> # vX.Y.Z`. The trailing comment with the semver tag is mandatory for human readability. This applies to every `uses:` line in every workflow file, including third-party actions, first-party (`actions/*`), and reusable workflows. Supply-chain attacks via tag mutation are a critical threat — SHA pinning is the only mitigation. When creating or modifying workflows, look up the SHA for the latest release of each action (e.g., via `gh api repos/actions/checkout/releases/latest --jq .tag_name` then resolve to SHA) and pin to it.</rule>
    <rule>Never add duplicate top-level `name:`, `on:`, or `jobs:` keys in workflow YAML.</rule>
    <rule>`.opencode/` is checked out by `actions/checkout`; do not COPY it in the Dockerfile.</rule>
    <rule>Dockerfile lives at `.github/.devcontainer/Dockerfile`. Consumer devcontainer uses `"image:"` — no local build.</rule>
    <rule>Repository labels are defined in `.github/.labels.json`. Use `scripts/import-labels.ps1` to sync them to a repo instance. When adding new labels, add them to this file — it is the single source of truth for the label set.</rule>
  </coding_conventions>

  <!-- ═══════════════════════════════════════════════════════════════════
       MANDATORY TOOL PROTOCOLS — ALL AGENTS MUST FOLLOW
       These are NON-NEGOTIABLE requirements for every agent in this system.
       Failure to follow these protocols is a critical defect.
       ═══════════════════════════════════════════════════════════════════ -->
  <mandatory_tool_protocols>
    <overview>
      ALL agents — orchestrator, specialists, and subagents — MUST use the following
      MCP tools as part of their standard operating procedure. These are not optional
      suggestions; they are mandatory requirements that apply to every non-trivial task.
      Agents that skip these protocols are operating incorrectly.
    </overview>

    <protocol id="sequential_thinking" enforcement="MANDATORY">
      <title>Sequential Thinking Tool — ALWAYS USE</title>
      <tool>sequential_thinking</tool>
      <when>
        EVERY non-trivial task. This means any task that involves more than a single
        obvious action. If in doubt, use it.
      </when>
      <required_usage_points>
        <point>At task START: Use sequential thinking to analyze the request, break it into steps, identify risks, and plan the approach BEFORE taking any action.</point>
        <point>At DECISION POINTS: Use sequential thinking when choosing between alternatives, evaluating trade-offs, or making architectural decisions.</point>
        <point>When DEBUGGING: Use sequential thinking to systematically isolate root causes.</point>
        <point>Before DELEGATION: The Orchestrator MUST use sequential thinking to plan the delegation tree, determine agent assignments, and define success criteria.</point>
      </required_usage_points>
      <violation>Skipping sequential thinking on a non-trivial task is a protocol violation. If an agent completes a complex task without invoking sequential_thinking, the work should be reviewed for quality issues.</violation>
    </protocol>

    <protocol id="knowledge_graph_memory" enforcement="MANDATORY">
      <title>Knowledge Graph Memory — ALWAYS USE</title>
      <tools>
        <tool>create_entities</tool>
        <tool>create_relations</tool>
        <tool>add_observations</tool>
        <tool>delete_entities</tool>
        <tool>delete_observations</tool>
        <tool>delete_relations</tool>
        <tool>read_graph</tool>
        <tool>search_nodes</tool>
        <tool>open_nodes</tool>
      </tools>
      <required_usage_points>
        <point>At task START: Call `read_graph` or `search_nodes` to retrieve existing context about the project, user preferences, prior decisions, and known patterns BEFORE planning or acting.</point>
        <point>After SIGNIFICANT WORK: Call `create_entities`, `add_observations`, or `create_relations` to persist important findings, decisions, patterns discovered, and context for future tasks.</point>
        <point>After COMPLETING a task: Store the outcome, any lessons learned, and follow-up items in the knowledge graph.</point>
        <point>When STARTING a new workflow or assignment: Search for prior related work, decisions, and context.</point>
      </required_usage_points>
      <what_to_store>
        <item>Project-specific patterns and conventions discovered during work</item>
        <item>User preferences and decisions that affect future tasks</item>
        <item>Architectural decisions and their rationale</item>
        <item>Error patterns and their resolutions</item>
        <item>Cross-task context that would otherwise be lost between sessions</item>
        <item>Workflow state and progress checkpoints</item>
      </what_to_store>
      <violation>Failing to read existing memory at task start or failing to persist important findings after task completion is a protocol violation.</violation>
    </protocol>

    <protocol id="change_validation" enforcement="MANDATORY">
      <title>Change Validation Protocol — ALWAYS FOLLOW</title>
      <when>
        After ANY non-trivial change to code, configuration, workflows, or infrastructure.
        This includes: logic changes, behavior changes, refactors, dependency updates,
        config changes, multi-file edits, workflow modifications.
      </when>
      <required_steps>
        <step order="1">Run the full validation suite: `pwsh -NoProfile -File ./scripts/validate.ps1 -All`</step>
        <step order="2">Fix ALL failures — do not skip, suppress, or ignore errors.</step>
        <step order="3">Re-run validation until ALL checks pass clean.</step>
        <step order="4">Only THEN proceed to commit and push.</step>
      </required_steps>
      <validation_commands>
        <command purpose="all checks">./scripts/validate.ps1 -All</command>
        <command purpose="lint only">./scripts/validate.ps1 -Lint</command>
        <command purpose="scan only">./scripts/validate.ps1 -Scan</command>
        <command purpose="test only">./scripts/validate.ps1 -Test</command>
        <command purpose="devcontainer">bash test/test-devcontainer-tools.sh</command>
      </validation_commands>
      <post_push>
        After push, monitor CI: `gh run list --limit 5`, `gh run watch &lt;id&gt;`, `gh run view &lt;id&gt; --log-failed`.
        If CI fails, STOP feature work, triage, fix, re-verify, push. Do NOT mark work complete while CI is red.
      </post_push>
      <violation>Committing or pushing code without running validation is a protocol violation. Marking a task complete while CI is failing is a protocol violation.</violation>
    </protocol>

    <agent_checklist>
      <!-- Agents: verify you have completed these items on every non-trivial task -->
      <item>☐ Called sequential_thinking at task start to plan approach</item>
      <item>☐ Called read_graph / search_nodes to retrieve prior context</item>
      <item>☐ Used sequential_thinking at key decision points during work</item>
      <item>☐ Ran validation (./scripts/validate.ps1 -All) before commit/push</item>
      <item>☐ Fixed all validation failures and re-verified clean</item>
      <item>☐ Persisted important findings to knowledge graph memory</item>
      <item>☐ Monitored CI after push and confirmed green</item>
    </agent_checklist>
  </mandatory_tool_protocols>

  <agent_specific_guardrails>
    <rule>The Orchestrator agent delegates to specialists via the `task` tool — never writes code directly.</rule>
    <rule>The Orchestrator MUST invoke `sequential_thinking` before planning any delegation and `read_graph` before every new task to load prior project context.</rule>
    <rule>ALL agents MUST follow the mandatory_tool_protocols defined above — sequential thinking, memory, and change validation are not optional.</rule>
    <rule>Prompt assembly pipeline:
      1. Read template from `.github/workflows/prompts/orchestrator-agent-prompt.md`.
      2. Prepend structured event context (event name, action, actor, repo, ref, SHA).
      3. Append raw event JSON from `${{ toJson(github.event) }}`.
      4. Write to `.assembled-orchestrator-prompt.md` and export path via `GITHUB_ENV`.
    </rule>
  </agent_specific_guardrails>

  <agent_readiness>
    <verification_protocol>
      MANDATORY: For any non-trivial change (logic, behavior, refactors, dependency updates, config changes, multi-file edits):
      run `./scripts/validate.ps1 -All`, fix all failures, re-run until clean. Do not skip or suppress errors.
      Do NOT commit or push until validation passes. Do NOT mark tasks complete while CI is red.
      See `mandatory_tool_protocols.change_validation` above for the full protocol.
    </verification_protocol>

    <verification_commands>
      <!--
        MANDATORY: After every non-trivial change, run validation BEFORE commit/push.
        Do NOT commit or push until it passes. Do NOT skip steps.

        Local (runs all checks sequentially — lint, scan, test):
          pwsh -NoProfile -File ./scripts/validate.ps1 -All

        This is the SAME script that CI calls with individual switches:
          ./scripts/validate.ps1 -Lint   (CI: lint job)
          ./scripts/validate.ps1 -Scan   (CI: scan job)
          ./scripts/validate.ps1 -Test   (CI: test job)

        If a check is skipped due to a missing local tool, run:
          pwsh -NoProfile -File ./scripts/install-dev-tools.ps1

        | Check                  | Command                                              | When to run              |
        |========================|======================================================|==========================|
        | All (local default)    | ./scripts/validate.ps1 -All                           | Every task               |
        | Lint only              | ./scripts/validate.ps1 -Lint                           | Quick check              |
        | Scan only              | ./scripts/validate.ps1 -Scan                           | Secrets concern          |
        | Test only              | ./scripts/validate.ps1 -Test                           | After lint passes        |
        | Devcontainer tests     | bash test/test-devcontainer-tools.sh                   | Dockerfile changes       |
      -->
      <rule>When adding a CI workflow check, add its equivalent to scripts/validate.ps1.</rule>
    </verification_commands>

    <post_commit_monitoring>
      After push, monitor CI until green: `gh run list --limit 5`, `gh run watch <id>`, `gh run view <id> --log-failed`.
      If any workflow fails, stop feature work, triage, fix, re-verify, push. Do not mark work complete while CI is failing.
    </post_commit_monitoring>

    <pipeline_speed_policy>
      <lane name="fast_readiness" blocking="true">Build, lint/format, unit tests — keep fast for merge readiness.</lane>
      <lane name="extended_validation" blocking="false">Integration suites, security scans, dependency audits.</lane>
      <rule>Protect the fast lane from slow steps.</rule>
    </pipeline_speed_policy>
  </agent_readiness>

  <validation_before_handoff>
    <step>Run applicable shell tests and verification commands.</step>
    <step>Validate workflow YAML: `grep -c "^name:" .github/workflows/orchestrator-agent.yml  # expect 1`</step>
    <step>Summarize: what changed, what was validated, remaining risks (secret-dependent paths, image cache misses).</step>
  </validation_before_handoff>

  <tool_use_instructions>
    <instruction id="querying_microsoft_documentation">
      <applyTo>**</applyTo>
      <title>Querying Microsoft Documentation</title>
      <tools><tool>microsoft_docs_search</tool><tool>microsoft_docs_fetch</tool><tool>microsoft_code_sample_search</tool></tools>
      <guidance>
        Use these MCP tools for Microsoft technologies (C#, ASP.NET Core, .NET, EF, NuGet).
        Prioritize retrieved info over training data for newer features.
      </guidance>
    </instruction>
    <instruction id="sequential_thinking_default_usage" enforcement="MANDATORY">
      <applyTo>*</applyTo>
      <title>Sequential Thinking — MANDATORY for all non-trivial tasks</title>
      <tools><tool>sequential_thinking</tool></tools>
      <guidance>
        **MUST USE** for all non-trivial requests. This is a mandatory protocol, not a suggestion.
        See `mandatory_tool_protocols.sequential_thinking` for full requirements.
        Invoke at: task start (planning), decision points, debugging, and before delegation.
        Skipping this tool on complex tasks is a protocol violation.
      </guidance>
    </instruction>
    <instruction id="memory_default_usage" enforcement="MANDATORY">
      <applyTo>*</applyTo>
      <title>Knowledge Graph Memory — MANDATORY for all non-trivial tasks</title>
      <tools><tool>create_entities</tool><tool>create_relations</tool><tool>add_observations</tool><tool>delete_entities</tool><tool>delete_observations</tool><tool>delete_relations</tool><tool>read_graph</tool><tool>search_nodes</tool><tool>open_nodes</tool></tools>
      <guidance>
        **MUST USE** for all non-trivial requests. This is a mandatory protocol, not a suggestion.
        See `mandatory_tool_protocols.knowledge_graph_memory` for full requirements.
        Invoke at: task start (read_graph/search_nodes), after significant work (create_entities/add_observations),
        and after task completion (persist outcomes and lessons learned).
        Skipping memory operations is a protocol violation.
      </guidance>
    </instruction>
  </tool_use_instructions>

  <available_tools>
    <summary>
      Tools available inside the devcontainer at runtime. Installed via
      `.github/.devcontainer/Dockerfile` unless noted otherwise.
    </summary>

    <runtimes_and_package_managers>
      <tool name="dotnet" version="10.0.102">`.NET SDK` — build, test, publish C#/F# projects. Includes Avalonia Templates 11.3.12.</tool>
      <tool name="node" version="24.14.0 LTS">`Node.js` — JavaScript runtime. Required for MCP server packages (`npx`).</tool>
      <tool name="npm">`npm` — Node package manager (bundled with Node.js).</tool>
      <tool name="bun" version="1.3.10">`Bun` — fast JavaScript/TypeScript runtime, bundler, and package manager.</tool>
      <tool name="uv" version="0.10.9">`uv` — Astral Python package manager. Also provides `uvx` for ephemeral tool runs.</tool>
    </runtimes_and_package_managers>

    <cli_tools>
      <tool name="gh">`GitHub CLI` — interact with GitHub API (issues, PRs, repos, releases, actions). Authenticated via `GH_ORCHESTRATION_AGENT_TOKEN` exported as `GH_TOKEN`.</tool>
      <tool name="opencode" version="1.2.24">`opencode CLI` — AI agent runtime. Runs agents defined in `.opencode/agents/` with MCP server support.</tool>
      <tool name="git">`Git` — version control (system package + devcontainer feature).</tool>
    </cli_tools>

    <github_authentication>
      <summary>
        GitHub API access uses a single token: `GH_ORCHESTRATION_AGENT_TOKEN`, an org-level PAT
        with scopes `repo`, `workflow`, `project`, `read:org`. This token is required for
        orchestrator execution — there is no fallback to `GITHUB_TOKEN`.
      </summary>
      <layer name="GH_ORCHESTRATION_AGENT_TOKEN">Org-level PAT configured as a repo/org secret. `run_opencode_prompt.sh` exports it as `GH_TOKEN`, `GITHUB_TOKEN`, and `GITHUB_PERSONAL_ACCESS_TOKEN` so that `gh` CLI, MCP GitHub server, and opencode all authenticate with the same token.</layer>
      <layer name="GITHUB_TOKEN (Actions-provided)">Only used for GHCR login (`docker/login-action`) to pull devcontainer images. Not used for orchestrator API operations.</layer>
    </github_authentication>

    <scripts_directory>
      <summary>PowerShell helper scripts in `scripts/` for GitHub setup and management tasks.</summary>
      <script name="scripts/common-auth.ps1">Shared `Initialize-GitHubAuth` function — checks `gh auth status`, authenticates via PAT token (`$env:GITHUB_AUTH_TOKEN`) or interactive login.</script>
      <script name="scripts/gh-auth.ps1">Extended GitHub auth helper — supports PAT token auth via `--with-token` and interactive fallback.</script>
      <script name="scripts/import-labels.ps1">Imports labels from `.github/.labels.json` into the repository.</script>
      <script name="scripts/create-milestones.ps1">Creates project milestones from plan docs.</script>
      <script name="scripts/test-github-permissions.ps1">Verifies `GITHUB_TOKEN` has required permissions (contents, issues, PRs, packages).</script>
      <script name="scripts/query.ps1">PR review thread manager — fetches unresolved review threads from a PR, summarizes them, and can batch-reply and resolve them. Supports `--AutoResolve`, `--DryRun`, `--Interactive`, `--ReplyEach`, `--Path`, `--BodyContains` filtering. Use this instead of writing ad-hoc scripts to resolve PR review comments.</script>
      <script name="scripts/update-remote-indices.ps1">Updates remote instruction module indices.</script>
    </scripts_directory>
  </available_tools>
</instructions>

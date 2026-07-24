# SOLAR-Ralph Reference

Deep-reference catalog for the SOLAR-Ralph framework. Use this alongside the [installation guide](../SOLAR-Ralph-implementation-guideline.md) when customizing individual files.

---

## Layer 1: Agent Roster

All agents live in `.github/agents/`. All agents use the same model tier by default (see [Model Policy](#model-policy) below).

| File                                             | Role                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| `orchestration-governor.agent.md`                | Pipeline router, delegation enforcer, step supervisor                          |
| `context-summarizer.agent.md`                    | Reads source files, produces compact digests. Only agent with `read` tool      |
| `frontend-implementation-specialist.agent.md`    | React, TypeScript, context, reducers, routing, components **[POST-IMPLEMENT]** |
| `backend-implementation-specialist.agent.md`     | Express, Prisma, services, repositories, auth **[POST-IMPLEMENT]**             |
| `frontend-test-specialist.agent.md`              | Vitest, RTL, reducer, hook, component tests **[POST-IMPLEMENT]**               |
| `backend-test-specialist.agent.md`               | Backend service, repository, integration, Prisma tests **[POST-IMPLEMENT]**    |
| `docs-curator.agent.md`                          | Documentation and template compliance **[POST-IMPLEMENT]**                     |
| `bug-investigation-specialist.agent.md`          | Root-cause classification; writes repro script                                 |
| `cache-external-integration-specialist.agent.md` | Redis, external APIs, TTL, retry, circuit-breaker **[POST-IMPLEMENT]**         |
| `frontend-review-auditor.agent.md`               | Adversarial frontend review                                                    |
| `backend-review-auditor.agent.md`                | Adversarial backend review                                                     |
| `release-readiness-specialist.agent.md`          | Go/No-Go gate before governor writes WORK_PACKAGE_COMPLETE                     |
| `design-planning-architect.agent.md`             | Solution shaping, decomposition, spec-first artifact production                |
| `security-auditor.agent.md`                      | Auth, JWT, CORS, cookies, input validation, rate limiting                      |

> **Note on [POST-IMPLEMENT] agents**: The implementation agents need to know your stack. Update the "Tech Stack" and "Constraints" sections to match your repo's language, framework, ORM, and test runner. The governance agents (governor, architect, auditors, security) are largely universal.

---

## Layer 2: Skill Library

All skills live in `.github/skills/<name>/SKILL.md`. Load with `#<skill-name>` or via the agent's skills list.

### Core Execution Skills

| Skill Folder                       | Purpose                                                                              | Tag |
| ---------------------------------- | ------------------------------------------------------------------------------------ | --- |
| `frontend-feature-implementation/` | Reflexion-cycle implementation: Responder → Evaluator → Revisor **[POST-IMPLEMENT]** |     |
| `backend-feature-implementation/`  | Same Reflexion cycle for backend **[POST-IMPLEMENT]**                                |     |
| `frontend-review/`                 | ARA 4-pattern gaming detector for frontend changes                                   |     |
| `backend-review/`                  | ARA 4-pattern gaming detector for backend changes                                    |     |
| `frontend-testing/`                | Vitest + RTL test procedures **[POST-IMPLEMENT]**                                    |     |
| `backend-testing/`                 | Jest/Vitest backend test procedures **[POST-IMPLEMENT]**                             |     |

### Context & Governance Skills

| Skill Folder             | Purpose                                                        |
| ------------------------ | -------------------------------------------------------------- |
| `context-summarization/` | Reads source files, produces compact digests for specialists   |
| `story-execution/`       | End-to-end: plan → implement → test → docs → review → ledger   |
| `doc-sync/`              | Keeps BR, implementation docs, and KB synchronized             |
| `memory-curation/`       | Decides what belongs in repo memory vs ledger vs docs          |
| `memory-verification/`   | Validates stale `.github/memories/repo/` facts before applying |
| `recursive-remediation/` | Bounded repair loops without scope creep                       |
| `release-governance/`    | 5-gate Go/No-Go check before pipeline closure                  |

### Debug & Browser Skills

| Skill Folder                       | Purpose                                                           |
| ---------------------------------- | ----------------------------------------------------------------- |
| `browser-reproduction/`            | Playwright MCP: navigate → snapshot → reproduce → Behavior Report |
| `external-integration-operations/` | Fetch MCP for API contracts; Puppeteer MCP for CDP/DOM inspection |

> **[POST-IMPLEMENT] skills**: The implementation and testing skills need their "Tech Stack" sections updated to match your project's conventions, test utilities, and file path patterns.

---

## Layer 3: Lifecycle Hooks

| File                       | Contents                                                                                                  | Tag                  |
| -------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------- |
| `.github/hooks/hooks.json` | One hook: `PostToolUse` (write-op guard → emits `ADVERSARIAL_VERIFY_REQUIRED` when ledger stage = VERIFY) | **[POST-IMPLEMENT]** |

**Customize**: Replace `npx tsc --noEmit` in PostToolUse with your stack's check command (e.g., `python -m mypy`, `dotnet build`, `cargo check`).

---

## Layer 4: Path-Specific Instructions

These scoped instruction files enforce lang/framework rules only within their directory, preventing "instruction leakage" across the full codebase.

| File                                 | Scope Pattern                                        | Tag                                                                       |
| ------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------- |
| `context-summarizer.instructions.md` | `applyTo: ".github/prompts/solar.prompt.md"`         | Dispatch pattern for the Governor — referenced by solar.prompt.md step 3b |
| `apps/frontend/.instructions.md`     | `applyTo: "apps/frontend/**/*.{ts,tsx,css,scss,md}"` | **[POST-IMPLEMENT]**                                                      |
| `apps/backend/.instructions.md`      | `applyTo: "apps/backend/**/*.{ts,js,md}"`            | **[POST-IMPLEMENT]**                                                      |

**For other repos**: Create one `.instructions.md` per app/service boundary. Match `applyTo` to the folder glob. Fill in constraints specific to your stack (state management patterns, API conventions, forbidden patterns, etc.).

**Reusable pattern instructions**: For patterns used by the Governor or shared across components (e.g., context-summarizer dispatch), define the pattern in an `.instructions.md` and scope `applyTo` to the consuming files. This keeps the pattern in one place rather than inlined in swappable playbooks.

---

## Layer 5: Persistent Repo Memory

All memory files live in `.github/memories/repo/`. These are concise fact sheets reused across sessions by Copilot, which stores them internally. The template ships pre-structured files you copy as scaffolding; the agent fills in the content from your codebase, Copilot ingests them, and the git-tracked files can be deleted afterward.

| File                    | What to Put Here                                                | Tag                  |
| ----------------------- | --------------------------------------------------------------- | -------------------- |
| `commands.md`           | Verified build, test, lint, and dev server commands             | **[POST-IMPLEMENT]** |
| `architecture.md`       | High-level folder layout, stack choices, data flow summary      | **[POST-IMPLEMENT]** |
| `workflow-facts.md`     | Branch naming, commit conventions, PR process, doc update rules | **[POST-IMPLEMENT]** |
| `frontend-facts.md`     | Component patterns, routing approach, state management choices  | **[POST-IMPLEMENT]** |
| `backend-facts.md`      | API conventions, DB access patterns, auth mechanism             | **[POST-IMPLEMENT]** |
| `security-facts.md`     | Auth flow details, secret locations, known risk areas           | **[POST-IMPLEMENT]** |
| `verification-facts.md` | Test commands, type-check commands, known flaky areas           | **[POST-IMPLEMENT]** |

> **Tip**: On first use, have the Orchestration Governor populate these files by running a codebase exploration pass before any story work begins. Use the `memory-curation` skill to guide what belongs here.

---

## Layer 6: Commands

| File                                     | Purpose                                       |
| ---------------------------------------- | --------------------------------------------- |
| `.github/commands/ralph-loop.prompt.md`  | Bounded autonomous story loop (`/ralph-loop`) |
| `.github/commands/audit-story.prompt.md` | Adversarial audit command (`/audit-story`)    |

These are universal — no customization needed. They reference ledger fields and agents that are already parameterized.

---

## Layer 7: Operator Guides

Reference documentation for humans operating the system.

| File                                        | Purpose                                        | Tag                  |
| ------------------------------------------- | ---------------------------------------------- | -------------------- |
| `.github/guides/solar-ralph-workflow.md`    | Maps SOLAR onto repo delivery workflow         | **[POST-IMPLEMENT]** |
| `.github/guides/agent-operations-guide.md`  | How to invoke agents, skills, and loops safely |                      |
| `.github/guides/memory-governance-guide.md` | Memory vs ledger vs docs decision rules        |                      |

---

## Layer 8: Knowledge Base Articles

These are generic reference articles that require no customization. Copy as-is.

| File                                                   | Content                                                   |
| ------------------------------------------------------ | --------------------------------------------------------- |
| `docs/knowledge-base/agent-orchestration-patterns.md`  | Hub-and-spoke design rationale and alternatives           |
| `docs/knowledge-base/adversarial-auditing-patterns.md` | ARA, code-gaming detection, verification backpressure     |
| `docs/knowledge-base/recursive-refinement-patterns.md` | Ralph-loop design, completion promise protocol            |
| `docs/knowledge-base/agent-memory-governance.md`       | Ledger hygiene, memory lifetimes, stale-fact prevention   |
| `docs/knowledge-base/connected-agent-topologies.md`    | Hub-and-spoke vs DAG vs fan-out; topology decision record |
| `docs/knowledge-base/mcp-integration-patterns.md`      | MCP server selection, security patterns, decision table   |

---

## Layer 9: MCP Integration (Optional but Recommended)

Enables browser automation, API contract testing, and GitHub integration for agents.

| File                    | Contents                                            | Tag                  |
| ----------------------- | --------------------------------------------------- | -------------------- |
| `.vscode/mcp.json`      | 4 MCP servers: Playwright, GitHub, Puppeteer, Fetch | **[POST-IMPLEMENT]** |
| `.vscode/settings.json` | Copilot agent enable flag; Autopilot opt-in comment | **[POST-IMPLEMENT]** |

### MCP Server Reference Table

| Server       | npm Package                              | Agent Use Case                                                  |
| ------------ | ---------------------------------------- | --------------------------------------------------------------- |
| `playwright` | `@playwright/mcp@latest`                 | Browser automation, accessibility tree, console/network capture |
| `github`     | `@modelcontextprotocol/server-github`    | Issues, PRs, CI status, code search                             |
| `puppeteer`  | `@modelcontextprotocol/server-puppeteer` | CDP `evaluate`, DOM inspection, localStorage/sessionStorage     |
| `fetch`      | `mcp-fetch-server`                       | Stateless HTTP — API contract testing without a browser         |

**[POST-IMPLEMENT]**: Set `COPILOT_MCP_GITHUB_TOKEN` in VS Code secret storage. Remove servers not relevant to your stack. See `.github/guides/mcp-operations-guide.md` for full setup.

---

## Layer 10: Verification Artifacts Directory

| File                               | Purpose                                              |
| ---------------------------------- | ---------------------------------------------------- |
| `verification-artifacts/README.md` | Naming conventions, retention policy, emission rules |
| `verification-artifacts/.gitkeep`  | Keeps directory tracked in git                       |

Files written here at runtime (e.g., `target-<slug>.json` from Design Planning Architect) are per-story and should not be committed unless explicitly needed for audit trails.

---

## Layer 11: Ledger State File

| File                    | Purpose                                            | Tag                  |
| ----------------------- | -------------------------------------------------- | -------------------- |
| `.github/.ai_ledger.md` | Active work queue, blockers, verification failures | **[POST-IMPLEMENT]** |

Start with the template structure below. Do not copy content from another project's ledger.

```markdown
## Objective

[one sentence]

## Work Queue

| id  | task | agent | status | stage |
| --- | ---- | ----- | ------ | ----- |

## Decisions Log

<!-- append-only; format: YYYY-MM-DD HH:MM UTC: <decision summary> -->
```

---

## Layer 12: Root Contract Files

| File                              | Purpose                                                                                               | Tag                  |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------- |
| `.github/AGENTS.md`               | Full orchestration contract: pipelines, delegation matrix, verification contract, completion promises |                      |
| `.github/copilot-instructions.md` | Instruction precedence, SOLAR operating references, loop guidance                                     | **[POST-IMPLEMENT]** |

**[POST-IMPLEMENT]** for `copilot-instructions.md`: Keep the SOLAR operating overlay section universal, but update the "Architecture Overview" and "Key Files & Directories" sections to match your repo structure.

---

## Phase 2 Enhancements (Apply After Core Is Stable)

These add quality, cost efficiency, and debug capability on top of the core SOLAR system.

| ID  | Item                                                          | Status                           | Notes                                                                                 |
| --- | ------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------- |
| A5  | Step-Level Process Supervision                                | ✅ In governor                   | Universal — no customization needed                                                   |
| A6  | ARA 2.0 — Hacker-Auditor Pairs                                | ⏭️ Phase 3                       | Add "Proxy Sovereignty" section to both review auditors                               |
| A7  | Semantic Gradient Refinement                                  | ✅ In ledger + .github/AGENTS.md | Universal                                                                             |
| A8  | Exploration SKILL.md for Bug Investigation                    | ⏭️ Phase 3                       | Create `.github/skills/exploration/SKILL.md`                                          |
| B5  | Bypass Approvals / Autopilot                                  | ✅ `.vscode/settings.json`       | **[POST-IMPLEMENT]** — uncomment `terminal.allowAutoExecute` per developer preference |
| B6  | Parallel Execution via Isolated Worktrees                     | ⏭️ Phase 3                       | Requires Copilot parallel agent fan-out                                               |
| B7  | Heuristic Context Rotation (Stream Parser)                    | ⏭️ Phase 3                       | Requires token-count hook API                                                         |
| B8  | JIT Skill Loading via Argument-Hint                           | ~Partial                         | `argumentHint` on skills; governor doesn't yet enforce stage-specific loading         |
| C5  | MCP Server Integration (Playwright, Puppeteer, Fetch, GitHub) | ✅ `.vscode/mcp.json`            | **[POST-IMPLEMENT]** — add GitHub token                                               |
| C6  | Verification-as-Code (VaC) Artifacts                          | ✅ `verification-artifacts/`     | Per-stage signed artifact automation pending                                          |
| C7  | Gutter Detection and Escalation                               | ⏭️ Phase 3                       | Add same-error-3x hash tracking to governor                                           |
| C8  | Path-Specific Instruction Globbing                            | ✅ `.instructions.md` files      | **[POST-IMPLEMENT]** — update `applyTo` glob                                          |
| C9  | GitHub-hosted Copilot Memory                                  | non-file                         | Manual admin toggle: org/repo Settings → GitHub Copilot → Memory                      |

---

## Model Policy

All agents use a single model tier by default. With the availability of capable low-cost models (e.g., DeepSeek V4 Flash), model tiering for cost optimization is no longer necessary. Agents requiring deeper reasoning (architect, security auditor) may optionally use a premium model.

**Recommended model**: `DeepSeek V4 Flash (deepseek)` — all agents.
**Premium alternative**: `Claude Sonnet 4.5 (copilot)` — architect, security auditor (optional).

---

## Quick Reference: Session Types

| Session-Type  | Behavior                                        | When to Use                                 |
| ------------- | ----------------------------------------------- | ------------------------------------------- |
| `chat`        | Governor runs interactively; no loop state      | Planning, single queries, knowledge lookups |
| `loop`        | Governor runs bounded cycle with max_iterations | `/ralph-loop` autonomous execution          |
| `manual-test` | Human drives app; agent observes and reports    | Manual testing sessions                     |

Set the active session type in `.github/.ai_ledger.md`:

```
Session-Type: loop
```

| `<promise>ESCALATION_REQUIRED</promise>` | Exceeds agent scope; human decision needed |

---

## Quick Reference: Verification Failure Format

Every failure entry in the ledger **must** include all three fields:

```markdown
- Verification Step: <what was checked>
- Failure: <error output summary>
- Root Cause Hint: <which concept, abstraction, or data path to investigate next>
```

A bare "test failed" entry is not acceptable and will be flagged by step supervision.

---

## Phase 3 Roadmap (Not Yet Implemented)

| ID  | Item                                                            | Trigger Condition                                                  |
| --- | --------------------------------------------------------------- | ------------------------------------------------------------------ |
| A6  | ARA 2.0 — Hacker-Auditor Pairs with Proxy Sovereignty detection | When over-mocking becomes a recurring false-pass pattern           |
| A8  | Exploration SKILL.md for Bug Investigation                      | When investigation specialist frequently requests manual grep help |
| B6  | Parallel Execution via Isolated Git Worktrees                   | When Copilot runtime supports parallel agent fan-out               |
| B7  | Heuristic Context Rotation via Stream Parser                    | When a reliable byte/token-count hook API is available             |
| B8  | Enforced JIT Skill Loading in Governor                          | When context window cost becomes measurably significant            |
| C7  | Gutter Detection in Governor                                    | When same-error loops are observed causing wasted iterations       |
| C9  | GitHub-hosted Copilot Memory                                    | When org admin enables Memory in GitHub Settings → Copilot         |

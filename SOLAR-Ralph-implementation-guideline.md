# SOLAR-Ralph Full Implementation Guideline

A complete reference for deploying SOLAR-Ralph in any repository. Items marked **[POST-IMPLEMENT]** contain repo-specific content that must be customized after the template files are copied. Items with no tag are universal and can be used as-is.

---

## What Is SOLAR-Ralph?

SOLAR-Ralph is a repo-native autonomous agent framework built on five pillars:

| Pillar           | What It Provides                                                       |
| ---------------- | ---------------------------------------------------------------------- |
| **S**pecialist   | Domain-specific agents for frontend, backend, testing, security, docs  |
| **O**rchestrator | Central governor that selects pipelines, delegates, and enforces gates |
| **L**edger       | Restart-safe work-state file; survival memory across sessions          |
| **A**dversarial  | Review auditors and security auditor with code-gaming detection        |
| **R**ecursive    | Bounded repair loops with escalation stop conditions                   |

---

## Minimum Viable Set (Phase 1 Core)

These 5 items are the absolute minimum to have a functioning SOLAR loop. Everything else layers on top.

| #   | File                                             | Purpose                                                                                                          | Tag                  |
| --- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | -------------------- |
| 1   | `AGENTS.md`                                      | Hub-and-spoke orchestration contract: delegation matrix, 4 pipelines, session types, completion promise protocol |                      |
| 2   | `.ai_ledger.md`                                  | Restart-safe state file: work queue, blockers, verification failures with Root Cause Hint, completion notes      | **[POST-IMPLEMENT]** |
| 3   | `.github/hooks/hooks.json`                       | Lifecycle hooks: PostToolUse type-check backpressure, Stop hook with Session-Type awareness                      | **[POST-IMPLEMENT]** |
| 4   | `.github/agents/orchestration-governor.agent.md` | Central orchestrator: pipeline selection, step supervision, mandatory delegation matrix                          |                      |
| 5   | `.github/commands/ralph-loop.prompt.md`          | Bounded autonomous loop: writes Session-Type, reads VerificationTarget, enforces completion promise              |                      |

> **Detailed reference**: For the full per-layer file catalog, model policy, Phase 2 enhancement tracker, and quick-reference tables, see [docs/solar-ralph-reference.md](docs/solar-ralph-reference.md).

---

## Applying to a New Repo — Step-by-Step

### Step 1: Scan Target Repository

Run the minimal setup scanner from the **root of your target repo**. This downloads ONLY what's needed to scan your project and fill `.github/solar-setup.md`.

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.ps1" -OutFile install.ps1; .\install.ps1; Remove-Item install.ps1
```

**macOS / Linux (Bash):**

```bash
curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.sh | bash
```

**What gets downloaded (5 files only):**

1. `.github/solar-setup.md` — Empty template for project configuration
2. `.github/agents/solar-bootstrap.agent.md` — Bootstrap agent (governance bypass)
3. `.github/prompts/solar-setup-scan-repo.prompt.md` — Repository scanner
4. `.github/instructions/solar.md` — SOLAR-specific instructions
5. `.github/solar.config.json` — Bootstrap mode configuration

**What is NOT downloaded:**

- All other prompts, agents, skills, hooks, guides, knowledge base (installed in Step 2)

> **Purpose:** Verify that the Solar Bootstrap agent can scan your repo WITHOUT being affected by existing `AGENTS.md` or `copilot-instructions.md` files.

**Run the repository scanner:**

```
/solar-setup-scan-repo
```

**Expected behavior:**

- Scanner detects: project name, tech stack (React/Vue/Express/etc.), commands (dev/test/build), folder paths, test framework
- Writes findings to `.github/solar-setup.md`
- Completes WITHOUT delegating to specialists or invoking pipelines
- Works correctly even if your repo already has `AGENTS.md` or `copilot-instructions.md`

**Review the output:**

- Open `.github/solar-setup.md` and verify detected values
- Correct any `NEEDS MANUAL INPUT` or `INFERRED:` entries
- Fix any misdetections

> **🔬 Governance Bypass Test:** If the scanner delegates to other agents or fails due to existing governance files, the Solar Bootstrap agent is NOT bypassing governance correctly. Stop and troubleshoot before proceeding to Step 2.

---

### Step 2: Install Full SOLAR Framework

Once the scan completes successfully and `.github/solar-setup.md` is filled, install the complete SOLAR framework:

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install-solar.ps1; .\install-solar.ps1; Remove-Item install-solar.ps1
```

**macOS / Linux (Bash):**

```bash
curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh | bash
```

**What gets downloaded (~52 files):**

- `AGENTS.md` — Orchestration contract
- All agent files (13 specialists, auditors, governor, architect, bootstrap)
- All skill files (13 skills)
- All setup prompts (core-config, agent-config, scaffold)
- Runtime commands (ralph-loop, audit-story)
- Hooks (hooks.json, stop.cjs, post-tool-use.cjs, user-prompt-submit.cjs)
- Guides (5 operator guides)
- Knowledge base (6 pattern guides)
- Verification artifacts folder

**Options:**

- Add `-Force` (PowerShell) or `--force` (Bash) to overwrite files that already exist
- Scripts are idempotent: skip files already present, report downloaded/skipped/failed

---

### Step 3: Apply Configuration to SOLAR Files

The `.github/solar-setup.md` file is already filled (from Step 1 scan). Now apply those values to all SOLAR files.

**3a.** Apply core configuration:

```
/solar-setup-core-config
```

**Updates:** `.github/instructions/solar.md`, `.github/hooks/hooks.json`, `.github/guides/solar-ralph-workflow.md`

**3b.** Apply agent and skill configuration:

```
/solar-setup-agent-config
```

**Updates:** 8 agent files, 6+ skill files, path-specific `.instructions.md` files

**3c.** Create project scaffolding:

```
/solar-setup-scaffold
```

**Creates:** `.ai_ledger.md`, 7 memory templates in `/memories/repo/`

Each command reports which files were updated and flags anything needing manual review.

### Step 3: Populate Repository Memory (Optional)

Memory templates were created by `/solar-setup-scaffold` in Step 2d. Optionally populate them with project-specific facts:

**Option A — Let Governor populate automatically:**
Skip this step. The Governor will populate memory files as needed during normal operation.

**Option B — Pre-populate with facts:**

```
@Orchestration-Governor explore the codebase and populate your memory with verified facts about architecture, commands, workflow, frontend, backend, security, and verification. Use templates from memories/repo/.
```

The Governor reads `/memories/repo/*.md` templates and fills them with project-specific facts.

**Memory files to populate:**

- `commands.md` — Build, test, dev, deploy commands
- `architecture.md` — Tech stack, folder structure, dependencies
- `workflow-facts.md` — Git conventions, branching, PR process
- `frontend-facts.md` — Frontend patterns, state management, routing
- `backend-facts.md` — Backend patterns, API design, data layer
- `security-facts.md` — Auth approach, secrets management, validation
- `verification-facts.md` — Test strategy, coverage requirements

**Important:** Memory files STAY in the repository. They are consumed by agents on every session. Do NOT delete them after population.

---

### Step 5: Verify the Hook

Run the Stop hook manually to confirm Session-Type detection works.

**PowerShell (Windows):**

```powershell
Set-Content .ai_ledger.md "Session-Type: chat"
# Confirm stop hook exits silently without blocking
```

**Bash (macOS/Linux):**

```bash
echo "Session-Type: chat" > .ai_ledger.md
# Confirm stop hook exits silently without blocking
```

Then test loop mode — update `.ai_ledger.md` to set `Session-Type: loop` and confirm the hook blocks exit until a `<promise>WORK_PACKAGE_COMPLETE</promise>` tag is written to the Completion Promise field.

### Step 6: Activate SOLAR

Once all POST-IMPLEMENT customizations are complete and the hook test passes, activate the system in `.github/solar.config.json`:

Change `"enabled": false` → `"enabled": true`:

```json
{
  "solar": {
    "enabled": true,
    "mode": "simple",
    "description": "SOLAR-Ralph system configuration"
  },
  ...
}
```

**Configuration options:**

- `solar.enabled` — Global on/off switch (overrides everything)
- `solar.mode` — Operating mode: `"simple"` (chat), `"loop"` (autonomous), `"plan"`, `"manual-test"`
- `hooks.enabled` — Global hook switch
- Each hook has `enabled` and `activeModes` fields for granular control

Then update `.ai_ledger.md`:

1. Set `Completion Promise: pending` (if not already set)
2. Remove the `<!-- TEMPLATE STATE: ... -->` comment at the top

Your ledger `Current Objective` section should look like:

```markdown
## Current Objective

- Pipeline: (none)
- Pipeline Stage: (none)
- Session-Type: chat
- VerificationTarget: (none)
- Completion Promise: pending
```

### Step 7: Run a Smoke Test Story

Pick a trivial task (e.g., "add a README badge") and execute it with `/ralph-loop` to verify the full pipeline runs end to end: Governor → Specialist → Test → Review → Close.

---

## Complete File Inventory

```
# Root contracts
AGENTS.md
.ai_ledger.md                                          [POST-IMPLEMENT]

# Agent definitions
.github/agents/orchestration-governor.agent.md
.github/agents/design-planning-architect.agent.md
.github/agents/bug-investigation-specialist.agent.md
.github/agents/frontend-implementation-specialist.agent.md     [POST-IMPLEMENT]
.github/agents/frontend-review-auditor.agent.md
.github/agents/frontend-test-specialist.agent.md               [POST-IMPLEMENT]
.github/agents/backend-implementation-specialist.agent.md      [POST-IMPLEMENT]
.github/agents/backend-review-auditor.agent.md
.github/agents/backend-test-specialist.agent.md                [POST-IMPLEMENT]
.github/agents/security-auditor.agent.md
.github/agents/docs-curator.agent.md                           [POST-IMPLEMENT]
.github/agents/release-readiness-specialist.agent.md
.github/agents/cache-external-integration-specialist.agent.md  [POST-IMPLEMENT]
.github/agents/solar-bootstrap.agent.md

# Hooks
.github/hooks/hooks.json                               [POST-IMPLEMENT]
.github/hooks/stop.cjs
.github/hooks/post-tool-use.cjs
.github/hooks/user-prompt-submit.cjs
.github/solar.config.json

# Skills
.github/skills/frontend-feature-implementation/SKILL.md        [POST-IMPLEMENT]
.github/skills/frontend-review/SKILL.md
.github/skills/frontend-testing/SKILL.md                       [POST-IMPLEMENT]
.github/skills/backend-feature-implementation/SKILL.md         [POST-IMPLEMENT]
.github/skills/backend-review/SKILL.md
.github/skills/backend-testing/SKILL.md                        [POST-IMPLEMENT]
.github/skills/story-execution/SKILL.md
.github/skills/doc-sync/SKILL.md
.github/skills/memory-curation/SKILL.md
.github/skills/memory-verification/SKILL.md
.github/skills/recursive-remediation/SKILL.md
.github/skills/release-governance/SKILL.md
.github/skills/browser-reproduction/SKILL.md
.github/skills/external-integration-operations/SKILL.md

# Commands
.github/commands/ralph-loop.prompt.md
.github/commands/audit-story.prompt.md
.github/commands/solar-setup-scan-repo.prompt.md
.github/commands/solar-setup-core-config.prompt.md
.github/commands/solar-setup-agent-config.prompt.md
.github/commands/solar-enter-bootstrap.prompt.md
.github/commands/solar-exit-bootstrap.prompt.md

# Setup config (fill this first, then run /solar-setup-core-config)
.github/solar-setup.md                                 [POST-IMPLEMENT]

# Path-specific instructions
apps/frontend/.instructions.md  (or <your-app>/.instructions.md) [POST-IMPLEMENT]
apps/backend/.instructions.md   (or <your-app>/.instructions.md) [POST-IMPLEMENT]

# Repo memory (all must be created fresh per repo)
/memories/repo/commands.md                            [POST-IMPLEMENT]
/memories/repo/architecture.md                        [POST-IMPLEMENT]
/memories/repo/workflow-facts.md                      [POST-IMPLEMENT]
/memories/repo/frontend-facts.md                      [POST-IMPLEMENT]
/memories/repo/backend-facts.md                       [POST-IMPLEMENT]
/memories/repo/security-facts.md                      [POST-IMPLEMENT]
/memories/repo/verification-facts.md                  [POST-IMPLEMENT]

# Copilot / IDE config
.github/copilot-instructions.md                       [POST-IMPLEMENT]
.vscode/mcp.json                                      [POST-IMPLEMENT]
.vscode/settings.json                                 [POST-IMPLEMENT]

# Verification artifacts directory
verification-artifacts/README.md
verification-artifacts/.gitkeep

# Operator guides
.github/guides/solar-ralph-workflow.md                [POST-IMPLEMENT]
.github/guides/agent-operations-guide.md
.github/guides/memory-governance-guide.md
.github/guides/bootstrap-mode-guide.md
.github/guides/mcp-operations-guide.md

# Knowledge base
docs/knowledge-base/agent-orchestration-patterns.md
docs/knowledge-base/adversarial-auditing-patterns.md
docs/knowledge-base/recursive-refinement-patterns.md
docs/knowledge-base/agent-memory-governance.md
docs/knowledge-base/connected-agent-topologies.md
docs/knowledge-base/mcp-integration-patterns.md
```

**Total files: 57**
**Universal (copy as-is): 35**
**Post-implement (must customize): 21**

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

### Step 1: Install SOLAR Files

Run the installer script from the **root of your target repo**. It downloads all required files from GitHub — no need to clone the template repo.

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install-solar.ps1; .\install-solar.ps1; Remove-Item install-solar.ps1
```

**macOS / Linux (Bash):**

```bash
curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh | bash
```

**Options:**

- Add `-Force` (PowerShell) or `--force` (Bash) to overwrite files that already exist.
- The scripts are idempotent by default: they skip files already present and report what was downloaded, skipped, or failed.

> **What gets downloaded:** All agents (including `solar-bootstrap`), skills, commands (including bootstrap mode toggles), hooks, operator guides (including bootstrap mode guide), verification artifacts, `solar-setup.md`, `.ai_ledger.md`, `AGENTS.md`, and repo memory scaffolding templates.
>
> **What is NOT downloaded** (intentionally excluded):
>
> - `docs/research/` — template development tracking only
> - `.vscode/mcp.json` / `.vscode/settings.json` — configure manually (see Layer 9)
> - `SOLAR-Ralph-implementation-guideline.md` — stays in the template repo
> - `README.md` — write your own

> **Prefer manual copy?** See the [Complete File Inventory](#complete-file-inventory) section for the full per-file list.

### Step 2: Fill in the Setup Config and Apply

All `[POST-IMPLEMENT]` customizations are consolidated into a single file: `.github/solar-setup.md`.

**Option A — Auto-fill (recommended):** Let the bootstrap agent scan the codebase and fill in the values:

```
@solar-bootstrap /solar-setup-scan-repo
```

> **Important:** Run this with the `@solar-bootstrap` agent to ensure governance isolation. The bootstrap agent bypasses all SOLAR rules (AGENTS.md, copilot-instructions.md, hooks) so setup commands can configure the system without interference from the rules they're establishing. See [docs/guides/bootstrap-mode-guide.md](docs/guides/bootstrap-mode-guide.md) for details.

The agent detects your stack, commands, folder paths, and conventions from existing project files and writes them into `solar-setup.md`. Review the output and correct any fields marked `NEEDS MANUAL INPUT`.

**Option B — Manual fill:** Open `.github/solar-setup.md` directly and fill in every value yourself (project name, stack, commands, folder paths, git conventions).

> **Note for `copilot-instructions.md`:** If your repo already has this file, do **not** replace it — merge instead. Copy the "SOLAR-Ralph Operating Overlay" subsection into your existing Workflows section. The setup agent handles new repos automatically; for existing files, merge manually after the agent runs.

**2b.** Apply values to core SOLAR files (copilot-instructions, hooks, workflow guide):

```
@solar-bootstrap /solar-setup-core-config
```

**2c.** Apply values to all agent, skill, and path instruction files:

```
@solar-bootstrap /solar-setup-agent-config
```

> **Important:** Run both with the **default Copilot agent** (no `@` prefix). Run them in order -- 2b first, then 2c.

Each command reports which files were updated and flags anything needing manual review.

> The detailed per-file customization reference is in the [Complete File Inventory](#complete-file-inventory) section below if you prefer to customize files manually.

### Step 3: Populate Repo Memory

**Workflow:**

1. Run the Orchestration Governor prompt below — it will scan your codebase and fill in each file with verified facts about your repo.
2. Copilot reads the filled files and stores the content internally as repo-scoped memory.
3. Once Copilot has ingested them, delete the `memories/repo/` folder from git — they are not needed at runtime and the live memory is managed by Copilot internally.

Run the Orchestration Governor in `chat` mode with the prompt:

```
@Orchestration-Governor explore the codebase and populate your memory with verified facts about architecture, commands, workflow, frontend, backend, security, and verification use templates from memories/repo/.
```

Files to populate then delete:

```
/memories/repo/commands.md
/memories/repo/architecture.md
/memories/repo/workflow-facts.md
/memories/repo/frontend-facts.md
/memories/repo/backend-facts.md
/memories/repo/security-facts.md
/memories/repo/verification-facts.md
```

### Step 4: Verify the Hook

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

### Step 5: Activate SOLAR

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

### Step 6: Run a Smoke Test Story

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

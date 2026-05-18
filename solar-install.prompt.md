---
description: Install SOLAR-Ralph into any repository — one prompt, full scaffold, no extra downloads needed
---

# SOLAR-Ralph Installation

You are installing the SOLAR-Ralph agent harness into this repository.
SOLAR-Ralph is a 5-layer governance system (Specialist / Orchestrator / Ledger / Adversarial / Ralph Loop) that turns agent chat into bounded, verifiable, multi-agent pipelines on GitHub Copilot.

**Layer meanings:** S = specialist agents (one per dev stage) · O = orchestration governor · L = ledger (shared state) · A = adversarial audit (a Governor dispatch rule — at VERIFY stage, Governor picks a non-author specialist to challenge the previous agent's output) · R = Ralph loop (verification artifacts + bounded iteration). Hooks are infrastructure support that share gate-enforcement workload with the Governor — they are not the adversarial layer.

**SOLAR's scope:** highest-quality code changes. Every task — whether implementing a feature, writing a test, or updating a doc — goes through the same bounded cycle: scan → plan/design → execute → verify → exit. Release, deployment, and CI/CD are outside SOLAR's scope and belong in user-defined workflows.

Follow every step below in order. Do not skip steps. Do not commit.

---

## Step 1 — Pre-flight: Gather Context

### 1A — MCP Check

Use the `vscode_askQuestions` tool to ask:

> **"Is the Fetch MCP tool available in this environment?"**
>
> - `available` — it is enabled and working
> - `not enabled` — it is allowed but not yet enabled
> - `restricted` — it is blocked by policy or environment

**If user selects `available`:**

- Fetch the current VS Code Copilot agent/prompt format directly (two fetches):
  - **Agents and prompts format**: `https://code.visualstudio.com/docs/copilot/customization/custom-agents` — note current frontmatter field names and tool-set names
  - **Hooks format**: `https://code.visualstudio.com/docs/copilot/customization/hooks` — note current field names and output shapes
- If either fetch fails (MCP blocked or returns empty): fall back to the embedded YAML skeletons in Step 5B as the authoritative format reference — do NOT attempt a keyword search fallback.
- Use the fetched formats when generating all files.
- Print: `MCP fetch available — using latest platform format as of {today's date}`

**If user selects `not enabled`:**

Use `vscode_askQuestions` to ask a follow-up:

> **"Have you enabled the Fetch MCP tool yet?"**
>
> - `yes, just enabled` — proceed
> - `not yet` — show instructions below, then wait

If `not yet`: print the following instructions and pause:

```
To enable the Fetch MCP tool in VS Code:
1. Open Settings (Ctrl+, or Cmd+,)
2. Search for "MCP" or open your settings.json
3. Add or enable the fetch server entry:
   "mcp": {
     "servers": {
       "fetch": {
         "command": "uvx",
         "args": ["mcp-server-fetch"]
       }
     }
   }
4. Reload the window (Ctrl+Shift+P → "Developer: Reload Window")
5. Re-run this prompt after enabling.
```

Do not proceed until the user confirms fetch is enabled. When they confirm → treat as `available` and continue from the fetch step above.

**If user selects `restricted`:**

- Do not attempt any fetch calls
- Print: `MCP fetch restricted — using built-in format knowledge`
- Proceed with built-in format knowledge for all generated files

---

## Step 2 — Clarifying Questions

Use the `vscode_askQuestions` tool to collect the following before generating any files. Do not free-text ask — pass all questions in a single tool call.

Questions:

1. **Target stack** — "What is your target stack?" (examples: React + TypeScript, Node.js + Express, Python / FastAPI, Go, full-stack monorepo — or type `generic` for stack-agnostic stubs)
2. **Test runner** — "What test runner do you use?" (examples: Jest, Vitest, Pytest, Go test — or `skip`)
3. **Existing agent / AI system** — "Does this repo already have an agent or AI instruction system (e.g. existing AGENTS.md, LangChain config, custom instructions files)?" (yes / no)
4. **Optional components** — "Which optional components do you want installed?" (multi-select: `learning system` / `session logging` / `stack-specific specialists` / `all` / `none`)

Wait for all answers before continuing. Store as:

- `{STACK}` — if user typed "skip" or "generic", set `{STACK} = generic`
- `{TEST_RUNNER}` — if "skip", set `{TEST_RUNNER} = unknown`
- `{HAS_EXISTING_SYSTEM}` — yes / no
- `{OPTIONAL_COMPONENTS}` — store answer only; optional components are not installed in this base installation

---

## Step 3 — Repo Sweep

Scan the repository for existing structure. Run all scans before generating any files — findings go into AGENTS.md and the ledger template.

**Scan targets (run in parallel):**

- `README.md` (root) → note project name, description, any stack hints
- `docs/` → list all `.md` files; note any architecture, conventions, API spec, guides
- `.github/instructions/` → list all `*.instructions.md`; note names and `applyTo` values
- `.github/agents/` → list any existing `.agent.md` files
- `.github/skills/` → list any existing skill folders
- `.github/AGENTS.md` → check if exists (conflict — see Step 4 Conflict Check)
- `.github/copilot-instructions.md` → check if exists (conflict)
- `package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml` → cross-check detected stack against `{STACK}`; use the `vscode_askQuestions` to ask if user want to update `{STACK}` if "generic" and a stack is detected

**After sweep, build a Repo Context block (stored for AGENTS.md Section 2):**

```
Repo: {project name from README or folder name}
Stack confirmed: {STACK}  |  Test runner: {TEST_RUNNER}
Existing instructions: {file list or none}
Existing agent files: {file list or none}
Existing docs: {doc list or none}
```

If `{HAS_EXISTING_SYSTEM}` = yes: also scan for LangChain, CrewAI, AutoGen, or similar config files; add them to the block with note: "existing system — integrate manually".

---

## Step 4 — Conflict Check

Before creating any file, check what was found in the sweep:

| File                              | If exists → action                                                                                                                  |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `.github/AGENTS.md`               | Create `.github/AGENTS.patch.md` with new content; tell user "AGENTS.md already exists — review AGENTS.patch.md and merge manually" |
| `.github/copilot-instructions.md` | Create `.github/copilot-instructions.patch.md`; same message                                                                        |
| `.github/agents/*.agent.md` (any) | Ask: "Agent {name} already exists. Overwrite? (y / n / skip-all)" — wait for answer before writing                                  |
| `.github/skills/*/SKILL.md` (any) | Same pattern as agents                                                                                                              |

Never silently overwrite. If user answers "skip-all", skip all existing files of that type and continue.

---

> **Formatting rule for all generated files:** When writing body text for agent, skill, ledger, or protocol files, preserve all markdown formatting exactly:
>
> - File paths and tool names enclosed in backticks: `.github/.ai_ledger.md`, `replace_string_in_file`
> - Key terms and stage names in **bold**: **TASK_COMPLETE**, **Implement**, **REJECTED**
> - Section headings (`##`, `###`) must remain as headings — do NOT flatten to plain text
> - `<constraints>`, `<tier_restrictions>`, `<identity>` XML tags must be present verbatim
>
> Apply this rule to every file generated in Steps 5A–5I.

---

## Step 5 — Generate Files

Create the following files. Use `{STACK}`, `{TEST_RUNNER}`, and the Repo Context block from Step 3 to tailor content.

### 5A — Core manifest

**`.github/AGENTS.md`** — Pure registry manifest. Content must be: **registry tables + Ledger Template + Config Toggles only**. No behavioral paragraphs (all orchestrator behavior lives in `solar.prompt.md` and `.agent.md` files).

Sections to generate (in this order):

1. **Section Index** — HTML comment block at the very top of the file (before any headings) listing each section with its starting line number. Format:

   ```
   <!-- SOLAR Section Index (update line numbers when file changes):
   §1 What is this file      — L[N]
   §2 Repository Context     — L[N]
   §3 Agent Registry         — L[N]
   §4 Skill Index            — L[N]
   §5 Playbook Index         — L[N]
   §6 Hook Configuration     — L[N]
   §7 Ledger Template        — L[N]
   §8 Config Toggles         — L[N]
   -->
   ```

   After generating the file, count actual line numbers and fill them in.

2. **What is this file** (1 paragraph — SOLAR-Ralph + this repo's name from sweep)
3. **Repository Context** (the Repo Context block from Step 3 — existing docs, instructions, and agent files found in sweep)
4. **Agent Registry** (use §3 skeleton below)
5. **Skill Index** (use §4 skeleton below)
6. **Playbook Index** (use §5 skeleton below)
7. **Hook Configuration** (use §6 skeleton below)
8. **Ledger Template** (verbatim from Step 5C, then append §7 archive note from skeleton below)
9. **Config Toggles** (use §8 skeleton below)

Do NOT include a "Usage" or behavioral paragraph section. Behavioral guidance lives in `solar.prompt.md` only.

**AGENTS.md §3–§8 verbatim skeletons (Tier 2 — copy verbatim; replace `[FILL IN]` tokens only):**

Naming note: `[FILL IN: X Specialist name]` → display name, e.g. `React-Ts Implementation Specialist` for `{STACK}`=react-ts, `Implementation Specialist` for generic. Loads Skill slug follows same pattern: `react-ts-implementation` or `implementation`.

**§3 Agent Registry:**

```
## §3 Agent Registry

| Name                                      | Dev Stage     | Role                                                                               | Loads Skill                            | Accepts                    | Produces                               | Optional |
| ----------------------------------------- | ------------- | ---------------------------------------------------------------------------------- | -------------------------------------- | -------------------------- | -------------------------------------- | -------- |
| Orchestration Governor                    | —             | Reads ledger stage → dispatches matching agent; owns exit decisions                | built-in                               | user prompt / ledger state | Work Queue row + Decisions Log entries | No       |
| Data Collector Specialist                 | Scan          | Gathers files and produces context manifest                                        | `data-collection`                      | task description           | `{task-id}-scan.json`                  | No       |
| Design Planning Architect                 | Plan + Design | Solution design, decomposition, tradeoff analysis                                  | `design-planning`                      | `{task-id}-scan.json`      | `{task-id}-design.json`                | No       |
| [FILL IN: Implementation Specialist name] | Implement     | Code changes scoped to task                                                        | `[FILL IN: implementation skill slug]` | `{task-id}-design.json`    | `{task-id}-impl.json`                  | No       |
| [FILL IN: Test Specialist name]           | Test          | Writes or repairs tests for the task output                                        | `[FILL IN: testing skill slug]`        | `{task-id}-impl.json`      | `{task-id}-test.json`                  | No       |
| [FILL IN: Review Auditor name]            | VERIFY role   | Adversarial audit — dispatched by Governor at VERIFY step, not as a pipeline stage | `[FILL IN: review skill slug]`         | any artifact               | `{task-id}-verify.json`                | No       |
| Docs Curator                              | Document      | Keeps docs aligned with code changes                                               | `doc-sync`                             | any artifact               | `{task-id}-docs.json`                  | No       |

**Agent Registry is a lookup table.** The Governor selects agents by Dev Stage role — row order does not control execution sequence. Execution sequence is defined by the Playbook SKILL.md.

**VERIFY dispatch**: no dedicated adversarial agent row. At the VERIFY step the Governor looks up the auditor role from this registry by domain match: code output → role `review-auditor`; design/docs output → role `design-planning-architect`. Do NOT hardcode stack-specific names in `solar.prompt.md`.
```

**§4 Skill Index:**

```
## §4 Skill Index

| Name                             | Dev Stage     | Purpose                                                                 | Path                                            | Optional |
| -------------------------------- | ------------- | ----------------------------------------------------------------------- | ----------------------------------------------- | -------- |
| `data-collection`                | Scan          | Gather files, run searches, produce context manifest                    | `.github/skills/data-collection/SKILL.md`       | No       |
| `design-planning`                | Plan + Design | Solution design, architecture-fit, task decomposition                   | `.github/skills/design-planning/SKILL.md`       | No       |
| `[FILL IN: implementation slug]` | Implement     | Code changes per task                                                   | `.github/skills/[FILL IN: folder]/SKILL.md`     | No       |
| `[FILL IN: testing slug]`        | Test          | Add or repair tests — ⚠ requires stack-specific runner setup before use | `.github/skills/[FILL IN: folder]/SKILL.md`     | No       |
| `[FILL IN: review slug]`         | VERIFY role   | Audit output — runs at VERIFY step, not as pipeline stage               | `.github/skills/[FILL IN: folder]/SKILL.md`     | No       |
| `doc-sync`                       | Document      | Sync docs after code or process changes                                 | `.github/skills/doc-sync/SKILL.md`              | No       |
| `recursive-remediation`          | Remediation   | Bounded repair loop for failed tests or review findings                 | `.github/skills/recursive-remediation/SKILL.md` | No       |
```

**§5 Playbook Index:**

```
## §5 Playbook Index

| Name                | Description                                                        | Path                                | Trigger                                       |
| ------------------- | ------------------------------------------------------------------ | ----------------------------------- | --------------------------------------------- |
| `implement-feature` | Triggered when user asks to implement, build, or add a feature     | `.github/skills/implement-feature/` | User prompt contains: implement / build / add |
| `bug-fix`           | Triggered when user asks to fix, debug, or resolve a bug or error  | `.github/skills/bug-fix/`           | User prompt contains: fix / debug / bug       |
| `create-doc`        | Triggered when user asks to write, create, or update documentation | `.github/skills/create-doc/`        | User prompt contains: write / create / doc    |

SOLAR-managed ordered step sequences the orchestrator follows inline. Custom playbooks: add a SKILL.md under `.github/skills/` and register a row here via `solar-registry-update`.
```

**§6 Hook Configuration:**

```
## §6 Hook Configuration

| Hook            | Trigger       | Script                            | Purpose                                                                        |
| --------------- | ------------- | --------------------------------- | ------------------------------------------------------------------------------ |
| `post-tool-use` | `PostToolUse` | `.github/hooks/post-tool-use.cjs` | Write-op guard → emit `ADVERSARIAL_VERIFY_REQUIRED` when ledger stage = VERIFY |
| `stop`          | `Stop`        | `.github/hooks/stop.cjs`          | Block premature exit when `Completion Promise: pending` in ledger              |

Optional hooks (add as needed): `pre-tool-use`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`. Register each in `.github/hooks/hooks.json`.

All hooks read `hooks` from `solar.config.json`. Set `false` to disable globally.
```

**§7 Archive note (append on the line after the Ledger Template closing code fence):**

```
> **Archive note**: At TASK_COMPLETE, the Governor copies this ledger to `verification-artifacts/{YYYYMMDD}-{task-id}-ledger-archive.md`, then resets `.ai_ledger.md` to the template defaults above. See `solar.prompt.md` step 4.
```

**§8 Config Toggles:**

```
## §8 Config Toggles

| Toggle           | Default | Effect                                                |
| ---------------- | ------- | ----------------------------------------------------- |
| `adversarial`    | `true`  | Adversarial audit gate active at VERIFY stage         |
| `learning`       | `false` | Learning system active — agents write to `learnings/` |
| `logging`        | `false` | Session logging active — hook writes to `logs/`       |
| `human_approval` | `true`  | Governor waits for user confirmation before dispatch  |
| `hooks`          | `true`  | All hooks active — set `false` to disable globally    |
```

**`.github/copilot-instructions.md`** — SOLAR system-wide overlay:

```
This repository uses the SOLAR-Ralph agent harness. Before every task:
1. Read .github/AGENTS.md — Agent Registry, Skill Index, ledger template, hook config, Repository Context.
2. Read .github/.ai_ledger.md (if it exists) — understand current task state and stage.
3. Orchestrator: read ledger stage → consult Agent Registry Dev Stage column → dispatch matching agent.
4. Agent: read task type → consult Skill Index → load the matching SKILL.md before acting.
5. All materials go in verification-artifacts/ only. TASK_COMPLETE requires adversarial audit: Governor dispatches a non-author specialist (domain-matched, not the artifact author) to verify output before closing.
```

**`.github/solar.config.json`**:

```json
{
  "adversarial": true,
  "learning": false,
  "logging": false,
  "human_approval": true,
  "hooks": true
}
```

### 5B — Agents (dev lifecycle coverage)

Generate each agent as a `.agent.md` file with YAML frontmatter. Each agent must be registered in AGENTS.md Agent Registry with its Dev Stage and Loads Skill columns filled.

**Orchestration Governor** — `.github/agents/orchestration-governor.agent.md`

Governor body (add below the YAML frontmatter skeleton):

```
Follow `.github/prompts/solar.prompt.md` for all task management — startup, resume, dispatch, gate checks, and TASK_COMPLETE.
```

**Required specialist agents (always generate, verbatim YAML skeletons, tailored to `{STACK}`):**

**Naming rules:**

- **If `{STACK}` = generic** — plain names, no prefix:
  - Files: `implementation-specialist.agent.md`, `test-specialist.agent.md`, `review-auditor.agent.md`, `docs-curator.agent.md`, `data-collector-specialist.agent.md`, `design-planning-architect.agent.md`
  - Skill references: `implementation`, `testing`, `review`, `doc-sync`, `data-collection`, `design-planning`
- **If `{STACK}` ≠ generic** — stack-prefixed names:
  - Files: `{stack}-implementation-specialist.agent.md`, `{stack}-test-specialist.agent.md`, `{stack}-review-auditor.agent.md`
  - Skill references: `{stack}-implementation`, `{stack}-testing`, `{stack}-review`
  - Role-agnostic files keep plain names: `data-collector-specialist.agent.md`, `design-planning-architect.agent.md`, `docs-curator.agent.md`

| Dev Stage     | File                                         | Loads Skill                                             |
| ------------- | -------------------------------------------- | ------------------------------------------------------- |
| Scan          | `data-collector-specialist.agent.md`         | `data-collection`                                       |
| Plan + Design | `design-planning-architect.agent.md`         | `design-planning`                                       |
| Implement     | `{stack}-implementation-specialist.agent.md` | `{stack}-implementation` or `implementation` if generic |
| Test          | `{stack}-test-specialist.agent.md`           | `{stack}-testing` or `testing` if generic               |
| Document      | `docs-curator.agent.md`                      | `doc-sync`                                              |
| VERIFY role   | `{stack}-review-auditor.agent.md`            | `{stack}-review` or `review` if generic                 |

**Verbatim YAML skeleton for each agent (use exactly — only replace `[FILL IN]` tokens):**

```yaml
# Orchestration Governor — .github/agents/orchestration-governor.agent.md
---
name: Orchestration Governor
description: SOLAR-Ralph orchestrator — reads registry, dispatches specialists, enforces gates, manages the ledger. Always runs inline, never forked.
model: Claude Sonnet 4.6 (copilot)
tools: [vscode/askQuestions, agent/runSubagent, read, search, edit]
user-invocable: true
---
```

```yaml
# Data Collector — .github/agents/data-collector-specialist.agent.md
---
name: Data Collector Specialist
description: Handles the Scan stage — gathers task context, repo state, and input findings.
model: Claude Haiku 4.5 (copilot)
tools: [read, search, edit]
user-invocable: false
---
```

```yaml
# Design Planning — .github/agents/design-planning-architect.agent.md
---
name: Design Planning Architect
description: Handles the Plan + Design stage — produces architecture or design plans.
model: Claude Sonnet 4.6 (copilot)
tools: [read, search, edit]
user-invocable: false
---
```

```yaml
# Implementation — .github/agents/{stack}-implementation-specialist.agent.md
---
name: [FILL IN: "{Stack} Implementation Specialist" or "Implementation Specialist" if generic]
description: Handles the Implement stage — writes [FILL IN: {stack}] code changes.
model: Claude Haiku 4.5 (copilot)
tools: [read, search, edit, execute, todo]
user-invocable: false
---
```

```yaml
# Test — .github/agents/{stack}-test-specialist.agent.md
---
name: [FILL IN: "{Stack} Test Specialist" or "Test Specialist" if generic]
description: Handles the Test stage — writes and runs tests for [FILL IN: {stack}]. Requires stack-specific test runner configuration before use.
model: Claude Haiku 4.5 (copilot)
tools: [read, search, edit, execute, todo]
user-invocable: false
---
```

```yaml
# Review Auditor — .github/agents/{stack}-review-auditor.agent.md
---
name: [FILL IN: "{Stack} Review Auditor" or "Review Auditor" if generic]
description: Handles the VERIFY role — adversarial audit of specialist output. Dispatched by Governor at VERIFY step, not as a pipeline stage.
model: Claude Sonnet 4.6 (copilot)
tools: [read, search, edit]
user-invocable: false
---
```

```yaml
# Docs Curator — .github/agents/docs-curator.agent.md
---
name: Docs Curator
description: Handles the Document stage — syncs and updates documentation.
model: Claude Sonnet 4.5 (copilot)
tools: [read, search, edit]
user-invocable: false
---
```

**Post-install note to print at end of Step 5:**

> Models assigned: Orchestrator + Design/Review = `Claude Sonnet 4.6 (copilot)`; Docs = `Claude Sonnet 4.5 (copilot)`; Scan/Implement/Test = `Claude Haiku 4.5 (copilot)`. To change: edit the `model:` field in each `.agent.md` file.

**Governor dispatch protocol — dispatch prompt MUST contain ONLY:**

1. 2–3 sentence task description
2. Schema type and input file path(s) from Materials
3. Result file path to write: `verification-artifacts/{task-id}-{stage}-result.json`
4. Return instruction verbatim: `"Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."`
5. Skill path: `"Load and follow: .github/skills/{skill-name}/SKILL.md"`

Never embed raw file contents or ledger history in the dispatch prompt.

**Verbatim specialist stub template (use for every specialist agent body — replace `[FILL IN]` tokens only):**

```markdown
---
name: [FILL IN: agent name]
description: [FILL IN: one sentence — dev stage + what it does]
model: [FILL IN: model from YAML skeleton above]
tools: [FILL IN: tools from YAML skeleton above]
user-invocable: false
---

Handles the **[FILL IN: Dev Stage]** stage. [FILL IN: one sentence what it does.] [FILL IN: one sentence what it does NOT do.]

Before acting: load the SKILL.md path provided in the dispatch prompt → follow skill steps exactly.

<constraints>
- Maximum 10 file reads per task. If more needed: append `BLOCKED: task exceeds scope — ESCALATION_REQUIRED` to Decisions Log and return to Governor without acting.
- Do not expand scope beyond the current Work Package in `.github/.ai_ledger.md`. Discovered out-of-scope work: append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log only.
- Do not self-certify output. Requires non-author verification before emitting TASK_COMPLETE.
- Return format: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only, no raw file contents.}`
[FILL IN for Test Specialist only: - Requires stack-specific test runner configuration. Before dispatching: verify `tools:` includes the correct executor and SKILL.md has runner-specific steps.]
</constraints>

<tier_restrictions>
This agent handles the **[FILL IN: Dev Stage]** stage only. It does NOT:

- Perform work belonging to other dev stages — [FILL IN: list all dev stage names EXCEPT this agent's own stage, e.g. for Implement agent: scan, design, test, review, and document are separate roles].
- Self-escalate to TASK_COMPLETE — that is the Governor’s gate decision.
- Expand scope for discovered work — append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log instead.
  </tier_restrictions>

<contract>
**Dev Stage**: [FILL IN: Scan | Plan + Design | Implement | Test | Document]
**Loads Skill**: `[FILL IN: skill-name]` — path: `.github/skills/[FILL IN: skill-name]/SKILL.md`
**Accepts**: `[FILL IN: e.g. verification-artifacts/{task-id}-input.json for Scan, verification-artifacts/{task-id}-scan.json for Plan + Design, verification-artifacts/{task-id}-design.json for Implement, verification-artifacts/{task-id}-impl.json for Test, any artifact for Review/Document]` (status: ready) + ledger stage=ASSIGNED + exit_criteria defined
**Produces**: `verification-artifacts/{task-id}-[FILL IN: type].json`
**Does NOT start if**: input material not ready OR exit_criteria empty → emit MATERIAL_INSUFFICIENT to orchestrator
**Cannot self-certify**: requires non-author verification before emitting TASK_COMPLETE
**Return format**: Return EXACTLY: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only. No raw file contents.}`
</contract>
```

### 5C — Ledger template

**`.github/.ai_ledger.md`**:

```markdown
## Objective

[one sentence]

## Work Queue

| id  | task | agent | status | stage | iteration |
| --- | ---- | ----- | ------ | ----- | --------- |

## Loop State

| max_iterations | current | exit_criteria               |
| -------------- | ------- | --------------------------- |
| 5              | 0       | [define before loop starts] |

Completion Promise: none

## Materials

<!-- Governor-owned index: tracks file paths + status only. Contents live in the files themselves. -->

| role   | path                                         | schema   | status  |
| ------ | -------------------------------------------- | -------- | ------- |
| input  | verification-artifacts/[task-id]-input.json  | [schema] | pending |
| output | verification-artifacts/[task-id]-result.json | [schema] | empty   |

## Decisions Log

<!-- append-only; format: YYYY-MM-DD HH:MM UTC: <decision summary> -->
```

### 5D — Hooks (infrastructure support)

- Hooks share gate-enforcement workload with the Governor — stateless event listeners, not agents, not the adversarial layer.
- Before generating: fetch `https://code.visualstudio.com/docs/copilot/customization/hooks` for current field names and output shapes. If fetch fails: use built-in knowledge and note `hooks schema unverified — using built-in knowledge`.
- Hooks are a VS Code Preview feature — schema may change between releases; use fetched docs as authoritative reference.
- Toggle: `"hooks": false` in `.github/solar.config.json` disables all hooks globally.

---

**`.github/hooks/hooks.json`** — VS Code agent hook registration:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "node .github/hooks/post-tool-use.cjs",
        "timeout": 20
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "node .github/hooks/stop.cjs",
        "timeout": 10
      }
    ]
  }
}
```

---

**`.github/hooks/common.cjs`** — shared utilities (required by all hook scripts):

```js
"use strict";
const fs = require("fs"),
  path = require("path");
function loadConfig() {
  try {
    return JSON.parse(
      fs.readFileSync(
        path.resolve(__dirname, "..", "solar.config.json"),
        "utf8",
      ),
    );
  } catch {
    return null;
  }
}
function readLedger() {
  try {
    return fs.readFileSync(
      path.resolve(__dirname, "..", ".ai_ledger.md"),
      "utf8",
    );
  } catch {
    return "";
  }
}
// Hooks are on when config.hooks is absent or true; off only when explicitly false.
function isSolarActive(config) {
  return config?.hooks !== false;
}
module.exports = { loadConfig, readLedger, isSolarActive };
```

---

**`.github/hooks/post-tool-use.cjs`** — write-op guard; injects ADVERSARIAL_VERIFY_REQUIRED when ledger is in VERIFY stage.

Hook scripts are standalone Node.js child processes. Input arrives via stdin as JSON; output is JSON written to stdout before `process.exit(0)`. Exit code `2` blocks and feeds stderr to the model.

```js
"use strict";
const common = require("./common.cjs");
let raw = "";
process.stdin.on("data", (c) => {
  raw += c;
});
process.stdin.on("end", () => {
  const config = common.loadConfig();
  if (!config || !common.isSolarActive(config)) process.exit(0);
  const input = (() => {
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  })();
  // VS Code tool names use camelCase (e.g. editFiles, createFile). Match write ops:
  const writePattern = /edit|creat|insert|delet|writ|replac/i;
  if (!writePattern.test(input.tool_name || "")) process.exit(0);
  const ledger = common.readLedger();
  if (/\|\s*VERIFY\s*\|/.test(ledger)) {
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext:
            "ADVERSARIAL_VERIFY_REQUIRED: ledger stage=VERIFY — Governor must dispatch a non-author specialist for adversarial audit before proceeding.",
        },
      }),
    );
  }
  process.exit(0);
});
```

---

**`.github/hooks/stop.cjs`** — loop-continuation guard; blocks premature exit when Completion Promise is pending or Verification failed.

Always check `stop_hook_active` from stdin JSON to prevent infinite loop.

```js
"use strict";
const common = require("./common.cjs");
let raw = "";
process.stdin.on("data", (c) => {
  raw += c;
});
process.stdin.on("end", () => {
  const config = common.loadConfig();
  if (!config || !common.isSolarActive(config)) process.exit(0);
  const input = (() => {
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  })();
  if (input.stop_hook_active) process.exit(0); // prevent infinite loop
  const ledger = common.readLedger();
  const hasPending = /Completion Promise:\s*pending/i.test(ledger);
  const hasFail = /Verification:\s*FAIL/i.test(ledger);
  // Only block if there is an active Work Queue task — do not block casual sessions.
  const hasActiveTask = /\|\s*(PENDING|IN_PROGRESS|ASSIGNED)\s*\|/i.test(
    ledger,
  );
  if ((hasPending || hasFail) && hasActiveTask) {
    const reason = hasFail
      ? "Verification FAIL in ledger — fix failures before stopping."
      : "Completion Promise pending — valid values: WORK_PACKAGE_COMPLETE, WORK_PACKAGE_BLOCKED, ESCALATION_REQUIRED.";
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "Stop",
          decision: "block",
          reason,
        },
      }),
    );
  }
  process.exit(0);
});
```

- Config: `"hooks": true` is the default. Set `"hooks": false` in `solar.config.json` to disable all hooks globally.
- Optional hooks (not generated by default): `pre-tool-use`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`. For each: create the `.cjs` script in `.github/hooks/` and register it in `hooks.json` following the same pattern.

### 5E — Instructions (minimal)

**`.github/instructions/solar.instructions.md`** — always generate:

```
---
applyTo: "**"
---
SOLAR-Ralph is active. Before every task: read .github/AGENTS.md.
Orchestrator: ledger stage → Agent Registry Dev Stage column → dispatch matching agent.
Agent: task type → Skill Index → load matching SKILL.md before acting.
All materials go in verification-artifacts/. TASK_COMPLETE requires adversarial audit: Governor dispatches a non-author specialist (domain-matched, not the artifact author) to verify output before closing.

## Communication Discipline

Work silent, signal only. All SOLAR agents minimize token output during execution.

Prohibited: "I will now read the file..." / "Let me check..." / "I understand..." / summarizing what you just did / paragraph-form status updates.

Three permitted outputs:
1. Signals — one-line stage indicators only (from your identity table)
2. Blockers — append `BLOCKED: <one-line reason>` to Decisions Log in `.github/.ai_ledger.md`
3. Artifacts — the final deliverable (code changes, design doc, handoff payload)

Do not narrate tool calls. Do not announce intent. Do not confirm routine actions in prose.
```

**`.github/instructions/{stack}.instructions.md`** — one stack file based on `{STACK}` and `{TEST_RUNNER}`:

- If `{STACK}` ≠ generic: generate a minimal instruction (under 20 lines) covering main frameworks, test runner `{TEST_RUNNER}`, lint tool, and key file paths detected in sweep
- If `{STACK}` = generic: populate from sweep findings — use repo name, stack signals from `package.json`/`pyproject.toml`/`go.mod`, detected test config files, and lint configs. Use `<!-- not detected — fill in -->` only for fields where sweep found nothing. Do not leave all fields as empty placeholders.
- Do not over-specify — agents fill in missing details on their first task
- File naming rule: when `{STACK}` = generic, always create the file as `.github/instructions/generic.instructions.md`. Do NOT reuse or overwrite a pre-existing instructions file with a different name. Pre-existing project instruction files are not renamed.

Note: instructions are auto-applied by platform via `applyTo`; they are not listed in Agent Registry or Skill Index. Note their `applyTo` patterns in the Repository Context section of AGENTS.md.

### 5F — Skills (dev lifecycle coverage)

Generate one `SKILL.md` per dev lifecycle step. Skills are loaded by agents at task time via the Skill Index — they are not pre-loaded. Each skill must be registered in AGENTS.md Skill Index.

**Required skills (always generate):**

| Dev Stage         | Skill name              | Folder                                  | Note                                                                           |
| ----------------- | ----------------------- | --------------------------------------- | ------------------------------------------------------------------------------ |
| Scan              | `data-collection`       | `.github/skills/data-collection/`       |                                                                                |
| Plan + Design     | `design-planning`       | `.github/skills/design-planning/`       |                                                                                |
| Implement         | `implementation`        | `.github/skills/implementation/`        |                                                                                |
| Test              | `testing`               | `.github/skills/testing/`               | ⚠ Requires stack-specific runner setup (jest, vitest, pytest, etc.) before use |
| Document          | `doc-sync`              | `.github/skills/doc-sync/`              |                                                                                |
| Review            | `review`                | `.github/skills/review/`                | Used at VERIFY step only — not a dispatched pipeline stage                     |
| Remediation (any) | `recursive-remediation` | `.github/skills/recursive-remediation/` |                                                                                |

**Default pipeline stage order:** Scan → Plan + Design → Implement → Test → Document. Review Auditor runs as the VERIFY role inside each micro-cycle — not a dispatched pipeline stage.

For `{STACK}` ≠ generic: prefix the `implementation`, `testing`, and `review` folder names with the stack slug (e.g. `react-ts-implementation/`) and register them in the Skill Index alongside the generic counterparts.

**Generate each core skill verbatim.** Copy each block exactly as shown; `[FILL IN: ...]` tokens are the only allowed deviations (agent names and project-specific doc paths).

**`.github/skills/data-collection/SKILL.md`**:

```markdown
# Data Collection

**Dev Stage**: Scan
**Purpose**: Gather task context, repository state, and raw input findings for the next pipeline stage.
**Loaded by**: `[FILL IN: data-collector agent name, e.g. data-collector-specialist]` when ledger stage = Scan

## Steps

1. Read `verification-artifacts/{task-id}-input.json` — confirm status=ready and exit_criteria are defined.
2. Scan relevant source files:
   - Read repo entry points and feature folders (max 10 reads total).
   - Identify files directly related to the task scope from the Work Package.
   - Note existing patterns, types, and interfaces relevant to the task.
3. Collect findings:
   - List impacted files and their current state.
   - Note any conflicts, dependencies, or constraints discovered.
   - Flag any out-of-scope items as `BLOCKED: OUT_OF_SCOPE: <description>` — do NOT include them in the artifact.
4. Write output to `verification-artifacts/{task-id}-scan.json` with schema: `{ "task_id": "", "findings": [], "impacted_files": [], "constraints": [], "out_of_scope_flags": [] }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Scan complete — {2-sentence summary of key findings}`.
```

**`.github/skills/design-planning/SKILL.md`**:

```markdown
# Design Planning

**Dev Stage**: Plan + Design
**Purpose**: Produce architecture plans, data shape definitions, and implementation blueprints from scan findings.
**Loaded by**: `[FILL IN: design-planning agent name, e.g. design-planning-architect]` when ledger stage = Plan + Design

## Steps

1. Read `verification-artifacts/{task-id}-scan.json` — confirm status=ready.
2. Analyze scan findings:
   - Identify the minimal change surface required to satisfy exit_criteria.
   - Check [FILL IN: architecture doc path, e.g. `docs/architecture.md`] for architectural constraints.
   - Note any patterns from [FILL IN: conventions doc path, e.g. `docs/guides/code-conventions.md`] applicable to this task.
3. Produce design plan:
   - Define data shapes, interfaces, or API contracts changed by this task.
   - List files to create or modify with their responsibilities.
   - Describe component/module interaction changes if any.
   - Flag alternatives considered and the chosen approach with rationale.
4. Write output to `verification-artifacts/{task-id}-design.json` with schema: `{ "task_id": "", "design_summary": "", "files_to_change": [], "data_shapes": {}, "alternatives_considered": [], "rationale": "" }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Design complete — {2-sentence summary of approach}`.
```

**`.github/skills/implementation/SKILL.md`**:

```markdown
# Implementation

**Dev Stage**: Implement
**Purpose**: Write code changes according to the approved design plan.
**Loaded by**: `[FILL IN: implementation agent name, e.g. implementation-specialist]` when ledger stage = Implement

## Steps

1. Read `verification-artifacts/{task-id}-design.json` — confirm status=ready and design is approved.
2. Implement changes:
   - Follow the file list and responsibilities from the design artifact.
   - Follow conventions from `.github/instructions/` files.
   - Keep changes strictly within the Work Package scope — no speculative improvements.
3. Validate:
   - Confirm no hardcoded secrets or environment-specific values in source.
   - Confirm changes stay within the scope defined in the design artifact.
4. Write output to `verification-artifacts/{task-id}-impl.json` with schema: `{ "task_id": "", "files_changed": [], "summary": "", "notes": "" }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Implementation complete — {2-sentence summary of changes}`.
```

**`.github/skills/doc-sync/SKILL.md`**:

```markdown
# Doc Sync

**Dev Stage**: Document
**Purpose**: Sync and update documentation to reflect completed implementation changes.
**Loaded by**: `[FILL IN: docs-curator agent name, e.g. docs-curator]` when ledger stage = Document

## Steps

1. Read the relevant implementation artifact from `verification-artifacts/` — confirm status=ready; note files changed and summary.
2. Identify documentation targets (populate from sweep findings):
   - [FILL IN: task/story tracking doc, e.g. story BR] — mark completed acceptance criteria.
   - [FILL IN: implementation notes doc] — update with decisions and data shape changes.
   - [FILL IN: architecture overview, e.g. `docs/architecture.md`] — update only if cross-cutting architecture changed.
   - [FILL IN: feature/module design doc] — update if feature logic or data flow changed.
   - [FILL IN: API spec doc] — update if endpoints or contracts changed.
3. Update documentation:
   - Record implementation decisions and data shape changes in relevant docs.
   - Update any "Last Updated" dates in modified docs.
   - Do not add documentation for unchanged code.
4. Write output to `verification-artifacts/{task-id}-docs.json` with schema: `{ "task_id": "", "docs_updated": [], "summary": "" }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Documentation complete — {2-sentence summary of docs updated}`.
```

**`.github/skills/review/SKILL.md`**:

```markdown
# Review

**Dev Stage**: VERIFY role (not a dispatched pipeline stage)
**Purpose**: Adversarial audit of specialist output — challenges assumptions, validates artifact schema, checks scope compliance, emits APPROVED or REJECTED verdict.
**Loaded by**: `[FILL IN: review-auditor agent name, e.g. review-auditor]` when ledger stage = VERIFY (dispatched by Governor, not as a pipeline stage)

## Steps

1. Read the artifact under review (path provided in dispatch prompt) — confirm it exists and schema is valid.
2. Audit the artifact against five injection patterns:
   - **Scope creep**: Does the artifact contain changes beyond the Work Package `exit_criteria` in `.github/.ai_ledger.md`?
   - **Self-certification**: Did the producing agent emit TASK_COMPLETE without Governor gate? (check Decisions Log)
   - **Stale materials**: Did the producing agent act on inputs with status ≠ ready? (check Materials table)
   - **Silent failures**: Is the artifact empty, malformed, or missing required schema fields?
   - **Loop bypass**: Did the specialist skip writing to `verification-artifacts/`?
3. For code artifacts: also check:
   - No hardcoded secrets or environment-specific values.
   - Changes match the approved design artifact (if available).
4. Emit verdict:
   - **APPROVED**: all checks pass — write `{ "verdict": "APPROVED", "task_id": "", "checks_passed": [], "notes": "" }`.
   - **REJECTED**: one or more checks fail — write `{ "verdict": "REJECTED", "task_id": "", "failures": [], "remediation_required": "" }`.
5. Write output to `verification-artifacts/{task-id}-verify.json`.
6. Append verdict to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: VERIFY {APPROVED|REJECTED} — {1-sentence reason}`.
```

**`.github/skills/recursive-remediation/SKILL.md`**:

```markdown
# Recursive Remediation

**Dev Stage**: Any (used when a previous stage artifact was REJECTED at VERIFY)
**Purpose**: Bounded iteration loop for fixing failures — max 3 remediation attempts before escalating.
**Loaded by**: Governor when VERIFY verdict = REJECTED and G3 loop-bounds-ok gate passes

## Steps

1. Read the REJECTED verify artifact (`verification-artifacts/{task-id}-verify.json`) — extract `failures` and `remediation_required`.
2. Check loop bounds: read Work Queue `iteration` column for this task.
   - If iteration ≥ 3: append `BLOCKED: ESCALATION_REQUIRED — max remediation iterations reached` to Decisions Log and return to Governor. Do NOT proceed.
3. Increment iteration: update Work Queue row `iteration` = current + 1, `status` = REMEDIATION.
4. Dispatch producing agent with remediation context:
   - Dispatch prompt must include: task description + failed artifact path + REJECTED reasons from verify artifact + result path + SKILL.md path + return instruction.
   - Do NOT include raw file contents in the dispatch prompt.
5. Await new artifact from producing agent.
6. Re-dispatch `[FILL IN: review-auditor agent name, e.g. review-auditor]` for adversarial audit of the new artifact (VERIFY step).
7. On APPROVED: update Work Queue row `status` = COMPLETE, `iteration` = final count. Continue pipeline.
8. On REJECTED again: return to step 2 (loop continues until iteration ≥ 3 or APPROVED).
9. Append each iteration outcome to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Remediation iteration {n} — {APPROVED|REJECTED} — {1-sentence reason}`.
```

**`.github/skills/testing/SKILL.md`**:

```markdown
# Testing

**Dev Stage**: Test
**Purpose**: Write and run tests for implemented changes.
**Loaded by**: `[FILL IN: test-specialist agent name, e.g. test-specialist]` when ledger stage = Test

⚠️ **Requires `{TEST_RUNNER}` configuration before use.** Verify test config file is present and `execute` tool can run `{TEST_RUNNER}` before dispatching.

## Steps

1. Read `verification-artifacts/{task-id}-impl.json` — confirm status=ready; note files changed.
2. Identify test targets:
   - For each changed file, locate or create the corresponding test file using `{TEST_RUNNER}` naming conventions.
   - Review existing tests to avoid duplication and match existing test style.
3. Write tests:
   - Cover the happy path for each changed function/component.
   - Add at least one edge case per Acceptance Criterion from the Work Package.
   - [FILL IN: add framework-specific patterns, e.g. RTL role/text queries for React, pytest fixtures for Python, mocking patterns for the stack].
4. Run tests:
   - Execute: [FILL IN: `{TEST_RUNNER}` run command, e.g. `npx vitest run`, `npm test`, `pytest`].
   - If tests fail: attempt one fix pass → if still failing, emit `BLOCKED: test failures — remediation needed` and return to Governor.
5. Write output to `verification-artifacts/{task-id}-test.json` with schema: `{ "task_id": "", "tests_added": [], "tests_passed": 0, "tests_failed": 0, "coverage_notes": "", "status": "pass|fail|partial" }`.
6. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Testing complete — {pass/fail counts and key coverage note}`.
```

**Note — Playbooks also use SKILL.md format** but have a different body style:

- Skills = domain knowledge and tool patterns for a specialist (reference bullets, not steps)
- Playbooks = ordered numbered steps with gate conditions for the governor to follow inline

Step 5F-Playbooks below contains the verbatim canonical playbook content to generate.

### 5F-Playbooks — Default playbooks (always generate)

Generate the following playbook SKILL.md files exactly as shown. Register each in the AGENTS.md Playbook Index.

**Stack prefix rule**: In dispatch steps, `{stack}-` agent and skill names use the `{STACK}` value (lowercased, hyphenated, e.g. `react-ts-`) if `{STACK}` ≠ generic. If `{STACK}` = generic, omit the `{stack}-` prefix entirely and use plain names (e.g. `implementation-specialist.agent.md`).

**`.github/skills/implement-feature/SKILL.md`**:

```markdown
---
name: implement-feature
description: Full Scan → Plan + Design → Implement → Test → Document pipeline for implementing a new feature or adding functionality to the codebase.
---

# Implement Feature

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to implement, build, or add a feature

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` is defined in Work Queue. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Data Collector Specialist]** Dispatch `data-collector-specialist.agent.md` as a subagent.
   - Input: `verification-artifacts/{task-id}-input.json` (status: ready)
   - SKILL: `.github/skills/data-collection/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-scan.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-scan.json`.

3. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent.
   - Input: `verification-artifacts/{task-id}-scan.json` (status: ready)
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-design.json`.

4. **[Gate: design approval]** Governor checks design output. If `config.human_approval = true` → use `vscode_askQuestions` to get user confirmation before proceeding. If rejected or changes requested → re-dispatch `design-planning-architect` with feedback (Ralph loop, max 3 iterations per `recursive-remediation` SKILL.md).

5. **[Gate: adversarial verify — design]** Governor dispatches `design-planning-architect` as non-author auditor (alternate approach challenge) → verify design artifact → verdict APPROVED or REJECTED. On REJECTED → return to design agent with rejection reasons.

6. **[Dispatch: Implementation Specialist]** Dispatch `{stack}-implementation-specialist.agent.md` as a subagent.
   - Input: `verification-artifacts/{task-id}-design.json` (status: ready, verdict: APPROVED)
   - SKILL: `.github/skills/{stack}-implementation/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-impl.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

7. **[Gate: adversarial verify — implementation]** Governor dispatches `{stack}-review-auditor.agent.md` → verify implementation artifact → verdict APPROVED or REJECTED. On REJECTED → re-dispatch with feedback via `recursive-remediation` SKILL.md.

8. **[Dispatch: Test Specialist]** Dispatch `{stack}-test-specialist.agent.md` as a subagent.
   - Input: `verification-artifacts/{task-id}-impl.json` (status: ready, verdict: APPROVED)
   - SKILL: `.github/skills/{stack}-testing/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-test.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

9. **[Gate: adversarial verify — tests]** Governor dispatches `{stack}-review-auditor.agent.md` → verify test artifact → verdict APPROVED or REJECTED. On REJECTED → remediate via `recursive-remediation` SKILL.md.

10. **[Dispatch: Docs Curator]** Dispatch `docs-curator.agent.md` as a subagent.
    - Input: `verification-artifacts/{task-id}-impl.json` (status: ready, verdict: APPROVED)
    - SKILL: `.github/skills/doc-sync/SKILL.md`
    - Result path: `verification-artifacts/{task-id}-docs.json`
    - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

11. **[Exit]** If all stages APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If any stage REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.
```

**`.github/skills/bug-fix/SKILL.md`**:

```markdown
---
name: bug-fix
description: Scan → Design → Implement → Test pipeline to locate and resolve a specific bug, error, or regression in the codebase.
---

# Bug Fix

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to fix, debug, or resolve a bug or error

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` includes the bug reproduction case or error description. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Data Collector Specialist]** Dispatch `data-collector-specialist.agent.md` as a subagent to locate the bug.
   - Input: `verification-artifacts/{task-id}-input.json` (status: ready, includes error description/reproduction steps)
   - SKILL: `.github/skills/data-collection/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-scan.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Await artifact → `verification-artifacts/{task-id}-scan.json` (must include root cause hypothesis).

3. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent with the root cause from scan.
   - Input: `verification-artifacts/{task-id}-scan.json` (status: ready, root cause identified)
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Design artifact must include the fix plan and rationale.

4. **[Gate: design approval]** Governor checks fix plan. If `config.human_approval = true` → use `vscode_askQuestions` to confirm before proceeding. If rejected or changes requested → re-dispatch `design-planning-architect` with feedback (Ralph loop, max 3 iterations per `recursive-remediation` SKILL.md).

5. **[Dispatch: Implementation Specialist]** Dispatch `{stack}-implementation-specialist.agent.md` as a subagent to apply the fix.
   - Input: `verification-artifacts/{task-id}-design.json` (status: ready, verdict: APPROVED)
   - SKILL: `.github/skills/{stack}-implementation/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-impl.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

6. **[Gate: adversarial verify — fix]** Governor dispatches `{stack}-review-auditor.agent.md` → verify implementation artifact → verdict APPROVED or REJECTED. On REJECTED → re-dispatch with feedback via `recursive-remediation` SKILL.md.

7. **[Dispatch: Test Specialist]** Dispatch `{stack}-test-specialist.agent.md` as a subagent to confirm the fix and add a regression test.
   - Input: `verification-artifacts/{task-id}-impl.json` (status: ready, verdict: APPROVED)
   - SKILL: `.github/skills/{stack}-testing/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-test.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Test must include a regression test that would have caught the original bug.

8. **[Gate: adversarial verify — tests]** Governor dispatches `{stack}-review-auditor.agent.md` → verify test artifact → verdict APPROVED or REJECTED. On REJECTED → remediate via `recursive-remediation` SKILL.md.

9. **[Exit]** If all stages APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If any stage REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.
```

**`.github/skills/create-doc/SKILL.md`**:

```markdown
---
name: create-doc
description: Plan + Design → Document pipeline for writing, creating, or updating documentation — BR files, implementation docs, architecture overviews, guides, or knowledge base articles.
---

# Create Doc

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to write, create, or update documentation

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` specifies the target doc type and the target file path or topic. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent to outline the documentation structure.
   - Input: `verification-artifacts/{task-id}-input.json` (status: ready, includes doc type + topic + context)
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Design artifact must include: target file path, section outline, template to follow (if any).

3. **[Gate: design approval]** Governor checks doc outline. If `config.human_approval = true` → use `vscode_askQuestions` to get user confirmation before writing. If rejected → re-dispatch with feedback (Ralph loop, max 3 iterations).

4. **[Dispatch: Docs Curator]** Dispatch `docs-curator.agent.md` as a subagent to write or update the documentation.
   - Input: `verification-artifacts/{task-id}-design.json` (status: ready, verdict: APPROVED)
   - SKILL: `.github/skills/doc-sync/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-docs.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

5. **[Gate: adversarial verify — documentation]** Governor dispatches `design-planning-architect.agent.md` as non-author challenger → verify doc artifact against template compliance and content accuracy → verdict APPROVED or REJECTED. On REJECTED → return to Docs Curator with rejection reasons.

6. **[Exit]** If APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.
```

### 5G — Prompts (2 only)

**`.github/prompts/solar.prompt.md`** — entry point to start any SOLAR-managed task:

```
---
agent: Orchestration Governor
description: Start a SOLAR-managed task — orchestrator reads registry and dispatches the right specialist
---
You are the Orchestration Governor.

1. READ (startup):
   Read `.github/AGENTS.md` lines 1–15 (Section Index). Then load only sections needed:
   - New task: §3 Agent Registry + §4 Skill Index + §5 Playbook Index
   - Resume: §3 Agent Registry + §4 Skill Index only
   - Ledger reset at TASK_COMPLETE: §7 Ledger Template only
   Read `.github/.ai_ledger.md`:
   - INTERRUPTED row found → use `vscode_askQuestions`: "Previous task interrupted at stage {stage}. Resume or discard?"
   - PENDING / IN_PROGRESS / ASSIGNED row found → resume from the next stage after the last COMPLETE entry in Decisions Log. Do NOT re-dispatch already-completed stages.
   - No active task → continue.

2. PLAN (startup):
   Match intent against Playbook Index and Skill Index.
   - Ambiguous or matches multiple → use `vscode_askQuestions` to confirm before dispatching.
   - Single-skill match → one micro-cycle.
   - Playbook match → N micro-cycles in sequence (defined by Playbook SKILL.md).
   Write Work Queue row: task, selected skill/playbook, status=PENDING, exit_criteria=TBD.

3. EXECUTE LOOP [for each stage in sequence]:

   3a. READ — G1-G4 gate check before dispatch:
       G1: materials-sufficient — required input artifacts exist and status=ready
       G2: design-approved — design artifact approved before implement (if human_approval=true: use vscode_askQuestions)
       G3: loop-bounds-ok — remediation attempts < 3
       G4: previous-verified — previous stage VERIFY passed (or was skipped)
       Blocked → append `BLOCKED: <one-line reason>` to Decisions Log; pause.

   3b. PLAN (optional) — if stage requires coordination write dispatch strategy. Skip for single-action stages.

   3c. EXECUTE — dispatch specialist:
       Dispatch prompt contains ONLY: task description + input path + SKILL.md path + result path + return instruction.
       Re-dispatches (remediation, re-test, re-audit) MUST explicitly repeat all 5 items — each subagent is a stateless isolated session with no memory of prior dispatches.
       Receive output artifact path from specialist return.

   3d. VERIFY (conditional):
       RUN if output contains: code changes, design artifact, document output.
       SKIP if output is: scan findings passed as handoff material, ledger/registry update.
       When RUN: look up auditor role from Agent Registry — do NOT hardcode names.
         Code output → dispatch agent with role: `review-auditor`
         Design/docs output → dispatch agent with role: `design-planning-architect`
       Auditor produces `{task-id}-verify.json` (verdict: APPROVED or REJECTED + reasoning).
       On APPROVED → continue.
       On REJECTED →
         (a) FIRST action — MUST succeed before any other step:
             `replace_string_in_file`: update Work Queue row status=REMEDIATION, iteration=<n+1>
         (b) Return specialist artifact for remediation; re-run VERIFY.
         (c) On re-VERIFY APPROVED: update Work Queue row status=COMPLETE, iteration=<final count>.
       Re-dispatches MUST explicitly repeat all 5 mandatory dispatch items including SKILL.md path.
       Append verdict to Decisions Log.

   3e. ARTIFACT — update ledger:
       Update Materials row: output artifact path + status=ready.
       Append Decisions Log entry (format: `YYYY-MM-DD HH:MM UTC: <2-sentence specialist output summary>`); use UTC time from most recent PostToolUse hook `timestamp` field.
       Advance stage: mark current stage COMPLETE in Work Queue.

4. TASK_COMPLETE:
   (1) Archive `.github/.ai_ledger.md` to `verification-artifacts/{YYYYMMDD}-{task-id}-ledger-archive.md` using `create_file`.
   (2) Reset `.ai_ledger.md` from the Ledger Template block in `.github/AGENTS.md` §7.
   (3) Delete `verification-artifacts/{task-id}-*` task artifact files.
   (4) Set Work Queue row to CLOSED. Never touch rows marked INTERRUPTED.

5. Materials discipline: manage `## Materials` as path+status index only — no raw content. Dispatch prompts contain ONLY: task description + input path + result path + SKILL.md path + return instruction. On specialist return: update Materials from the 2-sentence summary only — do NOT read result files directly.

6. Context discipline: use `startLine/endLine` for all file reads. Write findings to `verification-artifacts/` instead of accumulating raw content in context. For AGENTS.md: read Section Index first (lines 1–15), then read only the section needed.

7. Operation failure protocol (applies to all tool calls): on any tool call that returns an error or partial failure: (a) retry once using an alternative form (e.g. `replace_string_in_file` instead of `multi_replace_string_in_file`, smaller range); (b) if retry fails: append to Decisions Log as `BLOCKED: <tool-name> failed — <one-line reason>. Pending retry on next pickup.`; (c) do NOT silently continue past a failed write to `.github/.ai_ledger.md`; (d) for non-ledger failures (e.g. `create_file` on existing file): retry, then proceed if content is already correct.
```

**`.github/prompts/solar-registry-update.prompt.md`** — update AGENTS.md when components change:

```
---
agent: agent
description: Sync the SOLAR-Ralph registry in AGENTS.md after adding, swapping, or removing any component
---
You are updating the SOLAR-Ralph component registry.

Use the vscode_askQuestions tool to ask:
1. What changed? (added / swapped / removed)
2. Which component type? (agent / skill / instruction / hook / workflow)
3. What is the file path of the new or updated file?

Then:
- ADD agent: read the file → add a row to Agent Registry with Dev Stage + Loads Skill columns filled
- ADD skill: read the file → add a row to Skill Index with Dev Stage column filled
- ADD playbook: read the file → add a row to Playbook Index with Name, Description, Path, Trigger filled
- SWAP: read new file → update the existing row (Name, Dev Stage, Loads Skill, Accepts, Produces)
- REMOVE: confirm file deleted → remove the row
- Optional component: add row with Optional=Yes + enable instruction

Print a summary of all AGENTS.md changes made.
```

### 5H — Solar-system reference files (verbatim skeletons)

Generate each file verbatim as shown below. Do NOT paraphrase or summarize — copy exactly.

**`.github/solar-system/adversarial/skeleton-manifest.md`**:

```markdown
# Adversarial Trigger Conditions — Skeleton Manifest

The adversarial layer (A in SOLAR) is a Governor dispatch rule, not a dedicated agent. At the VERIFY step of each micro-cycle, the Governor picks a non-author specialist from the Agent Registry (domain match) to challenge the previous agent's output.

## Trigger Conditions

Adversarial audit is triggered when the producing specialist returns an artifact and VERIFY is required (code, design, or doc output). It is SKIPPED for scan/handoff artifacts.

## Five Injection Patterns to Watch

1. **Scope creep** — specialist expands beyond Work Package; auditor checks artifact against `exit_criteria` in ledger
2. **Self-certification** — specialist claims TASK_COMPLETE without Governor gate; blocked by stop hook and Governor contract
3. **Stale materials** — specialist acts on outdated input (status ≠ ready); caught by G1 gate before dispatch
4. **Silent failures** — specialist returns `completed` but artifact is empty or malformed; auditor opens and validates artifact schema
5. **Loop bypass** — specialist skips VERIFY by not writing to `verification-artifacts/`; post-tool-use hook injects ADVERSARIAL_VERIFY_REQUIRED signal
```

**`.github/solar-system/protocols/inquiry-first.md`**:

```markdown
# Inquiry-First Protocol — Canonical 4-Gate Contract

Before the Governor dispatches any specialist, all four gates must pass. A single failure blocks dispatch and appends `BLOCKED: <gate> failed` to the Decisions Log.

| Gate | Name                 | Condition                                                                                       | Failure Action                            |
| ---- | -------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------- |
| G1   | materials-sufficient | Required input artifacts exist in `verification-artifacts/` and status = ready                  | Emit MATERIAL_INSUFFICIENT; pause         |
| G2   | design-approved      | Design artifact approved before Implement stage (`human_approval=true` → `vscode_askQuestions`) | Await approval or request revision        |
| G3   | loop-bounds-ok       | Remediation iteration counter < 3                                                               | Emit ESCALATION_REQUIRED                  |
| G4   | previous-verified    | Previous stage VERIFY passed (verdict = APPROVED), or VERIFY was explicitly skipped             | Return to producing agent for remediation |
```

**`.github/solar-system/protocols/lifecycle-coordination.md`**:

```markdown
# Lifecycle Coordination — VERIFY Stage Trigger Mechanics

The VERIFY step runs conditionally inside each micro-cycle. The Governor decides whether to run or skip based on the artifact type returned by the specialist.

## Run VERIFY when output contains:

- Code changes (implementation or test artifacts)
- Design artifacts (architecture plans, data shape definitions)
- Document output (BR files, implementation docs, architecture updates)

## Skip VERIFY when output is:

- Scan findings passed as handoff material to the next stage
- Ledger or registry updates (metadata only, no deliverable content)

## Auditor Selection (domain match)

The Governor looks up the auditor from the Agent Registry by role — do NOT hardcode agent names in `solar.prompt.md`:

- Code output → agent with role `review-auditor`
- Design/docs output → agent with role `design-planning-architect` (non-author challenge)

## Post-VERIFY flow

- APPROVED → Governor advances to next stage; appends verdict to Decisions Log
- REJECTED → Governor returns artifact to producing agent with rejection reasons; increments remediation counter; re-dispatches VERIFY after fix
- REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log
```

Generate schemas as minimal valid JSON (empty envelope — agents fill properties on first use):

- `.github/solar-system/schemas/designer-output.schema.json`
- `.github/solar-system/schemas/implementer-handoff.schema.json`
- `.github/solar-system/schemas/review-result.schema.json`
- `.github/solar-system/schemas/qa-result.schema.json`
- `.github/solar-system/schemas/scout-findings.schema.json`
- `.github/solar-system/schemas/dev-progress.schema.json`

Each schema: `{ "$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "properties": {} }`

### 5I — Verification artifacts scaffold

- `verification-artifacts/README.md` — lifecycle rules: create `{task-id}-input.json` on assign; fill on ready; clean up on close; naming: `{task-id}-{type}.json`; default state: empty
- `verification-artifacts/.gitkeep`

---

## Step 6 — Report

After all files are created, print:

```
SOLAR-Ralph installation complete.

Files created: {count}
Stack: {STACK}  |  Test runner: {TEST_RUNNER}  |  MCP fetch: {available / unavailable}

Core:
  .github/AGENTS.md ✓  (includes Repository Context from sweep)
  .github/copilot-instructions.md ✓
  .github/solar.config.json ✓
  .github/.ai_ledger.md ✓

Agents ({count}):
  {name}  [Dev Stage: {stage}  |  Loads Skill: {skill}]
  ...

Skills ({count}):
  {name}  [Dev Stage: {stage}]
  ...

Hooks: post-tool-use, stop
Prompts: solar (entry), solar-registry-update (registry sync)
Instructions: solar, {stack}

Repository Context registered in AGENTS.md:
  Existing docs: {list or none}  ← available as Materials input for any task
  Existing instructions: {list or none}

Next steps:
  - Run the `solar` prompt to start your first task
  - Sync registry after any component change: run `solar-registry-update`
  - Tool-name notice: VS Code Copilot tool-set names may change between releases. Verify the `tools:` values in each generated `.agent.md` against the current VS Code docs at https://code.visualstudio.com/docs/copilot/customization/custom-agents. Flag any tool-set name not found in that page.
```

---

## Reference: Swapping Components

| Action              | Steps                                                                                                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Swap / add agent    | Create or replace `.github/agents/{name}.agent.md` → run `solar-registry-update`; ensure Dev Stage + Loads Skill columns are filled                                          |
| Remove agent        | Delete file → run `solar-registry-update`                                                                                                                                    |
| Swap / add playbook | Create or replace `.github/skills/{name}/SKILL.md` with numbered steps + gate conditions (playbook format) → run `solar-registry-update` to add/update row in Playbook Index |
| Remove playbook     | Delete `.github/skills/{name}/SKILL.md` → run `solar-registry-update` to remove the row from Playbook Index                                                                  |
| Swap / add skill    | Create or replace `.github/skills/{name}/SKILL.md` → run `solar-registry-update`                                                                                             |
| Swap instruction    | Replace `.github/instructions/{name}.instructions.md` (auto-applied; no registry row needed)                                                                                 |

Rule: AGENTS.md Agent Registry and Playbook Index are the sources of routing truth. Every component change ends with `solar-registry-update`.

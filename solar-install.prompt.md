---
agent: agent
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

- **Search step 1 — AGENTS.md spec**: Use `fetch_webpage` to search with keywords `agents.md format specification site:agents.md OR site:github.com OR site:code.visualstudio.com`. From results, select the URL that (a) is not a `github.io` legacy path and (b) contains "2026" or "Current" in its content. Fetch that URL → note the current format rules.
- **Search step 2 — Copilot agent/prompt frontmatter**: Use `fetch_webpage` to search with keywords `GitHub Copilot custom agent prompt file frontmatter VS Code customization site:code.visualstudio.com OR site:docs.github.com`. Fetch the top result → note current `.agent.md` and `.prompt.md` YAML frontmatter requirements.
- **Verification**: Confirm each fetched page contains "2026" or "Current" — if neither appears, discard and try the next result.
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
- `package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml` → cross-check detected stack against `{STACK}`; update `{STACK}` if "generic" and a stack is detected

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

## Step 5 — Generate Files

Create the following files. Use `{STACK}`, `{TEST_RUNNER}`, and the Repo Context block from Step 3 to tailor content.

### 5A — Core manifest

**`.github/AGENTS.md`** — Full bootstrap manifest with these sections:

1. **What is this file** (1 paragraph — SOLAR-Ralph + this repo's name from sweep)
2. **Repository Context** (the Repo Context block from Step 3 — existing docs, instructions, and agent files found in sweep)
3. **Agent Registry** (table: Name / Dev Stage / Role / Loads Skill / Accepts / Produces / Optional)
4. **Skill Index** (table: Name / Dev Stage / Purpose / Path / Optional)
5. **Playbook Index** (table: Name / Description / Path / Trigger — SOLAR-managed ordered step sequences the orchestrator follows; default playbooks listed here; custom playbooks added via `solar-registry-update`)
6. **Hook Configuration** (table: 2 hooks — post-tool-use / stop)
7. **Ledger Template** (verbatim from Step 5C)
8. **Config Toggles** (5 toggles with defaults)
9. **Usage** (1 paragraph explaining: orchestrator receives user prompt → matches intent to Playbook Index to select playbook → if ambiguous, uses `vscode_askQuestions` to confirm before dispatching; then follows playbook inline (never forked), dispatching each step as a forked specialist; agent reads Skill Index → loads matching SKILL.md before acting)

Agent Registry column notes:

- **Dev Stage**: which development step this agent handles (Scan / Plan / Design / Implement / Test / Document / Review)
- **Loads Skill**: the skill name this agent loads from the Skill Index at task time (or "built-in" if none)
- **VERIFY dispatch**: no dedicated adversarial agent is registered. At VERIFY stage, the Governor picks a non-author specialist from this registry by domain match. Any registered specialist can serve as auditor — the Governor decides at runtime based on what was produced.

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

Full instructions (this is the only fully detailed agent):

- **Always runs inline — never forked.** The governor is the only component that owns gates, adversarial dispatch, loop iteration, and ledger writes
- Reads `.github/AGENTS.md` Agent Registry on every task — this is the sole routing source of truth
- Reads `.github/.ai_ledger.md` before every action — current stage and any interrupted tasks
- Never executes task content directly — only reads, dispatches, and updates ledger

**On new task received:**

- Match the user prompt intent against the **Playbook Index** in AGENTS.md. Select the closest matching playbook. If the prompt is ambiguous or matches multiple playbooks, use `vscode_askQuestions` to confirm which playbook to run — do not dispatch any specialist until the playbook is confirmed.
- Write a new Work Queue row in `.github/.ai_ledger.md` immediately: id, task (from user prompt), selected playbook, status=PENDING, stage=SCAN, iteration=0
- If the user prompt is unclear or under-specified: do not attempt to plan stages yet — dispatch the scan-stage agent from the registry first; it produces `verification-artifacts/{task-id}-scan.json`; use that output to decide the full stage breakdown
- If an existing INTERRUPTED task is detected in the ledger: use `vscode_askQuestions` to ask "Previous task was interrupted at stage {stage}. Resume or discard?" before starting anything new
- Define exit_criteria in the ledger before dispatching any specialist

**Between stages (after each agent completes):**

- Update the Work Queue row: mark current stage done, advance stage to next in the planned sequence
- Add or update the Materials row for the output just produced: set status=ready, link the path in `verification-artifacts/`
- Append to Decisions Log (append-only): `[{stage} done] {agent} → {artifact-path}`
- Run the 4-gate pre-dispatch check before dispatching the next agent
- **Dispatch prompt discipline**: the runSubagent prompt you pass MUST contain ONLY: (1) 2-3 sentence task description, (2) schema type and input file path(s) from Materials, (3) the result file path to write to (`verification-artifacts/{task-id}-{stage}-result.json`), (4) this return instruction verbatim: `"Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."`. Never embed raw file contents or ledger history in the dispatch prompt — specialists read files in their own isolated context.
- **Materials index**: the governor owns the Materials table as a lightweight index only. It tracks file paths and status — it does NOT read the contents of specialist result files.

**Adapts the cycle to the task** — after scan output is available, plan the minimal stage set. Examples:

- "implement feature X" → scan → design → implement → verify → exit
- "update architecture doc" → scan → design → write doc → verify → exit
- "test parts A and B" → scan → plan → test → verify → exit
- "write commit/PR" → scan → execute → exit
  The task description + scan findings determine the stage sequence — not a fixed workflow

**Docs as materials:** existing docs registered in AGENTS.md Repository Context may be added as Materials input rows so agents can read them before acting

**On task complete (TASK_COMPLETE confirmed):**

- Append to Decisions Log: `[CLOSED] task-{id} — exit criteria met`
- Delete all `verification-artifacts/{task-id}-*` task artifact files (`.json` and `.md`)
- Set Work Queue row status=CLOSED
- Do NOT touch any row with status=INTERRUPTED — these are resume checkpoints
- **Ledger archive + reset**: immediately after writing TASK_COMPLETE: (1) copy the full `.github/.ai_ledger.md` to `verification-artifacts/{YYYYMMDD}-{task-id}-ledger-archive.md` using `create_file`; (2) reset `.ai_ledger.md` to the default state by reading the Ledger Template block from `.github/AGENTS.md` Section 7 and overwriting `.ai_ledger.md` with that content. This ensures the ledger is clean before the next task begins.

**On user interrupt / unexpected stop:**

- Do not clean up `verification-artifacts/` — preserve current state as resume checkpoint
- Set Work Queue row status=INTERRUPTED, record last completed stage
- On next invocation: detect INTERRUPTED status, use `vscode_askQuestions` to ask before proceeding

- 4 pre-dispatch gates must all pass before any dispatch: G1 materials-sufficient / G2 design-approved / G3 loop-bounds-ok / G4 previous-verified
- **G2 — design approval gate**: when `config.human_approval = true`, use `vscode_askQuestions` to pause and ask: "Review design artifact at `verification-artifacts/{task-id}-design.json`. Approve to proceed to implement?" (options: `Approve` / `Request changes`). Do not dispatch the implement stage until `Approve` is selected. If `Request changes`: re-dispatch design-planning-architect with feedback (Ralph loop, max 3 iterations). When `config.human_approval = false`, gate passes automatically if design artifact exists.
- On → VERIFY stage (adversarial audit): select a non-author specialist from the Agent Registry that did NOT produce the artifact under review. Selection rule: prefer the specialist whose domain best matches the output type — e.g. dispatch `review-auditor` to audit implementation output; dispatch `test-specialist` to audit a design artifact; dispatch `design-planning-architect` to audit test coverage. The selected auditor reads `verification-artifacts/{task-id}-{type}.json`, challenges assumptions and completeness, and produces `verification-artifacts/{task-id}-verify.json` with verdict `APPROVED` or `REJECTED` + specific reasoning. Append the verdict line to Decisions Log. Do not advance to COMPLETE if verdict = REJECTED — return the task to the producing agent for remediation.

**Required specialist agents (always generate, minimal stubs, tailored to `{STACK}`):**

| Dev Stage     | File                                 | Loads Skill                                             |
| ------------- | ------------------------------------ | ------------------------------------------------------- |
| Scan          | `data-collector-specialist.agent.md` | `data-collection`                                       |
| Plan + Design | `design-planning-architect.agent.md` | `design-planning`                                       |
| Implement     | `implementation-specialist.agent.md` | `{stack}-implementation` or `implementation` if generic |
| Test          | `test-specialist.agent.md`           | `{stack}-testing` or `testing` if generic               |
| Document      | `docs-curator.agent.md`              | `doc-sync`                                              |
| Review        | `review-auditor.agent.md`            | `{stack}-review` or `review` if generic                 |

For `{STACK}` ≠ generic: name stack-specific files as `{stack}-implementation-specialist.agent.md` etc. and register them with stack-prefixed skill names.

**Minimal stub template for every specialist:**

```
---
name: {Agent Name}
description: {one sentence — dev stage + what it does}
---

Handles the **{Dev Stage}** stage. {One sentence: what it does. One sentence: what it does NOT do.}

Before acting: read `.github/AGENTS.md` Skill Index → find this agent's row → load the SKILL.md listed in the "Loads Skill" column → follow skill steps.

## Contract
**Dev Stage**: {Scan | Plan | Design | Implement | Test | Document | Review}
**Loads Skill**: `{skill-name}` — path: `.github/skills/{skill-name}/SKILL.md`
**Accepts**: `verification-artifacts/{task-id}-input.json` (status: ready) + ledger stage=ASSIGNED + exit_criteria defined
**Produces**: `verification-artifacts/{task-id}-{type}.json`
**Does NOT start if**: input material not ready OR exit_criteria empty → emit MATERIAL_INSUFFICIENT to orchestrator
**Cannot self-certify**: requires non-author verification before emitting TASK_COMPLETE
**Return format**: Return EXACTLY: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only. No raw file contents.}`
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

Completion Promise: pending

## Materials

<!-- Governor-owned index: tracks file paths + status only. Contents live in the files themselves. -->

| role   | path                                         | schema   | status  |
| ------ | -------------------------------------------- | -------- | ------- |
| input  | verification-artifacts/[task-id]-input.json  | [schema] | pending |
| output | verification-artifacts/[task-id]-result.json | [schema] | empty   |

## Decisions Log

<!-- append-only -->
```

### 5D — Hooks (infrastructure support)

Hooks are infrastructure components that share gate-enforcement workload with the Governor. They are event listeners — not agents, not the adversarial layer. They read ledger state and emit signals; the Governor acts on those signals.

**Before generating any hook files:** search for and fetch the current VS Code agent hooks documentation:

- Use `fetch_webpage` with keywords `VS Code GitHub Copilot agent hooks customization Preview site:code.visualstudio.com OR site:docs.github.com`. Select the URL that is NOT a `github.io` legacy path and contains "2026" or "Preview" or "Current" in its content. Fetch that URL → note current field names and output shapes.
- **Verification**: If the fetched page does not contain "2026", "Preview", or "Current", discard and try the next result. If no valid result is found, fall back to built-in knowledge and note: `hooks schema unverified — using built-in knowledge`.
- Hooks are a Preview feature; the schema can change between VS Code releases. Use the fetched docs as the authoritative reference for all field names and output shapes when generating the files below.

All hooks read `hooks` from `.github/solar.config.json`. Set `"hooks": false` to disable all hooks globally — this is the single toggle for the entire hook system.

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

**Config note**: Hooks are **on by default** (`"hooks": true` in `solar.config.json`). Set `"hooks": false` to disable all hooks globally — one toggle controls everything.

**Optional hooks** (not generated by default — add as needed): `pre-tool-use`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`. For each: create the `.cjs` script in `.github/hooks/` and register it in `.github/hooks/hooks.json` following the same pattern as the two core hooks above.

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
2. Blockers — `BLOCKED: <one-line reason>` written to ledger ## Active Blockers
3. Artifacts — the final deliverable (code changes, design doc, handoff payload)

Do not narrate tool calls. Do not announce intent. Do not confirm routine actions in prose.
```

**`.github/instructions/{stack}.instructions.md`** — one stack file based on `{STACK}` and `{TEST_RUNNER}`:

- If `{STACK}` ≠ generic: generate a minimal instruction (under 20 lines) covering main frameworks, test runner `{TEST_RUNNER}`, lint tool, and key file paths detected in sweep
- If `{STACK}` = generic: generate a template with placeholder comments for each field
- Do not over-specify — agents fill in missing details on their first task

Note: instructions are auto-applied by platform via `applyTo`; they are not listed in Agent Registry or Skill Index. Note their `applyTo` patterns in the Repository Context section of AGENTS.md.

### 5F — Skills (dev lifecycle coverage)

Generate one `SKILL.md` per dev lifecycle step. Skills are loaded by agents at task time via the Skill Index — they are not pre-loaded. Each skill must be registered in AGENTS.md Skill Index.

**Required skills (always generate):**

| Dev Stage         | Skill name              | Folder                                  |
| ----------------- | ----------------------- | --------------------------------------- |
| Scan              | `data-collection`       | `.github/skills/data-collection/`       |
| Plan + Design     | `design-planning`       | `.github/skills/design-planning/`       |
| Implement         | `implementation`        | `.github/skills/implementation/`        |
| Test              | `testing`               | `.github/skills/testing/`               |
| Document          | `doc-sync`              | `.github/skills/doc-sync/`              |
| Review            | `review`                | `.github/skills/review/`                |
| Remediation (any) | `recursive-remediation` | `.github/skills/recursive-remediation/` |

For `{STACK}` ≠ generic: prefix the `implementation`, `testing`, and `review` folder names with the stack slug (e.g. `react-ts-implementation/`) and register them in the Skill Index alongside the generic counterparts.

**Minimal SKILL.md stub template (skill — domain knowledge):**

```markdown
# {Skill Name}

**Dev Stage**: {Scan | Plan | Design | Implement | Test | Document | Review}
**Purpose**: {one sentence}
**Loaded by**: `{agent-name}` when ledger stage = {stage}

## Steps

1. Read `verification-artifacts/{task-id}-input.json`
2. {Core action for this skill — 1–3 bullets, stack-tailored if {STACK} provided}
3. Write output to `verification-artifacts/{task-id}-{type}.json`
4. Append result summary to ledger Decisions Log
```

**Note — Playbooks also use SKILL.md format** but have a different body style:

- Skills = domain knowledge and tool patterns for a specialist (reference bullets, not steps)
- Playbooks = ordered numbered steps with gate conditions for the governor to follow inline

See the Playbook SKILL.md stub template in Step 5F-Playbooks below.

### 5F-Playbooks — Default playbooks (always generate)

Generate the following default playbook SKILL.md files. Register each in the AGENTS.md Playbook Index.

**Playbook SKILL.md stub template:**

```markdown
---
name: { playbook-name }
description:
  { one sentence — semantic trigger for VS Code auto-match; be precise }
---

# {Playbook Name}

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: {describe the user prompt pattern that activates this playbook}

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. If not → emit MATERIAL_INSUFFICIENT, do not proceed.
2. **[Dispatch: {specialist-name}]** Dispatch `{agent-file}.agent.md` as a subagent. Await artifact → `verification-artifacts/{task-id}-{type}.json`.
3. **[Gate: design approval]** Governor checks design output. If `config.human_approval = true` → use `vscode_askQuestions` to get user confirmation before proceeding. If rejected or changes requested → re-dispatch with feedback (Ralph loop, max 3 iterations).
4. **[Dispatch: {next-specialist}]** ...
5. **[Gate: adversarial verify]** Governor selects non-author specialist from Agent Registry (domain match) → dispatch for adversarial audit → verdict APPROVED or REJECTED.
6. **[Exit]** If APPROVED → update ledger CLOSED, clean up task artifacts. If REJECTED → return to producing agent.
```

**Required default playbooks:**

| Playbook name       | Description / semantic trigger                                     | Folder                              |
| ------------------- | ------------------------------------------------------------------ | ----------------------------------- |
| `implement-feature` | Triggered when user asks to implement, build, or add a feature     | `.github/skills/implement-feature/` |
| `bug-fix`           | Triggered when user asks to fix, debug, or resolve a bug or error  | `.github/skills/bug-fix/`           |
| `create-doc`        | Triggered when user asks to write, create, or update documentation | `.github/skills/create-doc/`        |

Generate a SKILL.md for each using the playbook stub above, with numbered steps tailored to the playbook's purpose and the detected `{STACK}`.

### 5G — Prompts (2 only)

**`.github/prompts/solar.prompt.md`** — entry point to start any SOLAR-managed task:

```
---
agent: agent
description: Start a SOLAR-managed task — orchestrator reads registry and dispatches the right specialist
---
You are the Orchestration Governor.

1. Read `.github/AGENTS.md` — load Agent Registry (Dev Stage + Loads Skill) and Skill Index.
2. Read `.github/.ai_ledger.md` — check for active or interrupted tasks.
   - INTERRUPTED row found → use `vscode_askQuestions`: "Previous task interrupted at stage {stage}. Resume or discard?"
   - No active task → continue.
3. Match the user prompt intent against the **Playbook Index** in AGENTS.md to select the playbook to follow.
   - Ambiguous or matches multiple playbooks → use `vscode_askQuestions` to confirm which playbook the user wants before dispatching anything.
   - Clear match → proceed with selected playbook inline.
4. Write a new Work Queue row immediately: task (from user prompt), selected playbook, status=PENDING, stage=SCAN, exit_criteria=TBD.
   - Prompt unclear → dispatch the Scan-stage agent from the registry first; use its output artifact to plan the stage sequence.
   - Prompt clear → plan the stage sequence in the ledger, then dispatch the first agent.
5. After each agent completes: mark current stage done in the Work Queue → add/update the Materials row with the output artifact path and status=ready → append a summary line to Decisions Log → advance stage.
6. Before each dispatch: run the 4-gate check (G1 materials-sufficient / G2 design-approved / G3 loop-bounds-ok / G4 previous-verified).
7. When all stages done: transition to VERIFY (adversarial audit) → select a non-author specialist from the Agent Registry that did NOT produce the output under review (prefer domain match: review-auditor for code, test-specialist for design, design-planning-architect for test coverage) → dispatch with output artifact as input → auditor produces `{task-id}-verify.json` (verdict: APPROVED or REJECTED + reasoning) → append verdict to Decisions Log → if REJECTED: return task to producing agent for remediation → emit TASK_COMPLETE only after APPROVED verdict is recorded.
8. On TASK_COMPLETE: (1) copy `.github/.ai_ledger.md` to `verification-artifacts/{YYYYMMDD}-{task-id}-ledger-archive.md` using `create_file`; (2) reset `.ai_ledger.md` from the Ledger Template block in `.github/AGENTS.md` Section 7; (3) delete `verification-artifacts/{task-id}-*` task artifact files; (4) set ledger row to CLOSED. Never touch rows marked INTERRUPTED.
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

### 5H — Solar-system reference files (minimal)

Generate as minimal reference docs — one paragraph per file is enough:

- `.github/solar-system/adversarial/skeleton-manifest.md` — adversarial trigger conditions + 5 injection patterns
- `.github/solar-system/protocols/inquiry-first.md` — canonical 4-gate contract table (G1–G4)
- `.github/solar-system/protocols/lifecycle-coordination.md` — VERIFY stage trigger mechanics

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

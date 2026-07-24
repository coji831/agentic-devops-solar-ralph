---
description: Verbatim file bodies for SOLAR-Ralph installation — read by solar-install.prompt.md via "→ Read INV:<slug>" directives. Each section contains one complete file body to copy verbatim.
---

# SOLAR-Ralph Installation Inventory

This file is the single source of truth for every verbatim file body generated during installation.
The main installer (`solar-install.prompt.md`) references sections here by slug using:
`→ Read INV:<slug> from solar-install-inventory.md and write verbatim to <target-path>.`

Sections are ordered by install step. Only replace `[FILL IN: ...]` tokens — all other content is copied as-is.

---

## INV:copilot-instructions

<!-- Target: .github/copilot-instructions.md -->

```
This repository uses the SOLAR-Ralph agent harness. Before every task:
1. Read .github/AGENTS.md — Agent Registry, Skill Index, ledger template, hook config, Repository Context.
2. Read .github/.ai_ledger.md (if it exists) — understand current task state and stage.
3. Orchestrator: read ledger stage → consult Agent Registry Dev Stage column → dispatch matching agent.
4. Agent: read task type → consult Skill Index → load the matching SKILL.md before acting.
5. All materials go in verification-artifacts/ only. TASK_COMPLETE requires adversarial audit: Governor dispatches a non-author specialist (domain-matched, not the artifact author) to verify output before closing.
```

---

## INV:solar-config

<!-- Target: .github/solar.config.json -->

```json
{
  "adversarial": true,
  "learning": false,
  "logging": false,
  "human_approval": true,
  "hooks": true
}
```

---

## INV:agents-md-sections-3-to-8

<!-- Target: appended to .github/AGENTS.md (after §1 What is this file, §2 Repository Context) -->
<!-- Replace [FILL IN] tokens for stack-specific agent/skill names. Leave all other content verbatim. -->

```
## §3 Agent Registry

| Name                                      | Dev Stage                | Role                                                                               | Loads Skill                            | Accepts                    | Produces                                  | Optional |
| ----------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------- | -------------------------------------- | -------------------------- | ----------------------------------------- | -------- |
| Orchestration Governor                    | —                        | Reads ledger stage → dispatches matching agent; owns exit decisions                | built-in                               | user prompt / ledger state | Work Queue row + Decisions Log entries    | No       |
| Context Summarizer                        | Scan (context pre-step)  | Reads source files and produces compact digests. Only agent with `read` tool.     | `context-summarization`                | task description + paths   | `{task-id}-digest.json`                   | No       |
| Data Collector Specialist                 | Scan                     | Gathers files and produces context manifest                                        | `data-collection`                      | digest + task description  | `{task-id}-scan.json`                     | No       |
| Design Planning Architect                 | Plan + Design            | Solution design, decomposition, tradeoff analysis                                  | `design-planning`                      | digest + scan findings     | `{task-id}-design.json`                   | No       |
| [FILL IN: Implementation Specialist name] | Implement                | Code changes scoped to task                                                        | `[FILL IN: implementation skill slug]` | digest + design plan       | `{task-id}-impl.json`                     | No       |
| [FILL IN: Test Specialist name]           | Test                     | Writes or repairs tests for the task output                                        | `[FILL IN: testing skill slug]`        | digest + impl summary      | `{task-id}-test.json`                     | No       |
| [FILL IN: Review Auditor name]            | VERIFY role              | Adversarial audit — dispatched by Governor at VERIFY step, not as a pipeline stage | `[FILL IN: review skill slug]`         | digest + artifact ref      | `{task-id}-verify.json`                   | No       |
| Docs Curator                              | Document                 | Keeps docs aligned with code changes                                               | `doc-sync`                             | digest + impl summary      | `{task-id}-docs.json`                     | No       |

**Agent Registry is a lookup table.** The Governor selects agents by Dev Stage role — row order does not control execution sequence. Execution sequence is defined by the Playbook SKILL.md.

**VERIFY dispatch**: no dedicated adversarial agent row. At the VERIFY step the Governor looks up the auditor role from this registry by domain match: code output → role `review-auditor`; design/docs output → role `design-planning-architect`. Do NOT hardcode stack-specific names in `solar.prompt.md`.

## §4 Skill Index

| Name                             | Dev Stage                | Purpose                                                                 | Path                                                  | Optional |
| -------------------------------- | ------------------------ | ----------------------------------------------------------------------- | ----------------------------------------------------- | -------- |
| `context-summarization`          | Scan (context pre-step)  | Read source files and produce compact digests for specialists           | `.github/skills/context-summarization/SKILL.md`       | No       |
| `data-collection`                | Scan                     | Gather files, run searches, produce context manifest                    | `.github/skills/data-collection/SKILL.md`             | No       |
| `design-planning`                | Plan + Design            | Solution design, architecture-fit, task decomposition                   | `.github/skills/design-planning/SKILL.md`             | No       |
| `[FILL IN: implementation slug]` | Implement                | Code changes per task                                                   | `.github/skills/[FILL IN: folder]/SKILL.md`           | No       |
| `[FILL IN: testing slug]`        | Test                     | Add or repair tests — ⚠ requires stack-specific runner setup before use | `.github/skills/[FILL IN: folder]/SKILL.md`           | No       |
| `[FILL IN: review slug]`         | VERIFY role              | Audit output — runs at VERIFY step, not as pipeline stage               | `.github/skills/[FILL IN: folder]/SKILL.md`           | No       |
| `doc-sync`                       | Document                 | Sync docs after code or process changes                                 | `.github/skills/doc-sync/SKILL.md`                    | No       |
| `recursive-remediation`          | Remediation              | Bounded repair loop for failed tests or review findings                 | `.github/skills/recursive-remediation/SKILL.md`       | No       |

## §5 Playbook Index

| Name                | Description                                                        | Path                                | Trigger                                       |
| ------------------- | ------------------------------------------------------------------ | ----------------------------------- | --------------------------------------------- |
| `implement-feature` | Triggered when user asks to implement, build, or add a feature     | `.github/skills/implement-feature/` | User prompt contains: implement / build / add |
| `bug-fix`           | Triggered when user asks to fix, debug, or resolve a bug or error  | `.github/skills/bug-fix/`           | User prompt contains: fix / debug / bug       |
| `create-doc`        | Triggered when user asks to write, create, or update documentation | `.github/skills/create-doc/`        | User prompt contains: write / create / doc    |

SOLAR-managed ordered step sequences the orchestrator follows inline. Custom playbooks: add a SKILL.md under `.github/skills/` and register a row here via `solar-registry-update`.

## §6 Hook Configuration

| Hook            | Trigger       | Script                            | Purpose                                                                        |
| --------------- | ------------- | --------------------------------- | ------------------------------------------------------------------------------ |
| `post-tool-use` | `PostToolUse` | `.github/hooks/post-tool-use.cjs` | Write-op guard → emit `ADVERSARIAL_VERIFY_REQUIRED` when ledger stage = VERIFY |

All hooks read `hooks` from `solar.config.json`. Set `false` to disable globally.

## §7 Ledger Template

## §8 Config Toggles

| Toggle           | Default | Effect                                                |
| ---------------- | ------- | ----------------------------------------------------- |
| `adversarial`    | `true`  | Adversarial audit gate active at VERIFY stage         |
| `learning`       | `false` | Learning system active — agents write to `learnings/` |
| `logging`        | `false` | Session logging active — hook writes to `logs/`       |
| `human_approval` | `true`  | Governor waits for user confirmation before dispatch  |
| `hooks`          | `true`  | All hooks active — set `false` to disable globally    |
```

---

## INV:governor-agent

<!-- Target: .github/agents/orchestration-governor.agent.md -->

```markdown
---
name: Orchestration Governor
description: SOLAR orchestrator — reads registry, dispatches specialists, enforces gates, manages the ledger. Always runs inline, never forked.
model: DeepSeek V4 Flash (deepseek)
tools: [vscode/askQuestions, agent/runSubagent, read, search, edit]
user-invocable: true
---

Follow `.github/prompts/solar.prompt.md` for all task management — startup, resume, dispatch, gate checks, and TASK_COMPLETE.
```

---

## INV:context-summarizer-agent

<!-- Target: .github/agents/context-summarizer.agent.md -->

```markdown
---
name: Context Summarizer
description: Reads source files and produces compact digests for specialists. Only agent with read privilege. Specialists get their context through this agent.
model: DeepSeek V4 Flash (deepseek)
tools: [read, search]
user-invocable: false
---

Handles context gathering for the pipeline. Reads source files, repository state, and task inputs — produces a compact digest that specialists consume instead of reading files directly. Does NOT design, implement code, test, review, or document.

Before acting: load the SKILL.md path provided in the dispatch prompt → follow skill steps exactly.

<constraints>
- Maximum 15 file reads per dispatch. If more needed: append `BLOCKED: task exceeds scope — ESCALATION_REQUIRED` to Decisions Log and return to Governor without acting.
- Do not expand scope beyond the current Work Package in `.github/.ai_ledger.md`. Discovered out-of-scope work: append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log only.
- Output must be a compact digest — no raw file contents. Use bullet summaries, path references, and key facts only.
- Return format: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only, no raw file contents.}`
</constraints>
```

---

## INV:specialist-agent-template

<!-- Target: each specialist .agent.md body (replace [FILL IN] tokens per agent) -->
<!-- Used for: data-collector, design-planning-architect, {stack}-implementation-specialist, {stack}-test-specialist, {stack}-review-auditor, docs-curator -->

```markdown
---
name: [FILL IN: agent name]
description: [FILL IN: one sentence — dev stage + what it does]
model: [FILL IN: model from naming table]
tools: [FILL IN: tools from naming table]
user-invocable: false
---

Handles the **[FILL IN: Dev Stage]** stage. [FILL IN: one sentence what it does.] [FILL IN: one sentence what it does NOT do.]

Context arrives via the dispatch prompt from the Governor — the Context Summarizer's digest is included inline with key facts, refs, and warnings. Do NOT read source files directly; use the digest for all context needs.

Before acting: load the SKILL.md path provided in the dispatch prompt → follow skill steps exactly.

<constraints>
- Input comes from digest only — do not read source files directly. If more needed: append `BLOCKED: task exceeds scope — ESCALATION_REQUIRED` to Decisions Log and return to Governor without acting.
- Do not expand scope beyond the current Work Package in `.github/.ai_ledger.md`. Discovered out-of-scope work: append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log only.
- Do not self-certify output. Requires non-author verification before emitting TASK_COMPLETE.
- Return format: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only, no raw file contents.}`
[FILL IN for Test Specialist only: - Requires stack-specific test runner configuration. Before dispatching: verify `tools:` includes the correct executor and SKILL.md has runner-specific steps.]
</constraints>

<tier_restrictions>
This agent handles the **[FILL IN: Dev Stage]** stage only. It does NOT:

- Perform work belonging to other dev stages — [FILL IN: list all dev stage names EXCEPT this agent's own stage].
- Self-escalate to TASK_COMPLETE — that is the Governor's gate decision.
- Expand scope for discovered work — append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log instead.
  </tier_restrictions>

<contract>
**Dev Stage**: [FILL IN: Scan | Plan + Design | Implement | Test | Document]
**Loads Skill**: `[FILL IN: skill-name]` — path: `.github/skills/[FILL IN: skill-name]/SKILL.md`
**Accepts**: `[FILL IN: input artifact path]` (status: ready) + ledger stage=ASSIGNED + exit_criteria defined
**Produces**: `verification-artifacts/{task-id}-[FILL IN: type].json`
**Does NOT start if**: input material not ready OR exit_criteria empty → emit MATERIAL_INSUFFICIENT to orchestrator
**Cannot self-certify**: requires non-author verification before emitting TASK_COMPLETE
**Return format**: Return EXACTLY: `{status: completed|partial|blocked}. Result: {artifact-path}. Summary: {2 sentences — key findings only. No raw file contents.}`
</contract>
```

---

## INV:ledger-template

<!-- Target: .github/.ai_ledger.md -->

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

## INV:hooks-json

<!-- Target: .github/hooks/hooks.json -->

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "command": "node .github/hooks/post-tool-use.cjs",
        "timeout": 20
      }
    ]
  }
}
```

---

## INV:common-cjs

<!-- Target: .github/hooks/common.cjs -->

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

module.exports = {
  loadConfig,
  readLedger,
  isSolarActive,
};
```

---

## INV:post-tool-use-cjs

<!-- Target: .github/hooks/post-tool-use.cjs -->

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

## INV:context-summarizer-instructions

<!-- Target: .github/instructions/context-summarizer.instructions.md -->

```markdown
---
description: Dispatch pattern for Context Summarizer. Referenced by solar.prompt.md step 3b.
applyTo: ".github/prompts/solar.prompt.md"
---

# Context Summarizer Dispatch Pattern

Before every specialist dispatch, the Governor must gather context via the Context Summarizer.

## Pattern

- Dispatch `context-summarizer.agent.md` with task description + target paths.
- SKILL: `.github/skills/context-summarization/SKILL.md`
- Result path: `verification-artifacts/{task-id}-digest.json`
- Await digest → read it (~20 lines, ~200 tokens) → include key facts inline in the specialist dispatch prompt.
- Do NOT pass the digest path for the specialist to read — specialists cannot read files directly.
```

---

## INV:solar-instructions

<!-- Target: .github/instructions/solar.instructions.md -->

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

---

## INV:skill-context-summarization

<!-- Target: .github/skills/context-summarization/SKILL.md -->

```markdown
# Context Summarization

**Dev Stage**: Scan (context-gathering step before any specialist dispatch)
**Purpose**: Read source files and produce a compact digest that the next specialist consumes instead of reading files directly.
**Loaded by**: `context-summarizer` when Governor dispatches before a specialist stage

## Steps

1. Read the dispatch prompt — extract the list of files/paths to investigate and the target specialist type.
2. For each target file or path:
   - Read key sections (entry points, interfaces, function signatures, relevant types).
   - Do NOT read full file bodies — use `startLine/endLine` for targeted reads.
   - Note file path, key exports, relevant patterns.
3. Build a compact digest:
   - `task_id` — the current work item ID.
   - `target_specialist` — which specialist this digest is for.
   - `refs[]` — array of `{path, section, relevance}` objects pointing to source files.
   - `facts[]` — bullet-point key facts the specialist needs to know (max 10 bullets, 1 line each).
   - `warnings[]` — anything the specialist should be cautious about.
4. Write output to `verification-artifacts/{task-id}-digest.json` with schema: `{ "task_id": "", "target_specialist": "", "refs": [], "facts": [], "warnings": [] }`.
5. Append digest summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Context gathered for {specialist} — {1-sentence summary of key facts delivered}`.
```

---

## INV:skill-data-collection

<!-- Target: .github/skills/data-collection/SKILL.md -->

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

---

## INV:skill-design-planning

<!-- Target: .github/skills/design-planning/SKILL.md -->

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

---

## INV:skill-implementation

<!-- Target: .github/skills/implementation/SKILL.md -->

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

---

## INV:skill-doc-sync

<!-- Target: .github/skills/doc-sync/SKILL.md -->

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

---

## INV:skill-review

<!-- Target: .github/skills/review/SKILL.md -->

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
   - Write the output to `verification-artifacts/{task-id}-{stage}-result.json`.
6. Append verdict to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: VERIFY {APPROVED|REJECTED} — {1-sentence reason}`.
```

---

## INV:skill-recursive-remediation

<!-- Target: .github/skills/recursive-remediation/SKILL.md -->

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

---

## INV:skill-testing

<!-- Target: .github/skills/testing/SKILL.md -->
<!-- Replace {TEST_RUNNER} with the value from Step 2 answers -->

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

---

## INV:playbook-implement-feature

<!-- Target: .github/skills/implement-feature/SKILL.md -->

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

---

## INV:playbook-bug-fix

<!-- Target: .github/skills/bug-fix/SKILL.md -->

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

---

## INV:playbook-create-doc

<!-- Target: .github/skills/create-doc/SKILL.md -->

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

---

## INV:solar-prompt

<!-- Target: .github/prompts/solar.prompt.md -->

```markdown
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

---

## INV:solar-registry-update-prompt

<!-- Target: .github/prompts/solar-registry-update.prompt.md -->

```markdown
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

---

## INV:adversarial-skeleton

<!-- Target: .github/solar-system/adversarial/skeleton-manifest.md -->

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

---

## INV:inquiry-first-protocol

<!-- Target: .github/solar-system/protocols/inquiry-first.md -->

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

---

## INV:lifecycle-coordination

<!-- Target: .github/solar-system/protocols/lifecycle-coordination.md -->

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

---

## INV:schema-envelopes

<!-- Target: each of the 6 minimal schema files below — write the same content to each -->
<!-- Files:
  .github/solar-system/schemas/designer-output.schema.json
  .github/solar-system/schemas/implementer-handoff.schema.json
  .github/solar-system/schemas/review-result.schema.json
  .github/solar-system/schemas/qa-result.schema.json
  .github/solar-system/schemas/scout-findings.schema.json
  .github/solar-system/schemas/dev-progress.schema.json
-->

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {}
}
```

---

## INV:verification-artifacts-readme

<!-- Target: verification-artifacts/README.md -->

```markdown
# Verification Artifacts

Lifecycle rules:

- Create `{task-id}-input.json` when a task is assigned (status: pending → ready when filled)
- Each pipeline stage writes its output artifact here: `{task-id}-{type}.json`
- Naming: `{task-id}-{type}.json` where type = scan | design | impl | test | docs | verify
- Clean up `{task-id}-*` files at TASK_COMPLETE (Governor archives ledger first)
- Default state: empty (only `.gitkeep` is committed)
```

---

## INV:report-template

<!-- Target: printed to chat at Step 6 — not a file write -->

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
Instructions: solar, context-summarizer, {stack}

Repository Context registered in AGENTS.md:
  Existing docs: {list or none}  ← available as Materials input for any task
  Existing instructions: {list or none}

Next steps:
  - Run the `solar` prompt to start your first task
  - Sync registry after any component change: run `solar-registry-update`
  - Tool-name notice: VS Code Copilot tool-set names may change between releases. Verify the `tools:` values in each generated `.agent.md` against the current VS Code docs at https://code.visualstudio.com/docs/copilot/customization/custom-agents. Flag any tool-set name not found in that page.
```

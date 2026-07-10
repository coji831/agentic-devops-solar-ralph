# SOLAR Framework — Scan & Comparison Report

**Date**: 2026-05-23
**Scope**: Fundamentals only — concept → install prompt → template scaffold → mandarin installation
**Purpose**: Identify alignment, gaps, and fix candidates across all four layers

---

## Summary

| Axis | Pair                         | Status                                                                              | Gap Count          |
| ---- | ---------------------------- | ----------------------------------------------------------------------------------- | ------------------ |
| 1    | Concept ↔ Install Prompt     | Mostly aligned — 2 concept staleness gaps                                           | 2                  |
| 2    | Install Prompt ↔ Template    | Aligned except 1 critical defect                                                    | 1                  |
| 3    | Template Scaffold ↔ Mandarin | Aligned on fundamentals; mandarin extends in all areas                              | 0 fundamental gaps |
| 4    | Mandarin Customizations      | Cataloged (intentional project + token hotfixes)                                    | —                  |
| 5    | Content Scan — hook files    | **CRITICAL: template hooks are wrong v4.1 system; mandarin post-tool-use is NO-OP** | 5                  |

---

## Axis 1 — Concept ↔ Install Prompt

**Source**: `docs/solar-ralph-concept.md`
**Target**: `solar-install.prompt.md`

### What was verified

Every structural concept element maps to a generated artifact:

| Concept Element                                                                     | Install Prompt Coverage                                                         | Status  |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------- |
| Specialist — forked, YAML-declared, communicates via verification-artifacts/ only   | §3 Agent Registry skeleton, specialist `.agent.md` constraints block            | ALIGNED |
| Orchestrator — always inline, owns all gates, G1–G4                                 | `solar.prompt.md` Step 3 execute loop + G1–G4 gate table                        | ALIGNED |
| Ledger — sparse, materials as links only, no Active Blockers section                | §7 Ledger Template in AGENTS.md, Step 5C in install prompt                      | ALIGNED |
| Adversarial — non-author, domain-matched, triggered at VERIFY                       | AGENTS.md §3 VERIFY dispatch note, `solar.prompt.md` Step 3d, `review.SKILL.md` | ALIGNED |
| Ralph Loop — exit criteria required, OR-logic termination                           | `solar.prompt.md` Step 3, loop state in Ledger Template                         | ALIGNED |
| Material gate (G1) fires before every dispatch                                      | `solar.prompt.md` G1 gate, specialist `<constraints>` "Does not start if..."    | ALIGNED |
| BLOCKED in Decisions Log, not Active Blockers section                               | `solar.prompt.md` Step 3a blocked → "append BLOCKED to Decisions Log"           | ALIGNED |
| AGENTS.md = single source of truth                                                  | `copilot-instructions.md` step 1 + `solar.instructions.md`                      | ALIGNED |
| Playbook vs Skill distinction (orchestrator uses playbooks; specialists use skills) | §4 Skill Index + §5 Playbook Index separation, AGENTS.md note text              | ALIGNED |
| Communication Discipline — silent operation, signals only                           | `solar.instructions.md` step 5E has Communication Discipline section            | ALIGNED |
| Config = 5 toggles                                                                  | `solar.config.json` exactly 5 fields                                            | ALIGNED |

### Gaps

**G1 — Concept: artifact naming is stale (`{task-id}-{type}.md` vs `.json`)**

The concept Helper Layer table describes Verification Artifacts as:

> "Typed artifact files `{task-id}-{type}.md`; empty by default; cleaned up when ledger closes task"

But the install prompt, all skill SKILL.md files, all schema files, and all AGENTS.md §7 Ledger Template entries use `.json` (e.g. `{task-id}-scan.json`, `{task-id}-design.json`). The concept's `.md` description is stale.

- Fix: update concept Helper Layer table cell to `{task-id}-{type}.json`.

---

**G2 — Concept: "One setup prompt only" conflicts with two generated prompts**

Concept Optional Layer says:

> "Prompts — One `setup` prompt only; everything else is playbooks"

But install prompt Step 5G generates **two** prompts:

- `solar.prompt.md` — task entry point
- `solar-registry-update.prompt.md` — registry sync utility

`solar-registry-update` is a utility prompt, not a task playbook, so this does not violate the spirit of the rule. But the concept text implies only one. Either:

- Clarify the concept: "One task-entry prompt + one optional utility prompt", or
- Add a note to install prompt that `solar-registry-update` is an admin utility, not a task trigger

---

## Axis 2 — Install Prompt ↔ Template Scaffold

**Source**: `solar-install.prompt.md` (Steps 5A–5I file manifest)
**Target**: `template/.github/`

### File manifest comparison

| Install Prompt Promise                                     | Template File                                                                                                                                                                       | Status               |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `.github/AGENTS.md`                                        | ✓ Present, 8 sections, line index, verbatim skeleton                                                                                                                                | ALIGNED              |
| `.github/copilot-instructions.md`                          | ✓ Exact 5-step checklist                                                                                                                                                            | ALIGNED              |
| `.github/solar.config.json`                                | ✓ Present — **see defect below**                                                                                                                                                    | DEFECT               |
| `.github/.ai_ledger.md`                                    | ✓ Empty template with all 5 sections                                                                                                                                                | ALIGNED              |
| `.github/agents/` (7 files)                                | ✓ All 7 agent files present: orchestration-governor, data-collector-specialist, design-planning-architect, implementation-specialist, test-specialist, review-auditor, docs-curator | ALIGNED              |
| `.github/hooks/hooks.json`                                 | ✓ PostToolUse + Stop only                                                                                                                                                           | ALIGNED              |
| `.github/hooks/common.cjs`                                 | ✓ Present (loadConfig, readLedger, isSolarActive)                                                                                                                                   | ALIGNED              |
| `.github/hooks/post-tool-use.cjs`                          | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/hooks/stop.cjs`                                   | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/instructions/solar.instructions.md`               | ✓ Present including Communication Discipline section                                                                                                                                | ALIGNED              |
| `.github/instructions/generic.instructions.md`             | ✓ Present — has unfilled `<!-- not detected — fill in -->` stubs (expected for reference template)                                                                                  | ALIGNED (note below) |
| `.github/prompts/solar.prompt.md`                          | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/prompts/solar-registry-update.prompt.md`          | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/skills/` (10 folders)                             | ✓ All 10 present: data-collection, design-planning, implementation, testing, review, doc-sync, recursive-remediation, implement-feature, bug-fix, create-doc                        | ALIGNED              |
| `.github/solar-system/adversarial/skeleton-manifest.md`    | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/solar-system/protocols/inquiry-first.md`          | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/solar-system/protocols/lifecycle-coordination.md` | ✓ Present                                                                                                                                                                           | ALIGNED              |
| `.github/solar-system/schemas/` (6 files)                  | ✓ All 6 stubs present                                                                                                                                                               | ALIGNED              |
| `verification-artifacts/README.md`                         | Need to verify                                                                                                                                                                      | —                    |
| `verification-artifacts/.gitkeep`                          | Need to verify                                                                                                                                                                      | —                    |

### Gaps

**G3 — CRITICAL: template `solar.config.json` has `"hooks": false`**

Install prompt (Step 5A) specifies the generated `solar.config.json` as:

```json
{
  "adversarial": true,
  "learning": false,
  "logging": false,
  "human_approval": true,
  "hooks": true
}
```

The template file has:

```json
{
  "adversarial": true,
  "learning": false,
  "logging": false,
  "human_approval": true,
  "hooks": false
}
```

`"hooks": false` disables all hooks globally. Any repo seeded from this template will have hooks silently off by default — defeating the guard mechanism. This is a **defect in the template**, not an intentional setting.

- Fix: change template `solar.config.json` `"hooks": false` → `"hooks": true`.

---

**Note — generic.instructions.md unfilled stubs**

Template `generic.instructions.md` has `<!-- not detected — fill in -->` placeholders for Lint Config, Key File Paths (5 entries). This is expected behavior for a reference scaffold — the install prompt's Step 5E instructs agents to fill these from sweep findings at install time. Not a gap; document as expected.

---

**Note — solar_version absent from both install prompt and template**

Neither the install prompt Step 6 report nor the AGENTS.md skeleton include a `solar_version` field. This is an **enhancement request** (tracking installed version), not a regression from a specified requirement. Flagged for later.

---

## Axis 3 — Template Scaffold ↔ Mandarin Installation

**Source**: `template/.github/`
**Target**: `mandarin-vite-react-ts/.github/`

### Fundamentals comparison

| Component                      | Template                                     | Mandarin                                                                                               | Delta                                     | Status                |
| ------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------- | --------------------- |
| AGENTS.md sections             | 8 (§1–§8)                                    | 8 (§1–§8)                                                                                              | None                                      | ALIGNED               |
| §3 Agent Registry rows         | 7 (generic names)                            | 7 (generic names)                                                                                      | None                                      | ALIGNED               |
| §4 Skill Index rows            | 7                                            | 7                                                                                                      | None                                      | ALIGNED               |
| §5 Playbook Index rows         | 3                                            | 5                                                                                                      | +story-level-dev, +create-epic-story-docs | EXTENDED              |
| Core agent files               | 7                                            | 7                                                                                                      | None                                      | ALIGNED               |
| Core skill files               | 7                                            | 7                                                                                                      | None                                      | ALIGNED               |
| Playbook files                 | 3 (implement-feature, bug-fix, create-doc)   | 5                                                                                                      | +2 project playbooks                      | EXTENDED              |
| Hooks in hooks.json            | 2 (PostToolUse, Stop)                        | 3 (PreToolUse, PostToolUse, Stop)                                                                      | +pre-tool-use                             | EXTENDED              |
| Hook script files              | 4 (common, hooks.json, post-tool-use, stop)  | 5 (+pre-tool-use.cjs)                                                                                  | +1                                        | EXTENDED              |
| Protocols                      | 2 (inquiry-first, lifecycle-coordination)    | 4 (+effective-tokens, +guardrails-signals)                                                             | +2 token protocols                        | EXTENDED              |
| Schemas                        | 6                                            | 13                                                                                                     | +7 telemetry schemas                      | EXTENDED              |
| solar.config.json base fields  | 5 (hooks=**false** defect)                   | 5 (hooks=**true** correct)                                                                             | Mandarin fixed defect                     | EXTENDED + FIXES G3   |
| solar.config.json extra fields | 0                                            | 14 (token guardrail config)                                                                            | +14                                       | EXTENDED              |
| copilot-instructions.md        | 5-step SOLAR checklist                       | 5-step + PinyinPal playbook (patch merge)                                                              | Customized                                | CUSTOMIZED            |
| solar.instructions.md          | 5-step + Communication Discipline            | 5-step + Communication Discipline                                                                      | None                                      | ALIGNED               |
| §6 Hook Configuration table    | 2 hooks                                      | 3 hooks (+pre-tool-use row)                                                                            | Consistent with hooks.json                | EXTENDED              |
| §2 Repository Context          | "solar-template" placeholder                 | PinyinPal project context                                                                              | Install-time fill                         | EXPECTED              |
| .ai_ledger.md                  | Empty template                               | Active (live task entries)                                                                             | In-use repo                               | EXPECTED              |
| post-tool-use.cjs              | Write-op guard + ADVERSARIAL_VERIFY_REQUIRED | Above + telemetry write + episode aggregation                                                          | Extended for token efficiency             | EXTENDED              |
| common.cjs                     | loadConfig, readLedger, isSolarActive        | Above + estimateTokens, getTelemetryModelMultipliers, resolveModelMultiplier, calculateEffectiveTokens | Extended for token efficiency             | EXTENDED              |
| solar_version                  | Absent                                       | Absent                                                                                                 | Confirmed gap in both                     | PENDING (enhancement) |
| copilot-instructions.patch.md  | Empty scaffold                               | Conflict marker (install collision)                                                                    | Expected                                  | EXPECTED              |

**Finding**: No fundamental regressions. Mandarin extends in all areas beyond the template baseline. Mandarin also corrects the `hooks: false` defect (G3) in its own installation.

---

## Axis 4 — Mandarin Customizations Catalog

### Project Customizations (PinyinPal-specific, not framework gaps)

| Item                              | Files                                            | Notes                                                                                                   |
| --------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `story-level-dev` playbook        | `.github/skills/story-level-dev/SKILL.md`        | Full story cycle: review AC → plan → implement → test → docs → gates → commit                           |
| `create-epic-story-docs` playbook | `.github/skills/create-epic-story-docs/SKILL.md` | Epic/story BR + implementation doc creation with templates                                              |
| PinyinPal copilot-instructions.md | `.github/copilot-instructions.md`                | Full PinyinPal playbook: architecture, state rules, testing rules, git conventions, automation protocol |
| Test Specialist configuration     | `.github/agents/test-specialist.agent.md`        | Vitest + RTL stack configuration                                                                        |
| §2 Repository Context             | `.github/AGENTS.md`                              | PinyinPal stack, existing docs list                                                                     |

### Token-Efficiency Hotfixes (candidates for upstream framework consideration)

| Hotfix                            | Files                                                  | Pattern                                                                                                                                                 |
| --------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H1 — `pre-tool-use.cjs`           | `.github/hooks/pre-tool-use.cjs`                       | Pre-dispatch guardrail: checks hardFailSignals; emits deny on hard-fail, warning otherwise                                                              |
| H2 — Extended `post-tool-use.cjs` | `.github/hooks/post-tool-use.cjs`                      | Telemetry infra (currently commented out) — captures guardrailSignals, batonRef, ET; appends TOKEN_USAGE/GUARDRAIL_FIRED entries to ledger              |
| H3 — Extended `common.cjs`        | `.github/hooks/common.cjs`                             | estimateTokens, buildTelemetryRecord, calculateEffectiveTokens — ET = m × (1.0I + 0.1Cr + 4.0O)                                                         |
| H4 — `guardrails-signals.md`      | `.github/solar-system/protocols/guardrails-signals.md` | Signal classification: warn-only vs hard-fail (DUPLICATE_READ_DETECTED, LARGE_READ_WINDOW, etc.)                                                        |
| H5 — `effective-tokens.md`        | `.github/solar-system/protocols/effective-tokens.md`   | ET formula definition, multiplier version tracking                                                                                                      |
| H6 — 7 extra schemas              | `.github/solar-system/schemas/`                        | telemetry-call, episode-telemetry, compaction-telemetry, jit-toolload-telemetry, artifactization-receipt, compact-handoff-packet, telemetry.schema.json |
| H7 — 14 extra config fields       | `.github/solar.config.json`                            | maxDispatchInputTokens, maxHighCostDispatchTokens, hardFailSignals, telemetry.modelMultipliersVersion, experiment.mode, etc.                            |
| H8 — Communication Discipline     | `.github/instructions/solar.instructions.md`           | Token compaction rules — **already merged into template**                                                                                               |

---

## Axis 5 — Content Scan: Hook File Bodies

**Scope**: Actual file contents vs install prompt spec verbatim bodies (Steps 5D).

### Install prompt spec (simple harness)

- `common.cjs` — 3 exports: `loadConfig`, `readLedger`, `isSolarActive`
- `post-tool-use.cjs` — write-op guard; emits `ADVERSARIAL_VERIFY_REQUIRED` via `hookSpecificOutput` when ledger stage = VERIFY
- `stop.cjs` — `stop_hook_active` infinite-loop guard + ledger pending/fail check; blocks via `hookSpecificOutput.decision: "block"`

### Template hook files — WRONG: old v4.1 system

All three template hook files are from an older, heavier v4.1 system. They do **not** match the install prompt spec.

**`common.cjs`** — v4.1 (200+ lines, 12 exports):
Exports include `logHookExecution`, `isBootstrapMode`, `resolveSessionLogDir`, `resolveLearningsDir`, `resolveErrorsPath`, `resolveDebugLogPath` — none of these exist in the spec. Implements hook log rotation, session log directory management, ERRORS.md/PATTERNS.md path resolution.

**`post-tool-use.cjs`** — v4.1, ADVERSARIAL guard unreachable:
Gates on `config.hooks.postToolUse.enabled` (nested key that does not exist in the 5-field solar.config.json). Always exits without acting. Has TypeScript check (`execSync` tsc), session log append, terminal tracking. `ADVERSARIAL_VERIFY_REQUIRED` injection is buried and unreachable. **Net effect: complete NO-OP.**

**`stop.cjs`** — v4.1, wrong output format:
Uses `console.log({ continue: true, systemMessage: "..." })` (old API). Spec requires `process.stdout.write({ hookSpecificOutput: { hookEventName: "Stop", decision: "block", reason } })`. Also calls `common.logHookExecution()` which is absent from the correct simple common.cjs. Missing `stop_hook_active` infinite-loop guard.

### Mandarin hook files — mixed state

**`common.cjs`** — CORRECT. Minimal base (loadConfig, readLedger, isSolarActive) + token telemetry extensions (intentional).

**`post-tool-use.cjs`** — WRONG: adversarial guard missing. The telemetry infra (`writePhase1Telemetry`) is defined but **commented out**. The write-op detection + ADVERSARIAL_VERIFY_REQUIRED injection block was never added. Hook is a **complete NO-OP**.

**`stop.cjs`** — CORRECT. Matches spec exactly: `stop_hook_active` guard, `hookSpecificOutput.decision: "block"`, `process.stdout.write`.

**`pre-tool-use.cjs`** — CORRECT (mandarin addition). Minimal stdin/stdout pattern; reads hardFailSignals; emits deny or warning.

### Content scan summary

| File                                                            | Template                                           | Mandarin                                     | Status           |
| --------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------- | ---------------- |
| `common.cjs`                                                    | v4.1 wrong exports                                 | Correct base + token extensions              | Template WRONG   |
| `post-tool-use.cjs`                                             | v4.1 wrong config gate, adversarial unreachable    | Adversarial missing, telemetry commented out | **Both WRONG**   |
| `stop.cjs`                                                      | v4.1 wrong output format, missing stop_hook_active | Correct                                      | Template WRONG   |
| `pre-tool-use.cjs`                                              | Not present                                        | Correct guardrail gate                       | Mandarin CORRECT |
| `hooks.json`                                                    | Correct (PostToolUse + Stop)                       | Correct (PreToolUse + PostToolUse + Stop)    | ALIGNED          |
| `solar.config.json`                                             | hooks: false                                       | hooks: true + 14 fields                      | Template WRONG   |
| `testing/SKILL.md`                                              | Vitest hardcoded, `[FILL IN]` at step 3            | n/a                                          | Template minor   |
| All agents, skills (non-testing), prompts, protocols, AGENTS.md | Correct — match install prompt spec                | Correct + project extensions                 | ALIGNED          |

---

## Fix Plan

### CRITICAL — Hook files must be replaced

| ID  | Fix                                             | File                                                     | Change                                                                                                         |
| --- | ----------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| F1  | Replace template common.cjs                     | `template/.github/hooks/common.cjs`                      | Replace v4.1 200-line system with install prompt spec (3 exports: loadConfig, readLedger, isSolarActive)       |
| F2  | Replace template post-tool-use.cjs              | `template/.github/hooks/post-tool-use.cjs`               | Replace v4.1 system with install prompt spec: write-op guard + ADVERSARIAL_VERIFY_REQUIRED injection           |
| F3  | Replace template stop.cjs                       | `template/.github/hooks/stop.cjs`                        | Replace v4.1 system with install prompt spec: stop_hook_active guard + hookSpecificOutput format               |
| F4  | Fix template solar.config.json                  | `template/.github/solar.config.json`                     | `"hooks": false` → `"hooks": true`                                                                             |
| F5  | Add adversarial guard to mandarin post-tool-use | `mandarin-vite-react-ts/.github/hooks/post-tool-use.cjs` | Add write-op detection + ADVERSARIAL_VERIFY_REQUIRED injection block before the (commented-out) telemetry call |

### Concept alignment (staleness)

| ID  | Fix                         | File                          | Change                                                                            |
| --- | --------------------------- | ----------------------------- | --------------------------------------------------------------------------------- |
| F6  | Fix artifact file extension | `docs/solar-ralph-concept.md` | Helper Layer table: `{task-id}-{type}.md` → `{task-id}-{type}.json`               |
| F7  | Clarify one-prompt rule     | `docs/solar-ralph-concept.md` | Optional Layer: note `solar-registry-update` is admin utility, not a task trigger |

### Minor template cleanup

| ID  | Fix                                    | File                                       | Change                                                                                            |
| --- | -------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| F8  | Fix testing/SKILL.md test runner token | `template/.github/skills/testing/SKILL.md` | Replace hardcoded `Vitest` with `{TEST_RUNNER}`; fill the `[FILL IN]` at step 3 with generic note |

### Enhancements (tracked, not regressions)

| ID  | Enhancement                               | Target                                         | Notes                                    |
| --- | ----------------------------------------- | ---------------------------------------------- | ---------------------------------------- |
| E1  | Add solar_version stamp                   | Install prompt Step 5A + template AGENTS.md §8 | Add as Config Toggles row or §1 metadata |
| E2  | Document pre-tool-use as optional pattern | Install prompt Step 5D hooks note              | Brief pattern note from mandarin H1      |

---

## Observations

1. **Template hooks are the most urgent fix**: all three `.cjs` files are from an unrelated v4.1 system. Any repo seeded from the template today gets broken hooks — post-tool-use is a NO-OP, stop uses the wrong API format, common.cjs exports functions the simple hooks don't call.
2. **Mandarin post-tool-use is also broken**: the adversarial guard was never added; telemetry is commented out. The hook does nothing. Fix F5 needed before any telemetry work can be validated.
3. **Mandarin stop.cjs is the correct reference**: use it verbatim as the baseline for the template fix (F3).
4. **Everything else in template is correct**: agents, skills, prompts, AGENTS.md, protocols, schemas all match the install prompt spec. Damage is isolated to the three hook files and solar.config.json.
5. **Concept patches are minimal**: two targeted text fixes only — no structural changes needed.

## Axis 4 — Mandarin Customizations Catalog

### Project Customizations (PinyinPal-specific, not framework gaps)

| Item                              | Files                                            | Notes                                                                                                   |
| --------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `story-level-dev` playbook        | `.github/skills/story-level-dev/SKILL.md`        | Full story cycle: review AC → plan → implement → test → docs → gates → commit                           |
| `create-epic-story-docs` playbook | `.github/skills/create-epic-story-docs/SKILL.md` | Epic/story BR + implementation doc creation with templates                                              |
| PinyinPal copilot-instructions.md | `.github/copilot-instructions.md`                | Full PinyinPal playbook: architecture, state rules, testing rules, git conventions, automation protocol |
| Test Specialist configuration     | `.github/agents/test-specialist.agent.md`        | Vitest + RTL stack configuration                                                                        |
| §2 Repository Context             | `.github/AGENTS.md`                              | PinyinPal stack, existing docs list                                                                     |

### Token-Efficiency Hotfixes (candidates for upstream framework consideration)

These are mandarin-originated extensions. The install prompt does not generate them. Listed for later upstream improvement work.

| Hotfix                                | Files                                                        | Pattern                                                                                                                                                                                                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H1 — `pre-tool-use.cjs` hook          | `.github/hooks/pre-tool-use.cjs`, `.github/hooks/hooks.json` | Pre-dispatch guardrail: reads solar.config.json hardFailSignals + maxDispatchInputTokens; emits `deny` on hard-fail; soft-block warning otherwise                                                                                                                                                              |
| H2 — Extended `post-tool-use.cjs`     | `.github/hooks/post-tool-use.cjs`                            | Telemetry write on every tool call: captures guardrailSignals, batonRef, tool_schema_token_load_size; writes timestamped telemetry artifacts; appends TOKEN_USAGE/GUARDRAIL_FIRED/TOOLSET_LOADED entries to ledger; upserts episode-telemetry.json                                                             |
| H3 — Extended `common.cjs`            | `.github/hooks/common.cjs`                                   | `estimateTokens()`, `getTelemetryModelMultipliers()`, `resolveModelMultiplier()`, `calculateEffectiveTokens()` — supports ET = m × (1.0I + 0.1Cr + 4.0O) formula                                                                                                                                               |
| H4 — `guardrails-signals.md` protocol | `.github/solar-system/protocols/guardrails-signals.md`       | Signal classification: warn-only vs hard-fail candidates (DUPLICATE_READ_DETECTED, LARGE_READ_WINDOW, DISPATCH_CONTEXT_OVER_BUDGET, DELTA_HANDOFF_SCHEMA_MISSING, etc.)                                                                                                                                        |
| H5 — `effective-tokens.md` protocol   | `.github/solar-system/protocols/effective-tokens.md`         | ET formula definition, multiplier version tracking                                                                                                                                                                                                                                                             |
| H6 — 7 extra telemetry schemas        | `.github/solar-system/schemas/`                              | telemetry-call, episode-telemetry, compaction-telemetry, jit-toolload-telemetry, artifactization-receipt, compact-handoff-packet, expanded telemetry.schema.json                                                                                                                                               |
| H7 — 14 extra config fields           | `.github/solar.config.json`                                  | maxDispatchInputTokens, maxHighCostDispatchTokens, maxHighCostPromptChars, maxReadWindowLines, maxReadsPerFilePerSession, requireArtifactRefForHighCost, enforceDeltaForRedispatch, artifactizationThresholdTokens, sessionBlockThreshold, hardFailSignals, telemetry.modelMultipliersVersion, experiment.mode |
| H8 — Communication Discipline         | `.github/instructions/solar.instructions.md`                 | Token compaction rules for agent communication — **already merged into template**                                                                                                                                                                                                                              |

---

## Fix Plan

### Critical (breaks expected behavior)

| ID  | Fix                   | File                                 | Change                             |
| --- | --------------------- | ------------------------------------ | ---------------------------------- |
| F1  | Correct hooks default | `template/.github/solar.config.json` | `"hooks": false` → `"hooks": true` |

### Concept alignment (staleness)

| ID  | Fix                                     | File                          | Change                                                                                                       |
| --- | --------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------ |
| F2  | Fix artifact file extension description | `docs/solar-ralph-concept.md` | Helper Layer table: `{task-id}-{type}.md` → `{task-id}-{type}.json`                                          |
| F3  | Clarify one-prompt rule                 | `docs/solar-ralph-concept.md` | Optional Layer Prompts note: clarify `solar.prompt.md` = task entry, `solar-registry-update` = admin utility |

### Enhancements (tracked, not regressions)

| ID  | Enhancement                                         | Target                                         | Notes                                                                                  |
| --- | --------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| E1  | Add `solar_version` stamp                           | Install prompt Step 5A + template AGENTS.md §8 | Add as Config Toggles row or §1 metadata                                               |
| E2  | Document pre-tool-use as optional framework pattern | Install prompt Step 5D hooks note              | Add to "Optional hooks" note with brief pattern description from H1                    |
| E3  | Surface Communication Discipline in install output  | Install prompt Step 5E                         | Already in template solar.instructions.md — verify install prompt Step 5E spec matches |

### Low priority / acceptable as-is

| ID  | Note                                                                      | Rationale                                                                                                                                                          |
| --- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| N1  | generic.instructions.md has unfilled stubs                                | Expected for reference template; install fills from sweep                                                                                                          |
| N2  | design-planning, testing, doc-sync SKILL.md files have `[FILL IN]` tokens | Expected; agents fill on first use                                                                                                                                 |
| N3  | Concept invariants are not numbered                                       | Prior plan referenced "8 invariants"; current concept.md does not use a numbered invariants list — no fix needed, prior plan was based on an older concept version |

---

## Observations

1. **Template → Mandarin is clean**: no fundamental regressions; all deltas are intentional extensions.
2. **Mandarin fixed G3**: the `hooks: false` defect in the template was corrected in mandarin. Fix needs to flow back to template (F1).
3. **Communication Discipline is already in template**: H8 was backported. solar.instructions.md in both template and mandarin are identical on this point.
4. **Token hotfixes (H1–H7) are mandarin-only**: no upstream equivalent exists. They are well-scoped and candidates for optional install prompt additions in a future pass.
5. **Concept is mostly accurate**: only two stale descriptions (G1: artifact extension, G2: one-prompt clarification). The concept does not require a major rewrite — targeted patches only.

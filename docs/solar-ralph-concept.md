# SOLAR-Ralph — Canonical Concept

Lightweight AI agent harness built on five composable layers. Template lives in `template/`; install into any repo via `solar-install.prompt.md`.

---

## Industry Comparison

| SOLAR Concept          | Industry Equivalent                                                                          | Key Learning                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Specialist**         | CrewAI Agent (`role/goal/backstory/tools` in YAML)                                           | YAML registry = the swap/add/remove mechanism — declarative, not hardcoded      |
| **Orchestrator**       | CrewAI Flow (`@start` → `@listen` → `@router`)                                               | Purely event-driven; reads state, fires next node, never executes tasks         |
| **Ledger**             | CrewAI Flow State (Pydantic `BaseModel`) + task `context` chain                              | Typed state object; materials pass via reference, never embedded                |
| **Ralph Loop**         | AutoGen `MaxMessageTermination \| TextMentionTermination \| FunctionCallTermination`         | Combine numeric cap + semantic keyword + function call approval — OR logic      |
| **Adversarial**        | CrewAI critic agent (primary + critic in round-robin)                                        | Bystander = non-author; triggered by stage transition, not hardcoded role name  |
| **AGENTS.md**          | CrewAI `agents.yaml` + `tasks.yaml` merged                                                   | Single-file portable bootstrap manifest                                         |
| **Context Summarizer** | Anthropic orchestrator-workers pattern (central coordinator delegates to restricted workers) | Dedicated reader agent produces compact digest; specialists have no `read` tool |
| **Hooks**              | CrewAI `callback` + middleware pipeline                                                      | Stateless post-task signals; not orchestration logic                            |
| **Installation**       | `crewai create crew` CLI scaffolds from YAML                                                 | One file bootstraps everything — proven viable                                  |

---

## Core Layer

### Specialist

- YAML-declared: `role`, `goal`, `constraints`, `tools`, `accepts` (input schema), `produces` (output schema)
- Registry in AGENTS.md — swap = update one YAML entry
- Runs in a **forked context** (subagent via tool call): isolated, returns one artifact path; failure is contained
- **No `read` tool** — context arrives via compact digest from the Context Summarizer, passed inline by the Governor
- Communicates **only** via structured handoff written to `verification-artifacts/` and referenced in the ledger — never direct agent-to-agent
- Gate before start: check ledger for `input_material: ready`. If not set → emit `MATERIAL_INSUFFICIENT` to orchestrator; do not start
- Design gate: orchestrator writes `design` artifact, user approves (`stage: APPROVED`), then specialist starts
- Writes step status to ledger **before returning** — enables recovery from last completed step on interruption

### Context Summarizer

- Only agent with the `read` tool — all source-file reads go through it
- Dispatched by Governor before every specialist stage
- Reads task-relevant files and produces a compact digest (`{task-id}-digest.json`): key facts, file refs, warnings
- Digest is ~20 lines (~200 tokens); Governor reads it and includes key facts inline in the specialist dispatch prompt
- Prevents context bloat from incidental file exploration by specialists

### Orchestrator

- Pure event-driven: reads ledger stage → dispatches specialist → advances stage
- Four read-only checks before any dispatch: (1) materials-sufficient? (2) design-approved? (3) loop bounds ok? (4) previous stage verified?
- **Always runs inline** — never forked. Owns all gates, adversarial dispatch, loop iteration, and ledger writes
- **Playbook selection**: semantically matches user prompt to Playbook Index; ambiguous match → `askQuestion` before dispatch — never assumes
- **Dispatch context**: every `runSubagent` call should include the current stage, the context digest (inline), relevant artifact paths, and the specialist's registry entry — keeping the dispatch prompt self-contained.
- Parallel dispatch: queue independent tasks in ledger Work Queue with `status: PENDING`; fires in parallel when no inter-dependency
- Resume: reads ledger cold on restart → identifies last `DONE` step → re-dispatches from next `PENDING`; no restart from scratch

### Ledger (single sparse document)

```
## Objective
## Work Queue
| id | task | agent | status | stage |
## Decisions Log (append-only)
```

- Sparse: fields only populated when content exists
- Blockers appended to Decisions Log as `BLOCKED: <reason>` — no separate `## Active Blockers` section

### Adversarial

- Not a named role: any agent that did **not** produce the output verifies it
- Triggered by ledger stage transition to `VERIFY` — orchestrator dispatches a domain-matched uninvolved specialist from Agent Registry; never hardcoded by name
- **Conditional VERIFY**: run for code/design/doc output; skip for scan handoffs and ledger/registry updates (no artifact to audit)
- Exit criteria must exist in ledger **before** task starts — verification checks output against criteria, not subjective judgment
- Normal review = quality; Adversarial = independence (non-author) — same mechanics, different trigger

### Ralph Loop

- Entry gate: materials-sufficient + exit_criteria defined — if either missing, loop does not start
- Exit (OR logic): `TextMentionTermination("TASK_COMPLETE")` OR `FunctionCallTermination("approve")` OR `MaxIterationTermination(n)`
- Specialists cannot emit `TASK_COMPLETE` without adversarial verification passing first
- Loop bounds: governor tracks `max_iterations` as a simple guard against infinite loops
- **Macro-cycle stage order**: Scan → Plan+Design → Implement → Test → Document (individual playbooks may omit stages)
- **Micro-cycle**: READ input → PLAN dispatch → EXECUTE specialist → VERIFY output → ARTIFACT ledger update

---

## Helper Layer (Minimal and Swappable)

| Component                  | Purpose                                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| **AGENTS.md**              | Single bootstrap manifest: agent registry + hook config + skill index + playbook index + ledger template |
| **Instructions**           | Reusable standardized constraints for agents; swap = update registry entry                               |
| **Playbooks**              | Ordered multi-step procedures (SKILL.md); orchestrator selects by intent match against Playbook Index    |
| **Skills**                 | Reference patterns for a specialist's bounded task; swap = edit SKILL.md + re-sync registry              |
| **Hooks**                  | Stateless lifecycle callbacks (read ledger/stdin → write stdout signal → exit); on by default            |
| **Verification Artifacts** | Typed artifact files `{task-id}-{type}.json`; empty by default; cleaned up when ledger closes task       |
| **MCP**                    | Tool entry declared in AGENTS.md; fetch for external data; loaded on demand                              |
| **Installation**           | AGENTS.md → setup agent scaffolds `.github/` structure; zero multi-file download                         |

### Playbook Execution Model

- Orchestrator runs inline — owns all gates at every boundary
- Each playbook step = forked specialist (subagent tool call) → returns one artifact path written to ledger Materials
- Ledger is the recovery contract: each step writes `DONE`/`INTERRUPTED` before the next step starts
- Forks happen at the lowest useful unit (one specialist, one bounded task)

### Skill vs. Playbook Distinction

|                | Skill                                                   | Playbook                                    |
| -------------- | ------------------------------------------------------- | ------------------------------------------- |
| **Teaches**    | How to do a bounded task (patterns, tools, constraints) | What sequence of specialists to run         |
| **Used by**    | Specialist (loaded before acting)                       | Orchestrator (dispatches step-by-step)      |
| **Body style** | Reference patterns                                      | Ordered numbered steps with gate conditions |

---

## Optional Layer (Minimize or Remove)

| Component    | Notes                                                                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Learning** | Append-only log per agent role, pruned after N entries; off by default                                                                             |
| **Prompts**  | One task-entry prompt (`solar.prompt.md`); `solar-registry-update.prompt.md` is an admin utility, not a task trigger; everything else is playbooks |
| **Config**   | 5 toggles: `adversarial`, `learning`, `logging`, `human_approval`, `hooks`                                                                         |
| **Logging**  | Separate from ledger (ledger = current state; log = append-only history); off by default                                                           |

---

## Key Design Invariants

These are non-negotiable. Breaking any one collapses the architecture:

1. Orchestrator never forks — it runs inline and owns all gates
2. Specialists never communicate directly — output goes to `verification-artifacts/` only
3. Adversarial auditor is always non-author, always domain-matched from registry — never hardcoded
4. Ralph loop requires declared exit criteria in ledger before starting — no open-ended loops
5. `TASK_COMPLETE` cannot be emitted without adversarial verification passing first
6. Ledger is sparse — links only, no embedded content
7. Material gate fires before every dispatch — `MATERIAL_INSUFFICIENT` stops the loop early
8. Blockers use `BLOCKED: <reason>` appended to Decisions Log — not a separate section

---

## Layer Communication

All inter-component communication is **mediated through the ledger and `verification-artifacts/`** — never direct agent-to-agent.

| From → To                  | Channel                                                                 | Content              |
| -------------------------- | ----------------------------------------------------------------------- | -------------------- |
| Orchestrator → Specialist  | Ledger dispatch (write stage + `input_material: ready`) + fork subagent | Task contract        |
| Specialist → Ledger        | Write artifact path + `status: DONE\|INTERRUPTED` before returning      | Step result          |
| Ledger → Orchestrator      | Source of truth for next dispatch decision (read after every step)      | Current state        |
| Orchestrator → Adversarial | Dispatch when stage transitions to `VERIFY`; pass artifact path         | Verification request |
| Adversarial → Ledger       | Write `PASS\|FAIL` + findings; orchestrator reads and gates next step   | Verdict              |
| Any → Decisions Log        | Append `BLOCKED: <reason>` on hard stop                                 | Blocker signal       |

**Rule**: if communication cannot be expressed as a ledger write or `verification-artifacts/` file, it should not happen.

---

## Startup, Resume, and Recovery

### Cold Start (fresh task)

1. Orchestrator reads AGENTS.md → loads agent registry + playbook index
2. Ledger does not exist → orchestrator creates it with Objective + empty Work Queue
3. Playbook selected by intent match → entry gate (materials? exit criteria?)
4. Loop begins with first specialist dispatch

### Resume (interrupted mid-run)

1. Orchestrator reads existing ledger cold
2. Scans Work Queue for last `DONE` step → identifies first `PENDING` step
3. Re-dispatches from that step; no playbook restart from scratch
4. If a step is `INTERRUPTED` (specialist forked but did not write status) → re-dispatch same specialist from last known checkpoint

### Version Upgrade Resume

- Ledger format is versioned (`solar_version` field in AGENTS.md); format is backward-compatible across minor versions
- Template upgrades: run install prompt again; diff AGENTS.md to identify what changed
- Breaking changes: version bump + migration note in CHANGELOG.md; ledger `solar_version` updated after migration

---

## Resilience and Error Proofing

| Failure Mode                  | Guard                                                     | Behavior                                                       |
| ----------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| Insufficient input            | Material gate (`input_material: ready` check)             | Emit `MATERIAL_INSUFFICIENT`; do not start                     |
| Infinite loop                 | Governor `max_iterations` guard                           | Hard stop at iteration limit; surface to user                  |
| Silent failure                | Specialist writes `status: INTERRUPTED` before any return | Orchestrator detects incomplete step on next read              |
| Bad output advancing pipeline | Adversarial VERIFY gate                                   | `FAIL` verdict blocks stage transition                         |
| Scope creep in specialist     | `tier_restrictions` in specialist contract                | Append `BLOCKED: OUT_OF_SCOPE: <description>` to Decisions Log |
| Ambiguous playbook match      | Orchestrator `askQuestion` before dispatch                | Never assumes; always confirms with user                       |
| Fork propagating failure      | Specialist runs isolated (subagent tool call)             | Failure is contained; orchestrator reads artifact status       |
| Stale materials               | Adversarial trigger condition #3                          | Audit flags stale reference before passing                     |

**Backpressure pattern**: the ledger Work Queue acts as a natural backpressure buffer. The orchestrator only fires the next step when the previous one writes `DONE` — parallel steps are explicitly declared with no inter-dependency, not inferred.

---

## Concept Enforcement (Keeping It Simple)

- **AGENTS.md is the single source of truth** — all component contracts declared there; nothing hardcoded outside it
- **No hardcoded agent names** in orchestration logic — all agent lookups are domain-role queries against the registry
- **Playbooks own "what"** — specialists own "how" — these two never mix
- **Gates are always orchestrator-owned** — no specialist can advance the pipeline or emit `TASK_COMPLETE` unilaterally
- **Swap any component**: update AGENTS.md registry entry (and/or SKILL.md file) → system picks up on next run; no code changes
- **Simplicity test**: if a change requires editing more than 2 files, the architecture has leaked

---

## System Persistence Between Versions

| Concern           | Mechanism                                                                           |
| ----------------- | ----------------------------------------------------------------------------------- |
| Ledger recovery   | `solar_version` field; backward-compatible schema across minor versions             |
| Artifact identity | `{task-id}-{type}.json` naming — task IDs stable across reinstalls                  |
| Template upgrades | Run install prompt again; AGENTS.md diff surfaces changes                           |
| Agent swap        | Update registry entry in AGENTS.md; existing ledger tasks continue unaffected       |
| Breaking changes  | Major version bump + migration note in CHANGELOG.md; ledger `solar_version` updated |
| Hook changes      | `solar.config.json` toggle; existing tasks not interrupted                          |

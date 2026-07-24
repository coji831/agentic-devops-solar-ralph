---
description: Install SOLAR-Ralph into any repository — one prompt, full scaffold, no extra downloads needed
---

# SOLAR-Ralph Installation

You are installing the SOLAR-Ralph agent harness into this repository.
SOLAR-Ralph is a 5-layer governance system (Specialist / Orchestrator / Ledger / Adversarial / Ralph Loop) that turns agent chat into bounded, verifiable, multi-agent pipelines on GitHub Copilot.

**Layer meanings:** S = specialist agents (one per dev stage) · O = orchestration governor · L = ledger (shared state) · A = adversarial audit (a Governor dispatch rule — at VERIFY stage, Governor picks a non-author specialist to challenge the previous agent's output) · R = Ralph loop (verification artifacts + bounded iteration). Hooks are infrastructure support that share gate-enforcement workload with the Governor — they are not the adversarial layer.

**SOLAR's scope:** highest-quality code changes. Every task — whether implementing a feature, writing a test, or updating a doc — goes through the same bounded cycle: scan → plan/design → execute → verify → exit. Release, deployment, and CI/CD are outside SOLAR's scope and belong in user-defined workflows.

Follow every step below in order. Do not skip steps. Do not commit.

> **Inventory file**: All verbatim file bodies for this installer live in `solar-install-inventory.md` (same folder as this file). When you see `→ Read INV:<slug> from solar-install-inventory.md`, open that file, find the `## INV:<slug>` section, and copy the fenced code block content verbatim to the target path. Replace `[FILL IN: ...]` tokens — all other content is copied as-is.

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

2. **What is this file** (1 paragraph — SOLAR-Ralph + this repo's name from sweep; then on a new line: `solar_version: "4.6.3"`)
3. **Repository Context** (the Repo Context block from Step 3 — existing docs, instructions, and agent files found in sweep)
4. **§3–§8** → Read `INV:agents-md-sections-3-to-8` from `solar-install-inventory.md` and append verbatim.
   - Replace `[FILL IN: Implementation Specialist name]` with the stack-tailored display name (e.g. `React-Ts Implementation Specialist` for `{STACK}=react-ts`, `Implementation Specialist` for generic).
   - Replace `[FILL IN: implementation skill slug]` / `[FILL IN: testing slug]` / `[FILL IN: review slug]` with the stack-prefixed slug or plain slug if generic (see naming rules in Step 5B).
   - Replace `[FILL IN: folder]` tokens in Skill Index with the actual skill folder names.
   - Do NOT include a "Usage" or behavioral paragraph section.

**`.github/copilot-instructions.md`**:
→ Read `INV:copilot-instructions` from `solar-install-inventory.md` and write verbatim to `.github/copilot-instructions.md`.

**`.github/solar.config.json`**:
→ Read `INV:solar-config` from `solar-install-inventory.md` and write verbatim to `.github/solar.config.json`.

### 5B — Agents (dev lifecycle coverage)

Generate each agent as a `.agent.md` file with YAML frontmatter. Each agent must be registered in AGENTS.md Agent Registry with its Dev Stage and Loads Skill columns filled.

**Naming rules:**

- **If `{STACK}` = generic** — plain names, no prefix:
  - Files: `context-summarizer.agent.md`, `implementation-specialist.agent.md`, `test-specialist.agent.md`, `review-auditor.agent.md`, `docs-curator.agent.md`, `data-collector-specialist.agent.md`, `design-planning-architect.agent.md`
  - Skill references: `context-summarization`, `implementation`, `testing`, `review`, `doc-sync`, `data-collection`, `design-planning`
- **If `{STACK}` ≠ generic** — stack-prefixed names:
  - Files: `context-summarizer.agent.md`, `{stack}-implementation-specialist.agent.md`, `{stack}-test-specialist.agent.md`, `{stack}-review-auditor.agent.md`
  - Skill references: `context-summarization`, `{stack}-implementation`, `{stack}-testing`, `{stack}-review`
  - Role-agnostic files keep plain names: `context-summarizer.agent.md`, `data-collector-specialist.agent.md`, `design-planning-architect.agent.md`, `docs-curator.agent.md`

| Dev Stage                | File                                         | Loads Skill                                             |
| ------------------------ | -------------------------------------------- | ------------------------------------------------------- |
| Scan (context-gathering) | `context-summarizer.agent.md`                | `context-summarization`                                 |
| Scan                     | `data-collector-specialist.agent.md`         | `data-collection`                                       |
| Plan + Design            | `design-planning-architect.agent.md`         | `design-planning`                                       |
| Implement                | `{stack}-implementation-specialist.agent.md` | `{stack}-implementation` or `implementation` if generic |
| Test                     | `{stack}-test-specialist.agent.md`           | `{stack}-testing` or `testing` if generic               |
| Document                 | `docs-curator.agent.md`                      | `doc-sync`                                              |
| VERIFY role              | `{stack}-review-auditor.agent.md`            | `{stack}-review` or `review` if generic                 |

**Verbatim YAML frontmatter for each agent (copy exactly — only replace `[FILL IN]` tokens):**

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
# Context Summarizer — .github/agents/context-summarizer.agent.md
---
name: Context Summarizer
description: Reads source files and produces compact digests for specialists. Only agent with the read tool.
model: DeepSeek V4 Flash (deepseek)
tools: [read, search]
user-invocable: false
---
```

```yaml
# Data Collector — .github/agents/data-collector-specialist.agent.md
---
name: Data Collector Specialist
description: Handles the Scan stage — gathers task context, repo state, and input findings.
model: Claude Haiku 4.5 (copilot)
tools: [search, edit]
user-invocable: false
---
```

```yaml
# Design Planning — .github/agents/design-planning-architect.agent.md
---
name: Design Planning Architect
description: Handles the Plan + Design stage — produces architecture or design plans.
model: Claude Sonnet 4.6 (copilot)
tools: [search, edit]
user-invocable: false
---
```

```yaml
# Implementation — .github/agents/{stack}-implementation-specialist.agent.md
---
name: [FILL IN: "{Stack} Implementation Specialist" or "Implementation Specialist" if generic]
description: Handles the Implement stage — writes [FILL IN: {stack}] code changes.
model: Claude Haiku 4.5 (copilot)
tools: [search, edit, execute, todo]
user-invocable: false
---
```

```yaml
# Test — .github/agents/{stack}-test-specialist.agent.md
---
name: [FILL IN: "{Stack} Test Specialist" or "Test Specialist" if generic]
description: Handles the Test stage — writes and runs tests for [FILL IN: {stack}]. Requires stack-specific test runner configuration before use.
model: Claude Haiku 4.5 (copilot)
tools: [search, edit, execute, todo]
user-invocable: false
---
```

```yaml
# Review Auditor — .github/agents/{stack}-review-auditor.agent.md
---
name: [FILL IN: "{Stack} Review Auditor" or "Review Auditor" if generic]
description: Handles the VERIFY role — adversarial audit of specialist output. Dispatched by Governor at VERIFY step, not as a pipeline stage.
model: Claude Sonnet 4.6 (copilot)
tools: [search, edit]
user-invocable: false
---
```

```yaml
# Docs Curator — .github/agents/docs-curator.agent.md
---
name: Docs Curator
description: Handles the Document stage — syncs and updates documentation.
model: Claude Sonnet 4.5 (copilot)
tools: [search, edit]
user-invocable: false
---
```

**Post-install note to print at end of Step 5:**

> Models assigned: Orchestrator + Design/Review = `Claude Sonnet 4.6 (copilot)`; Context Summarizer = `DeepSeek V4 Flash (deepseek)`; Docs = `Claude Sonnet 4.5 (copilot)`; Scan/Implement/Test = `Claude Haiku 4.5 (copilot)`. To change: edit the `model:` field in each `.agent.md` file.
>
> **Context flow**: Context Summarizer (the only agent with `read` tool) reads source files before each specialist dispatch. Specialists receive context via compact digest passed inline by the Governor — they do NOT read source files directly.

**Governor agent body:**
→ Read `INV:governor-agent` from `solar-install-inventory.md` and write verbatim (frontmatter + body) to `.github/agents/orchestration-governor.agent.md`.

**Context Summarizer agent body:**
→ Read `INV:context-summarizer-agent` from `solar-install-inventory.md` and write verbatim (frontmatter + body) to `.github/agents/context-summarizer.agent.md`.

**All other specialist agent bodies:**
→ Read `INV:specialist-agent-template` from `solar-install-inventory.md` for the shared body stub.
For each specialist agent: use the YAML frontmatter from the skeleton above + the body stub from the inventory. Replace all `[FILL IN: ...]` tokens per agent.

**Governor dispatch protocol — dispatch prompt MUST contain ONLY:**

1. 2–3 sentence task description
2. Relevant artifact paths from `verification-artifacts/`
3. Result file path to write: `verification-artifacts/{task-id}-{stage}-result.json`
4. Return instruction verbatim: `"Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."`
5. Skill path: `"Load and follow: .github/skills/{skill-name}/SKILL.md"`

Never embed raw file contents or ledger history in the dispatch prompt.

### 5C — Ledger template

**`.github/.ai_ledger.md`**:
→ Read `INV:ledger-template` from `solar-install-inventory.md` and write verbatim to `.github/.ai_ledger.md`.

### 5D — Hooks (infrastructure support)

- Hooks share gate-enforcement workload with the Governor — stateless event listeners, not agents, not the adversarial layer.
- Before generating: fetch `https://code.visualstudio.com/docs/copilot/customization/hooks` for current field names and output shapes. If fetch fails: use built-in knowledge and note `hooks schema unverified — using built-in knowledge`.
- Hooks are a VS Code Preview feature — schema may change between releases; use fetched docs as authoritative reference.
- Toggle: `"hooks": false` in `.github/solar.config.json` disables all hooks globally.

→ Read `INV:hooks-json` from `solar-install-inventory.md` and write verbatim to `.github/hooks/hooks.json`.
→ Read `INV:common-cjs` from `solar-install-inventory.md` and write verbatim to `.github/hooks/common.cjs`.
→ Read `INV:post-tool-use-cjs` from `solar-install-inventory.md` and write verbatim to `.github/hooks/post-tool-use.cjs`.

Optional hooks (not generated by default): `pre-tool-use`, `stop`, `user-prompt-submit`, `session-start`, `subagent-start`, `subagent-stop`, `pre-compact`. For each: create the `.cjs` script in `.github/hooks/` and register it in `hooks.json` following the same pattern.

### 5E — Instructions (minimal)

**`.github/instructions/solar.instructions.md`** — always generate:
→ Read `INV:solar-instructions` from `solar-install-inventory.md` and write verbatim to `.github/instructions/solar.instructions.md`.

**`.github/instructions/context-summarizer.instructions.md`** — always generate (reusable dispatch pattern for playbooks):
→ Read `INV:context-summarizer-instructions` from `solar-install-inventory.md` and write verbatim to `.github/instructions/context-summarizer.instructions.md`.

**`.github/instructions/{stack}.instructions.md`** — one stack file based on `{STACK}` and `{TEST_RUNNER}`:

- If `{STACK}` ≠ generic: generate a minimal instruction (under 20 lines) covering main frameworks, test runner `{TEST_RUNNER}`, lint tool, and key file paths detected in sweep
- If `{STACK}` = generic: populate from sweep findings — use repo name, stack signals from `package.json`/`pyproject.toml`/`go.mod`, detected test config files, and lint configs. Use `<!-- not detected — fill in -->` only for fields where sweep found nothing. Do not leave all fields as empty placeholders.
- Do not over-specify — agents fill in missing details on their first task
- File naming rule: when `{STACK}` = generic, always create the file as `.github/instructions/generic.instructions.md`. Do NOT reuse or overwrite a pre-existing instructions file with a different name. Pre-existing project instruction files are not renamed.

Note: instructions are auto-applied by platform via `applyTo`; they are not listed in Agent Registry or Skill Index. Note their `applyTo` patterns in the Repository Context section of AGENTS.md.

### 5F — Skills (dev lifecycle coverage)

Generate one `SKILL.md` per dev lifecycle step. Skills are loaded by agents at task time via the Skill Index — they are not pre-loaded. Each skill must be registered in AGENTS.md Skill Index.

**Required skills (always generate):**

| Dev Stage               | Skill name              | Folder                                  | Note                                                                           |
| ----------------------- | ----------------------- | --------------------------------------- | ------------------------------------------------------------------------------ |
| Scan (context pre-step) | `context-summarization` | `.github/skills/context-summarization/` |                                                                                |
| Scan                    | `data-collection`       | `.github/skills/data-collection/`       |                                                                                |
| Plan + Design           | `design-planning`       | `.github/skills/design-planning/`       |                                                                                |
| Implement               | `implementation`        | `.github/skills/implementation/`        |                                                                                |
| Test                    | `testing`               | `.github/skills/testing/`               | ⚠ Requires stack-specific runner setup (jest, vitest, pytest, etc.) before use |
| Document                | `doc-sync`              | `.github/skills/doc-sync/`              |                                                                                |
| Review                  | `review`                | `.github/skills/review/`                | Used at VERIFY step only — not a dispatched pipeline stage                     |
| Remediation (any)       | `recursive-remediation` | `.github/skills/recursive-remediation/` |                                                                                |

**Default pipeline stage order:** Scan → Plan + Design → Implement → Test → Document. Review Auditor runs as the VERIFY role inside each micro-cycle — not a dispatched pipeline stage.

For `{STACK}` ≠ generic: prefix the `implementation`, `testing`, and `review` folder names with the stack slug (e.g. `react-ts-implementation/`) and register them in the Skill Index alongside the generic counterparts.

→ Read `INV:skill-context-summarization` from `solar-install-inventory.md` and write verbatim to `.github/skills/context-summarization/SKILL.md`.
→ Read `INV:skill-data-collection` from `solar-install-inventory.md` and write verbatim to `.github/skills/data-collection/SKILL.md`.
→ Read `INV:skill-design-planning` from `solar-install-inventory.md` and write verbatim to `.github/skills/design-planning/SKILL.md`.
→ Read `INV:skill-implementation` from `solar-install-inventory.md` and write verbatim to `.github/skills/implementation/SKILL.md`.
→ Read `INV:skill-doc-sync` from `solar-install-inventory.md` and write verbatim to `.github/skills/doc-sync/SKILL.md`.
→ Read `INV:skill-review` from `solar-install-inventory.md` and write verbatim to `.github/skills/review/SKILL.md`.
→ Read `INV:skill-recursive-remediation` from `solar-install-inventory.md` and write verbatim to `.github/skills/recursive-remediation/SKILL.md`.
→ Read `INV:skill-testing` from `solar-install-inventory.md` and write verbatim to `.github/skills/testing/SKILL.md`.

- Before writing: replace all `{TEST_RUNNER}` tokens with the value collected in Step 2.

**Note — Playbooks also use SKILL.md format** but have a different body style:

- Skills = domain knowledge and tool patterns for a specialist (reference bullets, not steps)
- Playbooks = ordered numbered steps with gate conditions for the governor to follow inline

Step 5F-Playbooks below contains the verbatim canonical playbook content to generate.

### 5F-Playbooks — Default playbooks (always generate)

Generate the following playbook SKILL.md files. Register each in the AGENTS.md Playbook Index.

**Stack prefix rule**: In dispatch steps, `{stack}-` agent and skill names use the `{STACK}` value (lowercased, hyphenated, e.g. `react-ts-`) if `{STACK}` ≠ generic. If `{STACK}` = generic, omit the `{stack}-` prefix entirely and use plain names (e.g. `implementation-specialist.agent.md`).

→ Read `INV:playbook-implement-feature` from `solar-install-inventory.md` and write verbatim to `.github/skills/implement-feature/SKILL.md`.

- Before writing: replace `{stack}-` prefixes using the stack prefix rule above.
  → Read `INV:playbook-bug-fix` from `solar-install-inventory.md` and write verbatim to `.github/skills/bug-fix/SKILL.md`.
- Before writing: replace `{stack}-` prefixes using the stack prefix rule above.
  → Read `INV:playbook-create-doc` from `solar-install-inventory.md` and write verbatim to `.github/skills/create-doc/SKILL.md`.

→ Read `INV:solar-prompt` from `solar-install-inventory.md` and write verbatim to `.github/prompts/solar.prompt.md`.
→ Read `INV:solar-registry-update-prompt` from `solar-install-inventory.md` and write verbatim to `.github/prompts/solar-registry-update.prompt.md`.

### 5H — Solar-system reference files (verbatim skeletons)

Generate each file verbatim as shown below. Do NOT paraphrase or summarize — copy exactly from the inventory.

→ Read `INV:adversarial-skeleton` from `solar-install-inventory.md` and write verbatim to `.github/solar-system/adversarial/skeleton-manifest.md`.
→ Read `INV:inquiry-first-protocol` from `solar-install-inventory.md` and write verbatim to `.github/solar-system/protocols/inquiry-first.md`.
→ Read `INV:lifecycle-coordination` from `solar-install-inventory.md` and write verbatim to `.github/solar-system/protocols/lifecycle-coordination.md`.

Generate 6 minimal schema envelopes (empty — agents fill properties on first use):
→ Read `INV:schema-envelopes` from `solar-install-inventory.md` and write verbatim to each of these 6 files:

- `.github/solar-system/schemas/designer-output.schema.json`
- `.github/solar-system/schemas/implementer-handoff.schema.json`
- `.github/solar-system/schemas/review-result.schema.json`
- `.github/solar-system/schemas/qa-result.schema.json`
- `.github/solar-system/schemas/scout-findings.schema.json`
- `.github/solar-system/schemas/dev-progress.schema.json`

<!-- compact-handoff-schema removed in v5 — schema enforcement added ceremony without proportional benefit -->

### 5I — Verification artifacts scaffold

→ Read `INV:verification-artifacts-readme` from `solar-install-inventory.md` and write verbatim to `verification-artifacts/README.md`.
→ Create `verification-artifacts/.gitkeep` (empty file).

---

## Step 6 — Report

After all files are created, print the report using the template below:
→ Read `INV:report-template` from `solar-install-inventory.md` and print to chat (do NOT write to a file).

- Replace `{count}`, `{STACK}`, `{TEST_RUNNER}`, `{available / unavailable}` with actual values.
- Populate agents, skills, and repository context lists from what was generated in Step 5.

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

# SOLAR-Ralph v3 — Three-Tier Architecture Draft

> Status: Draft / Research
> Date: March 28, 2026
> Based on: v2 template analysis, mandarin v1 comparison, SOLAR-Ralph-Framework-v3.md research

---

## Overview

SOLAR v2 is a single monolithic install — all 14 agents, 14 skills, 5 pipelines, hooks, and ledger land together regardless of project size or team maturity. The research in v3 points toward a tiered model where teams adopt incrementally.

The proposed split:

| Tier | Name                     | Target User                           | Setup Time | Files Added |
| ---- | ------------------------ | ------------------------------------- | ---------- | ----------- |
| 1    | Generic Lightweight      | Solo devs, small projects, prototypes | < 5 min    | ~5 files    |
| 2    | Adapted High Performance | Teams with defined stack and workflow | 15–30 min  | ~40 files   |
| 3    | Extra Customization      | Enterprise / complex multi-repo orgs  | Ongoing    | 60+ files   |

---

## Tier 1 — Generic Lightweight (quick-setup)

**Goal:** You can clone, run `/solar-setup-quick`, and get meaningful agentic support on any project with no manual configuration. Zero decision fatigue.

### What it includes

**Agents (4 core only):**

- `orchestration-governor` — intake, routing, and completion decisions
- `design-planning-architect` — breaks down work before any code touches
- `implementation-specialist` — generic (not frontend/backend split yet)
- `security-auditor` — always available as a lightweight gate

**Pipelines (2):**

- Knowledge — question → governor → direct answer
- Simple Fix — governor → implementation → close

**Files:**

- `.github/AGENTS.md` — stripped-down contract with 4 roles only
- `.github/copilot-instructions.md` — minimal project instructions scaffold
- `.github/solar.config.json` — `mode: simple`, `solar.active: true`, no hooks

**No:** skills, hooks, ledger, memory, path-specific instructions, loop mode

### What it does NOT include (by design)

- No bug fix pipeline (use simple fix instead)
- No feature pipeline (use simple fix, escalate manually)
- No recursive repair or completion promises
- No audit trail

### Upgrade path

Running `/solar-upgrade-full` at any time migrates to Tier 2 non-destructively. Existing files are kept; missing files are added.

---

## Tier 2 — Adapted High Performance (full-setup)

**Goal:** The full v2 capability set, but now auto-detected and configured for your actual stack (frontend, backend, or both). This is the current default v2 template, made smarter via project scanning.

### What it includes (on top of Tier 1)

**Agents (all 14):**

- All Tier 1 agents
- `frontend-implementation-specialist` + `frontend-review-auditor` + `frontend-test-specialist`
- `backend-implementation-specialist` + `backend-review-auditor` + `backend-test-specialist`
- `bug-investigation-specialist`
- `cache-external-integration-specialist`
- `docs-curator`
- `release-readiness-specialist`
- `solar-bootstrap` (still available for config changes)

**Pipelines (all 4):**

- Knowledge, Simple Fix, Bug Fix, Feature

**Skills (all 14):**

- All current skills from `.github/skills/` — loaded on-demand per task context

**Files added:**

- `.github/.ai_ledger.md` — restart-safe work queue with completion promises
- `.github/instructions/*.instructions.md` — domain-scoped fact files (architecture, frontend, backend, security, verification, workflow, conventions) — auto-loaded by Copilot via `applyTo` patterns
- `.github/skills/` — full skill library
- `.github/hooks/hooks.json` — loop enforcement + post-tool-use type check
- `apps/frontend/.instructions.md` — auto-generated from stack scan
- `apps/backend/.instructions.md` — auto-generated from stack scan

**Config:**

- `solar.config.json`: `mode: simple` by default, `loop` opt-in via `/ralph-loop`
- Hooks active only in `loop` mode
- Type check command auto-detected from `tsconfig.json` / `package.json`

### Deep Adaptability Model

Tier 2's core promise: SOLAR configures itself around **your** project shape, not the other way around. Mandarin happens to be React+Express — but the adaptation system must handle any project type without manual overrides.

#### Scanning Design Principles

Two non-negotiable constraints govern every scan:

**1. Point-in-time scanning** — when `/solar-setup-scan-repo` is triggered, it uses the most advanced scanning technique available at that moment. Scanning capability is not pinned to the SOLAR version; it uses whatever the current Copilot agent model can do (semantic search, file system traversal, structured extraction). A re-scan one year later will produce better results than the initial scan — and that is by design. The profile is always regenerable.

**2. Over-scan — never trust known paths alone** — the scanner does NOT only probe a predefined list of well-known files (`package.json`, `CONTRIBUTING.md`, etc.). It always performs a full `**/*.md` sweep first to find workflow definitions, conventions, and rules stored wherever the team put them — random docs folders, wiki exports, `notes/`, `team/`, `processes/`, anywhere. Known-path probing is a fast supplement, not the primary strategy. A convention file named `our-rules.md` at the repo root is as valid as one named `code-conventions.md` in `docs/guides/`.

---

#### Pass 1 — Stack Detection (Agent Roster)

**Primary: full `**/\*.md` + manifest sweep\*\*

The scanner first does a broad read of all Markdown files and all manifests before applying any label. This ensures a `pyproject.toml` buried in a subfolder, or a `README.md` that mentions "we use Flutter", is not missed.

**Probe targets (combined):**

| Source                        | What it reveals                                                   |
| ----------------------------- | ----------------------------------------------------------------- |
| `**/*.md` (all Markdown)      | Stack mentions, technology names, framework references in any doc |
| `package.json` (any depth)    | `dependencies` / `devDependencies` → React, Vue, Express, NestJS  |
| `pyproject.toml` / `setup.py` | Python stack → FastAPI, Django, ML libs                           |
| `Cargo.toml`                  | Rust                                                              |
| `go.mod`                      | Go                                                                |
| `*.tf` files                  | Terraform / infra                                                 |
| `.github/workflows/*.yml`     | CI system + existing gates                                        |
| `tsconfig.json`               | TypeScript confirmation + path aliases                            |

**Detection logic:**

```
Phase A — Semantic sweep:
  Read all **/*.md → extract technology/stack names via semantic analysis
  Flag any file that contains workflow language, convention rules, or process descriptions
  Record file path + extracted signals → candidate list

Phase B — Manifest probe:
  Scan for known manifests at any depth
  For each manifest found: classify domain + detect test runner + detect ORM/framework

Phase C — Merge + label:
  Combine Phase A signals with Phase B signals
  Assign projectType + domain list
  Prefer manifest evidence over prose evidence for stack classification
  Use prose evidence to supplement (e.g., a monorepo README that lists services)
```

**Domain → Agent mapping (unchanged, but now driven by over-scan):**

| Detected Domain                          | Specialist Agents Activated                              |
| ---------------------------------------- | -------------------------------------------------------- |
| `react-ts`, `vue`, `angular`             | frontend-implementation, frontend-review, frontend-test  |
| `express`, `nestjs`, `fastapi`, `django` | backend-implementation, backend-review, backend-test     |
| `python-ml`, `jupyter`, `pytorch`        | ml-experiment-specialist, data-pipeline-specialist       |
| `react-native`, `flutter`, `swift`       | mobile-implementation-specialist, mobile-test-specialist |
| `terraform`, `kubernetes`, `ansible`     | infra-specialist, infra-review-specialist                |
| `monorepo` (multiple domains)            | one specialist pair per detected workspace               |
| `library` / `cli`                        | generic-implementation + api-contract-specialist         |

**Fallback:**

```
if nothing detected:
  projectType = "unknown"
  domains = [{ name: "generic", path: ".", stack: "unknown" }]
  agents = 4 core only (Tier 1 roster)
  log: "Stack undetected — defaulting to generic Tier 1 roster"
```

---

#### Pass 2 — Convention Ingestion (Rules)

**Primary: full `**/\*.md` semantic scan first, then known-path supplement\*\*

The scanner reads every `.md` file in the repo and semantically classifies each one. Any file that contains:

- Ordered rules, naming conventions, or "must/should/never" language
- Code style directives
- File naming patterns
- Checklist items with compliance gates

...is flagged as a **convention candidate** regardless of its path or filename.

**Confidence tiers:**

| Source                                                    | Confidence | Treatment                                                       |
| --------------------------------------------------------- | ---------- | --------------------------------------------------------------- |
| Any `**/*.md` with convention signals                     | High       | Parse and extract rules                                         |
| `CONTRIBUTING.md`, `code-conventions.md`, `STYLEGUIDE.md` | High       | Parse directly (known format)                                   |
| `.eslintrc` / `eslint.config.js`                          | High       | Extract rule set name only (not individual rules — too brittle) |
| `pyproject.toml [tool.ruff]`, `rustfmt.toml`              | High       | Extract linter config name                                      |
| `.editorconfig`                                           | Medium     | Extract indent/line-ending settings                             |
| `README.md` (## Contributing section)                     | Medium     | Extract checklist items only                                    |
| Any `**/*.md` with partial convention signals             | Low        | Flag for human review, do not seed as rules                     |

**What gets extracted → `.github/instructions/conventions.instructions.md`:**

- Naming patterns (files, functions, test suffixes)
- Linter rule set name
- Required checklist items
- Template paths if referenced in any doc

**Fallback:**

```
if no convention files detected:
  conventions = { detected: false }
  .github/instructions/conventions.instructions.md = scaffold with [POST-IMPLEMENT] markers
  log: "No convention files detected — conventions.instructions.md scaffolded for manual fill"
```

---

#### Pass 3 — Domain Memory Mapping

**Driven by Pass 1 output — adaptive per project type:**

Memory files are generated to match the detected domain — not a fixed 7-file set.

| Project Type  | Generated Memory Files                                                       |
| ------------- | ---------------------------------------------------------------------------- |
| Web fullstack | commands, architecture, frontend, backend, security, workflow, verification  |
| ML research   | commands, datasets, experiments, models, infrastructure, workflow            |
| Mobile        | commands, architecture, platforms (ios/android), state, deployment, workflow |
| Microservices | commands, services-map, contracts, data-stores, deployment, workflow         |
| Library/CLI   | commands, api-surface, compatibility, release, workflow                      |
| Infra/DevOps  | commands, resource-map, environments, secrets-policy, workflow               |
| Unknown       | commands, workflow ← minimum viable set                                      |

**Seed strategy:**

Each generated file gets:

- **Auto-detected fields** filled from scan evidence
- **Unfilled fields** marked `[SCAN-INCOMPLETE — fill manually]`
- A `scan-confidence: high | medium | low` frontmatter field

`workflow.md` is always generated. Others are seeded from the Pass 1 profile.

**Fallback:**

```
if projectType = "unknown":
  generate only commands.md + workflow.md
  both fully scaffolded with [POST-IMPLEMENT] markers
  log: "Unknown project type — minimal memory set generated"
```

---

#### Pass 4 — Workflow Inference (Delivery Process)

**Primary: full `**/\*.md` semantic scan — workflows can live anywhere\*\*

The over-scan principle matters most here. Teams document their delivery process in whatever file made sense at the time — a random `process.md`, a section buried in `CONTRIBUTING.md`, a `team/how-we-work.md`, or even inline in `copilot-instructions.md` (the mandarin pattern). The scanner must find it wherever it is.

**Semantic sweep (Phase A — primary):**

Read every `**/*.md` and classify each file for:

- Ordered step sequences (numbered lists describing a delivery process)
- "When to do X" or "before commit" language
- Checklist items tied to story/task/PR close
- Template references (file must exist at path X)
- "Must follow" or "do not skip" compliance language

Any file with these signals → **workflow candidate**, regardless of path.

**Structured source probe (Phase B — supplement):**

```
.github/solar-workflows/*.workflow.md   → already defined, skip inference
.github/copilot-instructions.md         → extract any workflow prose sections
                                          ← mandarin's 8-step workflow lives here
CONTRIBUTING.md                          → extract checklist items as steps
.github/pull_request_template.md        → PR checklist → delivery steps
.github/ISSUE_TEMPLATE/*.md             → infer doc creation steps
git log --oneline -50                   → conventional commit pattern detection
```

**Inference rules:**

```
if conventional commits detected in git log:
  add "conventional-commits" to detectedRules

if PR template has checklist with "tests pass":
  infer test gate step in workflow

if any **/*.md contains ordered delivery steps (semantic):
  extract as workflow steps → status: inferred, source: <file path>

if copilot-instructions.md has workflow section:
  extract prose → structured .workflow.md → status: inferred, source: copilot-instructions.md
  ← this is the mandarin migration path
```

**Output marking — inferred files are never treated as contracts:**

```yaml
---
name: feature-delivery
status: inferred # agents treat as suggestion, not enforced pipeline
source: docs/process.md # traceability — which file was the source
confidence: medium
---
```

**Fallback:**

```
if no workflow signals found anywhere:
  generate feature-delivery.workflow.md as blank scaffold
  generate bug-fix.workflow.md as blank scaffold
  status: scaffolded
  log: "No workflow patterns detected — starter workflows scaffolded for manual fill"
```

---

#### Pass 5 — Folder Structure Probe (Path Instructions)

**Primary: detect any subfolder with its own manifest, README, or `.instructions.md`**

The scanner does not assume `apps/frontend` and `apps/backend`. It finds the actual workspace structure.

**Detection:**

```
Phase A — Manifest-anchored:
  any subfolder with package.json    → workspace candidate
  any subfolder with pyproject.toml  → workspace candidate
  any subfolder with Cargo.toml      → workspace candidate

Phase B — README-anchored:
  any subfolder with README.md that describes a specific domain → workspace candidate
  (catches workspaces without manifests — docs packages, infra folders, etc.)

Phase C — Existing instructions:
  any **/.instructions.md already present → record path, do not overwrite
```

**Generation per detected path:**

```
for each detected workspace:
  read that folder's manifest + README
  generate .instructions.md with:
    - detected stack for that path
    - test command for that path
    - path-specific lint config if present
    - [POST-IMPLEMENT] markers for unfilled sections
    - scan-confidence frontmatter field
```

**Fallback:**

```
if no subfolder workspaces detected (flat repo):
  no .instructions.md files generated
  single-domain instructions folded into copilot-instructions.md
  log: "Flat repo structure — no path-specific instructions generated"
```

---

#### Scan Output — `solar-project-profile.json`

All 5 passes write into a single artifact. This is the source of truth for all downstream generation:

```json
{
  "scanVersion": "3.0",
  "scanDate": "2026-03-28",
  "scanStrategy": "point-in-time + over-scan",
  "projectType": "web-fullstack",
  "confidence": "high",
  "fallbacksTriggered": [],
  "domains": [
    {
      "name": "frontend",
      "path": "apps/frontend",
      "stack": "react-ts",
      "testCmd": "npx vitest",
      "instructionsFile": "apps/frontend/.instructions.md"
    },
    {
      "name": "backend",
      "path": "apps/backend",
      "stack": "express-prisma",
      "testCmd": "npm test",
      "instructionsFile": "apps/backend/.instructions.md"
    }
  ],
  "conventions": {
    "detected": true,
    "confidence": "high",
    "sources": ["docs/guides/code-conventions.md", ".eslintrc.json"],
    "candidatesFound": [
      "docs/guides/code-conventions.md",
      "CONTRIBUTING.md",
      "our-team-rules.md"
    ],
    "lintConfig": ".eslintrc.json",
    "testFileSuffix": "*.test.ts"
  },
  "memory": {
    "categories": [
      "commands",
      "architecture",
      "frontend",
      "backend",
      "security",
      "workflow",
      "verification"
    ],
    "seedConfidence": "medium"
  },
  "workflows": {
    "existing": [],
    "inferred": [
      {
        "name": "feature-delivery",
        "source": ".github/copilot-instructions.md",
        "confidence": "high"
      },
      {
        "name": "doc-creation",
        "source": "docs/guides/business-requirements-format-guide.md",
        "confidence": "medium"
      }
    ],
    "scaffolded": []
  },
  "ciSystem": "github-actions",
  "existingGates": ["jest", "tsc --noEmit"],
  "detectedRules": ["conventional-commits", "template-compliance"]
}
```

**Key difference from a fixed-path scan:** `conventions.candidatesFound` lists every file the semantic sweep flagged — not just the ones matching known names. The user can see what the scanner found and correct misclassifications before the profile drives agent generation.

---

#### Fallback Summary

| Pass                  | Failure Condition                                   | Fallback                                                     |
| --------------------- | --------------------------------------------------- | ------------------------------------------------------------ |
| Pass 1 — Stack        | No manifest anywhere, no stack signals in any `.md` | `projectType: unknown`, 4 core agents only                   |
| Pass 2 — Conventions  | No convention signals in any `.md`                  | Scaffold `conventions.md` with `[POST-IMPLEMENT]`            |
| Pass 3 — Memory       | Unknown project type                                | Generate `commands.md` + `workflow.md` only                  |
| Pass 4 — Workflows    | No workflow signals in any `.md`                    | Scaffold blank `feature-delivery` + `bug-fix` workflows      |
| Pass 5 — Folders      | Flat repo, no workspaces                            | Skip `.instructions.md`, fold into `copilot-instructions.md` |
| **Full scan failure** | Unreadable / empty repo                             | Emit Tier 1 config only, log all skipped passes              |

### Workflow Definition Format (`.workflow.md` Contract)

> **Discovery vs authoring:** Pass 4 of the scanner finds workflow signals anywhere in the repo and infers `.workflow.md` files. This section defines what those files look like once authored or promoted from an inferred draft. See [Appendix: Workflow File Reference](#appendix-workflow-file-reference) for full examples.

**Alignment with VS Code native format:** `.workflow.md` is a SOLAR-named variant of VS Code's native `.prompt.md` (prompt files) — the official format for repeatable tasks. SOLAR adds `pipeline`, `trigger`, `status`, `source`, and `confidence` frontmatter fields on top of the base prompt file format. A `.workflow.md` can be opened and run like any prompt file; SOLAR agents additionally parse the frontmatter to route it as a named pipeline.

**Location:** `.github/solar-workflows/*.workflow.md`

**Frontmatter contract:**

```yaml
---
name: <workflow-name>           # unique identifier, used by governor for routing
trigger: "<phrase>" | "<cmd>"   # natural language phrases or slash commands that activate this workflow
pipeline: custom                # custom | extends-feature | extends-bug-fix | extends-simple-fix
status: active                  # active (enforced) | inferred (suggestion only, from Pass 4 scan) | scaffolded (blank template)
source: <file-path>             # only present on inferred files — traceability back to the source doc
confidence: high | medium | low # only present on inferred files
---
```

**Pipeline types:**

| Type                 | Behaviour                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------ |
| `custom`             | Fully user-defined — governor reads steps and executes in order, no built-in pipeline contract applies |
| `extends-feature`    | Injects project steps into the built-in Feature pipeline at named injection points                     |
| `extends-bug-fix`    | Injects project steps into the built-in Bug Fix pipeline                                               |
| `extends-simple-fix` | Minimal injection for small patches that don't need the full feature pipeline                          |

**Promotion from inferred to active:**

1. Pass 4 generates `status: inferred` file — agents treat it as a suggestion
2. User reviews, edits steps to match actual process
3. User removes `status: inferred` and sets `status: active` — governor now enforces it as a contract

**Template enforcement:**

The `docs-curator` skill reads `.github/solar-workflows/` during planning and validates agent output against declared template paths. Agents that skip a workflow step must explicitly record the reason in the ledger — gaps are not silent.

### What Tier 2 is NOT

- No MCP server integrations
- No GitHub Agentic Workflows (CI/CD automation)
- No multi-model engine selection per agent
- No org-level shared agent library
- No vector/semantic memory
- No automated enforcement of workflow compliance (CI gate) — that is Tier 3

---

## Tier 3 — Extra Customization (advanced-setup)

**Goal:** SOLAR becomes a **platform you build on**, not a template you copy. Teams define their own agents, skills, pipeline types, memory schemas, and enforcement gates. The framework ships as a versioned dependency, not a fork.

### Wide Customizability Model

Tier 2 adapts SOLAR to fit your project. Tier 3 lets you extend SOLAR itself — adding capabilities that don't exist in the core, and removing or replacing defaults that don't fit your domain.

---

#### 1. Custom Agent Authoring

Beyond activating/deactivating existing agents, Tier 3 provides **agent authoring tooling**:

- `/solar-new-agent <name>` — scaffolds a new `.agent.md` with the required pipeline contract fields, tool declarations, and delegation matrix entry
- New agents can be domain specialists (e.g., `data-validation-specialist`, `mobile-platform-specialist`, `terraform-reviewer`) or project-role replacements (e.g., `company-security-auditor` overriding the default)
- Custom agents declare which built-in pipeline stages they participate in and what signals trigger their invocation
- They can reference and extend built-in agent behavior via `extends: backend-implementation-specialist`

**Org-level sharing:** custom agents committed to this repo's `.github/agents/` are referenced by downstream projects:

```json
"agentLibrary": "github://org/agentic-devops-solar-ralph/.github/agents@v3.0"
```

Version-pinned. Teams pull updates via `/solar-upgrade-agents`.

---

#### 2. Custom Skill Authoring

- `/solar-new-skill <name>` — scaffolds a `SKILL.md` with the YAML frontmatter format agents already know
- Domain-specific skills: `ml-experiment-tracking`, `mobile-platform-deployment`, `api-contract-validation`, `terraform-drift-detection`
- Skills can declare tool requirements, trigger conditions, and injection points into existing pipeline stages
- Skill library is versioned and shareable via the org agent library mechanism
- A `skill-validator` agent (new in Tier 3) checks that new skills don't conflict with existing pipeline contracts before activation

---

#### 3. Extended Pipeline Types

Tier 2 offers `custom` and `extends-*` workflow types. Tier 3 adds:

| Pipeline Feature           | Description                                                                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Parallel stages**        | Multiple specialists run concurrently within a stage, results merged before next stage                                                          |
| **Conditional branches**   | `if: project-type == 'ml'` routes to a different specialist chain                                                                               |
| **Human-approval gates**   | Pipeline pauses and requires explicit human sign-off before continuing (useful for production deployments, destructive operations)              |
| **Cross-repo triggers**    | A pipeline completion in one service triggers a dependent pipeline in another (microservices contract testing)                                  |
| **Non-delivery use cases** | Support for research workflows (hypothesis → experiment → result docs), ops workflows (runbook → execute → verify), not just feature/bug cycles |

Pipeline definitions move from `.workflow.md` (simple step lists) to `.pipeline.md` (richer DAG-like definitions with stage metadata).

---

#### 4. Pluggable Memory

Beyond flat `.md` memory files, Tier 3 supports alternative memory backends:

- **Episodic store** — ledger history indexed per story, queryable by `docs-curator` for pattern detection across many delivery cycles
- **Semantic/vector** — MCP retrieval server indexes the docs folder; agents query it for relevant prior work before planning
- **External knowledge bases** — Confluence, Notion, internal wikis connected via custom MCP server; agents ground planning decisions in org-level knowledge, not just repo knowledge
- **Custom memory schema** — projects define their own memory category files (beyond the 7 defaults); schema declared in `solar-project-profile.json`

Memory consolidation scripts run on story close — configurable, replaceable, or disabled per project.

---

#### 5. MCP Integration Layer

Each agent declares its permitted MCP tools explicitly — no agent gets blanket access (zero-trust model from v3 research):

```json
// In agent's .agent.md frontmatter
"mcp-servers": [
  { "server": "github", "tools": ["search_code", "list_issues", "create_pull_request"] },
  { "server": "fetch", "tools": ["fetch_url"] },
  { "server": "org-confluence", "tools": ["search_pages", "read_page"] }
]
```

Built-in MCP integrations:

- GitHub — issues, PRs, code search, branch management
- Fetch/Browser — documentation scraping, external API validation
- Database — Prisma/direct DB queries for backend specialists
- Org-custom — internal JIRA, Confluence, internal API registries

`/solar-setup-mcp` — configures which MCP servers are available and maps them to agent permission groups.

---

#### 6. GitHub Agentic Workflows (CI-embedded agents)

Agents that run outside VS Code, triggered by GitHub events or schedules:

- `triage-issues.md` — classify + label new issues by semantic content
- `docs-maintenance.md` — scheduled doc freshness pass; opens issues for stale docs
- `pr-review-assistant.md` — auto-review gate before human merge
- `compliance-gate.md` — blocks merge if workflow steps in `.workflow.md` files are incomplete
- `kb-capture-check.md` — on PR merge, scans for uncaptured struggles; opens issue if threshold exceeded

These are natural language `.md` files compiled to GitHub Actions via `gh aw compile`. Projects can author their own agentic workflows using the same pattern.

---

#### 7. Multi-Model Engine Selection

`solar.config.json` extended with per-agent model hints — route expensive reasoning to high-power models, routine iteration to fast defaults:

```json
"agents": {
  "design-planning-architect": { "engine": "claude-4-thinking" },
  "security-auditor": { "engine": "gpt-4o" },
  "frontend-test-specialist": { "engine": "copilot-default" },
  "triage-issues": { "engine": "copilot-default" }
}
```

Per-pipeline routing also supported — high-stakes Feature + Security pipelines can mandate a minimum model tier.

---

#### 8. Advanced Governance Controls

- Per-agent operation limits (e.g., `security-auditor` max 3 file writes per run, `frontend-implementation` max 10 files per session)
- Audit log output to `.github/audit/YYYY-MM-DD.log` — records agent invocations, tool calls, and completion state
- Draft-PR-only mode for all agentic workflow outputs — nothing auto-merges
- Kill-switch via `solar.config.json`: `"emergencyStop": true` — halts all agentic workflows immediately
- Scope isolation — agents only see files within their declared `scope` glob; cross-scope reads require explicit escalation

---

## Capability Matrix

| Capability                               | Tier 1 (Lightweight) | Tier 2 (High Perf)              | Tier 3 (Advanced)           |
| ---------------------------------------- | -------------------- | ------------------------------- | --------------------------- |
| Core agents (4)                          | ✅                   | ✅                              | ✅                          |
| Domain-shaped agent roster               | ❌ (4 only)          | ✅ (detected per stack)         | ✅ + custom agents          |
| Skills library                           | ❌                   | ✅ (14 built-in)                | ✅ + custom domain skills   |
| Loop mode + hooks                        | ❌                   | ✅                              | ✅                          |
| Ledger (restart-safe)                    | ❌                   | ✅                              | ✅ + episodic history index |
| Memory files                             | ❌                   | ✅ (domain-adaptive categories) | ✅ + pluggable backends     |
| Path-specific instructions               | ❌                   | ✅ (detected paths)             | ✅ + MCP-grounded           |
| Project profile scan                     | ✅ (minimal)         | ✅ (deep, any stack)            | ✅                          |
| Convention ingestion                     | ❌                   | ✅ (doc templates, lint, CI)    | ✅                          |
| Workflow inference (from commit history) | ❌                   | ✅                              | ✅                          |
| Custom workflow definitions              | ❌                   | ✅ (custom + extends)           | ✅ + parallel + conditional |
| Workflow compliance (interactive)        | ❌                   | ✅ (agent-enforced)             | ✅                          |
| Workflow compliance (CI gate)            | ❌                   | ❌                              | ✅                          |
| Custom agent authoring                   | ❌                   | ❌                              | ✅                          |
| Custom skill authoring                   | ❌                   | ❌                              | ✅                          |
| Extended pipeline types (DAG)            | ❌                   | ❌                              | ✅                          |
| MCP server integrations                  | ❌                   | ❌                              | ✅ (zero-trust per agent)   |
| GitHub Agentic Workflows (CI)            | ❌                   | ❌                              | ✅                          |
| Multi-model engine selection             | ❌                   | ❌                              | ✅ (per agent + pipeline)   |
| Org-level shared agent library           | ❌                   | ❌                              | ✅ (versioned)              |
| Semantic/vector memory                   | ❌                   | ❌                              | ✅                          |
| External knowledge base integration      | ❌                   | ❌                              | ✅                          |
| Audit logging                            | ❌                   | ❌                              | ✅                          |
| Per-agent operation limits + scope       | ❌                   | ❌                              | ✅                          |
| CI/CD embedded agents                    | ❌                   | ❌                              | ✅                          |
| Non-delivery workflows (ML, ops)         | ❌                   | ✅ (via custom type)            | ✅ (richer pipeline types)  |
| Struggle/KB capture on close             | ❌                   | ✅ (agent-enforced)             | ✅ (automated CI gate)      |

---

## File Footprint Comparison

|                                          | Tier 1           | Tier 2                     | Tier 3                              |
| ---------------------------------------- | ---------------- | -------------------------- | ----------------------------------- |
| `.github/AGENTS.md`                      | Minimal          | Full                       | Full + custom agents + MCP blocks   |
| `.github/copilot-instructions.md`        | Scaffold         | Full                       | Full                                |
| `.github/solar.config.json`              | Basic (3 fields) | Full (5 modes)             | Extended (agents, mcp, limits)      |
| `.github/solar-project-profile.json`     | None             | Generated by scan          | Generated by scan                   |
| `.github/agents/*.agent.md`              | 4                | Domain-detected (variable) | Variable + custom + org-ref entries |
| `.github/skills/*/SKILL.md`              | 0                | 14 built-in                | 14 + custom domain skills           |
| `.github/.ai_ledger.md`                  | None             | Template                   | Template + history index            |
| `.github/instructions/*.instructions.md` | None             | Domain-adaptive (variable) | Variable + custom schema            |
| `.github/hooks/hooks.json`               | None             | Full                       | Full + per-agent limits             |
| `.github/solar-workflows/*.workflow.md`  | None             | User-defined or inferred   | User-defined + CI-enforced          |
| `.github/workflows/agents/*.md`          | None             | None                       | 4+ agentic workflows                |
| `.github/audit/*.log`                    | None             | None                       | Generated on each agent run         |
| `apps/**/.instructions.md`               | None             | Detected paths (variable)  | Detected paths + MCP context        |

---

## Setup Command Mapping

| Command                           | Tier                            |
| --------------------------------- | ------------------------------- |
| `/solar-setup-quick`              | Tier 1                          |
| `/solar-setup-full`               | Tier 2                          |
| `/solar-upgrade-full`             | Tier 1 → Tier 2                 |
| `/solar-setup-advanced` _(new)_   | Tier 3                          |
| `/solar-setup-mcp` _(new)_        | Tier 3 — MCP only               |
| `/solar-setup-workflows` _(new)_  | Tier 3 — Agentic Workflows only |
| `/solar-upgrade-advanced` _(new)_ | Tier 2 → Tier 3                 |

---

## Mandarin Proof-of-Concept: Pre-SOLAR Baseline

The mandarin repo is the most concrete evidence for where to draw the tier lines. It demonstrates a **working project-defined workflow system that runs entirely without SOLAR** — just default Copilot agent + a medium or high reasoning model.

### What mandarin defined (no SOLAR required)

**Use Case 1 — Doc Creation:**
The entire documentation pipeline lives in `copilot-instructions.md` as prose. No SOLAR, no special agents. A default Copilot agent with a mid-tier reasoning model can follow it:

- 7 typed templates in `docs/templates/` (epic BR, story BR, epic impl, story impl, commit, file header, feature design)
- Named file paths with exact naming conventions (`epic-<num>-<slug>/story-<epic>-<story>-<short>.md`)
- Creation checklists: cross-link bidirectionally, scaffold stories from known AC, fill required sections only
- Documentation standards: strict template compliance, no extra sections, no story numbers in high-level docs
- KB extraction protocol: trigger conditions, content routing (guides vs KB), cross-link rules
- Technical Challenges section: when to write it, what fields to include, format example

**Use Case 2 — Feature / Bug Delivery:**
The 8-step Story-Level Development Workflow in `copilot-instructions.md`:

```
Review Requirements → Plan Changes → Implement Code → Tests → Run Locally
→ Update Documentation → Pre-Commit Gate → Commit
```

With project-specific rules injected at each step:

- After Implement: update file-level header comments, check API spec
- After Tests: `npm test` must pass before docs step
- After Docs: verify no stale cross-links
- On Close: extract struggles if debug > 1hr, record test pass rate in impl doc

Both use cases performed **consistently with default Copilot** because everything is explicit in copilot-instructions.md. No agent routing, no ledger, no specialists — just well-structured prose + a reasoning model that follows instructions precisely.

### What SOLAR adds on top of the mandarin baseline

| Layer               | Without SOLAR (mandarin baseline)           | With SOLAR Tier 2                                                |
| ------------------- | ------------------------------------------- | ---------------------------------------------------------------- |
| Workflow definition | Prose in copilot-instructions.md            | Structured `.workflow.md` files, first-class pipeline routes     |
| Execution model     | Agent interprets prose, may drift over time | Governor reads workflow file, executes steps, tracks in ledger   |
| Specialist routing  | Single agent does everything                | Governor delegates to domain specialists per step                |
| Error recovery      | Manual retry, no self-repair                | Bounded recursive repair with explicit completion promises       |
| Adversarial review  | None                                        | Review auditor challenges output before closure                  |
| Restart safety      | Context lost on session end                 | Ledger preserves state — pick up where stopped                   |
| Struggle capture    | Agent may or may not follow the rule        | `docs-curator` agent enforced at close, recorded in ledger       |
| Template compliance | Agent interprets "must follow template"     | `docs-curator` reads template file, validates section by section |

### Why reasoning model matters

The mandarin pattern works WITHOUT SOLAR but **requires a medium or high reasoning model** to follow correctly. A fast/cheap model will:

- Skip checklist items in the 8-step workflow
- Add non-template sections to docs
- Forget to cross-link or update `Last Update` dates
- Miss the struggle-capture trigger condition

SOLAR Tier 2 reduces this dependency by making the pipeline structural rather than instructional — the governor enforces the sequence, the specialists own their domains, and the ledger tracks what was done. A lower-capability model can follow SOLAR Tier 2 successfully because the structure compensates for lower instruction-following fidelity.

**Practical implication for tier design:** Tier 1 (4 agents, no workflow files, no ledger) still requires a good reasoning model — it behaves like mandarin-without-SOLAR. Tier 2 (structured workflows + ledger + specialists) is where SOLAR starts providing value independent of model quality.

### Mandarin's current tier placement

Mandarin today sits between Tier 1 and Tier 2:

| Capability                     | Mandarin today    | Required for Tier 2 |
| ------------------------------ | ----------------- | ------------------- |
| copilot-instructions.md        | ✅ comprehensive  | ✅                  |
| AGENTS.md + 13 agents          | ✅                | ✅                  |
| Active ledger                  | ✅ (root level)   | ✅                  |
| Skills folder (14 skills)      | ✅                | ✅                  |
| hooks.json                     | ✅ (in .github/)  | ✅                  |
| Memory files                   | ❌ not structured | ✅ 7 memory files   |
| solar.config.json              | ❌ not present    | ✅                  |
| solar-workflows/\*.workflow.md | ❌ (prose only)   | ✅ (new in Tier 2)  |
| Path-specific instructions     | ✅ (2 files)      | ✅                  |
| Stack auto-detection on setup  | ❌ manual         | ✅                  |

Migration from mandarin's current state to Tier 2 is minimal: add `solar.config.json`, populate `.github/instructions/*.instructions.md` files (or run `/solar-setup-full` to auto-generate them), and extract the prose workflows into `.workflow.md` files. No existing files need to change.

---

## Open Questions

1. **Should Tier 1 include the ledger?** The ledger adds restart-safety even for solo devs. Could be a `--with-ledger` flag on quick-setup.

2. **Project profile scan reliability** — addressed by the 5-pass over-scan strategy with per-pass fallbacks. Any pass that fails emits a `[POST-IMPLEMENT]` scaffold rather than aborting. Unknown project type → `generic`, minimal memory, 4 core agents. Full scan failure → Tier 1 config only with all skipped passes logged.

3. **Workflow inference quality bar** — addressed: inferred `.workflow.md` files carry `status: inferred` + `source: <file path>` frontmatter. Agents treat `status: inferred` as a suggestion, not a pipeline contract. Users promote to `status: active` explicitly. The risk of a misrepresenting inferred workflow is mitigated by traceability — the source file is always cited so users can verify the extraction.

4. **Convention ingestion depth** — how deep should the scanner read? Reading `CONTRIBUTING.md` and `code-conventions.md` is safe. Parsing `.eslintrc` rule names and feeding them to agents is useful but brittle. Define the depth boundary per convention file type.

5. **Custom agent authoring contract** — a custom agent published to the org library must conform to the SOLAR pipeline contract (delegation matrix, completion promises). A `skill-validator` agent should check this before the custom agent is activated. Define the validation rules.

6. **Non-delivery workflow support in Tier 2** — ML research and ops workflows don't follow feature/bug cycles. The `custom` pipeline type handles them in Tier 2, but the `docs-curator` and `release-readiness-specialist` agents have no concept of experiment close or runbook close. Need to define how custom pipeline types declare their own close criteria and which agents participate.

7. **Pluggable instruction compatibility** — if a project switches from flat `.github/instructions/*.instructions.md` files to a semantic MCP backend, agents that read these files directly will need updating. The `applyTo`-based model is the default abstraction — MCP can be layered on top in Tier 3.

8. **`extends-*` injection point standardization** — the built-in Feature and Bug Fix pipelines need named injection points (`after-implement`, `after-tests`, `on-close`, etc.) added to AGENTS.md so project workflow files can reference them unambiguously. This is a breaking change to the pipeline contract format.

9. **Workflow definition format for Tier 3 DAG pipelines** — simple YAML frontmatter + body works for Tier 2 step lists. Parallel stages and conditional branches need a richer format. Avoid inventing a new DSL — evaluate whether the existing `hooks.json` event model can be extended instead.

10. **Struggle capture threshold** — when the `feature-delivery` workflow says "extract struggles if debug > 1hr", how does an agent measure that? Options: (a) trust agent self-report in ledger, (b) wall-clock time between ledger state transitions, (c) explicit `<!-- debug-time: 2h -->` annotation in impl docs. Option (c) is simplest and most portable across tiers.

11. **Tier 3 as a platform — versioning strategy** — if downstream projects reference `.github/agents@v3.0` from this repo, any breaking change to agent `.md` files becomes a semver concern. Need a versioning and changelog policy for the agent library before org-level sharing is viable.

---

## Appendix: Workflow File Reference

Full example workflow files. These are the mandarin repo use cases converted from prose to `.workflow.md` contracts — the reference implementation for Tier 2 workflow authoring.

### Example 1 — `doc-creation.workflow.md` (custom pipeline)

```markdown
---
name: doc-creation
trigger: "create epic" | "create story" | "create docs"
pipeline: custom
status: active
---

## Steps

1. Identify type: epic or story
2. Load the matching template from `docs/templates/`
   - Epic BR → `epic-business-requirements-template.md`
   - Story BR → `story-business-requirements-template.md`
   - Epic impl → `epic-implementation-template.md`
   - Story impl → `story-implementation-template.md`
3. Fill ALL required sections — no placeholder headings left unfilled
4. Create BR file at: `docs/business-requirements/epic-<num>-<slug>/[README or story-<n>-<m>-<short>.md]`
5. Create implementation file at: `docs/issue-implementation/epic-<num>-<slug>/[README or story-<n>-<m>-<short>.md]`
6. Cross-link both files bidirectionally (BR → impl, impl → BR)
7. Verify template compliance: all sections present, no non-template sections added
8. For epics: scaffold initial story files if ACs are known
```

### Example 2 — `feature-delivery.workflow.md` (extends built-in Feature pipeline)

```markdown
---
name: feature-delivery
trigger: "implement story" | "/ralph-loop"
pipeline: extends-feature
status: active
---

## Injection Points

### after-implement

- Update file-level header comments for any changed exported surface
- Check `api/api-spec.md` if any endpoints were added or changed

### after-tests

- Run `npm test` — must pass before proceeding to docs step
- Confirm no regressions in feature test suite

### after-docs

- Verify no stale cross-links in changed docs
- Confirm `Last Update` date fields updated in both BR and impl docs

### on-close

- If debug time exceeded 1 hour: extract struggle to knowledge base
  - Technical challenge → `docs/knowledge-base/` (conceptual, reusable)
  - Quick fix → `docs/guides/` (project-specific, action-oriented)
- Run full feature test suite: record final pass rate in impl doc
- Set `Status: Completed` in both BR and impl docs
```

### Example 3 — `bug-fix-dev.workflow.md` (extends Bug Fix pipeline — development context)

```markdown
---
name: bug-fix-dev
trigger: "fix bug" | "bug in"
pipeline: extends-bug-fix
status: active
---

## Injection Points

### after-implement

- Update file-level header comments if fix changes exported behaviour

### after-tests

- Run targeted test suite for affected feature only
- Confirm reproduction script from investigation no longer produces error

### on-close

- Record fix summary in story implementation doc
- If root cause was non-obvious: add Technical Challenge entry
```

### Example 4 — `bug-fix-prod.workflow.md` (extends Bug Fix pipeline — post-release, stricter gates)

```markdown
---
name: bug-fix-prod
trigger: "production bug" | "hotfix"
pipeline: extends-bug-fix
status: active
---

## Injection Points

### after-implement

- Update file-level header comments
- Flag any behaviour change that could affect other features

### after-tests

- Run FULL test suite (not targeted) — `npm test`
- Record pass rate in impl doc before proceeding

### after-docs

- Update architecture doc if root cause revealed a structural gap

### on-close

- Mandatory: record root cause + fix in knowledge base regardless of debug time
- Create follow-up story if fix introduced tech debt or deferred scope
- Security auditor gate: required if fix touched auth, validation, or data handling
```

### Use-Case to Workflow Mapping

| Use Case                                     | Workflow File                  | Type                         |
| -------------------------------------------- | ------------------------------ | ---------------------------- |
| Create epic / story docs following templates | `doc-creation.workflow.md`     | `custom`                     |
| Implement + test + doc sync for a feature    | `feature-delivery.workflow.md` | `extends-feature`            |
| Fix a bug during active development          | `bug-fix-dev.workflow.md`      | `extends-bug-fix`            |
| Fix a production bug / hotfix after release  | `bug-fix-prod.workflow.md`     | `extends-bug-fix` (stricter) |

# Copilot Instructions for AI Coding Agents

<!-- ============================================================
  TEMPLATE MODE — SOLAR IS INACTIVE
  ============================================================
  This is the agentic-devops-solar-ralph template in its default state.
  SOLAR autonomous hooks are disabled until you complete setup below.

  ⚠️  APPLYING TO AN EXISTING REPO?
  If your target repo already has a .github/copilot-instructions.md,
  do NOT replace it. Instead, MERGE the SOLAR-Ralph sections below
  into your existing file:
    - Copy the "SOLAR-Ralph Operating Overlay" subsection into your
      existing ## Workflows section (or add it after).
    - Copy the "📁 SOLAR-Ralph Key Files" section at the bottom.
    - Keep all your existing project-specific content intact.

  SETUP CHECKLIST (fill in every [POST-IMPLEMENT] block, then activate):
  1. [ ] Replace [YOUR-REPO-NAME] with your project name (line below)
  2. [ ] Fill in ## Quick Start — install/dev/test commands
  3. [ ] Fill in ## Architecture — stack, folders, state, auth
  4. [ ] Fill in ## Workflows — dev flow, test framework, deployment
  5. [ ] Fill in ## Naming & Structure — file/function conventions
  6. [ ] Fill in ## Testing — framework, coverage, query conventions
  7. [ ] Fill in ## Documentation Standards — doc types, style
  8. [ ] Fill in ## Code Change Checklist — project-specific gates
  9. [ ] Fill in ## Git & Branching — branch naming, commit format
  10. [ ] Fill in ## Closing Work Items — PR/merge criteria
  11. [ ] Fill in ## Key Files — index of important files/docs
  12. [ ] Set `SOLAR_ACTIVE: true` in .ai_ledger.md to enable hooks
  ============================================================ -->

Operational playbook for AI agents contributing to `[YOUR-REPO-NAME]`.

> **Setup:** Fill in every `[POST-IMPLEMENT]` block. SOLAR-Ralph sections are ready to use as-is.

## ⚡ Quick Start

<!-- [POST-IMPLEMENT] -->

Install: `[install command]` | Dev: `[dev command]` | Tests: `[test command]`

## 🏗️ Architecture

<!-- [POST-IMPLEMENT: tech stack, folder layout, state, routing, auth] -->

**Frontend**: [stack + feature folder]
**Backend**: [stack + folder]
**State**: [approach] | **Data**: [DB/ORM] | **Auth**: [auth approach]

## 🔄 Workflows

<!-- [POST-IMPLEMENT: workflow summaries + links to detailed guides] -->

Development: [local dev flow] | Testing: [framework + command] | Deployment: [targets]

### 🤖 SOLAR-Ralph Operating Overlay

When work is executed through the repo's SOLAR-Ralph files, treat the current workflow above as the governing delivery path and the SOLAR files as the execution overlay.

- Orchestration contract: `AGENTS.md`
- Restart-safe ledger: `.ai_ledger.md`
- Lifecycle hooks: `.github/hooks/hooks.json`
- Path-specific instructions: <!-- [POST-IMPLEMENT: any special instructions for certain file paths] -->
- Operator guides: `.github/guides/solar-ralph-workflow.md`, `.github/guides/agent-operations-guide.md`, `.github/guides/memory-governance-guide.md`

Working rules:

- Keep active execution state in `.ai_ledger.md`.
- Keep concise persistent facts in `/memories/repo/`.
- Keep durable guidance in `docs/`.
- Use bounded recursive repair loops with explicit completion promises instead of open-ended retry.
- Route frontend, backend, security, review, and documentation work through their matching specialist roles when the SOLAR overlay is active.

### 🧪 Task-Level Development Workflow

Follow this sequence for every task (feature, bug fix, or enhancement):

1. **Review** — Confirm AC clarity; resolve ambiguities before coding.
2. **Plan** — Identify impacted areas; check <!-- [POST-IMPLEMENT: architecture docs or impacted areas guide] --> for conflicts.
3. **Implement** — Keep scope bound to AC; defer extras to a follow-up task.
4. **Test** — Cover happy path + at least one edge case; isolate unit tests for new logic.
5. **Run Locally** — Verify manually; capture any AC discrepancies.
6. **Docs** — Record decisions, data shape changes, performance notes.
7. **Pre-Commit Gate** — Tests pass; type check & lint clean.
8. **Commit** — `<type>(<scope>): <summary>`; include doc updates in same commit. <!-- [POST-IMPLEMENT:  Replace with project-specific commit message format] -->

If blocked: pause and record the blocker with a concrete escalation reason in `.ai_ledger.md`.

## 🏷️ Naming & Structure

<!-- [POST-IMPLEMENT: naming conventions for files, functions, tests, branches] -->

## 🧪 Testing

<!-- [POST-IMPLEMENT: framework, coverage requirements, query conventions] -->

## 📝 Documentation Standards

<!-- [POST-IMPLEMENT: doc types, content requirements, style guide] -->

## 🛠️ Code Change Checklist

<!-- [POST-IMPLEMENT: checklist items] -->

## 🌿 Git & Branching

<!-- [POST-IMPLEMENT: branch naming convention] -->

## ✅ Closing Work Items

<!-- [POST-IMPLEMENT: closing criteria, PR requirements] -->

## 🧷 Quality Gates

<!-- [POST-IMPLEMENT:  add any project-specific gates, e.g., performance benchmarks, security review] -->

## 🛠️ Resources

<!-- [POST-IMPLEMENT: add links to architecture docs, style guides, testing guidelines, or any other resources agents should reference during implementation] -->

## 📁 SOLAR-Ralph Key Files

<!-- [POST-IMPLEMENT: add any other important files that agents should be aware of -->

SOLAR Workflow: `.github/guides/solar-ralph-workflow.md`
Agent Operations: `.github/guides/agent-operations-guide.md`
Memory Governance: `.github/guides/memory-governance-guide.md`

---

If any section is unclear or missing — ask for clarification before proceeding.

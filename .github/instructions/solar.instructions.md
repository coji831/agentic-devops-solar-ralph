# SOLAR-Ralph Copilot Instructions

This file contains all SOLAR-specific Copilot instructions, workflows, and overlays. Project-specific instructions should remain in `.github/copilot-instructions.md`.

---

## 🤖 SOLAR-Ralph Operating Overlay

When work is executed through the repo's SOLAR-Ralph files, treat the user's project workflow as the governing delivery path and the SOLAR files as the execution overlay.

**Core SOLAR Files:**

- Orchestration contract: `.github/AGENTS.md`
- Restart-safe ledger: `.github/.ai_ledger.md`
- Lifecycle hooks: `.github/hooks/hooks.json`
- Path-specific instructions: `.github/instructions/solar.instructions.md`
- Operator guides: `.github/guides/solar-ralph-workflow.md`, `.github/guides/agent-operations-guide.md`, `.github/guides/memory-governance-guide.md`

**Working Rules:**

- Keep active execution state in `.github/.ai_ledger.md`
- Keep concise persistent facts in `.github/memories/repo/`
- Keep durable guidance in `docs/`
- Use bounded recursive repair loops with explicit completion promises instead of open-ended retry
- Route frontend, backend, security, review, and documentation work through their matching specialist roles when the SOLAR overlay is active

---

## 🧪 Task-Level Development Workflow

Follow this sequence for every task (feature, bug fix, or enhancement):

1. **Review** — Confirm AC clarity; resolve ambiguities before coding
2. **Plan** — Identify impacted areas; check architecture docs for conflicts
3. **Implement** — Keep scope bound to AC; defer extras to a follow-up task
4. **Test** — Cover happy path + at least one edge case; isolate unit tests for new logic
5. **Run Locally** — Verify manually; capture any AC discrepancies
6. **Docs** — Record decisions, data shape changes, performance notes
7. **Pre-Commit Gate** — Tests pass; type check & lint clean
8. **Commit** — `<type>(<scope>): <summary>`; include doc updates in same commit

**If blocked:** Pause and record the blocker with a concrete escalation reason in `.github/.ai_ledger.md`.

---

## 🛠️ SOLAR Setup & Bootstrap

**Bootstrap Mode Override:**

- Use only for setup and recovery operations
- Bypasses all SOLAR governance hooks temporarily
- Activated automatically by the `Solar Bootstrap` agent
- Manual activation: `/solar-enter-bootstrap` (emergency only)
- Manual deactivation: `/solar-exit-bootstrap`

**Installation Modes:**

- **Minimal install:** Installs only core framework files (agents, hooks, skills, prompts, guides)
- **Enhanced install:** Runs full setup wizard and scaffolds project files (ledger, instructions, memory)

**Setup Commands:**

- `/solar-setup-scan-repo` — Auto-detect project stack and paths
- `/solar-setup-core-config` — Apply config to core SOLAR files
- `/solar-setup-agent-config` — Apply config to agents, skills, and path instructions
- `/solar-setup-scaffold` — Create ledger, solar.instructions.md, and memory templates

**Activation:**
All governance and memory files are created only after setup is complete. SOLAR remains disabled until `solar.active: true` is set in `.github/solar.config.json`.

---

## 📁 SOLAR-Ralph Key Files

**Workflow & Operations:**

- SOLAR Workflow Guide: `.github/guides/solar-ralph-workflow.md`
- Agent Operations Guide: `.github/guides/agent-operations-guide.md`
- Memory Governance Guide: `.github/guides/memory-governance-guide.md`

**Knowledge Base:**

- Full documentation: `docs/knowledge-base/`
- Implementation guideline: `SOLAR-Ralph-implementation-guideline.md`
- Framework reference: `docs/solar-ralph-reference.md`

---

For complete details, see the SOLAR-Ralph implementation guideline and knowledge base in `docs/knowledge-base/`.

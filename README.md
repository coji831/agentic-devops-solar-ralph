# 🤖 SOLAR-Ralph: The Autonomous Engineering Harness

[![Copilot 2026 Ready](https://img.shields.io/badge/Copilot-2026_Ready-blue.svg)](https://github.com/features/copilot)
[![Framework SOLAR-Ralph](https://img.shields.io/badge/Framework-SOLAR--Ralph-orange.svg)](#the-solar-framework)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Stop "vibe coding" and start building autonomous agentic teams.**

The SOLAR-Ralph Harness is a professional-grade template for implementing the **Specialist, Orchestrator, Ledger, Adversarial, and Recursive** framework within the GitHub Copilot ecosystem. It solves the "Human-in-the-Loop Bottleneck" by transforming AI from a reactive autocomplete tool into a relentless autonomous co-worker.

---

## 🏗️ The SOLAR Framework (Early 2026 Standard)

Unlike flat multi-agent systems, SOLAR-Ralph uses a **Hierarchical Multi-Agent System (HMAS)** to manage complexity and prevent "Context Rot."

| Layer | Component        | Implementation              | Purpose                                                |
| :---- | :--------------- | :-------------------------- | :----------------------------------------------------- |
| **S** | **Specialist**   | `.github/agents/*.agent.md` | High-fidelity domain experts (Frontend, Security, DB). |
| **O** | **Orchestrator** | `.github/AGENTS.md`         | The Governor. Decomposes tasks and routes via skills.  |
| **L** | **Ledger**       | `.github/.ai_ledger.md`     | Amnesia-free persistent state and "Mistake Records".   |
| **A** | **Adversarial**  | Review Auditors + Security  | Reward Auditing (ARA) to prevent "Code Gaming".        |
| **R** | **Recursive**    | `/ralph-loop` + Stop hooks  | Deterministic iteration via bounded loops.             |

---

## 🚀 Quick Start

**1. Install:**

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install.ps1; .\install.ps1; Remove-Item install.ps1

# macOS/Linux (Bash)
curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh | bash
```

**2. Setup:** Run `/solar-setup-quick` (or `/solar-setup-full` for advanced customization)

**3. Test:** Run `/ralph-loop "Add a README badge"`

**📖 Detailed Guide:** See [SOLAR-Ralph Implementation Guideline](SOLAR-Ralph-implementation-guideline.md)

---

## 🔥 Key 2026 Features Included

### 1. The Ralph Wiggum Loop (Deterministic Persistence)

Embraces the philosophy that **"Iteration Beats Perfection."** The agent is trapped in a self-correcting bash loop that re-injects the prompt until your code passes strong "Backpressure" gates (tests, types, and builds).

### 2. Agentic Context Rotation

Solves the "malloc/free problem" of context windows. Our Stop Hooks automatically monitor token usage and trigger rotations at 80% capacity, clearing history while preserving state in the Ledger and Git.

### 3. Adversarial Reward Auditing (ARA)

Included specialized auditors that hunt for "Proxy Sovereignty"—detecting when implementation agents modify unit tests to pass rather than fixing underlying bugs.

### 4. Hybrid Persistent Memory

Combines local `.github/memories/repo/` fact files with GitHub-hosted **Copilot Memory** for cross-session intelligence that survives amnesia.

---

## 📂 Repository Structure

- `.github/AGENTS.md` - Orchestration contract and pipeline definitions
- `.github/.ai_ledger.md` - Persistent work state and mistake ledger
- `.github/agents/` - 14 specialist personas (Governor, Architects, Specialists, Auditors)
- `.github/skills/` - 14 reusable workflows (Implementation, Testing, Review, Governance)
- `.github/prompts/` - Setup commands and runtime prompts
- `.github/commands/` - Core runtime commands (`ralph-loop`, `audit-story`)
- `.github/hooks/` - Lifecycle automation (Stop hooks, Post-tool-use validation)
- `.github/guides/` - Operator documentation and workflow guides
- `.github/memories/repo/` - Persistent fact templates (optional)
- `verification-artifacts/` - Evidence backbone for release readiness
- `docs/knowledge-base/` - Pattern guides and architectural references

---

## 🛡️ Security & Governance

- **Bypass Approvals Mode:** Configured for low-risk pipelines to enable true "Away From Keyboard" (AFK) development.
- **Sandboxed MCPs:** Local stdio servers are restricted via OS-level sandboxing (macOS/Linux).

# 🤖 SOLAR-Ralph: The Autonomous Engineering Harness

[![Copilot 2026 Ready](https://img.shields.io/badge/Copilot-2026_Ready-blue.svg)](https://github.com/features/copilot)
[![Framework SOLAR-Ralph](https://img.shields.io/badge/Framework-SOLAR--Ralph-orange.svg)](#the-solar-framework)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Stop "vibe coding" and start building autonomous agentic teams.**

The SOLAR-Ralph Harness is a professional-grade template for implementing the **Specialist, Orchestrator, Ledger, Adversarial, and Recursive** framework within the GitHub Copilot ecosystem. It solves the "Human-in-the-Loop Bottleneck" by transforming AI from a reactive autocomplete tool into a relentless autonomous co-worker.

---

## 🏗️ The SOLAR Framework (Early 2026 Standard)

Unlike flat multi-agent systems, SOLAR-Ralph uses a **Hierarchical Multi-Agent System (HMAS)** to manage complexity and prevent "Context Rot."

| Layer | Component        | Implementation        | Purpose                                                 |
| :---- | :--------------- | :-------------------- | :------------------------------------------------------ |
| **S** | **Specialist**   | `.github/agents/*.md` | High-fidelity domain experts (Frontend, Security, DB).  |
| **O** | **Orchestrator** | `AGENTS.md`           | The Governor. Decomposes tasks and routes via `/skill`. |
| **L** | **Ledger**       | `.ai_ledger.md`       | Amnesia-free persistent state and "Mistake Records".    |
| **A** | **Adversarial**  | `Audit-Story.md`      | Reward Auditing (ARA) to prevent "Code Gaming".         |
| **R** | **Recursive**    | `/ralph-loop`         | Deterministic iteration via the Ralph Wiggum Technique. |

---

## 🚀 Quick Start (5 Minutes)

1.  **Clone the Harness:**
    `git clone https://github.com/coji831/agentic-devops-solar-ralph.`

2.  **Install MCP Infrastructure:**
    Configure your `.vscode/mcp.json` with the included servers for browser automation and repo access.

3.  **Initialize the Ledger:**
    `cp.ai_ledger.example.md.ai_ledger.md`

4.  **Launch your first Autonomous Loop:**

    ```bash
    /ralph-loop "Implement a secure JWT auth flow. Use TDD. <promise>SUCCESS</promise>" --max-iterations 20
    ```

---

## 🛠️ Template Setup — Applying to a New Repo

SOLAR-Ralph ships in **template mode** (SOLAR is inactive by default). For the complete step-by-step setup guide — including which files to copy, what to customize, and how to activate the system — see the **[Full Implementation Guideline](SOLAR-Ralph-implementation-guideline.md)**.

**TL;DR:**

1. Copy universal files into your target repo (see guideline Step 1)
2. Customize `[POST-IMPLEMENT]` sections for your stack (see guideline Step 2)
3. Populate `/memories/repo/` with your repo's facts (see guideline Step 3)
4. Set `SOLAR_ACTIVE: true` in `.ai_ledger.md` to activate hooks

---

## 🔥 Key 2026 Features Included

### 1. The Ralph Wiggum Loop (Deterministic Persistence)

Embraces the philosophy that **"Iteration Beats Perfection."** The agent is trapped in a self-correcting bash loop that re-injects the prompt until your code passes strong "Backpressure" gates (tests, types, and builds).

### 2. Agentic Context Rotation

Solves the "malloc/free problem" of context windows. Our Stop Hooks automatically monitor token usage and trigger rotations at 80% capacity, clearing history while preserving state in the Ledger and Git.

### 3. Adversarial Reward Auditing (ARA)

Included specialized auditors that hunt for "Proxy Sovereignty"—detecting when implementation agents modify unit tests to pass rather than fixing underlying bugs.

### 4. Hybrid Persistent Memory

Combines local `/memories/repo/` fact files with GitHub-hosted **Copilot Memory** for cross-session intelligence that survives amnesia.

---

## 📂 Repository Structure

- `.github/agents/` - Specialist personas (Claude 4.5/GPT-5 optimized).
- `.github/skills/` - Procedural knowledge (TDD, migrations, security scans).
- `.github/hooks/` - Lifecycle automation (Stop hooks, Post-tool lints).
- `/verification-artifacts/` - Evidence backbone for release readiness.
- `AGENTS.md` - The global pipeline contract and delegation rules.

---

## 🛡️ Security & Governance

- **Bypass Approvals Mode:** Configured for low-risk pipelines to enable true "Away From Keyboard" (AFK) development.
- **Sandboxed MCPs:** Local stdio servers are restricted via OS-level sandboxing (macOS/Linux).

# SOLAR-Ralph Implementation Guideline

A guide for installing, running, and extending the SOLAR-Ralph agent harness in your repository.

---

## 1. Installation

Open `solar-install.prompt.md` in VS Code agent mode and follow the prompts. The installer runs interactively — it asks clarifying questions (target stack, test runner, optional components) and generates all files in one pass.

**Steps:**

1. Copy `solar-install.prompt.md` to your target repository root (or reference it directly from this template repo).
2. Open GitHub Copilot Chat in agent mode.
3. Reference the file: `#solar-install.prompt.md` — then send.
4. Answer the installer questions when prompted (stack, test runner, existing agent system, optional components).
5. Review generated files; merge any `.patch.md` conflict files manually if AGENTS.md or copilot-instructions.md already existed.

---

## 2. What Gets Installed

The base installation generates the following files:

| Category                     | Count | Location                                                                 |
| ---------------------------- | ----- | ------------------------------------------------------------------------ |
| Orchestration manifest       | 1     | `.github/AGENTS.md`                                                      |
| Agents                       | 7     | `.github/agents/*.agent.md`                                              |
| Skills                       | 7     | `.github/skills/*/SKILL.md`                                              |
| Hooks                        | 2     | `.github/hooks/hooks.json` + `post-tool-use.cjs` + `stop.cjs`            |
| Prompts                      | 2     | `.github/prompts/solar.prompt.md` + `solar-registry-update.prompt.md`    |
| Instructions                 | 2     | `.github/instructions/solar.instructions.md` + `{stack}.instructions.md` |
| System config                | 1     | `.github/solar.config.json`                                              |
| Ledger                       | 1     | `.github/.ai_ledger.md`                                                  |
| Copilot overlay              | 1     | `.github/copilot-instructions.md`                                        |
| Solar-system reference files | 9     | `.github/solar-system/`                                                  |

**Agents (7):** Orchestration Governor, Data Collector Specialist, Design Planning Architect, Implementation Specialist, Test Specialist, Docs Curator, Review Auditor.

**Skills (7):** `data-collection`, `design-planning`, `implementation`, `testing`, `doc-sync`, `review`, `recursive-remediation`.

**Hooks (2):** `post-tool-use` (write-op guard — ADVERSARIAL_VERIFY_REQUIRED signal at VERIFY stage), `stop` (blocks exit when Completion Promise: pending).

---

## 3. First Task

After installation, run the solar prompt in GitHub Copilot Chat agent mode:

```
#solar.prompt.md
```

The Governor reads `.github/AGENTS.md` and `.github/.ai_ledger.md`, writes a Work Queue row, and dispatches the first specialist. Task output goes to `verification-artifacts/`.

---

## 4. Registry Sync

After adding or removing agents or skills, run:

```
#solar-registry-update.prompt.md
```

This updates the Agent Registry and Skill Index tables in `.github/AGENTS.md` to match the current file set. Required after any component change — AGENTS.md is the sole routing source of truth.

---

## 5. Optional Components

### Learning System

Activates agent learning capture (patterns, errors, feature requests).

1. Set `"learning": true` in `.github/solar.config.json`.
2. Add `"learningsPath": ".github/solar-system/learnings/"` to `solar.config.json`.
3. The agent scaffolds `PATTERNS.md`, `ERRORS.md`, `FEATURE_REQUESTS.md`, and `LOG-SOURCES.md` in `.github/solar-system/learnings/` on first use.

### Session Logging

Activates per-session activity log files.

1. Set `"logging": true` in `.github/solar.config.json`.
2. Add `"logsPath": ".github/solar-system/logs/"` to `solar.config.json`.
3. Log files are written to `.github/solar-system/logs/` at runtime and are gitignored by default.

### Stack-Specific Specialists

For non-generic stacks (e.g. React + TypeScript, Node.js + Express), the installer generates stack-prefixed agent and skill files (e.g. `react-ts-implementation-specialist.agent.md`). If you add stack specialists after installation:

1. Create the agent `.agent.md` file in `.github/agents/`.
2. Create the skill `SKILL.md` file in `.github/skills/{name}/`.
3. Run `#solar-registry-update.prompt.md` to register both in AGENTS.md.

---

## 6. Config Reference

The 5 flags in `.github/solar.config.json`:

| Flag             | Default | Effect                                                                                    |
| ---------------- | ------- | ----------------------------------------------------------------------------------------- |
| `adversarial`    | `true`  | Adversarial audit gate at VERIFY stage. Disable only for exploration tasks.               |
| `learning`       | `false` | Learning system. Agents write patterns/errors to `learnings/`.                            |
| `logging`        | `false` | Session logging. Hook writes activity logs to `logs/`.                                    |
| `human_approval` | `true`  | Governor waits for user confirmation before dispatching. Set `false` for unattended runs. |
| `hooks`          | `true`  | All hooks active. Set `false` to disable globally.                                        |

To disable all hooks globally, set in `solar.config.json`:

```json
"hooks": false
```

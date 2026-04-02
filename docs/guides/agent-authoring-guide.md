# Agent Authoring Guide

A reference for creating `.agent.md` files in this repository. Covers all frontmatter fields, the three SOLAR agent patterns, tool names, and how to use subagents and handoffs.

**Official docs:** [VS Code — Custom Agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents)

---

## When to create an agent (vs. a prompt)

| Need                                                | Use                                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------------- |
| Persistent persona — always same role, tools, model | `.agent.md` (this guide)                                                  |
| One-off task, no tool restrictions needed           | `.prompt.md` (see [prompt-authoring-guide.md](prompt-authoring-guide.md)) |
| Portable multi-file capability with scripts         | `SKILL.md`                                                                |

---

## File location and naming

All workspace agents live in `.github/agents/`. VS Code detects every `.agent.md` file in that folder automatically.

**Naming convention:** `kebab-case-role.agent.md`

```
.github/agents/
  orchestration-governor.agent.md
  security-auditor.agent.md
  backend-implementation-specialist.agent.md
```

The agent is invoked by its `name:` value (can contain spaces), not the filename.

---

## Frontmatter field reference

```yaml
---
name: My Agent # Display name; used in @mentions and subagent lists
description: "One-line role statement" # Shown in the agent picker and as chat placeholder
tools: [read, search, edit, execute, agent, todo] # See tool names below
model: Claude Haiku 4.5 (copilot) # Or an array for fallback: [Model A, Model B]
user-invocable: true # false = hidden from picker, usable only as subagent
agents: # Explicit subagent allow-list (omit = no subagent calls)
  - Other Agent Name
handoffs: # Suggested next-action buttons after a response
  - label: Button text
    agent: target-agent-name
    prompt: Pre-filled prompt for the target
    send: false # true = auto-submit
    model: Claude Sonnet 4.5 (copilot) # optional model for this handoff
---
```

All fields except `description` are optional, but `name`, `tools`, and `model` should always be set explicitly.

---

## Valid tool names

VS Code built-in tools you can add to the `tools` array:

| Tool name | What it grants                                    |
| --------- | ------------------------------------------------- |
| `read`    | File reading, directory listing                   |
| `search`  | Codebase and semantic search                      |
| `edit`    | File create/edit/delete                           |
| `execute` | Terminal commands                                 |
| `agent`   | Subagent invocation (requires `agents:` list too) |
| `todo`    | Manage the todo list                              |
| `web`     | Web fetch / browser tools                         |

MCP server tools use the format `<server-name>/<tool-name>` or `<server-name>/*` for all tools from a server.

> **Rule:** Never add tools an agent doesn't need. Auditors and read-only agents should have only `[read, search, execute]`. Write access is a privilege, not a default.

---

## SOLAR agent patterns

SOLAR uses three distinct agent patterns. Match the pattern to the role.

---

### Pattern 1 — Governor / Orchestrator

**Purpose:** Delegates to specialists; never does the implementation itself.

```yaml
---
name: My Governor
description: "Orchestrates work across specialists"
tools: [read, search, edit, execute, agent, todo]
model: [Claude Haiku 4.5 (copilot), Claude Sonnet 4.5 (copilot)]
user-invocable: true
agents:
  - Specialist One
  - Specialist Two
---
```

**Key choices:**

- `agent` tool is required to invoke subagents; `agents:` lists the exact allow-list.
- Model array provides a fallback: tries Haiku first (cheaper), falls back to Sonnet.
- `user-invocable: true` — appears in the agent picker for direct user invocation.
- Body instructs the agent to delegate, not implement.

**Example in this repo:** [orchestration-governor.agent.md](../../.github/agents/orchestration-governor.agent.md)

---

### Pattern 2 — Specialist (with write access)

**Purpose:** Implements code, writes files, runs terminal commands for a specific domain.

```yaml
---
name: Backend Implementation Specialist
description: "Use when implementing backend domain changes"
tools: [read, search, edit, execute, todo]
model: Claude Sonnet 4.5 (copilot)
user-invocable: false
---
```

**Key choices:**

- `user-invocable: false` — hidden from the picker; only reachable as a subagent from the governor.
- Has `edit` and `execute` because it actually writes files and runs commands.
- No `agents:` property — specialists don't spawn their own subagents.
- Sonnet or better model for reasoning-heavy implementation work.

**Examples in this repo:** `backend-implementation-specialist.agent.md`, `frontend-implementation-specialist.agent.md`

---

### Pattern 3 — Auditor / Read-only specialist

**Purpose:** Reviews, challenges, or audits without making changes.

```yaml
---
name: Security Auditor
description: "Use when changes affect auth, cookies, JWT, CORS..."
tools: [read, search, execute]
model: Claude Haiku 4.5 (copilot)
user-invocable: false
---
```

**Key choices:**

- No `edit` tool — cannot modify files by design. This enforces the adversarial role.
- `execute` is kept for running lint/test commands to check existing state.
- Haiku model is sufficient; auditing is pattern-matching, not generation.
- `user-invocable: false` — only invoked by the governor when needed.

**Examples in this repo:** `security-auditor.agent.md`, `backend-review-auditor.agent.md`, `frontend-review-auditor.agent.md`

---

## Body structure

The body is Markdown prepended to every user prompt when the agent is active.

**SOLAR convention:** use `<xml-tags>` for major structural sections. This makes the sections unambiguous to the model and avoids clashing with Markdown headings in user messages.

```markdown
---
name: My Specialist
description: "..."
tools: [read, search, edit]
model: Claude Sonnet 4.5 (copilot)
user-invocable: false
---

<identity>
You are the [role] for this repository. One sentence that defines purpose.
</identity>

<progress_protocol>
Output each line immediately before the corresponding step:

- Step 1 indicator
- Step 2 indicator
  </progress_protocol>

<execution_steps>
Detailed instructions for what the agent must do.
</execution_steps>

<constraints>
- Hard rules the agent must never violate
- e.g., "NEVER write a completion promise just to exit"
</constraints>
```

---

## Subagent configuration

To allow an agent to call other agents:

1. Add `agent` to the `tools` array.
2. Add an explicit `agents:` allow-list in frontmatter (or `*` for all).

```yaml
tools: [read, search, edit, execute, agent, todo]
agents:
  - Backend Implementation Specialist
  - Frontend Implementation Specialist
```

Omitting `agents:` entirely means the agent cannot invoke subagents even if it has the `agent` tool.

Setting `user-invocable: false` on a specialist hides it from the picker but keeps it available as a subagent target.

---

## Handoffs

Handoffs add "next action" buttons after a response. Useful for multi-stage workflows.

```yaml
handoffs:
  - label: Start Implementation
    agent: implementation-specialist
    prompt: Implement the plan above. Follow the story BR.
    send: false
```

- `send: false` — button appears, user reviews before clicking.
- `send: true` — clicking the button auto-submits. Use only for low-risk transitions.
- `agent` matches the target's `name:` value (case-sensitive).

---

## Decision guide

```
Does the agent orchestrate and delegate?
  YES → Pattern 1 (Governor). Add agent tool + agents allow-list.
  NO  ↓

Does the agent write or modify files?
  YES → Pattern 2 (Specialist). Include edit + execute tools.
  NO  ↓

Does the agent review or audit without modifying?
  YES → Pattern 3 (Auditor). read + search + execute only. No edit.
```

---

## SOLAR naming convention

| Role                      | Suffix                       |
| ------------------------- | ---------------------------- |
| Coordinator/governor      | `-governor`                  |
| Writes code for a domain  | `-implementation-specialist` |
| Writes tests for a domain | `-test-specialist`           |
| Reviews code for a domain | `-review-auditor`            |
| Cross-cutting security    | `security-auditor`           |
| Setup/bootstrap utility   | `solar-bootstrap`            |
| Architecture decisions    | `design-planning-architect`  |

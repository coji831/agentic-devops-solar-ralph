# Prompt Authoring Guide

A reference for creating `.prompt.md` files in this repository. Explains when to use each format pattern and why the existing SOLAR prompts look different from each other.

**Official docs:** [VS Code — Prompt Files](https://code.visualstudio.com/docs/copilot/customization/prompt-files)

---

## Why the formats differ

VS Code prompt files share the same `.prompt.md` extension but serve different purposes. The frontmatter fields and body structure should match the intended use case:

| Field           | What it controls                                                             |
| --------------- | ---------------------------------------------------------------------------- |
| `name`          | The `/command` name in chat                                                  |
| `description`   | Tooltip shown in the command picker                                          |
| `agent`         | Which agent runs the prompt (`ask`, `agent`, `plan`, or a custom agent name) |
| `model`         | Which LLM runs the prompt (defaults to the user's current picker selection)  |
| `tools`         | Tool list available to the prompt (overrides agent defaults)                 |
| `argument-hint` | Placeholder text shown in the chat input                                     |

No field is required. Omitting `agent` uses whatever agent is currently active when the user runs the command. Omitting `model` uses whatever the user has selected.

The SOLAR prompts use **three distinct patterns**, each suited to a different type of task.

---

## Pattern 1 — Lightweight trigger

**Use when:** you want to delegate immediately to a specific agent with minimal setup.

```markdown
---
name: solar
description: "One-line description of what this triggers"
model: "Claude Haiku 4.5 (copilot)"
---

[TASK]: ${input:task:Describe what you want done}

@Orchestration Governor
```

**Key choices:**

- `model` is specified so a fast/cheap model handles routing; the delegated agent may use its own model.
- Body is minimal — just the user input variable and an `@AgentName` mention.
- `@AgentName` at the bottom hard-routes execution to that agent unconditionally.

**Example in this repo:** [solar.prompt.md](../../.github/prompts/solar.prompt.md)

---

## Pattern 2 — Structured task prompt

**Use when:** the prompt carries its own detailed instructions and the agent follows them directly.

```markdown
---
name: solar-audit-story
description: "What this prompt does and what it returns"
model: "Claude Sonnet 4.5 (copilot)"
---

[TARGET]: ${input:target:What to audit}

## Section 1

Instructions for this section...

## Section 2

Instructions for this section...
```

**Key choices:**

- `model` is set to a more capable model because the prompt body contains reasoning-heavy instructions.
- No `agent` field — runs in the current agent context (usually `agent` mode when invoked via `/command`).
- Body uses Markdown headings to structure the task the AI must execute.
- `${input:variableName:placeholder}` collects required inputs from the user at run time.

**Example in this repo:** [solar-audit-story.prompt.md](../../.github/prompts/solar-audit-story.prompt.md)

---

## Pattern 3 — Bootstrap / setup prompt

**Use when:** the prompt must run with a specific custom agent that has restricted tools and isolated context.

```markdown
---
name: solar-setup-quick
description: "Short description"
agent: Solar Bootstrap
---

<identity>
You are the XYZ Agent. One-sentence role statement.
</identity>

<task_goal>
High-level objective. What success looks like.
</task_goal>

<task>
1. Step one
2. Step two
3. Step three
</task>
```

**Key choices:**

- `agent: Solar Bootstrap` hard-binds the prompt to that agent — governance hooks are bypassed, tool set is scoped.
- No `model` field — the agent's own model preference applies.
- Body uses XML-like tags (`<identity>`, `<task>`, `<task_goal>`) rather than Markdown headings. This is a SOLAR convention that makes the structure unambiguous for the bootstrap agent, which parses these prompts programmatically.

**Example in this repo:** [solar-setup-quick.prompt.md](../../.github/prompts/solar-setup-quick.prompt.md), [solar-enter-bootstrap.prompt.md](../../.github/prompts/solar-enter-bootstrap.prompt.md)

---

## Decision guide

```
Does the prompt need a specific custom agent (e.g. Solar Bootstrap)?
  YES → Pattern 3 (bootstrap/setup). Use XML tags in body.
  NO  ↓

Does the prompt delegate everything to another agent via @AgentName?
  YES → Pattern 1 (lightweight trigger). Keep body minimal.
  NO  ↓

Does the prompt carry its own detailed instructions?
  YES → Pattern 2 (structured task). Use Markdown sections + ${input:...}.
```

---

## Input variables

Collect user input at run time with the `${input:...}` syntax:

```
${input:variableName}                   # required input, no placeholder
${input:variableName:placeholder text}  # required input with hint
```

The AI will prompt the user for any unfilled variables when the command runs.

---

## Frontmatter field reference

```yaml
---
name: solar-my-prompt # used as /solar-my-prompt in chat
description: "Short description shown in the command picker"
agent: Solar Bootstrap # omit to use the current active agent
model: "Claude Sonnet 4.5 (copilot)" # omit to use the user's picker selection
tools: ["search/codebase", "vscode/askQuestions"] # omit to inherit from agent
argument-hint: "Describe what you want done" # placeholder in chat input
---
```

All fields are optional. Add only what you need.

---

## SOLAR naming convention

All prompts in this repo use the `solar-` prefix:

| Prefix                           | Purpose                       |
| -------------------------------- | ----------------------------- |
| `solar`                          | Governor trigger (no suffix)  |
| `solar-setup-*`                  | Bootstrap setup commands      |
| `solar-enter-*` / `solar-exit-*` | Mode transitions              |
| `solar-audit-*`                  | Adversarial review commands   |
| `solar-workflow-*`               | Documentation/process updates |

---

## File location

All workspace prompt files live in `.github/prompts/`. Users invoke them via `/command-name` in the VS Code chat input.

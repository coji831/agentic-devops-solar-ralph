# SOLAR Hooks — Firing Conditions Reference

Documents when each hook fires, what guards gate it, and the current stripped state for debugging.

---

## Hook Overview

| Hook file                | Event              | Fires when                                 |
| ------------------------ | ------------------ | ------------------------------------------ |
| `user-prompt-submit.cjs` | `UserPromptSubmit` | User sends a message to the chat           |
| `post-tool-use.cjs`      | `PostToolUse`      | Any tool call completes                    |
| `stop.cjs`               | `Stop`             | Agent response ends                        |
| `subagent-announce.cjs`  | `SubagentStart`    | A subagent is spawned via the `agent` tool |

---

## Guard Chain (Normal Operation)

All four hooks run the same layered guard chain. An early exit at any layer means the hook silently skips its output.

```
Layer 1 — Global kill switches
  ↓ config.solar.active === false           → exit 0
  ↓ config.hooks.enabled === false          → exit 0
  ↓ config.hooks.<hookKey>.enabled === false → exit 0

Layer 2 — Read ledger → determine currentMode
  ↓ ledger has "Session-Type: <type>"       → sessionTypes[type] → currentMode
  ↓ no ledger / no match                    → currentMode = "simple"

Layer 3 — Bootstrap bypass
  ↓ currentMode === "bootstrap"             → exit 0

Layer 4 — activeModes check
  ↓ currentMode NOT in hook's activeModes[] → exit 0

Layer 5 — Hook-specific logic runs
```

### Per-hook activeModes (default config)

| Hook               | activeModes                  |
| ------------------ | ---------------------------- |
| `userPromptSubmit` | `["loop"]`                   |
| `postToolUse`      | `["loop"]`                   |
| `stop`             | `["loop"]`                   |
| `subagentAnnounce` | `["simple", "loop", "plan"]` |

**Implication:** by default, `userPromptSubmit`, `postToolUse`, and `stop` only fire when the ledger contains `Session-Type: loop`. In any other session type (chat, plan, manual-test) they silently skip. `subagentAnnounce` fires in more modes but still requires `solar.active: true`.

---

## Per-Hook Logic (after guards pass)

### `user-prompt-submit.cjs`

- Reads ledger for `Completion Promise: pending`
- If pending: emits `systemMessage` warning the agent a SOLAR task is active
- If not pending: emits `{ continue: true }` (no message, just unblocks)

### `post-tool-use.cjs`

- Reads `toolName` from stdin input
- Early exits if tool is NOT a write operation (regex: `edit|creat|appl|insert|delet|writ|replac`)
- If write op: runs `npx tsc --noEmit` (configured command)
- Emits error summary if TypeScript errors found, or generic "code modified" reminder
- Always emits `{ continue: true }`

### `stop.cjs`

- Reads ledger for `Completion Promise: pending`
- If pending AND mode enforces completion (`modeConfig.enforceCompletion === true`): emits `systemMessage` blocking the stop with continuation reminder
- If NOT pending: emits `{ continue: false }` (allows stop)

### `subagent-announce.cjs`

- Reads `agent_type` from stdin JSON (provided by VS Code on `SubagentStart`)
- Maps agent name → model string via `MODEL_MAP`
- Emits `systemMessage: "Subagent: <Name>  |  model: <model>"` as a toast notification

---

## Why Hooks Don't Fire (Common Causes)

**Most frequent cause: `solar.active: false`**
All hooks check `config.solar.active` first. The template default is `false`. If never set to `true`, zero hooks fire.

**Second most frequent: session type not in activeModes**
For `userPromptSubmit`, `postToolUse`, `stop` — they only fire in `"loop"` mode. The ledger must contain `Session-Type: loop` for the mode to resolve to `"loop"`. A normal chat session resolves to `"simple"`, which is not in `activeModes` for those three hooks.

**For `subagentAnnounce` specifically:**

- Requires `chat.useCustomAgentHooks: true` in VS Code settings
- Only fires when a subagent is actually spawned (governor must call the `agent` tool)
- No subagent spawn = no `SubagentStart` event = no hook fire

---

## Stripped State (Temporary — Debugging)

All four hooks have had their guard chains removed. In stripped state:

- No config file needed
- No `solar.active` check
- No mode check
- No bootstrap bypass
- No `activeModes` filter
- Hooks fire on **every** event they are registered for, unconditionally

**Stripped hook behavior:**

| Hook                     | Stripped behavior                                                               |
| ------------------------ | ------------------------------------------------------------------------------- |
| `user-prompt-submit.cjs` | Always emits pending-task reminder if ledger has pending, else `continue: true` |
| `post-tool-use.cjs`      | Runs TSC on every write tool call unconditionally                               |
| `stop.cjs`               | Blocks stop if ledger has pending, else allows stop                             |
| `subagent-announce.cjs`  | Always emits agent name + model toast                                           |

**To restore guards:** revert each hook file to its guarded version from git, or re-add the guard blocks following the pattern in this doc.

---

## VS Code Settings Required

```json
{
  "chat.useCustomAgentHooks": true
}
```

Without this setting, `SubagentStart` (and any scoped agent hooks) never fire regardless of hook file or config state.

# Bootstrap Mode Guide

## What Is Bootstrap Mode?

Bootstrap mode is a special operating state that **completely disables SOLAR-Ralph governance** to allow setup utilities to run without interference from the rules they are establishing.

**Problem it solves:** When `AGENTS.md` and `.github/copilot-instructions.md` already exist in a repository, GitHub Copilot treats them as "Global Mandates" that override single-prompt instructions. This causes setup commands to trigger SOLAR pipelines, ledger updates, and delegation matrices — exactly the behaviors they're trying to configure.

**Solution:** Bootstrap mode creates a deterministic bypass where SOLAR governance is temporarily suspended, allowing setup commands to operate as simple file workers.

---

## When Bootstrap Mode Is Active

Bootstrap mode activates automatically in these scenarios:

### Automatic Activation

1. **`@solar-bootstrap` agent invoked** — The dedicated bootstrap agent auto-activates bootstrap mode before executing any setup work and auto-deactivates afterward.

2. **Session-Type is `bootstrap`** — If `.ai_ledger.md` contains `Session-Type: bootstrap`, all SOLAR hooks bypass enforcement.

3. **Config mode is `bootstrap`** — If `.github/solar.config.json` has `solar.mode: "bootstrap"`, all hooks exit immediately without any governance checks.

### Manual Activation (Emergency/Troubleshooting Only)

Run `/solar-enter-bootstrap` to manually switch to bootstrap mode. This is only needed if:

- Bootstrap agent auto-activation failed
- Setup was interrupted mid-execution
- You need to manually recover from a broken SOLAR configuration

**Always run `/solar-exit-bootstrap` after manual activation to restore normal operation.**

---

## What Gets Disabled During Bootstrap Mode

When bootstrap mode is active, the following SOLAR components are **completely inactive**:

| Component                          | Normal Behavior                                 | Bootstrap Behavior                   |
| ---------------------------------- | ----------------------------------------------- | ------------------------------------ |
| **AGENTS.md delegation matrix**    | Routes tasks through pipelines and specialists  | Ignored — no routing                 |
| **Governor orchestration**         | Decomposes work, delegates, tracks completion   | Not invoked                          |
| **Lifecycle hooks**                | Enforce loop continuation, type checks, prompts | Exit immediately without enforcement |
| **`.ai_ledger.md` updates**        | Tracks work state, blockers, verification       | File not modified                    |
| **`/memories/repo/` updates**      | Stores persistent facts                         | Folder not modified                  |
| **`manage_todo_list` tool**        | Plans multi-step work                           | Forbidden in bootstrap agent         |
| **Specialist skill invocations**   | Load domain-specific best practices             | Skipped                              |
| **Session-Type-based enforcement** | Loop mode requires completion promise           | No enforcement                       |

**What IS still active:**

- File reading and editing tools
- Search and grep tools
- Basic command execution (if needed for detection)
- Standard VS Code / MCP server behavior

---

## Bootstrap Agent vs Manual Commands

### Bootstrap Agent (Recommended Primary Path)

```
@solar-bootstrap /solar-setup-scan-repo
@solar-bootstrap /solar-setup-core-config
@solar-bootstrap /solar-setup-agent-config
```

**How it works:**

1. Agent checks command matches allowed pattern (`/solar-setup-*`)
2. Agent reads current config, stores `solar.enabled` and `solar.mode`
3. Agent writes `solar.mode: "bootstrap"` and `solar.enabled: false`
4. Agent outputs `🔧 BOOTSTRAP MODE ACTIVE`
5. Agent executes setup logic (scan/apply config)
6. Agent restores previous config values
7. Agent outputs `✅ Setup operation complete` and `🔒 Bootstrap mode deactivated`

**Advantages:**

- Automatic activation/deactivation (no manual mode toggling needed)
- Visual confirmation of bootstrap state
- Scope guard prevents misuse (only works with setup commands)
- Consistent error handling and completion protocol

### Manual Commands (Fallback / Troubleshooting)

```
/solar-enter-bootstrap
[run your setup operations manually]
/solar-exit-bootstrap
```

**When to use:**

- Bootstrap agent routing failed
- Need to manually edit SOLAR config files during setup
- Recovering from interrupted setup
- Debugging bootstrap mode behavior

**Important:** Manual mode requires YOU to remember to run `/solar-exit-bootstrap`. If you forget, SOLAR governance remains disabled until you manually restore it.

---

## Verification: How to Tell If Bootstrap Mode Is Active

### Method 1: Check Config File

```bash
cat .github/solar.config.json | grep mode
```

Look for: `"mode": "bootstrap"`

### Method 2: Check Agent Output

The `@solar-bootstrap` agent always outputs:

```
🔧 BOOTSTRAP MODE ACTIVE
```

at the start and:

```
🔒 Bootstrap mode deactivated
```

at the end.

### Method 3: Check Ledger Session-Type

```bash
grep "Session-Type" .ai_ledger.md
```

If it shows `Session-Type: bootstrap`, mode is active.

---

## Safety Boundaries & Scope Guards

### Bootstrap Agent Scope Restriction

The `@solar-bootstrap` agent will **refuse to execute** if the command does NOT match these patterns:

- `/solar-setup-scan-repo`
- `/solar-setup-core-config`
- `/solar-setup-agent-config`
- `/solar-enter-bootstrap`
- `/solar-exit-bootstrap`

**If you invoke it for any other task**, you will get:

```
⛔ This agent is ONLY for SOLAR setup utilities.
Use the default agent or @Orchestration-Governor for other tasks.
```

This prevents accidental misuse where someone invokes `@solar-bootstrap` to bypass governance for non-setup work.

### Emergency Exit Conditions

The bootstrap agent will stop immediately and output an error if:

1. **SOLAR already active** — `.ai_ledger.md` contains `SOLAR_ACTIVE: true`
   - You must deactivate SOLAR before running setup utilities

2. **Missing setup config** — `.github/solar-setup.md` does not exist
   - Run the installer script first

3. **Config parse error** — `.github/solar.config.json` is corrupted or missing
   - Restore from backup or reinstall SOLAR files

---

## Common Scenarios

### Scenario 1: First-Time SOLAR Installation

**Workflow:**

1. Run installer script → Downloads all SOLAR files including `solar-setup.md`
2. Run `@solar-bootstrap /solar-setup-scan-repo` → Auto-detects project values
3. Review `.github/solar-setup.md`, fix any `NEEDS MANUAL INPUT` fields
4. Run `@solar-bootstrap /solar-setup-core-config` → Applies values to copilot-instructions, hooks, guides
5. Run `@solar-bootstrap /solar-setup-agent-config` → Applies values to agents, skills, path instructions
6. Set `SOLAR_ACTIVE: true` in `.ai_ledger.md` → Activates governance

**Key point:** The `@solar-bootstrap` agent handles all mode toggling automatically. You never manually enter/exit bootstrap mode.

### Scenario 2: Interrupted Setup Recovery

**Problem:** Setup command failed halfway through, bootstrap mode might still be active.

**Recovery:**

1. Check config: `cat .github/solar.config.json | grep mode`
2. If it shows `"bootstrap"`, run `/solar-exit-bootstrap`
3. Re-run the failed setup command with `@solar-bootstrap`

### Scenario 3: Manual SOLAR Configuration Edit

**Problem:** You need to manually edit agent definitions or hook scripts after setup.

**Approach:**

- **Do NOT use bootstrap mode** — edit the files directly
- Bootstrap mode is only for the automated setup commands
- Manual file edits don't trigger governance, so no bypass is needed

### Scenario 4: Setup Command Runs But Still Triggers Governor

**Problem:** You ran `/solar-setup-scan-repo` but the agent still mentioned "creating a plan" or "updating the ledger."

**Root Cause:** You forgot to prefix the command with `@solar-bootstrap`.

**Fix:**

1. Run `/solar-exit-bootstrap` to clean up any partial state
2. Re-run the command correctly: `@solar-bootstrap /solar-setup-scan-repo`
3. Verify you see `🔧 BOOTSTRAP MODE ACTIVE` in the output

---

## Advanced: How Hook Bypass Works

Each of the three lifecycle hooks (`stop.cjs`, `post-tool-use.cjs`, `user-prompt-submit.cjs`) contains this bypass logic:

```javascript
// Determine current mode from Session-Type in ledger
const sessionTypeMatch = ledger.match(/Session-Type:\s*(\w+)/i);
const sessionType = sessionTypeMatch
  ? sessionTypeMatch[1].toLowerCase()
  : "chat";
const currentMode = config.sessionTypes?.[sessionType] || "simple";

// Bootstrap mode bypass - governance disabled during setup
if (currentMode === "bootstrap") {
  process.exit(0);
}
```

**What this does:**

1. Reads `Session-Type` from `.ai_ledger.md`
2. Maps it to a mode using `sessionTypes` in `solar.config.json`
3. If the mode is `"bootstrap"`, the hook **exits immediately** without any enforcement

This happens **before** any other checks (active modes, completion promises, type checks), ensuring bootstrap mode has the highest priority.

---

## Troubleshooting

### Problem: Agent ignores bootstrap mode and still follows AGENTS.md

**Diagnosis:**

- Check if you invoked with `@solar-bootstrap` (required)
- Verify `.github/solar.config.json` exists and is valid JSON
- Check `solar.mode` in config — should be `"bootstrap"` during setup

**Fix:**

- Use `@solar-bootstrap` prefix for all setup commands
- If config is corrupted, restore from installer or Git

---

### Problem: Bootstrap mode "stuck" — SOLAR won't activate after setup

**Diagnosis:**

- Check `solar.mode` in `.github/solar.config.json`
- Should be `"simple"`, NOT `"bootstrap"`

**Fix:**

- Run `/solar-exit-bootstrap` to restore normal mode
- Or manually edit config: set `"mode": "simple"`

---

### Problem: Setup command shows "BOOTSTRAP MODE ACTIVE" but still updates ledger

**Diagnosis:**

- Incorrect agent invoked, or agent definition doesn't have forbidden tools

**Fix:**

- Verify you used `@solar-bootstrap`, not default agent
- Check `.github/agents/solar-bootstrap.agent.md` has `manage_memory` in FORBIDDEN_TOOLS list
- Reinstall SOLAR files if agent definition is missing or corrupted

---

## Related Files

- `.github/agents/solar-bootstrap.agent.md` — Bootstrap agent definition
- `.github/solar.config.json` — Mode configuration and hook activation rules
- `.github/hooks/stop.cjs` — Stop hook with bootstrap bypass
- `.github/hooks/post-tool-use.cjs` — Post-tool-use hook with bootstrap bypass
- `.github/hooks/user-prompt-submit.cjs` — User prompt hook with bootstrap bypass
- `.github/commands/solar-enter-bootstrap.prompt.md` — Manual mode activation
- `.github/commands/solar-exit-bootstrap.prompt.md` — Manual mode deactivation

---

## Best Practices

1. **Always use `@solar-bootstrap` for setup commands** — Don't rely on manual mode toggling unless necessary

2. **Run setup commands in sequence** — scan-repo → core-config → agent-config

3. **Review auto-detected values** — After scan-repo, check `solar-setup.md` for `NEEDS MANUAL INPUT` or `INFERRED:` markers

4. **Don't use bootstrap mode for feature development** — It disables all safety checks and governance

5. **Only one mode at a time** — Don't manually enter bootstrap mode while the bootstrap agent is running

6. **Clean exit on errors** — If a setup command fails, run `/solar-exit-bootstrap` before retrying

---

**When in doubt:** Use `@solar-bootstrap` for all `/solar-setup-*` commands and let the agent handle mode management automatically.

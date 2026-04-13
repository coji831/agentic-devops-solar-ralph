# SOLAR Hook System Reference

## Hook Overview

| Hook                   | Trigger           | Purpose                           | Gates                        | Key Behavior                                                       | Logs |
| ---------------------- | ----------------- | --------------------------------- | ---------------------------- | ------------------------------------------------------------------ | ---- |
| **session-start**      | Session init      | Session log + LEARNINGS inject    | Global¹                      | Creates session-\*.json, reads LEARNINGS.md                        | 7    |
| **user-prompt-submit** | User prompt       | Loop task reminder + ERRORS nudge | Global¹ + Bootstrap² + Mode³ | Checks pending tasks, suggests error review                        | 7    |
| **pre-tool-use**       | Before tool call  | Delegation gates + watch mode     | Global¹ + Bootstrap² + Mode³ | Gates: Inquiry⁴, Stage 1⁵, Watch⁶, Bypass⁷                         | 8    |
| **post-tool-use**      | After tool call   | Session events + TS errors        | Global¹ + Bootstrap² + Mode³ | Dual logging⁸, tsc check, last-terminal tracking¹⁰, cycle reminder | 11   |
| **subagent-start**     | Before subagent   | Handoff payload inject            | Global¹ + Typed⁹             | Extracts ledger handoff section                                    | 5    |
| **subagent-stop**      | After subagent    | Validate handoff response         | Global¹ + Typed⁹             | Requires: completedBy, status, workPackage                         | 9    |
| **pre-compact**        | Before compaction | State snapshot                    | Global¹                      | Saves session state to pre-compact-state.md                        | 3    |
| **stop**               | Session end       | Block if incomplete               | Global¹ + Bootstrap² + Mode³ | Blocks: pending tasks, failed verification                         | 5    |

## Gate Definitions

**¹ Global Gates** (all hooks):

- `config.solar?.active` - SOLAR master switch (v4.1: merged `hooks.enabled` into `solar.active`)
- Hook-specific toggle (e.g., `config.hooks.preToolUse?.enabled`)

**² Bootstrap Bypass**: When `sessionType === "bootstrap"`, all governance rules skipped

**³ Mode Gates**: Only active in modes listed in `activeModes` array (typically `["loop"]`)

**⁴ Inquiry Gate**: Validates 3 checkboxes checked in ledger `## Inquiry Gate` section

**⁵ Stage 1 Gate**: Checks for `Stage 1: PASS` marker in ledger before allowing delegation

**⁶ Watch Mode**: Confirms high-risk tools (git, file ops) in loop mode before execution

**⁷ Bypass Agents**: Skip gates - design, architect, bug investigation, solar bootstrap, solar scan

**⁸ Dual Logging**: Appends to `session-*.json` (session events) + `posttooluse.log` (hook trace)

**⁹ Typed Payloads**: Requires `handoffInstructions.typedPayloads: true` in config

**¹⁰ Last-Terminal Tracking**: Parses `run_in_terminal` results, stores only the latest terminal ID, and warns when a new terminal opens while the previous tracked terminal is still marked open (until `kill_terminal` for that ID)

## Mode Activation

| Mode      | Active Hooks                                                       |
| --------- | ------------------------------------------------------------------ |
| `loop`    | user-prompt-submit, pre-tool-use (delegation), post-tool-use, stop |
| `simple`  | session-start, pre-compact, subagent-\*                            |
| All modes | pre-tool-use (watch mode only)                                     |

**Mode Resolution**: Extract `Session-Type` from ledger → map to config mode (default: "simple")

## Code Structure (v4.1)

All 8 production hooks follow a standardized 4-section pattern:

```javascript
// [imports]
const fs = require("fs");
const common = require("./common.cjs");

// [helper functions]
function hookSpecificHelper() {
  /* ... */
}

// [main function]
function main() {
  const config = common.loadConfig();
  // Core logic
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution("HookName", "EXIT (error - " + error.message + ")");
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}
```

**Common Utilities** (`common.cjs`):

- **Core**: `loadConfig()`, `readLedger()`, `getSessionType()`, `logHookExecution()`
- **Gates**: `isSolarActive()`, `isBootstrapMode()`
- **Paths**: `resolveSessionLogDir()`, `resolveLearningsDir()`, `resolveLearningsPath()`, `resolveErrorsPath()`, `resolveLedgerPath()`, `resolveDebugLogPath()`
- **Terminal tracking**: Stateless warning on every `run_in_terminal` invocation (no state persistence)

All 8 hooks import `common.cjs` and use centralized path resolution—no duplicate logic.

**Benefits**:

- **Uniform structure**: Easy to locate logic (always in helpers section) and error handling (always in try/catch)
- **Centralized utilities**: Update once in `common.cjs`, applies to all 8 hooks
- **Reduced duplication**: ~200 lines removed by extracting common functions
- **Predictable maintenance**: Same 4-section pattern across all hooks makes debugging consistent

## Logging

- **Function**: `common.logHookExecution(eventName, message)`
- **Directory**: `.github/solar-system/logs/`
- **Format**: `[ISO8601] [EventName] <message>`
- **Rotation**: Built-in daily retention in `common.cjs` (default 7 days, configurable via `logging.hookLog.daysToKeep`); users can still clean logs manually when needed
- **Total**: 55 log points across 8 hooks

## Known Issues (v4.1)

| Severity | File              | Line | Issue                                    |
| -------- | ----------------- | ---- | ---------------------------------------- |
| LOW      | session-start.cjs | 150  | Missing EXIT log on learnings file error |

**Fixed in v4.1**:

- ✅ pre-compact.cjs: Global gates added (no longer bypasses SOLAR disable)
- ✅ pre-tool-use.cjs: Now logs before inquiry gate block (line 132)

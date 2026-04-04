# SOLAR Hooks — Expected Behavior Specification

Documents the expected output for every hook under every significant input condition.
Use this as the verification spec when modifying hook scripts.

> **Related:** `docs/knowledge-base/hooks-firing-conditions.md` — covers the guard
> chain, activeModes, and common reasons hooks don't fire.
> This document covers what happens _after_ the guards pass.

---

## Summary Table

| Hook script              | VS Code event      | Active modes                      | Phase introduced | Script                                        |
| ------------------------ | ------------------ | --------------------------------- | ---------------- | --------------------------------------------- |
| `session-start.cjs`      | `SessionStart`     | always (config-gated)             | v4 Phase 1       | [↓](#sessionstart--session-startcjs)          |
| `user-prompt-submit.cjs` | `UserPromptSubmit` | `loop`                            | v3               | [↓](#userpromptsubmit--user-prompt-submitcjs) |
| `pre-tool-use.cjs`       | `PreToolUse`       | `loop` (agent calls + Watch Mode) | v3 / v4 Phase 2  | [↓](#pretooluse--pre-tool-usecjs)             |
| `post-tool-use.cjs`      | `PostToolUse`      | `loop`                            | v3               | [↓](#posttooluse--post-tool-usecjs)           |
| `stop.cjs`               | `Stop`             | `loop`                            | v3               | [↓](#stop--stopcjs)                           |
| `subagent-start.cjs`     | `SubagentStart`    | always (config-gated)             | v4 Phase 3       | [↓](#subagentstart--subagent-startcjs)        |
| `subagent-stop.cjs`      | `SubagentStop`     | always (config-gated)             | v4 Phase 3       | [↓](#subagentstopcjs--subagent-stopcjs)       |

**Output shapes used below:**

- `PASS` — `{ "continue": true }` with no `systemMessage`
- `PASS+MSG` — `{ "continue": true, "systemMessage": "..." }`
- `BLOCK` — `{ "continue": false }` (Stop hook only)
- `ASK` — `{ "hookSpecificOutput": { "permissionDecision": "ask", ... } }` (Phase 2 — PreToolUse Watch Mode)
- `INJECT` — `{ "hookSpecificOutput": { "hookEventName": "...", "additionalContext": "..." } }` (SubagentStart)
- `ALLOW` — `{ "decision": "allow" }` (SubagentStop)
- `BLOCK-DECISION` — `{ "decision": "block", "reason": "..." }` (SubagentStop)
- `SILENT` — no output; `process.exit(0)` or early return

---

## SessionStart — `session-start.cjs`

**Fires on:** VS Code session open  
**Input:** none (no stdin)  
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `hooks.sessionStart.injectLearnings: false`  
**Config flag:** `selfImprovement.learningsPath` (optional; defaults to `.github/solar-system/.learnings/`)

### Scenarios

| #   | Condition                                                                 | Expected output                                                                     |
| --- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| P1  | Kill switches pass · LEARNINGS.md has `###` entries                       | `PASS+MSG` — `hookSpecificOutput.additionalContext: "SOLAR Learnings Summary: ..."` |
| P2  | Kill switches pass · LEARNINGS.md exists but has no `###` entries (empty) | `PASS` — no injection; `{ continue: true }`                                         |
| S1  | `solar.active: false`                                                     | `SILENT`                                                                            |
| S2  | `hooks.sessionStart.injectLearnings: false`                               | `SILENT`                                                                            |
| S3  | LEARNINGS.md file missing or unreadable                                   | `PASS` — graceful skip; `{ continue: true }`                                        |

### Notes

- Injects up to 20 non-header, non-comment lines from LEARNINGS.md as a condensed summary.
- An empty LEARNINGS.md (as shipped in Phase 1) produces P2 — no context noise on first use.
- `hookSpecificOutput.hookEventName` must be `"SessionStart"` for VS Code to route the output correctly.

---

## UserPromptSubmit — `user-prompt-submit.cjs`

**Fires on:** every user message sent to the agent  
**Input:** none (no stdin)  
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `hooks.userPromptSubmit.enabled: false` · mode not in `activeModes` · bootstrap mode  
**Active by default:** `loop` mode only

### Scenarios

| #   | Condition                                                                         | Expected output                                           |
| --- | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| P1  | Loop mode · `Completion Promise: pending` in ledger · ERRORS.md has `###` entries | `PASS+MSG` — delegation reminder + ERRORS.md review nudge |
| P2  | Loop mode · `Completion Promise: pending` · ERRORS.md empty or missing            | `PASS+MSG` — delegation reminder only (no nudge)          |
| P3  | Loop mode · no `Completion Promise: pending`                                      | `PASS` — `{ continue: true }` only                        |
| S1  | `solar.active: false`                                                             | `SILENT`                                                  |
| S2  | `Session-Type: chat` (resolves to `simple`, not in activeModes)                   | `SILENT`                                                  |
| S3  | Bootstrap mode                                                                    | `SILENT`                                                  |
| S4  | `hooks.userPromptSubmit.enabled: false`                                           | `SILENT`                                                  |

### Notes

- ERRORS.md nudge is appended to the delegation message — it does NOT replace it.
- Nudge only fires when `hooks.postToolUse.logErrorsToLearnings: true` in config (reuses the same flag as `post-tool-use.cjs`).
- If ERRORS.md is unreadable, the catch silently suppresses the nudge; base delegation message still emits (P2 behaviour).

---

## PreToolUse — `pre-tool-use.cjs`

**Fires on:** every tool call before execution  
**Input:** stdin JSON with `toolName` / `tool` / `name` field  
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `hooks.preToolUse.enabled: false` · bootstrap mode  
**Active by default:** fires on `agent` tool calls (delegation gate) and on any tool call matching `watchModeToolPatterns` in loop mode (Watch Mode gate)

### Scenarios

| #   | Condition                                                                                          | Expected output                                           |
| --- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| W1  | Loop mode · `watchModeEnabled: true` · tool name matches `watchModeToolPatterns`                   | `ASK` — `permissionDecision: "ask"` (evaluated before P1) |
| W2  | Loop mode · tool name does NOT match patterns                                                      | `PASS` — Watch Mode not triggered; falls through to P1–P4 |
| W3  | Non-loop mode · tool matches patterns                                                              | `PASS` — Watch Mode scope is loop-only (OD-6 Option B)    |
| W4  | `watchModeEnabled: false` or `solar.active: false`                                                 | `PASS` — Watch Mode disabled; falls through to P1–P4      |
| P1  | Tool is not `agent` (and Watch Mode did not fire)                                                  | `PASS` — early return, no delegation gate                 |
| P2  | Tool is `agent` · target is a bypass agent (design, architect, bug investigation, solar bootstrap) | `PASS` — bypass list match                                |
| P3  | Tool is `agent` · not bypass · loop mode · Stage 1 complete in ledger                              | `PASS` — delegation allowed                               |
| P4  | Tool is `agent` · not bypass · loop mode · Stage 1 NOT complete                                    | `BLOCK` — "Complete Stage 1 before delegating"            |
| S1  | Bootstrap mode                                                                                     | `SILENT`                                                  |
| S2  | `solar.active: false`                                                                              | `SILENT` (fail open)                                      |

### Notes

- **Evaluation order:** Watch Mode (W1–W4) runs first using the shared config/ledger reads. If Watch Mode fires (`ASK`), the delegation gate (P1–P4) is not reached.
- Bypass list patterns (v3): `design`, `architect`, `bug investigation`, `solar bootstrap`, `solar scan` — matched case-insensitively against agent name.
- Config/ledger are read once at the top of the handler and shared by both gates; no duplicate I/O.
- `SILENT` here uses `process.exit(0)` (fail-open), not `{ continue: true }` — pre-tool-use fail-open means the tool call proceeds unblocked.

---

## PostToolUse — `post-tool-use.cjs`

**Fires on:** every tool call after execution  
**Input:** stdin JSON with `toolName` · `error` · `isError` fields  
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `hooks.postToolUse.enabled: false` · mode not in `activeModes` · bootstrap mode  
**Active by default:** `loop` mode only  
**Write-op guard:** non-write tool names (not matching `edit|creat|appl|insert|delet|writ|replac`) short-circuit to `PASS` before any config read

### Scenarios

| #   | Condition                                                                                                   | Expected output                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| P1  | Tool is a read op (e.g., `read_file`, `grep_search`)                                                        | `PASS` — write-op guard short-circuits                                                        |
| P2  | Write op · loop mode · no failure · `typeCheckOnWrite: false`                                               | `PASS`                                                                                        |
| P3  | Write op · loop mode · no failure · `typeCheckOnWrite: true` · tsc passes                                   | `PASS+MSG` — "Code modified in loop. Update .ai_ledger.md..."                                 |
| P4  | Write op · loop mode · no failure · `typeCheckOnWrite: true` · tsc finds errors                             | `PASS+MSG` — "TypeScript errors: TS2345 ... Fix before claiming progress..." (up to 3 errors) |
| P5  | Write op · loop mode · tool failed (`input.error` truthy or `isError: true`) · `logErrorsToLearnings: true` | `PASS+MSG` — "Tool failure detected. Record error in ERRORS.md before continuing."            |
| P6  | Write op · loop mode · tool failed · `logErrorsToLearnings: false`                                          | falls through to P2/P3/P4 — failure not surfaced                                              |
| S1  | Config missing or unreadable                                                                                | `PASS` — `loadConfig()` returns null; kill switch emits `{ continue: true }`                  |
| S2  | `solar.active: false`                                                                                       | `PASS` — kill switch                                                                          |
| S3  | `Session-Type: chat`                                                                                        | `PASS` — not in activeModes                                                                   |
| S4  | Bootstrap mode                                                                                              | `PASS`                                                                                        |

### Notes

- P5 takes priority over P3/P4: if the tool failed, the ERRORS.md instruction is emitted and the function returns — tsc does NOT run.
- P1 short-circuits before config is loaded (no file I/O cost on read ops).
- `isError` is a secondary failure signal; `input.error` truthy is the primary. If VS Code sets `isError: true` on a partial success in future, spurious entries could appear in ERRORS.md. Monitor and adjust if observed.
- tsc `catch` in `buildTscMessage` treats non-zero exit (errors found) and process-level throws the same — both extract TS error lines from `e.stdout`. A completely missing `tsc` binary produces an empty error list (P3 output, not P4).

---

## Stop — `stop.cjs`

**Fires on:** agent response ends (before VS Code stops the turn)  
**Input:** none (no stdin)  
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `hooks.stop.enabled: false` · mode not in `activeModes` · bootstrap mode  
**Active by default:** `loop` mode only

### Scenarios

| #   | Condition                                                             | Expected output                                                             |
| --- | --------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| B1  | Loop mode · `Completion Promise: pending` · `enforceCompletion: true` | `PASS+MSG` — continuation reminder with valid promise options               |
| B2  | Loop mode · `Verification: FAIL` · `enforceCompletion: true`          | `PASS+MSG` — "Verification shows FAIL — run `npm test` and fix failures..." |
| P1  | Loop mode · no pending promise · no verification failure              | `BLOCK` — `{ continue: false }` allows stop                                 |
| P2  | Loop mode · `enforceCompletion: false` (mode config)                  | `BLOCK` — enforcement disabled, stop allowed                                |
| S1  | `solar.active: false`                                                 | `SILENT`                                                                    |
| S2  | `Session-Type: chat`                                                  | `SILENT`                                                                    |
| S3  | Bootstrap mode                                                        | `SILENT`                                                                    |

### Notes

- `{ continue: false }` is the _allow_ signal for `Stop` — it means "do not block the stop." This is the inverse of `PostToolUse`/`UserPromptSubmit` where `continue: true` means allow.
- `{ continue: true, systemMessage: "..." }` on `Stop` means "block the stop and show this message." Counter-intuitive naming — correct per VS Code hook spec.
- `SILENT` exits via `process.exit(0)` in this hook (not `{ continue: false }`) — exits before any output. VS Code treats no output from the Stop hook as allow-stop.
- Valid completion promise values surfaced in B1 message: `WORK_PACKAGE_COMPLETE`, `WORK_PACKAGE_BLOCKED`, `ESCALATION_REQUIRED`.

---

## SubagentStart — `subagent-start.cjs`

**Fires on:** subagent delegation starts (before subagent receives first context)
**Input:** none (no stdin)
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `handoffs.typedPayloadsEnabled: false`
**Config flags:** `handoffs.schemasPath` (informational reference in output only)

### Scenarios

| #   | Condition                                                                         | Expected output                                                                                                   |
| --- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| P1  | Kill switches pass · ledger has non-empty `## Handoff Payload` section            | `INJECT` — `additionalContext: "HANDOFF PAYLOAD FROM GOVERNOR (read this before starting):\n\n<payload text>..."` |
| P2  | Kill switches pass · ledger `## Handoff Payload` section is `(none)` or `(empty)` | `INJECT` — `additionalContext: "No handoff payload in ledger. Proceed with request context only."`                |
| P3  | Kill switches pass · ledger file missing or unreadable                            | `INJECT` — same as P2; graceful fallback                                                                          |
| S1  | `solar.active: false`                                                             | `SILENT`                                                                                                          |
| S2  | `hooks.enabled: false`                                                            | `SILENT`                                                                                                          |
| S3  | `handoffs.typedPayloadsEnabled: false`                                            | `PASS` — `{ continue: true }` (typed injection disabled, not silent)                                              |

### Notes

- Output shape is `INJECT` (`hookSpecificOutput` with `hookEventName: "SubagentStart"`) — same structure as `SessionStart`.
- P2 and P3 still produce `INJECT` output (not `PASS`) to signal to the subagent that context injection ran and found nothing — avoids ambiguity between "hook did not fire" and "no payload was set".
- The payload text is extracted by matching `## Handoff Payload` through the next `##` heading or end of file. Values `(none)` and `(empty)` are treated as absent.
- Schema reference appended to P1 output: `"Reference schemas in .github/solar-system/schemas/ for the typed format."`

---

## SubagentStop — `subagent-stop.cjs`

**Fires on:** subagent response ends (before the subagent turn closes)
**Input:** stdin JSON with `response` or `output` field (subagent response text); optional `stop_hook_active: boolean`
**Kill switches:** `solar.active: false` · `hooks.enabled: false` · `handoffs.typedPayloadsEnabled: false`

### Scenarios

| #   | Condition                                                                                         | Expected output                                                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| V1  | Kill switches pass · response contains all 3 required fields                                      | `ALLOW` — `{ "decision": "allow" }`                                                                                                                |
| V2  | Kill switches pass · response missing 1+ required fields (`completedBy`, `status`, `workPackage`) | `BLOCK-DECISION` — `{ "decision": "block", "reason": "missing: <fields>. Produce handoff summary conforming to implementer-handoff.schema.json" }` |
| G1  | `stop_hook_active: true` in stdin input                                                           | `ALLOW` — infinite loop guard; unconditional allow regardless of response content                                                                  |
| G2  | No stdin piped (TTY mode) or stdin unparseable                                                    | `ALLOW` — graceful fallback; no response to validate                                                                                               |
| G3  | Response text field absent from hook input (`response` and `output` both missing)                 | `ALLOW` — no text to validate                                                                                                                      |
| S1  | `solar.active: false`                                                                             | `SILENT`                                                                                                                                           |
| S2  | `hooks.enabled: false`                                                                            | `SILENT`                                                                                                                                           |
| S3  | `handoffs.typedPayloadsEnabled: false`                                                            | `ALLOW` — `{ "decision": "allow" }` (not silent; typed validation disabled)                                                                        |
| S4  | Config missing or unparseable                                                                     | `SILENT` — fail open; subagent allowed to stop                                                                                                     |

### Notes

- Output shape uses top-level `decision` field (`"allow"` / `"block"`), NOT `hookSpecificOutput` — this is the `SubagentStop`-specific format per VS Code hook spec.
- Field matching is regex-based against response text (case-insensitive): `/completed[- _]?by/i`, `/status\s*:/i`, `/work[- _]?package/i`. Not JSON schema parsing.
- `stop_hook_active` guard (G1) is **critical** — without it, a `BLOCK-DECISION` response would re-trigger the hook, causing an infinite block loop. Always check this field first.
- V2 block message references `implementer-handoff.schema.json` specifically — the minimum contract for any subagent returning to the governor.
- `SILENT` in this hook means `process.exit(0)` before any output, which VS Code treats as allow-stop (fail-open). Same semantics as `Stop` hook silent behavior.

---

## Regression Test Commands

Run these from the workspace root against a known ledger/config state:

```powershell
# SessionStart — empty learnings (expect: { continue: true })
node .github/hooks/session-start.cjs

# UserPromptSubmit — loop mode with pending task (requires ledger with Session-Type: loop + Completion Promise: pending)
node .github/hooks/user-prompt-submit.cjs

# PostToolUse — read op (expect: { continue: true })
echo '{"toolName":"read_file"}' | node .github/hooks/post-tool-use.cjs

# PostToolUse — write op, no failure, tsc disabled (expect: { continue: true })
echo '{"toolName":"replace_string_in_file"}' | node .github/hooks/post-tool-use.cjs

# PostToolUse — write op, tool failure (expect: ERRORS.md systemMessage)
echo '{"toolName":"replace_string_in_file","error":"file not found"}' | node .github/hooks/post-tool-use.cjs

# Stop — no pending task (expect: { continue: false })
node .github/hooks/stop.cjs

# SubagentStart — no ledger payload (expect: additionalContext with "No handoff payload" message)
node .github/hooks/subagent-start.cjs

# SubagentStop — valid response (expect: { decision: "allow" })
echo '{"response":"workPackage: WP-1\nstatus: completed\ncompletedBy: Backend Implementation Specialist"}' | node .github/hooks/subagent-stop.cjs

# SubagentStop — missing fields (expect: { decision: "block", reason: "..." })
echo '{"response":"Here are the changes I made."}' | node .github/hooks/subagent-stop.cjs

# SubagentStop — stop_hook_active guard (expect: { decision: "allow" }, no blocking loop)
echo '{"response":"incomplete","stop_hook_active":true}' | node .github/hooks/subagent-stop.cjs
```

> **Prerequisite:** `solar.active` must be `true` in `solar.config.json` for guarded hooks to fire.
> For isolated testing, temporarily set `solar.active: true` or use the stripped hook variants.

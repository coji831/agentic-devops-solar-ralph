# Hook System Test Guide

**Purpose**: Validate hook system fires correctly before implementing v4.1 features  
**Created**: 2026-04-13  
**Status**: Ready for testing

---

## What Was Created

### 1. Test Hook File

**Location**: `.github/hooks/test-hook.cjs`

**Capabilities**:

- Logs all hook events to `.github/solar-system/logs/hook-tests/`
- Creates event-specific log files and a master log
- Performs unique test actions for each event type
- Tracks session state, tool executions, subagents

### 2. Hook Registration

**Location**: `.github/hooks/hooks.json`

**Changes**: Added test hook as FIRST entry for all 8 events:

- `SessionStart` - Creates session marker file
- `UserPromptSubmit` - Counts user prompts
- `PreToolUse` - Logs tool interceptions
- `PostToolUse` - Counts tool executions
- `PreCompact` - Logs compaction events (may not fire - platform limitation)
- `SubagentStart` - Tracks active subagents
- `SubagentStop` - Removes from active subagents list
- `Stop` - Cleans up session, creates summary

---

## How to Test

### Step 1: Reload VS Code Window

**Required**: VS Code only reads `hooks.json` at startup

```
Ctrl+Shift+P → "Developer: Reload Window"
```

**OR** Close and reopen VS Code

### Step 2: Start a New Copilot Session

**Triggers**: `SessionStart` hook

**Expected**:

- Console log: `[TEST-HOOK] SessionStart fired at ...`
- File created: `.github/solar-system/logs/hook-tests/session-active.marker`
- Log created: `.github/solar-system/logs/hook-tests/sessionstart.log`

### Step 3: Submit a User Prompt

**Example**: Type "hello" in Copilot chat

**Triggers**: `UserPromptSubmit` hook

**Expected**:

- Console log: `[TEST-HOOK] UserPromptSubmit fired at ...`
- File updated: `.github/solar-system/logs/hook-tests/prompt-counter.txt` (increments)
- Log updated: `.github/solar-system/logs/hook-tests/userpromptsubmit.log`

### Step 4: Trigger a Tool Call

**Example**: Ask Copilot "list files in .github/hooks"

**Triggers**: `PreToolUse` → `PostToolUse` hooks

**Expected**:

- Console logs for both hooks
- Files created/updated:
  - `.github/solar-system/logs/hook-tests/tool-intercepts.log`
  - `.github/solar-system/logs/hook-tests/tool-execution-counter.txt`
- Logs updated: `pretooluse.log` and `posttooluse.log`

### Step 5: Invoke a Subagent (Optional)

**Example**: Ask to run Explore subagent

**Triggers**: `SubagentStart` → `SubagentStop` hooks

**Expected**:

- Console logs for both hooks
- File updated: `.github/solar-system/logs/hook-tests/active-subagents.json`
- Logs updated: `subagentstart.log` and `subagentstop.log`

### Step 6: End Session

**Example**: Close chat or run `/stop`

**Triggers**: `Stop` hook

**Expected**:

- Console log: `[TEST-HOOK] Stop fired at ...`
- Session marker deleted: `session-active.marker`
- Summary created: `session-summary-[timestamp].txt`
- Log updated: `stop.log`

---

## Verification Checklist

After completing Steps 1-6, check:

✅ **Directory exists**: `.github/solar-system/logs/hook-tests/`  
✅ **Master log exists**: `master-[timestamp].log` (contains all events)  
✅ **Event logs exist** (at least):

- `sessionstart.log`
- `userpromptsubmit.log`
- `pretooluse.log`
- `posttooluse.log`
- `stop.log`

✅ **Test files created**:

- `prompt-counter.txt` (shows count > 0)
- `tool-execution-counter.txt` (shows count > 0)
- `tool-intercepts.log` (has entries)
- `session-summary-[timestamp].txt` (created at end)

✅ **Console output visible** (check VS Code Output panel → GitHub Copilot Chat)

---

## Expected Test Results

### ✅ SUCCESS Criteria

**All hooks fire correctly**:

- Each hook creates log entry in its event-specific log
- Master log contains all events in chronological order
- Test actions complete (files created, counters incremented)
- No errors in `errors.log` (if file doesn't exist = good!)

**Timing**:

- Hooks complete within timeout (5s for test, 10-20s for original)
- No noticeable delay in Copilot responses

### ❌ FAILURE Indicators

**Hook not firing**:

- Event log file missing
- No console output for that event
- Test files not created

**Possible causes**:

- VS Code window not reloaded after hooks.json change
- File permission issues (check errors.log)
- Hook script syntax error (node will report)

**PreCompact special case**:

- PreCompact hook MAY NOT FIRE (VS Code platform limitation noted in v4.1 plan)
- Missing `precompact.log` is NOT a failure
- If it fires, consider it a bonus!

---

## Troubleshooting

### No logs created at all

1. Check VS Code Output panel → GitHub Copilot Chat for hook errors
2. Manually test hook: `node .github/hooks/test-hook.cjs`
3. Check file permissions on `.github/solar-system/logs/`

### Specific event not logging

1. Verify hook registered in `hooks.json` for that event
2. Check event name matches exactly (case-sensitive)
3. Look in `errors.log` for that event's errors

### Timeout errors

1. Increase timeout in `hooks.json` (currently 5s for test hook)
2. Check for blocking operations in test hook script

---

## Next Steps After Testing

### If ALL tests pass ✅

**Proceed with v4.1 implementation**:

1. Hook system confirmed working
2. File writes successful
3. Event detection accurate
4. Ready to implement P0 fixes (inquiry gate, learning capture, session logging)

### If ANY tests fail ❌

**Debug before implementing v4.1**:

1. Review `errors.log` for specific failures
2. Fix file permission issues
3. Verify hook registration syntax
4. Test hooks individually: `GITHUB_COPILOT_HOOK_EVENT=SessionStart node .github/hooks/test-hook.cjs`

---

## Cleanup After Testing

When ready to remove test hooks:

1. **Remove test hook from hooks.json**: Delete all test-hook.cjs entries
2. **Delete test hook file**: `rm .github/hooks/test-hook.cjs`
3. **Archive test logs** (optional): Move `hook-tests/` to `verification-artifacts/`
4. **Reload VS Code window** to apply hook changes

**OR keep test hooks running** during v4.1 development for ongoing validation.

---

## Test Log Analysis

### Sample Master Log Entry (JSON)

```json
{
  "timestamp": "2026-04-13T10:30:45.123Z",
  "event": "PostToolUse",
  "data": {
    "action": "Post-tool-use logging test",
    "canReadStdin": true
  },
  "process": {
    "pid": 12345,
    "cwd": "c:\\CodeProjects\\Personal\\agentic-devops-solar-ralph",
    "argv": ["node", ".github/hooks/test-hook.cjs"]
  }
}
```

### What to Look For

**Healthy logs show**:

- Sequential timestamps (events fire in order)
- Consistent process info (same PID for session events)
- Proper event names (exact case matches)
- Data fields populated (not empty objects)

**Problem indicators**:

- Missing events in sequence
- Timestamps out of order
- Empty data objects
- Error messages in data fields

---

**Test Duration**: ~5-10 minutes for full test cycle  
**Validation Goal**: Confirm hook system ready for v4.1 P0 implementation

// pre-compact.cjs
// SOLAR-Ralph PreCompact hook
// Fires before VS Code Copilot auto-compacts the context window.
// Reads active in-progress todos and current ledger pipeline stage,
// then writes a snapshot to /memories/session/pre-compact-state.md
// before truncation occurs.
//
// Output format: PreCompact uses COMMON output only.
// hookSpecificOutput is NOT used here -- VS Code ignores it on PreCompact events.
// Return { "continue": true } to allow compaction to proceed.

//
// Changelog:
// - v4.1: Added global gates (isSolarActive check)

"use strict";

// [imports]
const fs = require("fs");
const path = require("path");
const os = require("os");
const common = require("./common.cjs");

// [helper functions]
function safeRead(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (_) {
    return "";
  }
}

function extractField(text, label) {
  const regex = new RegExp("^" + label + ":\\s*(.+)$", "m");
  const match = text.match(regex);
  return match ? match[1].trim() : "(not found)";
}

function extractInProgressTodos(ledger) {
  const lines = ledger.split("\n");
  const inProgress = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Match todo-list entries that are in-progress or unchecked
    if (/in-progress/i.test(line) || /^\s*[-*]\s*\[ \]/.test(line)) {
      inProgress.push(line.trim());
    }
  }

  return inProgress.length > 0 ? inProgress.join("\n") : "(none found)";
}

// [main function]
function main() {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (!common.isSolarActive(config)) {
    return;
  }

  common.logHookExecution("PreCompact", "ENTRY");

  const workspaceRoot = process.env.VSCODE_WORKSPACE_ROOT || process.cwd();
  const ledgerPath = path.join(workspaceRoot, ".github", ".ai_ledger.md");
  const outputDir = path.join(os.homedir(), ".aitk", "memories", "session");
  const outputPath = path.join(outputDir, "pre-compact-state.md");

  // Read ledger
  const ledger = safeRead(ledgerPath);

  // Extract state
  const pipelineStage = extractField(ledger, "Pipeline Stage");
  const sessionType = extractField(ledger, "Session-Type");
  const pipeline = extractField(ledger, "Pipeline");
  const inProgress = extractInProgressTodos(ledger);

  // Format snapshot
  const now = new Date().toISOString().slice(0, 10);
  const snapshot = [
    "# Pre-Compact State Snapshot",
    "",
    "Date: " + now,
    "Trigger: auto-compaction",
    "",
    "## Ledger State",
    "Session-Type: " + sessionType,
    "Pipeline: " + pipeline,
    "Pipeline Stage: " + pipelineStage,
    "",
    "## In-Progress Todos",
    inProgress,
    "",
    "## Notes",
    "This file was written by pre-compact.cjs before VS Code truncated the context window.",
    "Read this file at loop restart to resume from the correct pipeline stage.",
  ].join("\n");

  // Write snapshot -- create directory if needed
  try {
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    fs.writeFileSync(outputPath, snapshot, "utf8");
  } catch (writeErr) {
    // Non-fatal: log to stderr but do not block compaction
    process.stderr.write(
      "[pre-compact.cjs] Failed to write snapshot: " + writeErr.message + "\n",
    );
  }

  // Return common output only -- allow compaction to proceed
  const output = {
    continue: true,
    systemMessage:
      "Pre-compact state saved to /memories/session/pre-compact-state.md (pipeline stage: " +
      pipelineStage +
      ")",
  };

  common.logHookExecution(
    "PreCompact",
    "EXIT (snapshot written - stage: " + pipelineStage + ")",
  );
  process.stdout.write(JSON.stringify(output));
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution("PreCompact", "EXIT (error - " + error.message + ")");
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

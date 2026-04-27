// test-hook.cjs
// SOLAR-Ralph v4.1 Pre-Implementation Test
// Purpose: Validate hook system fires correctly for all events before implementing actual features
// Tests: File writes, logging, event detection, parameter access

const fs = require("fs");
const path = require("path");

// --- Configuration ---
const TEST_LOG_DIR = path.resolve(
  __dirname,
  "../solar-system/logs/hook-tests/",
);
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, "-");

// --- Ensure test log directory exists ---
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// --- Core logging function ---
function logEvent(eventName, data) {
  ensureDir(TEST_LOG_DIR);

  const logEntry = {
    timestamp: new Date().toISOString(),
    event: eventName,
    data: data || {},
    process: {
      pid: process.pid,
      cwd: process.cwd(),
      argv: process.argv,
    },
  };

  // Write to event-specific log
  const eventLogPath = path.join(
    TEST_LOG_DIR,
    `${eventName.toLowerCase()}.log`,
  );
  const logLine = JSON.stringify(logEntry) + "\n";
  fs.appendFileSync(eventLogPath, logLine, "utf8");

  // Write to master test log
  const masterLogPath = path.join(TEST_LOG_DIR, `master-${TIMESTAMP}.log`);
  fs.appendFileSync(masterLogPath, logLine, "utf8");

  console.log(`[TEST-HOOK] ${eventName} fired at ${logEntry.timestamp}`);
}

// --- Event-Specific Actions ---

function testSessionStart() {
  logEvent("SessionStart", {
    action: "Session initialization test",
    env: {
      user: process.env.USER || process.env.USERNAME,
      home: process.env.HOME || process.env.USERPROFILE,
    },
  });

  // Test: Create a session marker file
  const markerPath = path.join(TEST_LOG_DIR, "session-active.marker");
  fs.writeFileSync(markerPath, new Date().toISOString(), "utf8");
}

function testUserPromptSubmit() {
  logEvent("UserPromptSubmit", {
    action: "User prompt interception test",
    stdin: process.stdin.isTTY ? "TTY" : "Pipe",
  });

  // Test: Count user prompts
  const counterPath = path.join(TEST_LOG_DIR, "prompt-counter.txt");
  let count = 0;
  if (fs.existsSync(counterPath)) {
    count = parseInt(fs.readFileSync(counterPath, "utf8") || "0", 10);
  }
  count++;
  fs.writeFileSync(counterPath, count.toString(), "utf8");
}

function testPreToolUse() {
  logEvent("PreToolUse", {
    action: "Pre-tool-use interception test",
    canReadStdin: !!process.stdin,
  });

  // Test: Log tool intercepts
  const interceptPath = path.join(TEST_LOG_DIR, "tool-intercepts.log");
  const interceptLog = `${new Date().toISOString()} - PreToolUse fired\n`;
  fs.appendFileSync(interceptPath, interceptLog, "utf8");
}

function testPostToolUse() {
  logEvent("PostToolUse", {
    action: "Post-tool-use logging test",
    canReadStdin: !!process.stdin,
  });

  // Test: Count tool executions
  const toolCountPath = path.join(TEST_LOG_DIR, "tool-execution-counter.txt");
  let count = 0;
  if (fs.existsSync(toolCountPath)) {
    count = parseInt(fs.readFileSync(toolCountPath, "utf8") || "0", 10);
  }
  count++;
  fs.writeFileSync(toolCountPath, count.toString(), "utf8");
}

function testPreCompact() {
  logEvent("PreCompact", {
    action: "Pre-compaction state preservation test",
    warning: "PreCompact hook may not fire (VS Code platform limitation)",
  });

  // Test: Create compaction warning file
  const compactPath = path.join(TEST_LOG_DIR, "compaction-events.log");
  const compactLog = `${new Date().toISOString()} - PreCompact fired (rare event!)\n`;
  fs.appendFileSync(compactPath, compactLog, "utf8");
}

function testSubagentStart() {
  logEvent("SubagentStart", {
    action: "Subagent initialization test",
    parentPid: process.ppid,
  });

  // Test: Track active subagents
  const subagentPath = path.join(TEST_LOG_DIR, "active-subagents.json");
  let subagents = [];
  if (fs.existsSync(subagentPath)) {
    try {
      subagents = JSON.parse(fs.readFileSync(subagentPath, "utf8"));
    } catch (e) {
      subagents = [];
    }
  }
  subagents.push({
    pid: process.pid,
    startTime: new Date().toISOString(),
  });
  fs.writeFileSync(subagentPath, JSON.stringify(subagents, null, 2), "utf8");
}

function testSubagentStop() {
  logEvent("SubagentStop", {
    action: "Subagent cleanup test",
    exitCode: process.exitCode || 0,
  });

  // Test: Remove from active subagents
  const subagentPath = path.join(TEST_LOG_DIR, "active-subagents.json");
  if (fs.existsSync(subagentPath)) {
    try {
      let subagents = JSON.parse(fs.readFileSync(subagentPath, "utf8"));
      subagents = subagents.filter((s) => s.pid !== process.pid);
      fs.writeFileSync(
        subagentPath,
        JSON.stringify(subagents, null, 2),
        "utf8",
      );
    } catch (e) {
      // Ignore parse errors
    }
  }
}

function testStop() {
  logEvent("Stop", {
    action: "Session cleanup test",
    uptime: process.uptime(),
  });

  // Test: Remove session marker
  const markerPath = path.join(TEST_LOG_DIR, "session-active.marker");
  if (fs.existsSync(markerPath)) {
    fs.unlinkSync(markerPath);
  }

  // Test: Create session summary
  const summaryPath = path.join(
    TEST_LOG_DIR,
    `session-summary-${TIMESTAMP}.txt`,
  );
  const summary = `Session ended at ${new Date().toISOString()}\nProcess uptime: ${process.uptime()}s\n`;
  fs.writeFileSync(summaryPath, summary, "utf8");
}

// --- Main Execution Logic ---

function main() {
  console.log("[TEST-HOOK] Hook fired - running all test actions");

  // Run all test actions
  testSessionStart();
  testUserPromptSubmit();
  testPreToolUse();
  testPostToolUse();
  testPreCompact();
  testSubagentStart();
  testSubagentStop();
  testStop();

  // Log analysis
  logEvent("HookSystemAnalysis", {
    action: "Hook system validated",
    finding: "VS Code hooks work but don't receive event context",
    note: "Each event needs dedicated hook file",
  });

  console.log("[TEST-HOOK] All test actions completed");
}

// --- Execute ---
try {
  //main();
  process.exit(0);
} catch (error) {
  const errorLogPath = path.join(TEST_LOG_DIR, "errors.log");
  ensureDir(TEST_LOG_DIR);
  const errorLog = `${new Date().toISOString()} - ERROR: ${error.message}\n${error.stack}\n\n`;
  fs.appendFileSync(errorLogPath, errorLog, "utf8");
  console.error(`[TEST-HOOK] ERROR:`, error);
  process.exit(1);
}

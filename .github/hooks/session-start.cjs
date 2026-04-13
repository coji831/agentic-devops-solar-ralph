// session-start.cjs
// SOLAR-Ralph v4 SessionStart hook
// Reads .learnings/LEARNINGS.md and injects a condensed summary into session context.
// Creates a per-session activity log JSON file in solar-system/logs/.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - v4.1 P0 Fix: Added debug logging for session log creation
// - Phase 5 S12: Added createSessionLog() for session-*.json activity log
// - Phase 1: Added LEARNINGS.md injection at session start

// [imports]
const fs = require("fs");
const path = require("path");
const common = require("./common.cjs");

// [helper functions]

function rotateOldLogs(logDir, maxFiles) {
  try {
    var existing = fs
      .readdirSync(logDir)
      .filter(function (f) {
        return f.match(/^session-.*\.json$/);
      })
      .map(function (f) {
        return path.join(logDir, f);
      })
      .sort();
    while (existing.length >= maxFiles) {
      fs.unlinkSync(existing.shift());
    }
  } catch (e) {}
}

function createSessionLog(cfg) {
  const debugLog = common.resolveDebugLogPath();
  try {
    var logDir = common.resolveSessionLogDir(cfg);

    try {
      const debugDir = path.dirname(debugLog);
      if (!fs.existsSync(debugDir)) {
        fs.mkdirSync(debugDir, { recursive: true });
      }
      fs.appendFileSync(
        debugLog,
        "[SessionStart] Log dir: " + logDir + "\n",
        "utf8",
      );
    } catch (e) {}

    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
      try {
        fs.appendFileSync(debugLog, "[SessionStart] Created log dir\n", "utf8");
      } catch (e) {}
    }
    rotateOldLogs(logDir, cfg.logging.sessionLog.maxFiles || 20);
    var ts = new Date().toISOString().replace(/[:.]/g, "-");
    var logFilePath = path.join(logDir, "session-" + ts + ".json");

    var sessionData = {
      session: new Date().toISOString(),
      events: [],
    };

    fs.writeFileSync(logFilePath, JSON.stringify(sessionData, null, 2), "utf8");
    fs.writeFileSync(
      path.join(logDir, ".current-session"),
      logFilePath,
      "utf8",
    );

    try {
      fs.appendFileSync(
        debugLog,
        "[SessionStart] Created session log: " + logFilePath + "\n",
        "utf8",
      );
    } catch (e) {}
  } catch (e) {
    try {
      fs.appendFileSync(
        debugLog,
        "[SessionStart] ERROR: " + e.message + "\n" + e.stack + "\n",
        "utf8",
      );
    } catch (logError) {}
  }
}

function extractLearningsSummary(learningsPath) {
  var content = fs.readFileSync(learningsPath, "utf8");
  var lines = content.split("\n").filter(function (l) {
    var t = l.trim();
    return (
      t && !t.startsWith("#") && !t.startsWith("<!--") && !t.startsWith("```")
    );
  });
  return lines.slice(0, 20).join(" ").trim();
}

// [main function]
function main() {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (!common.isSolarActive(config)) {
    return;
  }

  common.logHookExecution("SessionStart", "ENTRY");

  if (
    config.logging &&
    config.logging.sessionLog &&
    config.logging.sessionLog.enabled !== false
  ) {
    createSessionLog(config);
  }

  if (!config.hooks?.sessionStart?.injectLearnings) {
    common.logHookExecution(
      "SessionStart",
      "EXIT (learnings injection disabled)",
    );
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  var learningsSummary = "";
  try {
    learningsSummary = extractLearningsSummary(
      common.resolveLearningsPath(config),
    );
  } catch (e) {
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  if (!learningsSummary) {
    common.logHookExecution("SessionStart", "EXIT (no learnings content)");
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  common.logHookExecution(
    "SessionStart",
    "Injecting learnings summary (" + learningsSummary.length + " chars)",
  );
  common.logHookExecution("SessionStart", "EXIT (success)");
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: "SOLAR Learnings Summary: " + learningsSummary,
      },
    }),
  );
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution(
    "SessionStart",
    "EXIT (error - " + error.message + ")",
  );
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

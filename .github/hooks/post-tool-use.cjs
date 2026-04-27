// post-tool-use.cjs
// SOLAR-Ralph v4 PostToolUse hook
// Fires after every tool call.
// Logs session events, runs TypeScript checks on write operations, suggests ERRORS.md logging.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - v4.1 P0 Fix: Added debug logging for session log operations
// - Phase 5 S12: Added appendSessionEvent() for session-*.json activity log
// - Phase 1: Added ERRORS.md write instruction on tool failure

// [imports]
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const common = require("./common.cjs");

// [helper functions]
function isWriteOp(toolName) {
  return /edit|creat|appl|insert|delet|writ|replac/i.test(toolName);
}

// Stateless terminal warning - warns on every terminal open
function handleTerminalTracking(toolName) {
  if (toolName === "run_in_terminal") {
    return {
      shouldWarn: true,
      message:
        "⚠️ Terminal opened. Remember to close unused terminals to avoid confusion.",
    };
  }
  return { shouldWarn: false, message: "" };
}

function appendSessionEvent(input) {
  const debugLog = common.resolveDebugLogPath();
  try {
    const cfg = common.loadConfig();
    if (
      !cfg ||
      !cfg.logging ||
      !cfg.logging.sessionLog ||
      cfg.logging.sessionLog.enabled === false
    ) {
      try {
        fs.appendFileSync(
          debugLog,
          "[PostToolUse] Session logging disabled in config\n",
          "utf8",
        );
      } catch (e) {}
      return;
    }

    const logDir = common.resolveSessionLogDir(cfg);
    const currentSessionRef = path.join(logDir, ".current-session");

    if (!fs.existsSync(currentSessionRef)) {
      try {
        fs.appendFileSync(
          debugLog,
          "[PostToolUse] No .current-session marker\n",
          "utf8",
        );
      } catch (e) {}
      return;
    }

    const activeLogPath = fs.readFileSync(currentSessionRef, "utf8").trim();

    if (!activeLogPath || !fs.existsSync(activeLogPath)) {
      try {
        fs.appendFileSync(
          debugLog,
          "[PostToolUse] Session log missing: " + activeLogPath + "\n",
          "utf8",
        );
      } catch (e) {}
      return;
    }

    const toolName = (
      input.toolName ||
      input.tool ||
      input.name ||
      "unknown"
    ).toLowerCase();
    const toolFailed = !!(input.error || input.isError === true);
    const filePath = input.filePath || input.path || "";
    const event = {
      t: new Date().toISOString(),
      tool: toolName,
      ok: !toolFailed,
    };
    if (filePath) event.file = filePath;
    if (toolFailed && input.error)
      event.note = String(input.error).slice(0, 200);

    try {
      const logData = JSON.parse(fs.readFileSync(activeLogPath, "utf8"));
      logData.events.push(event);
      fs.writeFileSync(activeLogPath, JSON.stringify(logData, null, 2), "utf8");

      try {
        fs.appendFileSync(
          debugLog,
          "[PostToolUse] Appended event: " +
            toolName +
            " (" +
            (event.ok ? "OK" : "FAIL") +
            ")\n",
          "utf8",
        );
      } catch (e) {}
    } catch (e) {
      try {
        fs.appendFileSync(
          debugLog,
          "[PostToolUse] Append ERROR: " + e.message + "\n",
          "utf8",
        );
      } catch (logError) {}
    }
  } catch (e) {
    try {
      fs.appendFileSync(
        debugLog,
        "[PostToolUse] OUTER ERROR: " + e.message + "\n" + e.stack + "\n",
        "utf8",
      );
    } catch (logError) {
      /* Can't even log - exit silently */
    }
  }
}

function resolveSessionMode(config) {
  const ledger = common.readLedger();
  const match = ledger.match(/Session-Type:\s*(\w+)/i);
  const sessionType = match ? match[1].toLowerCase() : "chat";
  return config.sessionTypes?.[sessionType] || "simple";
}

function buildTscMessage(cfg, currentMode) {
  const modeConfig = cfg.modes?.[currentMode] || {};
  if (
    !modeConfig.typeCheckOnWrite ||
    !cfg.hooks.postToolUse.typeCheck?.enabled
  ) {
    return "";
  }
  try {
    const cmd = cfg.hooks.postToolUse.typeCheck.command || "npx tsc --noEmit";
    const timeout = cfg.hooks.postToolUse.typeCheck.timeout || 10000;
    execSync(cmd + " 2>&1", { timeout, encoding: "utf8" });
    return "";
  } catch (e) {
    const errors = ((e.stdout || "").match(/error TS\d+[^\n]*/g) || []).slice(
      0,
      3,
    );
    return errors.length
      ? "TypeScript errors: " +
          errors.join(" | ") +
          ". Fix before claiming progress in .ai_ledger.md."
      : "";
  }
}

// [main function]
function main(data) {
  try {
    const input = JSON.parse(data || "{}");
    const config = common.loadConfig();

    if (
      !config ||
      !common.isSolarActive(config) ||
      !config.hooks?.postToolUse?.enabled
    ) {
      return;
    }

    common.logHookExecution("PostToolUse", "ENTRY");

    appendSessionEvent(input);

    const toolName = (
      input.toolName ||
      input.tool ||
      input.name ||
      ""
    ).toLowerCase();

    const terminalCapture = handleTerminalTracking(toolName);

    if (!isWriteOp(toolName)) {
      if (terminalCapture?.shouldWarn && terminalCapture.message) {
        common.logHookExecution(
          "PostToolUse",
          "INJECT (terminal warning after new terminal open)",
        );
        console.log(
          JSON.stringify({
            continue: true,
            systemMessage: terminalCapture.message,
          }),
        );
        return;
      }

      common.logHookExecution(
        "PostToolUse",
        "PASS (read-only tool: " + toolName + ")",
      );
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const currentMode = resolveSessionMode(config);

    if (currentMode === "bootstrap") {
      common.logHookExecution("PostToolUse", "EXIT (bootstrap mode)");
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const activeModes = config.hooks.postToolUse.activeModes || [];
    if (!activeModes.includes(currentMode)) {
      common.logHookExecution(
        "PostToolUse",
        "EXIT (mode not active: " + currentMode + ")",
      );
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    if (config.hooks.postToolUse.logErrorsToLearnings) {
      const toolFailed = !!input.error || input.isError === true;
      if (toolFailed) {
        common.logHookExecution(
          "PostToolUse",
          "INJECT (tool failure - log to ERRORS.md)",
        );
        console.log(
          JSON.stringify({
            continue: true,
            systemMessage:
              "Tool failure detected. Record the error, tool name, and root cause in " +
              common.resolveErrorsPath(config) +
              " before continuing.",
          }),
        );
        return;
      }
    }

    const tscMessage = buildTscMessage(config, currentMode);

    if (tscMessage) {
      common.logHookExecution(
        "PostToolUse",
        "INJECT (TypeScript errors detected)",
      );
      console.log(
        JSON.stringify({ continue: true, systemMessage: tscMessage }),
      );
    } else if (config.modes?.[currentMode]?.typeCheckOnWrite) {
      common.logHookExecution("PostToolUse", "INJECT (ledger update reminder)");
      console.log(
        JSON.stringify({
          continue: true,
          systemMessage:
            "Code modified in loop. Update .ai_ledger.md with step outcome and run narrowest verification.",
        }),
      );
    } else {
      common.logHookExecution(
        "PostToolUse",
        "PASS (no type check or ledger reminder)",
      );
      console.log(JSON.stringify({ continue: true }));
    }
  } catch (e) {
    common.logHookExecution("PostToolUse", "EXIT (outer error - fail open)");
    console.log(JSON.stringify({ continue: true }));
  }
}

// [main invoke and top level try catch]
try {
  let data = "";
  process.stdin.on("data", (chunk) => (data += chunk));
  process.stdin.on("end", () => main(data));
} catch (error) {
  common.logHookExecution(
    "PostToolUse",
    "EXIT (error - " + error.message + ")",
  );
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

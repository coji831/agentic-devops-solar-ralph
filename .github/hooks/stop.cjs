// stop.cjs
// SOLAR-Ralph v4 Stop hook
// Fires when agent attempts to end conversation.
// Blocks exit if SOLAR loop has pending work or failed verification.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - Phase 5 S12: Added finalizeSessionLog() for session-*.json teardown

// [imports]
const fs = require("fs");
const path = require("path");
const common = require("./common.cjs");

// [helper functions]
function resolveSessionMode(cfg, ledger) {
  const match = ledger.match(/Session-Type:\s*(\w+)/i);
  const sessionType = match ? match[1].toLowerCase() : "chat";
  return cfg.sessionTypes?.[sessionType] || "simple";
}

function finalizeSessionLog(cfg) {
  try {
    if (
      !cfg.logging ||
      !cfg.logging.sessionLog ||
      cfg.logging.sessionLog.enabled === false
    )
      return;
    const logDir = common.resolveSessionLogDir(cfg);
    const currentSessionRef = path.join(logDir, ".current-session");
    if (!fs.existsSync(currentSessionRef)) return;
    const activeLogPath = fs.readFileSync(currentSessionRef, "utf8").trim();
    if (activeLogPath && fs.existsSync(activeLogPath)) {
      try {
        const logData = JSON.parse(fs.readFileSync(activeLogPath, "utf8"));
        logData.events.push({
          t: new Date().toISOString(),
          tool: "SESSION_END",
          ok: true,
        });
        fs.writeFileSync(
          activeLogPath,
          JSON.stringify(logData, null, 2),
          "utf8",
        );
      } catch (e) {}
    }
    try {
      fs.unlinkSync(currentSessionRef);
    } catch (e) {}
  } catch (e) {}
}

// [main function]
function main() {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (!common.isSolarActive(config) || !config.hooks?.stop?.enabled) {
    return;
  }

  common.logHookExecution("Stop", "ENTRY");

  const ledger = common.readLedger();
  const currentMode = resolveSessionMode(config, ledger);

  if (currentMode === "bootstrap") {
    process.exit(0);
  }

  const activeModes = config.hooks.stop.activeModes || [];
  if (!activeModes.includes(currentMode)) {
    process.exit(0);
  }

  const modeConfig = config.modes?.[currentMode] || {};
  const shouldEnforce =
    modeConfig.enforceCompletion && config.hooks.stop.enforceLoopContinuation;

  const isPending = /Completion Promise:\s*pending/i.test(ledger);
  const isVerificationFailed = /Verification:\s*FAIL/i.test(ledger);

  if (!shouldEnforce || (!isPending && !isVerificationFailed)) {
    finalizeSessionLog(config);
    common.logHookExecution("Stop", "ALLOW (no enforcement needed)");
    console.log(JSON.stringify({ continue: false }));
    process.exit(0);
  }

  const reason = isVerificationFailed
    ? "Verification shows FAIL — run `npm test` and fix failures before writing a completion promise."
    : "Continue working — do NOT write a completion promise just to exit.";

  const completionOptions =
    "<promise>WORK_PACKAGE_COMPLETE</promise> (all work verified done), " +
    "<promise>WORK_PACKAGE_BLOCKED</promise> (blocked, no new hypothesis, documented), " +
    "<promise>ESCALATION_REQUIRED</promise> (needs human decision).";

  finalizeSessionLog(config);

  common.logHookExecution(
    "Stop",
    "BLOCK (loop in progress - pending: " +
      isPending +
      ", verif failed: " +
      isVerificationFailed +
      ")",
  );
  console.log(
    JSON.stringify({
      continue: true,
      systemMessage: `SOLAR loop still in progress. ${reason} Only write it when genuinely true: ${completionOptions}`,
    }),
  );
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution("Stop", "EXIT (error - " + error.message + ")");
  console.log(JSON.stringify({ continue: false }));
  process.exit(0);
}

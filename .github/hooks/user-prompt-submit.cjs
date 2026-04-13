// user-prompt-submit.cjs
// SOLAR-Ralph v4 UserPromptSubmit hook
// Fires when user submits a prompt in chat.
// Checks for pending SOLAR tasks and injects reminder + ERRORS.md review nudge.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - Phase 1: Added getErrorsNudge() to suggest ERRORS.md review on retry

// [imports]
const fs = require("fs");
const common = require("./common.cjs");

// [helper functions]
function getErrorsNudge(cfg) {
  if (!cfg.hooks?.postToolUse?.logErrorsToLearnings) return "";

  try {
    const content = fs.readFileSync(common.resolveErrorsPath(cfg), "utf8");
    return /^###\s/m.test(content)
      ? " Review .github/solar-system/.learnings/ERRORS.md for previously logged failures before retrying."
      : "";
  } catch (e) {
    return "";
  }
}

// [main function]
function main() {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (
    !common.isSolarActive(config) ||
    !config.hooks?.userPromptSubmit?.enabled
  ) {
    return;
  }

  common.logHookExecution("UserPromptSubmit", "ENTRY");

  const ledger = common.readLedger();
  const sessionType = common.getSessionType(ledger);
  const currentMode = config.sessionTypes?.[sessionType] || "simple";

  if (common.isBootstrapMode(config, sessionType)) {
    common.logHookExecution("UserPromptSubmit", "EXIT (bootstrap mode)");
    process.exit(0);
  }

  const activeModes = config.hooks.userPromptSubmit.activeModes || [];
  if (!activeModes.includes(currentMode)) {
    common.logHookExecution(
      "UserPromptSubmit",
      "EXIT (mode not active: " + currentMode + ")",
    );
    process.exit(0);
  }

  const hasPendingTask = /Completion Promise:\s*pending/i.test(ledger);

  if (hasPendingTask) {
    common.logHookExecution(
      "UserPromptSubmit",
      "INJECT (pending task reminder)",
    );
    console.log(
      JSON.stringify({
        continue: true,
        systemMessage:
          "SOLAR task active. Follow the Mandatory Delegation Matrix in AGENTS.md. " +
          "Check .ai_ledger.md for current objective before acting. Do not skip required agents." +
          getErrorsNudge(config),
      }),
    );
  } else {
    common.logHookExecution("UserPromptSubmit", "PASS (no pending task)");
    console.log(JSON.stringify({ continue: true }));
  }
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution(
    "UserPromptSubmit",
    "EXIT (error - " + error.message + ")",
  );
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

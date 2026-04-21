// [imports]
const common = require("./common.cjs");

// [helper functions]
function isWatchModeTriggered(config, sessionType, toolName) {
  if (!common.isSolarActive(config)) return false;
  if (config.hooks?.preToolUse?.watchModeEnabled !== true) return false;
  if (sessionType !== "loop") return false;
  const patterns = config.hooks.preToolUse.watchModeToolPatterns;
  if (!Array.isArray(patterns) || patterns.length === 0) return false;
  return patterns.some((p) => toolName.includes(p.toLowerCase()));
}

function isBypassAgent(config, targetAgent) {
  const bypassAgents = config?.hooks?.preToolUse?.routerBypassAgents;
  if (Array.isArray(bypassAgents) && bypassAgents.length > 0) {
    return bypassAgents.some((a) =>
      targetAgent.toLowerCase().includes(a.toLowerCase()),
    );
  }
  // Fallback to hardcoded patterns if config missing
  const BYPASS_PATTERNS = [
    "design",
    "architect",
    "bug investigation",
    "solar bootstrap",
    "solar scan",
  ];
  return BYPASS_PATTERNS.some((p) => targetAgent.toLowerCase().includes(p));
}

function isStage1Complete(ledger) {
  return (
    /Stage\s*1.*PASS/i.test(ledger) ||
    /Pipeline Stage:\s*[2-9]/i.test(ledger) ||
    /Pipeline Stage:\s*CLOSED/i.test(ledger)
  );
}

function isInquiryGateComplete(ledger) {
  const inquirySection = ledger.match(
    /## Inquiry Gate\s*([\s\S]*?)(?=\n##|$)/i,
  );
  if (!inquirySection) return true; // No inquiry gate section = not enforcing

  const sectionText = inquirySection[1];
  const checkboxes = sectionText.match(/- \[[x ]\]/gi) || [];

  if (checkboxes.length !== 3) return false;

  const allChecked = checkboxes.every((cb) => /- \[x\]/i.test(cb));
  return allChecked;
}

// [main function]
function main(data) {
  try {
    const input = JSON.parse(data || "{}");
    const config = common.loadConfig();

    if (
      !common.isSolarActive(config) ||
      config.hooks?.preToolUse?.enabled === false
    ) {
      return;
    }

    common.logHookExecution("PreToolUse", "ENTRY");

    const toolName = (
      input.toolName ||
      input.tool ||
      input.name ||
      ""
    ).toLowerCase();

    const ledger = common.readLedger();
    const sessionType = common.getSessionType(ledger);

    if (isWatchModeTriggered(config, sessionType, toolName)) {
      common.logHookExecution(
        "PreToolUse",
        "BLOCK (watch mode - tool: " + toolName + ")",
      );
      console.log(
        JSON.stringify({
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "ask",
            permissionDecisionReason:
              "High-risk operation in loop mode requires user confirmation",
          },
        }),
      );
      return;
    }

    if (toolName !== "agent") {
      common.logHookExecution("PreToolUse", "PASS (tool: " + toolName + ")");
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const agentArgs = input.input || input.arguments || input.params || {};
    const targetAgent =
      agentArgs.agentName || agentArgs.agent || agentArgs.name || "";

    if (isBypassAgent(config, targetAgent)) {
      common.logHookExecution(
        "PreToolUse",
        "PASS (bypass agent: " + targetAgent + ")",
      );
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    if (common.isBootstrapMode(config, sessionType)) {
      process.exit(0);
    }

    if (!isInquiryGateComplete(ledger)) {
      const targetLabel = targetAgent
        ? `to ${targetAgent}`
        : "to implementation";
      common.logHookExecution(
        "PreToolUse",
        "BLOCK (inquiry gate incomplete - target: " + targetAgent + ")",
      );
      console.log(
        JSON.stringify({
          decision: "block",
          message:
            `Inquiry Gate incomplete. Before delegating ${targetLabel}, ensure:\n` +
            `1. Files examined (minimum 3 reads)\n` +
            `2. Ambiguities resolved\n` +
            `3. Plan approved\n` +
            `Check all 3 boxes in ## Inquiry Gate section of .ai_ledger.md.`,
        }),
      );
      return;
    }

    if (isStage1Complete(ledger)) {
      common.logHookExecution(
        "PreToolUse",
        "PASS (Stage 1 complete - agent: " + targetAgent + ")",
      );
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const targetLabel = targetAgent ? `to ${targetAgent}` : "to implementation";
    common.logHookExecution(
      "PreToolUse",
      "BLOCK (Stage 1 incomplete - target: " + targetAgent + ")",
    );
    console.log(
      JSON.stringify({
        decision: "block",
        message:
          `Stage 1 (Design Planning Architect) has not been completed for this pipeline. ` +
          `Delegate to Design Planning Architect before proceeding ${targetLabel}.`,
      }),
    );
  } catch (e) {
    common.logHookExecution("PreToolUse", "EXIT (parse error - fail open)");
    process.exit(0);
  }
}

// [main invoke and top level try catch]
try {
  let data = "";
  process.stdin.on("data", (chunk) => (data += chunk));
  process.stdin.on("end", () => main(data));
} catch (error) {
  common.logHookExecution("PreToolUse", "EXIT (error - " + error.message + ")");
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

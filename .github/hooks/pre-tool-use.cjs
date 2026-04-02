const fs = require("fs");
const path = require("path");

let data = "";
process.stdin.on("data", (chunk) => (data += chunk));
process.stdin.on("end", () => {
  try {
    const input = JSON.parse(data || "{}");
    const toolName = (
      input.toolName ||
      input.tool ||
      input.name ||
      ""
    ).toLowerCase();

    // Only fire on agent delegation calls
    if (toolName !== "agent") {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const configPath = path.resolve(__dirname, "../solar.config.json");
    let config = null;
    try {
      config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    } catch (e) {
      // Config missing or invalid - fail open
      process.exit(0);
    }

    // Global kill switches
    if (
      !config.solar?.active ||
      !config.hooks?.enabled ||
      config.hooks?.preToolUse?.enabled === false
    ) {
      process.exit(0);
    }

    // Resolve target agent name from tool input
    const agentArgs = input.input || input.arguments || input.params || {};
    const targetAgent =
      agentArgs.agentName || agentArgs.agent || agentArgs.name || "";

    // Bypass agents: Design/Architect agents open pipelines; Bug Investigation
    // diagnoses before implementation; Solar Bootstrap operates outside governance.
    const BYPASS_PATTERNS = [
      "design",
      "architect",
      "bug investigation",
      "solar bootstrap",
      "solar scan",
    ];
    const isBypass = BYPASS_PATTERNS.some((p) =>
      targetAgent.toLowerCase().includes(p),
    );

    if (isBypass) {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    // Read ledger for Stage 1 completion signal
    const ledgerPath = path.resolve(__dirname, "../.ai_ledger.md");
    const ledger = fs.existsSync(ledgerPath)
      ? fs.readFileSync(ledgerPath, "utf8")
      : "";

    // Bootstrap mode bypass - governance disabled during setup
    const sessionTypeMatch = ledger.match(/Session-Type:\s*(\w+)/i);
    const sessionType = sessionTypeMatch
      ? sessionTypeMatch[1].toLowerCase()
      : "chat";
    const currentMode = config.sessionTypes?.[sessionType] || "simple";

    if (currentMode === "bootstrap") {
      process.exit(0);
    }

    // Stage 1 is complete when:
    // - Explicit Stage 1 PASS marker present
    // - Pipeline already at Stage 2 or beyond
    // - Pipeline is closed
    const stage1Complete =
      /Stage\s*1.*PASS/i.test(ledger) ||
      /Pipeline Stage:\s*[2-9]/i.test(ledger) ||
      /Pipeline Stage:\s*CLOSED/i.test(ledger);

    if (stage1Complete) {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    // Stage 1 not found — block delegation and redirect to Design Planning Architect
    const targetLabel = targetAgent ? `to ${targetAgent}` : "to implementation";
    const blockMessage =
      `Stage 1 (Design Planning Architect) has not been completed for this pipeline. ` +
      `Delegate to Design Planning Architect before proceeding ${targetLabel}.`;

    console.log(JSON.stringify({ decision: "block", message: blockMessage }));
  } catch (e) {
    // Parse error - fail open
    process.exit(0);
  }
});

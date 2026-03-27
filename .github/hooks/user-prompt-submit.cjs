const fs = require("fs");
const path = require("path");

const configPath = path.resolve(__dirname, "../solar.config.json");
let config = null;
try {
  config = JSON.parse(fs.readFileSync(configPath, "utf8"));
} catch (e) {
  // Config missing or invalid - exit silently
  process.exit(0);
}

// Global kill switches
if (
  !config.solar?.active ||
  !config.hooks?.enabled ||
  !config.hooks?.userPromptSubmit?.enabled
) {
  process.exit(0);
}

const ledgerPath = path.resolve(__dirname, "../.ai_ledger.md");
const ledger = fs.existsSync(ledgerPath)
  ? fs.readFileSync(ledgerPath, "utf8")
  : "";

// Determine current mode from Session-Type in ledger
const sessionTypeMatch = ledger.match(/Session-Type:\s*(\w+)/i);
const sessionType = sessionTypeMatch
  ? sessionTypeMatch[1].toLowerCase()
  : "chat";
const currentMode = config.sessionTypes?.[sessionType] || "simple";

// Bootstrap mode bypass - governance disabled during setup
if (currentMode === "bootstrap") {
  process.exit(0);
}

// Check if this hook should be active for the current mode
const activeModes = config.hooks.userPromptSubmit.activeModes || [];
if (!activeModes.includes(currentMode)) {
  process.exit(0);
}

const hasPendingTask = /Completion Promise:\s*pending/i.test(ledger);

if (hasPendingTask) {
  console.log(
    JSON.stringify({
      continue: true,
      systemMessage:
        "SOLAR task active. Follow the Mandatory Delegation Matrix in AGENTS.md. " +
        "Check .ai_ledger.md for current objective before acting. Do not skip required agents.",
    }),
  );
} else {
  console.log(JSON.stringify({ continue: true }));
}

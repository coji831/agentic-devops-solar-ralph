const { execSync } = require("child_process");
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
    const isWriteOp = /edit|creat|appl|insert|delet|writ|replac/i.test(
      toolName,
    );

    if (!isWriteOp) {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

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
      !config.hooks?.postToolUse?.enabled
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
    const activeModes = config.hooks.postToolUse.activeModes || [];
    if (!activeModes.includes(currentMode)) {
      process.exit(0);
    }

    // Check if type-check is enabled for this mode
    const modeConfig = config.modes?.[currentMode] || {};
    const shouldTypeCheck =
      modeConfig.typeCheckOnWrite &&
      config.hooks.postToolUse.typeCheck?.enabled;

    if (shouldTypeCheck) {
      let tscMessage = "";
      try {
        const tscCmd =
          config.hooks.postToolUse.typeCheck.command || "npx tsc --noEmit";
        const tscTimeout = config.hooks.postToolUse.typeCheck.timeout || 10000;
        execSync(tscCmd + " 2>&1", { timeout: tscTimeout, encoding: "utf8" });
      } catch (e) {
        if (e.stdout) {
          const errors = (e.stdout.match(/error TS\d+[^\n]*/g) || []).slice(
            0,
            3,
          );
          if (errors.length) {
            tscMessage =
              "TypeScript errors: " +
              errors.join(" | ") +
              ". Fix before claiming progress in .ai_ledger.md.";
          }
        }
      }

      const message =
        tscMessage ||
        "Code modified in loop. Update .ai_ledger.md with step outcome and run narrowest verification.";
      console.log(JSON.stringify({ continue: true, systemMessage: message }));
    } else {
      console.log(JSON.stringify({ continue: true }));
    }
  } catch (e) {
    console.log(JSON.stringify({ continue: true }));
  }
});

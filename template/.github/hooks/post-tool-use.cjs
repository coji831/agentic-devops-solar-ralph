"use strict";
const common = require("./common.cjs");
let raw = "";
process.stdin.on("data", (c) => {
  raw += c;
});
process.stdin.on("end", () => {
  const config = common.loadConfig();
  if (!config || !common.isSolarActive(config)) process.exit(0);
  const input = (() => {
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  })();
  // VS Code tool names use camelCase (e.g. editFiles, createFile). Match write ops:
  const writePattern = /edit|creat|insert|delet|writ|replac/i;
  if (!writePattern.test(input.tool_name || "")) process.exit(0);
  const ledger = common.readLedger();
  if (/\|\s*VERIFY\s*\|/.test(ledger)) {
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext:
            "ADVERSARIAL_VERIFY_REQUIRED: ledger stage=VERIFY — Governor must dispatch a non-author specialist for adversarial audit before proceeding.",
        },
      }),
    );
  }
  process.exit(0);
});

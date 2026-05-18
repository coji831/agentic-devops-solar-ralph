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
  if (input.stop_hook_active) process.exit(0); // prevent infinite loop
  const ledger = common.readLedger();
  const hasPending = /Completion Promise:\s*pending/i.test(ledger);
  const hasFail = /Verification:\s*FAIL/i.test(ledger);
  // Only block if there is an active Work Queue task — do not block casual sessions.
  const hasActiveTask = /\|\s*(PENDING|IN_PROGRESS|ASSIGNED)\s*\|/i.test(
    ledger,
  );
  if ((hasPending || hasFail) && hasActiveTask) {
    const reason = hasFail
      ? "Verification FAIL in ledger — fix failures before stopping."
      : "Completion Promise pending — valid values: WORK_PACKAGE_COMPLETE, WORK_PACKAGE_BLOCKED, ESCALATION_REQUIRED.";
    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "Stop",
          decision: "block",
          reason,
        },
      }),
    );
  }
  process.exit(0);
});

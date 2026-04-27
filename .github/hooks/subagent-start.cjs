// subagent-start.cjs
// SOLAR-Ralph v4 SubagentStart hook
// Reads the Handoff Payload section from the ledger and injects it as
// additionalContext into the subagent's starting context at delegation time.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - Phase 3: Added typed payload extraction and injection

// [imports]
const common = require("./common.cjs");

// [helper functions]
function extractHandoffPayload(content) {
  var sectionMatch = content.match(
    /##\s*Handoff Payload\s*\n([\s\S]*?)(?=\n##\s|$)/,
  );
  if (!sectionMatch) return null;
  var payload = sectionMatch[1].trim();
  if (!payload || payload === "(none)" || payload === "(empty)") return null;
  return payload;
}

// [main function]
function main() {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (!common.isSolarActive(config)) {
    return;
  }

  common.logHookExecution("SubagentStart", "ENTRY");

  if (!config.handoffs?.typedPayloadsEnabled) {
    common.logHookExecution("SubagentStart", "EXIT (typed payloads disabled)");
    console.log(JSON.stringify({ continue: true }));
    process.exit(0);
  }

  const ledgerContent = common.readLedger();
  const handoffPayload = extractHandoffPayload(ledgerContent);

  const additionalContext = handoffPayload
    ? "HANDOFF PAYLOAD FROM GOVERNOR (read this before starting):\n\n" +
      handoffPayload +
      "\n\nReference schemas in .github/solar-system/schemas/ for the typed format."
    : "No handoff payload in ledger. Proceed with request context only.";

  common.logHookExecution(
    "SubagentStart",
    handoffPayload
      ? "INJECT (handoff payload present)"
      : "PASS (no handoff payload)",
  );
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "SubagentStart",
        additionalContext: additionalContext,
      },
    }),
  );
}

// [main invoke and top level try catch]
try {
  main();
} catch (error) {
  common.logHookExecution(
    "SubagentStart",
    "EXIT (error - " + error.message + ")",
  );
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

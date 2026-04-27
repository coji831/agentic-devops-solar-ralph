// subagent-stop.cjs
// SOLAR-Ralph v4 SubagentStop hook
// Validates that a subagent response contains minimum required output fields
// before allowing the subagent to stop. Blocks if required fields are absent.
//
// NOTE: SubagentStop output uses the top-level decision format, NOT hookSpecificOutput.
// Always check stop_hook_active in input to prevent infinite blocking loops.
//
// Changelog:
// - v4.1: Merged hooks.enabled into solar.active (Option A)
// - Phase 3: Added handoff field validation (completedBy, status, workPackage)

// [imports]
const common = require("./common.cjs");

// [helper functions]
function validateHandoffFields(hookInput) {
  if (hookInput && hookInput.stop_hook_active === true) {
    common.logHookExecution(
      "SubagentStop",
      "ALLOW (stop_hook_active - prevent deadlock)",
    );
    return { decision: "allow" };
  }

  var responseText = "";
  if (hookInput && typeof hookInput.response === "string") {
    responseText = hookInput.response;
  } else if (hookInput && typeof hookInput.output === "string") {
    responseText = hookInput.output;
  } else {
    common.logHookExecution("SubagentStop", "ALLOW (no response text)");
    return { decision: "allow" };
  }

  var REQUIRED_FIELD_PATTERNS = [
    /completed[- _]?by/i,
    /status\s*:/i,
    /work[- _]?package/i,
  ];

  var missingFields = [];
  REQUIRED_FIELD_PATTERNS.forEach(function (pattern, idx) {
    if (!pattern.test(responseText)) {
      var labels = ["completedBy", "status", "workPackage"];
      missingFields.push(labels[idx] || "field-" + idx);
    }
  });

  if (missingFields.length > 0) {
    common.logHookExecution(
      "SubagentStop",
      "BLOCK (missing fields: " + missingFields.join(", ") + ")",
    );
    return {
      decision: "block",
      reason:
        "Subagent response is missing required handoff fields: " +
        missingFields.join(", ") +
        ". Produce a handoff summary conforming to .github/solar-system/schemas/implementer-handoff.schema.json before stopping.",
    };
  }

  common.logHookExecution("SubagentStop", "ALLOW (validation passed)");
  return { decision: "allow" };
}

// [main function]
function main(inputData) {
  const config = common.loadConfig();
  if (!config) process.exit(0);

  if (!common.isSolarActive(config)) {
    return;
  }

  common.logHookExecution("SubagentStop", "ENTRY");

  if (!config.handoffs?.typedPayloadsEnabled) {
    common.logHookExecution("SubagentStop", "ALLOW (typed payloads disabled)");
    console.log(JSON.stringify({ decision: "allow" }));
    return;
  }

  var hookInput = null;
  try {
    hookInput = JSON.parse(inputData);
  } catch (e) {
    common.logHookExecution("SubagentStop", "ALLOW (unparseable input)");
    console.log(JSON.stringify({ decision: "allow" }));
    return;
  }

  const result = validateHandoffFields(hookInput);
  console.log(JSON.stringify(result));
}

// [main invoke and top level try catch]
try {
  if (process.stdin.isTTY) {
    console.log(JSON.stringify({ decision: "allow" }));
    process.exit(0);
  }

  let inputData = "";
  process.stdin.resume();
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (inputData += chunk));
  process.stdin.on("end", () => main(inputData));
} catch (error) {
  common.logHookExecution(
    "SubagentStop",
    "EXIT (error - " + error.message + ")",
  );
  console.log(JSON.stringify({ decision: "allow" }));
  process.exit(0);
}

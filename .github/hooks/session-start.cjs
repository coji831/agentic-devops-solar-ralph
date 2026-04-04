// session-start.cjs
// SOLAR-Ralph v4 Phase 1 - SessionStart hook
// Reads .learnings/LEARNINGS.md and injects a condensed summary into session context
// via the SessionStart hookSpecificOutput additionalContext field.
// ASCII only in this script.

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
  !config.hooks?.sessionStart?.injectLearnings
) {
  process.exit(0);
}

// Resolve learnings path: config-driven or default relative to this hook
var learningsDir;
if (config.selfImprovement && config.selfImprovement.learningsPath) {
  // learningsPath is relative to workspace root (.github/hooks/ -> workspace root is ../../)
  learningsDir = path.resolve(
    __dirname,
    "../../",
    config.selfImprovement.learningsPath,
  );
} else {
  learningsDir = path.resolve(__dirname, "../solar-system/.learnings/");
}

var learningsPath = path.join(learningsDir, "LEARNINGS.md");

var learningsSummary = "";
try {
  var content = fs.readFileSync(learningsPath, "utf8");
  // Extract non-empty, non-header, non-comment lines for condensed summary
  var lines = content.split("\n").filter(function (l) {
    var t = l.trim();
    return (
      t && !t.startsWith("#") && !t.startsWith("<!--") && !t.startsWith("```")
    );
  });
  learningsSummary = lines.slice(0, 20).join(" ").trim();
} catch (e) {
  // Learnings file missing or unreadable - no injection needed
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

if (!learningsSummary) {
  // File exists but has no extractable content yet - skip injection
  console.log(JSON.stringify({ continue: true }));
  process.exit(0);
}

console.log(
  JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: "SOLAR Learnings Summary: " + learningsSummary,
    },
  }),
);

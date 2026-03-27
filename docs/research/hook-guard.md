# Hook Guard: Preventing Unintended Agent Termination

The issue where the agent stops after the first step is caused by the line `console.log(JSON.stringify({ continue: false }));`. In the 2026 GitHub Copilot hook schema, returning `continue: false` from any lifecycle hook (like `PostToolUse` or `userPromptSubmitted`) acts as a "kill switch" that terminates the entire agent session immediately.[1]

To fully suspend the SOLAR-Ralph system during setup or when deactivated, you should use a **Passive Pass-through** pattern. When the system is off, the hook should exit with code `0` and provide no output (or `{ "continue": true }`), allowing the agent to proceed with its native behavior.

### 1. Improved Toggle Mechanism: The Sentinel File

Parsing a Markdown ledger with regex is token-heavy and prone to state-sync errors. The most robust 2026 pattern for hook suspension is the **Sentinel File Gate**. Using a zero-byte hidden file (e.g., `.solar_on`) is faster and eliminates the "stopped session" bug.

**Updated Hook Script (`scripts/solar-gate.js`):**

```javascript
const fs = require("fs");
const path = require("path");

// 1. GLOBAL SUSPENSION CHECK
// Using a sentinel file instead of ledger parsing for performance and reliability
if (!fs.existsSync(".solar_on")) {
  // Pass-through: Do not print anything and exit 0.
  // This lets Copilot work normally without any SOLAR interference.
  process.exit(0);
}

const ledgerPath = ".github/.ai_ledger.md";
const ledger = fs.existsSync(ledgerPath)
  ? fs.readFileSync(ledgerPath, "utf8")
  : "";

// 2. SESSION CONTEXT DETECTION
const isLoop = /Session-Type:\s*loop/i.test(ledger);
const isPending = /Completion Promise:\s*pending/i.test(ledger);

// 3. RECURSION SAFETY (2026 Standard)
// Always check this field provided in the hook input JSON to prevent infinite billing loops
const input = JSON.parse(fs.readFileSync(0, "utf8"));
if (input.stop_hook_active === false) {
  // If we aren't in a loop context, allow clean exit
  process.exit(0);
}

if (isLoop && isPending) {
  console.log(
    JSON.stringify({
      continue: true,
      systemMessage:
        "SOLAR loop active. Continue until <promise>WORK_PACKAGE_COMPLETE</promise> is written.",
    }),
  );
} else {
  // Allow normal completion
  console.log(JSON.stringify({ continue: false }));
}
```

---

### 2. Implementation Suggestions

#### I. Use Agent-Scoped Hooks (Isolation)

Instead of global workspace hooks in `.github/hooks/*.json` which affect the default agent, move your SOLAR logic into **Agent-Scoped Hooks** inside your specialist `.agent.md` files.

- **Benefit:** Your setup command (run by the default agent) will never even trigger these scripts, effectively "suspending" them by design.[2]
- **Frontmatter Config:**
  ```yaml
  ---
  name: Logic-Specialist
  hooks:
    agentStop: "node./scripts/solar-gate.js"
  ---
  ```

#### II. Prompt-Based Bypass (The "BOOTSTRAP" Tag)

If you must use global hooks, add a bypass check for a specific keyword in the prompt. This allows your "old" model agents to identify a setup task and skip the recursive logic.

**Add to the top of your script:**

```javascript
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const isSetup = /SETUP|BOOTSTRAP|INSTALL/i.test(input.initialPrompt |

| "");

if (isSetup) {
    process.exit(0); // Immediately bypass all SOLAR logic for setup tasks
}
```

#### III. Automate the Toggle

Update your `/solar-apply-setup` command to create the sentinel file as its final step:

1.  Run setup scanning.
2.  Edit configuration files.
3.  **Command:** `touch.solar_on` (This "turns on" the hooks for the first time).

### Summary of Hook Behavior for 2026

| System State        | Hook Logic          | Agent Result                                    |
| :------------------ | :------------------ | :---------------------------------------------- |
| **SOLAR Off**       | Exit `0`, no output | Agent finishes task and stops normally.         |
| **SOLAR On (Loop)** | `continue: true`    | Agent is forced to retry/continue autonomously. |
| **SOLAR On (Done)** | `continue: false`   | Agent is allowed to stop because goal is met.   |
| **Bypass (Setup)**  | `process.exit(0)`   | Hooks are ignored; setup completes in one go.   |

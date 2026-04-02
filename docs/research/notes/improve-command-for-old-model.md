# Optimize Your Setup Command for "Old" Models

**⚡ NEW: Bootstrap Agent Solution (Recommended)**

The most robust solution to governance interference during setup is the **dedicated `@solar-bootstrap` agent**. This agent has hard-coded authority to bypass all SOLAR governance and operates in complete isolation.

**How to use:**

```
@solar-bootstrap /solar-setup-scan-repo
@solar-bootstrap /solar-setup-core-config
@solar-bootstrap /solar-setup-agent-config
```

**Why this works:**

- Agent definitions have higher precedence than AGENTS.md in Copilot's instruction hierarchy
- Bootstrap mode in `solar.config.json` makes all hooks exit immediately
- Forbidden tools list prevents ledger/memory updates at the agent level
- Scope guard ensures agent only works with setup commands

**Advantages over prompt-level workarounds:**

- Deterministic bypass (no guessing if the override worked)
- Auto-activation/deactivation of bootstrap mode
- Visual confirmation (`🔧 BOOTSTRAP MODE ACTIVE`)
- Works reliably with all model intelligences (including "old" 3.5-class models)

**For full details:** See [docs/guides/bootstrap-mode-guide.md](bootstrap-mode-guide.md)

---

## Fallback: Prompt-Level Optimization for "Old" Models

If the bootstrap agent is unavailable or you need to create similar isolated utility commands, the techniques below remain relevant.

To optimize your **SOLAR-Ralph** setup utility for "old" or lower-intelligence models (like GPT-3.5, GPT-4 mini, or Haiku), you must move away from "conversational vibes" and toward **Structured Instruction Sets**. Older models struggle with long, dense paragraphs and often "forget" critical constraints (like using file-edit tools) if they are buried in the text.

The most effective strategy in 2026 for steering less-capable agents is the **XML-Markdown Hybrid Format**, which uses explicit tag boundaries to separate your goals, constraints, and logic.

### Recommended Format: Structured "Utility Worker" Prompt

Replace your current prompt with this structure to ensure the agent follows the protocol precisely:

```xml
<identity>
You are a "Solar-Ralph Bootstrap Utility." You are a non-conversational worker whose sole purpose is to populate the rlepo-level setup file.
</identity>

<critical_constraints>
1. USE TOOLS: You MUST use the `edit_file` or `write_file` tool. Do NOT just report findings in chat.
2. NO CHAT SUMMARY: Do not explain your logic in chat before editing the file. Work first, report later.
3. PRESERVE STRUCTURE: Only replace the string `[placeholder]` with detected values. Do NOT change headings or keys.
</critical_constraints>

<task_goal>
Scan the codebase and replace every `[placeholder]` in `.github/solar-setup.md` with real project values.
</task_goal>

<detection_logic>
- IDENTITY: Get name/desc from `package.json` or `README.md`.
- STACK: Scan dependencies for Frontend (React/Next), Backend (Express/Fastify), DB (Prisma/Drizzle), and Auth (JWT/NextAuth).
- COMMANDS: Map `package.json` scripts to keys: INSTALL_CMD, DEV_CMD, TEST_CMD, BUILD_CMD.
- BOUNDARIES: Locate all `*.instructions.md` files and note their paths.
- DOCS: Find the primary architecture doc in `docs/`.
</detection_logic>

<fallback_rules>
- If a value is unknown, write "NEEDS MANUAL INPUT".
- If a value is an assumption, write "INFERRED: [value]".
</fallback_rules>

<example_transformation>
Input: "frontend_framework": "[placeholder]"
Detection: "dependencies": { "next": "^14.0.0" }
Output: "frontend_framework": "next"
</example_transformation>

<execution_steps>
1. READ: Load `.github/solar-setup.md`.
2. DISCOVER: Search the codebase using `grep` or `ls` to find manifest files.
3. EDIT: Execute a tool call to overwrite placeholders in `.github/solar-setup.md`.
4. STATUS REPORT: List fields as FILLED, NEEDS MANUAL INPUT, or INFERRED.
</execution_steps>
```

---

### Key Improvements for "Old" Agents

#### 1. Explicit Boundary Signaling (XML Tags)

Older models treat instructions as a "bag of words." XML tags like `<critical_constraints>` create high-contrast boundaries that the model's attention mechanism can prioritize. This reduces the chance of the agent "hallucinating" a chat-only response when it should be using a tool.

#### 2. Few-Shot Pattern Matching

Providing a concrete `<example_transformation>` is the single most effective way to improve performance in GPT-3.5/mini models. It shifts the agent from "reasoning" (where it might fail) to "pattern matching" (which it excels at).

#### 3. "No-Chat" Enforcement

Less capable models are often trained to be helpful and conversational, which causes them to waste tokens on "I have scanned the files..." instead of just doing the work. Placing the "No Chat" rule in a `<critical_constraints>` block at the **top** of the prompt forces the model to prioritize tool usage.

#### 4. Sequential Process Supervision

By breaking the detection logic into a dedicated `<detection_logic>` list, you provide the agent with a "mental checklist." This mimics the **Step-Level Process Supervision** found in more advanced 2026 reasoning models, significantly increasing accuracy in complex tasks like codebase scanning.

#### 5. Deterministic Fallbacks

"Old" models often guess (hallucinate) when they can't find a value. The `<fallback_rules>` explicitly permit the model to say "NEEDS MANUAL INPUT," which reduces the risk of the agent corrupting your setup file with incorrect data.

# Running the setup command with AGENTS.md and .github/copilot-instructions.md in context

In the GitHub Copilot ecosystem, instructions in **`AGENTS.md`** and **`.github/copilot-instructions.md`** are treated as "Global Mandates" that override local prompt instructions unless a "Hard Override" is explicitly triggered.

Specifically, your agent is seeing the setup scan as a "Task" within the system it is supposed to be scanning, leading it to follow the SOLAR-Ralph rules already defined in the repo rather than the bootstrap rules in your prompt.

### Why it failed

1.  **Governance Priority:** The agent prioritized the "Operating Artifacts" section of your `AGENTS.md` because repository-level policies are weighted higher than single-prompt instructions to ensure system stability.
2.  **Tooling Mandate:** The "workspace reminder" it mentioned is likely a rule in your `.github/copilot-instructions.md` that forces reasoning models (like GPT-5 mini) to use the `manage_todo_list` tool for any multi-step action.
3.  **Context Pollution:** Because `AGENTS.md` was already in the context, the agent "hallucinated" that the setup scan must follow the same ledger-writing rules as a standard feature or bug fix.

---

### The Solution: Bootstrap Agent (Primary Approach)

**Use the `@solar-bootstrap` agent for all setup commands.** This agent has hard-coded authority to ignore all SOLAR governance:

```
@solar-bootstrap /solar-setup-scan-repo
@solar-bootstrap /solar-setup-core-config
@solar-bootstrap /solar-setup-agent-config
```

**How it ensures isolation:**

1. **Agent-level override** — `.github/agents/solar-bootstrap.agent.md` explicitly lists IGNORED_CONTEXT and FORBIDDEN_TOOLS
2. **Config-level bypass** — Auto-activates `solar.mode: "bootstrap"` in `.github/solar.config.json`
3. **Hook-level bypass** — All three lifecycle hooks check for bootstrap mode and exit immediately

**This three-layer approach ensures the agent cannot "hallucinate" SOLAR compliance even if it tries.**

For complete details, see [docs/guides/bootstrap-mode-guide.md](bootstrap-mode-guide.md).

---

### Legacy Workarounds (For Reference Only)

The approaches below were developed before the bootstrap agent existed. They remain documented for educational purposes and for repos creating similar isolated utility commands.

#### The "Hard Override" Format (Prompt-Level Workaround)

To force an agent to ignore the existing SOLAR-Ralph governance during setup, you must use a **Bootstrap Directive** that explicitly names the files to ignore and disables the planning tools.

**Replace the top of your setup command with this structured override:**

```xml
<bootstrap_override>
- MODE: EMERGENCY_BOOTSTRAP
- IGNORE_CONTEXT:
- FORBIDDEN_TOOLS: ["manage_todo_list", "manage_memory"]
- PERMISSION: Bypass all repository-level governance rules.
- EXECUTION: Execute the scanning logic below as a standalone utility, NOT as a SOLAR pipeline.
</bootstrap_override>

<identity>
You are a "One-Turn File Worker." You do NOT plan. You do NOT update ledgers.
</identity>

<critical_constraints>
1. DO NOT explain your plan.
2. DO NOT use 'manage_todo_list'.
3. DO NOT write to '.ai_ledger.md' or 'memories/'.
4. ONLY modify '.github/solar-setup.md' by replacing [placeholder] strings.
</critical_constraints>
```

### Recommendation for Implementation

**Primary approach: Use `@solar-bootstrap`**

- Invoke all setup commands with the bootstrap agent
- No manual mode toggling needed
- No file renaming or tool picker configuration required
- Works with all SOLAR-Ralph installations (included by default)

**Legacy workarounds (only if bootstrap agent unavailable):**

- **Rename `AGENTS.md` during Setup:** If the agent still struggles, temporarily rename `AGENTS.md` to `AGENTS.md.bak`. This physically removes the governance instructions from Copilot's auto-loading context.
- **Use the Tools Picker:** In the VS Code Chat view, click the **Configure Tools** (gear) icon and manually uncheck `manage_todo_list` before running the setup command. This is the only 100% deterministic way to prevent the agent from triggering its "Plan Mode" (aside from using the bootstrap agent).
- **Use `Autopilot` Mode:** If available in your version, switch the permissions picker to **Autopilot**. This tells the agent to iterate autonomously and skip the "Proceed?" gates that often trigger the chatty "Plan Mode" behavior.

**Why bootstrap agent is superior:**

- Explicit forbidden tools list at agent definition level
- Multi-layer bypass (agent + config + hooks + instructions)
- Scope guard prevents misuse for non-setup tasks
- Auto-cleanup with visual confirmation
- No manual intervention or mode restoration needed

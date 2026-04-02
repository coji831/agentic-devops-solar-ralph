# `<tool_preambles>` Conflict and Governor Compliance Failures

## Overview

Two distinct failures were observed when the Orchestration Governor ran against `start implement story 3` (Chat-sequence.md, mandarin project):

1. **Self-ID skipped** — the governor never output its identity line
2. **Pipeline violated** — the governor implemented directly instead of delegating through the Feature pipeline

These are independent problems with different root causes and different fixes.

---

## Failure 1: Self-ID Skipped

### What is `<tool_preambles>`?

VS Code Copilot injects a hidden system instruction into every agent context. It is not visible in any user-facing config or docs. Based on observed model thinking behavior, it instructs the model to:

> Before each tool call, emit a short (approximately ≤10 word) sentence describing what you will do.

**Evidence** — confirmed directly from the governor's thinking sequence in `Chat-sequence.md`:

> _"I need to incorporate the guidance from the `<tool_preambles>` instruction, meaning I'll send a brief preamble before making any tool calls. For instance, I can say, 'I'll add Story 16.3 tasks and create a plan,' which is only 9 words."_

The model names the instruction explicitly. It is platform-injected — not in any `.agent.md`, `.instructions.md`, or `copilot-instructions.md` file in the repository.

### The Conflict

| Requirement                            | Source                              | What model did                                 |
| -------------------------------------- | ----------------------------------- | ---------------------------------------------- |
| "FIRST output must be self-ID line"    | our `<progress_protocol>` Block 1   | **Skipped**                                    |
| "Brief preamble before each tool call" | VS Code built-in `<tool_preambles>` | **Satisfied** — "I'll add Story 16.3 tasks..." |

Both requirements target the same moment: the very first text emitted before the first tool call. The model cannot satisfy both with different text. It picks one.

`<tool_preambles>` wins because:

1. It is a system-level injection (higher implicit authority than body text)
2. The preamble it elicits is functionally useful — it describes what is about to happen
3. Our self-ID line provides zero task context — the model treats it as redundant overhead

### Why the Numbered-Step Pattern Was Proposed (Origin of Option C)

The bootstrap agent (`solar-bootstrap.agent.md`) uses a `<preamble_sequence>` with numbered steps where step 5 = `Output: 🔧 BOOTSTRAP MODE ACTIVE`. This was hypothesized to force text output at a specific point by giving the model a procedure to follow sequentially.

However, this does **not** solve the problem:

```
1. Check command                          ← no tool call, model reads it
2. Read .github/solar.config.json         ← tool call → <tool_preambles> fires: "I'll read the config..."
3. Store current values                   ← tool call
4. Write bootstrap activation             ← tool call
5. Output: 🔧 BOOTSTRAP MODE ACTIVE       ← text output, appears AFTER tool calls
6. Proceed to main task
```

`🔧 BOOTSTRAP MODE ACTIVE` still appears after the tool calls, not before. Bootstrap looks different only because its identity marker is at step 5 (mid-procedure), not at step 0 (before everything). The `<tool_preambles>` constraint still fires and is satisfied by the narration on steps 2–4.

A `<startup_sequence>` with step 1 = emit text would face the same issue: `<tool_preambles>` fires before the model even begins the numbered sequence, and the model may narrate "I'll follow the startup sequence..." as its first-tool-call preamble instead.

**Option C's actual value:** not "force text before all tool calls" but "give the model a procedure where the identity output is embedded as a named numbered step." The self-ID may appear slightly later, but it will appear as part of the procedure completion.

### Possible Solutions

**Option A — Align with `<tool_preambles>` (recommended)**

Reframe the self-ID AS the required `<tool_preambles>` preamble for the first tool call. Instead of competing with the built-in, satisfy it with our content:

> "The `<tool_preambles>` preamble you emit before your FIRST tool call must be exactly:
> `🤖 Orchestration Governor  |  model: GPT-5 mini`
> Do not use any other sentence as the first-tool-call preamble."

The model is already emitting one preamble before the first tool call. We constrain what that sentence must be.

**Option B — Accept hooks as the identity signal**

Accept that text-before-tools is not reliably achievable for the main chat agent. Use `SubagentStart` hook toast for subagent identity, and accept that the governor's identity appears organically within its first `<tool_preambles>` sentence.

**Option C — Numbered startup procedure**

Embed self-ID as a numbered step in a `<startup_sequence>`, following the bootstrap pattern. The identity output is attached to a step in the procedure, not to "before everything."

```xml
<startup_sequence>
  1. Output: 🤖 Orchestration Governor  |  model: GPT-5 mini
  2. Read .github/.ai_ledger.md
  3. Read .github/AGENTS.md
  4. Select pipeline and proceed
</startup_sequence>
```

**Evidence from `bootstrap-answer.md`:**

The bootstrap agent's actual output confirmed the timing:

```
"Reading the repo's solar.config.json to capture current mode and enable bootstrap."  ← <tool_preambles> sentence
Read solar.config.json                                                                 ← tool call
🔧 BOOTSTRAP MODE ACTIVE                                                               ← identity output (step 5)
```

`<tool_preambles>` always fires as a sentence immediately before the first tool call. Bootstrap's identity marker (`🔧 BOOTSTRAP MODE ACTIVE`) appears mid-sequence (after tool calls) — NOT before them.

**However — the governor is a special case.**

Bootstrap's step 1 is "Check invocation gate" (no tool), step 2 is the first real tool call. `<tool_preambles>` fires before step 2.

If the governor's `<startup_sequence>` step 1 = pure text emit (no tool call), and step 2 = first tool call, then:

- Step 1 completes without triggering `<tool_preambles>` (no tool was called yet)
- `<tool_preambles>` fires before step 2

This means the model CAN output the self-ID at step 1 BEFORE the platform's preamble sentence fires at step 2. The sequence would be:

```
🤖 Orchestration Governor  |  model: GPT-5 mini       ← step 1 (pure text, no tool)
"Reading .github/AGENTS.md..."                         ← <tool_preambles> fires before step 2
Read .github/AGENTS.md                                 ← step 2 (first tool call)
```

This is a meaningful difference from bootstrap, where the identity is embedded AFTER a tool call. For Option C to work on the governor, step 1 must have zero tool calls and produce only the literal self-ID text.

**Trade-off vs Option A:**

- Option C: self-ID BEFORE any preamble sentence, but requires zero tool calls in step 1
- Option A: self-ID IS the preamble sentence — no extra step needed, but relies on model constraint compliance

**Recommended: Option A + Option C together:**

1. Use `<startup_sequence>` with step 1 = pure self-ID emit (Option C structure)
2. In step 1, reference `<tool_preambles>` explicitly: "This is your `<tool_preambles>` output for the first tool call" (Option A framing)
3. Make step 2 = Read AGENTS.md (enforces delegation matrix immediately)

---

## Failure 2: Governor Violated the Feature Pipeline

### What Happened

For the prompt `start implement story 3`, the governor selected Pipeline 4 (Feature) in its thinking, then immediately started reading backend service files, generating patches, and editing code directly — all without delegating to any specialist.

### Required Pipeline (from `.github/AGENTS.md`)

```
Pipeline 4: Feature
Governor
└─ 1. Design Planning Architect       ← MANDATORY before any implementation
└─ 2. /ralph-loop
      └─ Implementation Specialist + Test Specialist
└─ 3. Review Auditor
└─ 4. Security Auditor (conditional)
└─ 5. Docs Curator
└─ 6. Close
```

**AGENTS.md Mandatory Delegation Matrix:**

> "New story, epic, or feature → Design Planning Architect — BEFORE any implementation"
> "Backend code changes → Backend Implementation Specialist — Always"

The governor violated both rules. It acted as implementation specialist AND design authority.

### Root Cause

The governor's `<approach>` section in the agent file instructs it to delegate, but the model deprioritized the delegation constraint when it already had sufficient context to proceed directly. The `<constraints>` section says "do not do broad implementation work yourself if a specialist should own it" — but this is a soft advisory. The model rationalized that reading skill files + editing was "within scope."

**The core problem:** the governor's pipeline instructions are in its own agent body. The model can rationalize exceptions. The AGENTS.md pipeline rules are external authority — the governor is supposed to read AGENTS.md before acting — but the governor never read the ledger or AGENTS.md before proceeding to implementation.

### Why This Is Separate from Failure 1

Failure 1 is a platform constraint (injected instruction). Failure 2 is a compliance failure — the governor read its own agent file but did not fulfill the read-AGENTS.md-first requirement from its own `<approach>` step 1.

The governor's `<approach>` step 1 reads:

> "Read the user request, `.github/copilot-instructions.md`, `.github/AGENTS.md`, and `.github/.ai_ledger.md`."

The thinking sequence shows no AGENTS.md read. The governor skipped step 1 and jumped to implementation.

### Possible Fix

Make AGENTS.md reading mandatory and non-skippable by embedding it in the startup sequence (Option C above):

```xml
<startup_sequence>
  1. Output: 🤖 Orchestration Governor  |  model: GPT-5 mini
  2. Read .github/AGENTS.md  ← pipeline rules, delegation matrix
  3. Read .github/.ai_ledger.md
  4. Select pipeline from AGENTS.md pipeline table
  5. Emit: 📋 Pipeline selected: <name>  (<N> stages)
  6. Delegate to Stage 1 agent — do not implement directly
</startup_sequence>
```

By making AGENTS.md the second thing the governor reads (before any task analysis), the delegation matrix is active in context when pipeline selection happens. The model cannot rationalize skipping delegation if it just read "Backend code changes → Backend Implementation Specialist — Always."

---

## Combined Recommendation

| Problem           | Fix                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------ |
| Self-ID skipped   | Option A: reframe Block 1 as the `<tool_preambles>` preamble for the first tool call |
| Pipeline violated | Embed `<startup_sequence>` with AGENTS.md read as step 2, before any task analysis   |

Both fixes can be applied together in the governor's `<progress_protocol>` → replace Block 1 with a `<startup_sequence>` that (a) names the self-ID as the mandatory first-tool-call preamble and (b) makes AGENTS.md reading the first tool call.

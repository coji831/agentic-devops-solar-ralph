# SOLAR-Ralph v4 Feasibility Analysis

**Source:** `docs/research/framework/SOLAR-Ralph-framework-v4.md`
**Target System:** VS Code Copilot agent pipeline (`.agent.md`, `.prompt.md`, `.instructions.md`, `AGENTS.md`, `stop.cjs` hooks, `.github/solar-system/`)
**Date:** 2026-04-04

---

## Section 1: Lightweight Orchestration and Modular Governance Patterns

### Feasibility

- Proven technique? **YES** — Orchestrator-Worker, Hierarchical, and Router patterns are standard multi-agent patterns with production deployments documented across cited literature (refs 3, 5, 6).
- Achievable in VS Code Copilot agents? **YES** — Orchestrator-Worker, Hierarchical, Handoff (via native `handoffs` frontmatter), and parallel subagents are all natively achievable. Only Group Chat (shared-thread consensus) has no native primitive.
- Limitations:
  - Group Chat (consensus via shared thread) is not achievable — no shared persistent message bus between agents exists; all inter-agent communication routes through the coordinator turn
  - Planner-Executor loop reduction requires conditional pipeline routing logic in the governor (no auto-skip primitive)

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/AGENTS.md` — pipeline contracts implementing Orchestrator-Worker (Governor → Specialists) and Hierarchical (Governor → Design Planning Architect → Specialists)
  - `.github/agents/orchestration-governor.agent.md` — central orchestrator role
  - `.github/agents/*.agent.md` — 16 specialist worker agents covering frontend, backend, security, docs, testing, review
  - `solar.config.json` — `modes` map enabling simple/loop/plan/bootstrap routing at the session level
  - Pipeline 1–4 in `AGENTS.md` — implement sequential, conditional, and hierarchical flows
- Gap:
  - No Router pattern (no dynamic routing to agents based on skill matching without full pipeline selection)
  - No formal latency or cost classification per pipeline stage
  - No `agents:` restriction list in governor `.agent.md` — governor should declare its allowed subagent roster explicitly to prevent unintended agent selection in parallel runs

### Implementation Skeleton

Files to create or modify:

- `.github/AGENTS.md` — add Router pipeline entry: lightweight routing table mapping signal type to agent without full pipeline overhead
- `.github/agents/orchestration-governor.agent.md` — add conditional skip logic for Pipeline 2 planner phase on clearly scoped tasks; add explicit `agents:` list restricting which subagents governor can delegate to
- `.github/agents/*.agent.md` — add `handoffs:` frontmatter to specialist agents for post-task next-step suggestions (e.g., Implementation → Review handoff)
- `.github/solar-system/patterns/orchestration-patterns.md` — document latency/cost classification per pipeline pattern; document parallel subagent usage policy

Folder changes (if any):

```
.github/
  solar-system/           ← NEW top-level SOLAR isolation dir
    patterns/
      orchestration-patterns.md
```

Config / frontmatter fields needed:

- `model: [model-name, fallback-model]` in worker `.agent.md` — assign smaller models (e.g., `Claude Haiku 4.5 (copilot)`) to executor agents; larger models to coordinator/architect
- `agents: [agent-name-list]` in governor `.agent.md` — explicit subagent roster restricts which specialists the governor can delegate to; use `*` to allow all or `[]` to prevent any subagent use
- `handoffs: [{ label, agent, prompt, send, model }]` — native post-task transition field; each entry adds a button after the agent response that switches to the target agent with a pre-filled prompt
- `solar.config.json` → `modes.router` — new lightweight mode entry: `{ enforceCompletion: false, typeCheckOnWrite: false }`
- `solar.config.json` → `hooks.preToolUse.routerBypassAgents` — list of agent names invokable without full pipeline gating

Isolation: **SOLAR-only**

---

## Section 2: Designer-Implementer Firewalls and Security Protocols

### Feasibility

- Proven technique? **YES** — Structured output enforcement via JSON schema is production-standard (refs 14, 15, 16); Skeleton IR is well-documented for GUI agents (ref 18); TLA+ formal verification and hot-patching are specialized research techniques.
- Achievable in VS Code Copilot agents? **PARTIALLY** — The Designer-Implementer separation is achievable as a two-agent delegation pattern. Strict JSON schema enforcement between agents is achievable via `.instructions.md` output contracts but NOT via constrained decoding (VS Code does not expose OpenAI's `strict: true` structured output mode to agent authors). TLA+ compilation and hot-patching are out of scope. **NEW (verified 2026-04-04):** Agent-scoped `hooks:` in `.agent.md` frontmatter (preview) enables per-agent pre/post-tool lifecycle enforcement — a partial firewall mechanism that does not require routing through the governor.
- Limitations:
  - No native constrained decoding in VS Code Copilot — JSON schema compliance is prompt-enforced, not deterministic
  - Skeleton IR concept is achievable as a markdown intermediate plan format, not a compiled IR
  - The 24-skeleton adversarial manifest (Elder Plinus methodology, ref 20) is a red-teaming research artifact; only a prompt-based approximation is achievable
  - Hot-patching (runtime instruction redirection without restart) is architecturally impossible in stateless Copilot sessions

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/agents/design-planning-architect.agent.md` — explicit Designer role that produces plans before implementation starts
  - `.github/hooks/pre-tool-use.cjs` — partial firewall: blocks implementation agents from bypassing the design/architect bypass list
  - `.github/hooks/post-tool-use.cjs` — write-gate that checks ledger state on every file edit (enforcement hook)
  - `.github/skills/backend-review/`, `.github/skills/frontend-review/` — adversarial review layer (Implementer output challenged post-execution)
  - `.github/agents/security-auditor.agent.md` — dedicated security challenge role
- Gap:
  - No formal JSON schema contract between Design Planning Architect output and Implementation Specialist input
  - No structured output enforcement — agent handoff content is free-form markdown
  - No skeleton IR format defined for plan-to-implementation handoffs
  - No adversarial manifest for prompt injection / persona hijacking detection beyond generic security auditor role
  - No hot-patch mechanism (by design — stateless sessions make this inapplicable)

### Implementation Skeleton

Files to create or modify:

- `.github/solar-system/schemas/designer-output.schema.json` — JSON schema defining required fields for Design Planning Architect output handed to implementation agents
- `.github/solar-system/schemas/implementer-handoff.schema.json` — JSON schema for typed handoff from implementer back to governor
- `.github/instructions/solar.instructions.md` — add output contract section: Design Planning Architect MUST produce fields matching `designer-output.schema.json` before any implementation agent is invoked
- `.github/agents/design-planning-architect.agent.md` — add output format constraint referencing schema file
- `.github/solar-system/adversarial/skeleton-manifest.md` — prompt-based approximation of vulnerability pattern catalog (persona hijacking, intent inversion, scope creep, instruction override)

Folder changes (if any):

```
.github/
  solar-system/
    schemas/
      designer-output.schema.json
      implementer-handoff.schema.json
    adversarial/
      skeleton-manifest.md
```

Config / frontmatter fields needed:

- `.github/agents/design-planning-architect.agent.md` → `hooks:` field (preview, requires `chat.useCustomAgentHooks: true`)

  ```yaml
  hooks:
    PreToolUse:
      - type: command
        command: "node .github/hooks/design-architect-pre-tool.cjs"
    PostToolUse:
      - type: command
        command: "node .github/hooks/design-architect-post-tool.cjs"
  ```

- `solar.config.json` → `hooks.preToolUse.requireDesignBeforeImpl: boolean` — flag to block impl agents when no approved design artifact exists in ledger
- VS Code settings → `chat.useCustomAgentHooks: true` — required to activate `hooks:` frontmatter on individual agents

[ASSUMPTION: VS Code `.agent.md` does not natively validate output against JSON schema — compliance is enforced via instruction text and adversarial review, not constrained decoding.]

Isolation: **SOLAR-only**

---

## Section 3: Project-Agnostic Pipeline Cores and Dynamic Injection

### Feasibility

- Proven technique? **YES** — Context-as-compiled-view, tiered memory (Working Context / Session / Memory / Artifacts), and cognitive agnosticism are well-established patterns documented in Google ADK production guidance (ref 10) and context engineering literature (refs 13, 26, 27).
- Achievable in VS Code Copilot agents? **PARTIALLY** — The three-tier context separation (instructions, ledger, docs) already maps loosely to the ADK model. Dynamic model swapping is limited to the `model:` field in `.agent.md` front matter. Full artifact handle patterns (JIT loading of large files by reference) require workarounds since VS Code agents cannot manage their own file handles natively. Business-as-Code entity schema injection is achievable via `.instructions.md` `applyTo` glob patterns. **NEW (verified 2026-04-04):** Session memory (`/memories/session/`) is now a platform-native Memory tier primitive. `PreCompact` hook fires before context compaction events, enabling governor-mediated state export before truncation.
- Limitations:
  - No native "Artifact" tier with lazy-loading handles; agents must read full file contents via `read_file` tool
  - Model swapping (OpenAI → Gemini → Anthropic) is constrained to what VS Code Copilot exposes in `model:` field — not all providers are available simultaneously
  - "Cognitive Agnosticism" is achievable in principle but limited by provider availability in the Copilot extension

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/instructions/*.instructions.md` with `applyTo` patterns — approximate "Working Context" injection per file scope
  - `.github/.ai_ledger.md` — approximate "Session" layer (durable interaction log for restart safety)
  - `.github/AGENTS.md` + `solar.config.json` — pipeline core separated from project specifics (project-agnostic structure is the template's design goal)
  - `.github/agents/*.agent.md` with `model:` field — partial cognitive agnosticism
  - `scripts/install-solar.ps1`, `install-solar.sh` — three-repository deployment model (agent-library = this repo, agent-setup = install scripts, resource-catalog = target project)
  - **NEW (verified 2026-04-04):** `/memories/session/` — built-in session-scoped Memory tier; platform primitive for state that survives turn boundaries within a conversation but is cleared between conversations
  - **NEW (verified 2026-04-04):** `PreCompact` hook event — fires before context compaction with `trigger: "auto"`; SOLAR can hook this to export ledger hot-state to `/memories/session/` before truncation
- Gap:
  - No formal four-tier context classification (Working Context / Session / Memory / Artifacts) documented as a SOLAR concept — now updated: Memory tier = `/memories/session/` (session-scoped) + `memory` tool (cross-session)
  - No artifact handle pattern — no guidance on when to pass a file path reference vs. load full content
  - No JIT context loading strategy defined in any `.instructions.md` or guide
  - No governor-mediated proactive compaction policy — `PreCompact` hook enables reactive export before truncation but a threshold-based proactive trigger (compact before hitting the limit) must still be defined as a governor instruction
  - No explicit policy for which state goes to `/memories/session/` vs `.ai_ledger.md` vs `solar-system/` learnings files

### Implementation Skeleton

Files to create or modify:

- `.github/solar-system/context/context-tiers.md` — defines the four-tier mapping: Working Context (which instructions are injected), Session (ledger), Memory (Copilot memory tool), Artifacts (file path handles)
- `.github/solar-system/context/artifact-handle-pattern.md` — rules for when to pass a file path reference vs. load full content into context
- `.github/instructions/solar.instructions.md` — add "Context Management" section: agent guidance on tier assignment and compaction triggers
- `.github/solar-system/context/compaction-policy.md` — defines ledger compaction trigger threshold (e.g., ledger exceeds N tasks or N lines → summarize completed tasks)

Folder changes (if any):

```
.github/
  solar-system/
    context/
      context-tiers.md
      artifact-handle-pattern.md
      compaction-policy.md
```

Config / frontmatter fields needed:

- `solar.config.json` → `context.ledgerCompactionThreshold: number` — line count at which completed ledger tasks are summarized
- `solar.config.json` → `context.artifactHandleEnabled: boolean` — flag to instruct agents to prefer path references over full content for files above a size threshold
- `solar.config.json` → `context.artifactSizeThresholdLines: number` — line count above which files should be handled by reference
- `.github/hooks/hooks.json` → add `PreCompact` hook entry:

  ```json
  {
    "hooks": {
      "PreCompact": [
        {
          "type": "command",
          "command": "node .github/hooks/pre-compact.cjs",
          "windows": "node .github/hooks/pre-compact.cjs"
        }
      ]
    }
  }
  ```

  Script reads active ledger stage and in-progress todos, writes snapshot to `/memories/session/pre-compact-state.md`, returns common output `{ "continue": true, "systemMessage": "Context state saved before compaction" }`. Note: `PreCompact` uses common output only — no `hookSpecificOutput`.

[ASSUMPTION: VS Code Copilot does not expose an SDK-level compaction API; `PreCompact` detects when compaction is imminent but not a user-configurable threshold. Governor-mediated proactive compaction (ledger line count) must be a separate instruction-level policy.]

Isolation: **SOLAR-only**

---

## Section 4: Isolated Self-Improvement in .github/solar-system/

### Feasibility

- Proven technique? **YES** — The "Ralph Wiggum" self-improvement loop pattern (ref 28, 29), filesystem-as-memory (refs 31, 32), and hook-driven learning capture are demonstrated in Claude Code and vibe-better-with-claude-code projects.
- Achievable in VS Code Copilot agents? **YES** — The `.github/solar-system/` directory separation, learning markdown files, and hook-based activators are all achievable. **NEW (verified 2026-04-04):** SOLAR's `.cjs` hooks use Copilot CLI format, which VS Code parses natively — format compatibility is confirmed. `SessionStart` hook now exists as a native activator equivalent that injects LEARNINGS.md content at the start of each session via `additionalContext`. Agent-scoped `hooks:` in `.agent.md` also enable per-agent learning behavior.
- Limitations:
  - No native scheduled/periodic hook — Compound Review must be triggered manually or via a `/solar-*` prompt command (no timer-based or periodic hook event exists)
  - "Stateless but iterative" loop requires the ledger + `memory` tool + `/memories/session/` to persist state across turns; true statefulness is simulated
  - Git diff automation for learning extraction requires `run_in_terminal` tool calls from the governor, not an autonomous background process

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/hooks/pre-tool-use.cjs` — partial bash-guard: blocks certain agent delegation patterns; equivalent to `bash-guard.sh` concept
  - `.github/hooks/post-tool-use.cjs` — write-gate / error detector: fires on every file write operation
  - `.github/hooks/user-prompt-submit.cjs` — activator equivalent: fires on every user prompt, checks ledger state
  - `.github/hooks/stop.cjs` — loop continuation enforcement: blocks premature exit
  - `.github/hooks/hooks.json` — hook registration and mode configuration
  - `solar.config.json` → `modes.bootstrap` — isolated mode for setup/recovery operations
- Gap:
  - No `.github/solar-system/` directory exists — the concept of an isolated self-improvement subdirectory is entirely absent
  - No `.learnings/ERRORS.md` — no persistent error log for agent-observed failures
  - No `LEARNINGS.md` — no persistent learning extraction file
  - No `FEATURE_REQUESTS.md` — no mechanism to capture improvement ideas during execution
  - No Compound Review process or triggering prompt
  - No explicit instruction for the governor to write back verified facts as learnings (the Write-Back Rule in `AGENTS.md` is close but targets `*.instructions.md`, not a learnings file)

### Implementation Skeleton

Files to create or modify:

- `.github/solar-system/.learnings/ERRORS.md` — persistent log of agent-observed errors and their corrections
- `.github/solar-system/.learnings/LEARNINGS.md` — positive learnings: conventions confirmed, non-obvious solutions, project gotchas
- `.github/solar-system/.learnings/FEATURE_REQUESTS.md` — improvement ideas captured during task execution
- `.github/solar-system/README.md` — explains the solar-system isolation boundary and what belongs here vs. `.github/`
- `.github/hooks/session-start.cjs` — NEW: reads `.github/solar-system/.learnings/LEARNINGS.md`; outputs `{ "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "<condensed LEARNINGS.md summary>" } }`
- `.github/hooks/hooks.json` — add `SessionStart` and `PreCompact` hook entries:

  ```json
  {
    "hooks": {
      "SessionStart": [
        { "type": "command", "command": "node .github/hooks/session-start.cjs" }
      ],
      "PreCompact": [
        { "type": "command", "command": "node .github/hooks/pre-compact.cjs" }
      ]
    }
  }
  ```

- `.github/hooks/user-prompt-submit.cjs` — modify: remove learning-reminder injection (superseded by `SessionStart` hook; retain only ledger-state checks)
- `.github/hooks/post-tool-use.cjs` — modify: on tool failure detection, surface ERRORS.md write instruction to agent
- `.github/prompts/solar-compound-review.prompt.md` — new: Compound Review trigger prompt that instructs governor to extract patterns from recent ledger tasks and update AGENTS.md and LEARNINGS.md
- `.github/instructions/solar.instructions.md` — add: self-improvement write-back rules (when to write to ERRORS.md vs LEARNINGS.md vs FEATURE_REQUESTS.md)

Folder changes (if any):

```
.github/
  solar-system/
    README.md
    .learnings/
      ERRORS.md
      LEARNINGS.md
      FEATURE_REQUESTS.md
```

Config / frontmatter fields needed:

- `solar.config.json` → `selfImprovement.enabled: boolean` — global toggle for learning write-back behavior
- `solar.config.json` → `selfImprovement.learningsPath: string` — path to solar-system learnings directory (default: `.github/solar-system/.learnings/`)
- `solar.config.json` → `hooks.sessionStart.injectLearnings: boolean` — whether `session-start.cjs` reads and injects LEARNINGS.md summary
- `solar.config.json` → `hooks.postToolUse.logErrorsToLearnings: boolean` — whether post-tool-use hook surfaces ERRORS.md write instruction on failure
- VS Code settings → `chat.useCustomAgentHooks: true` — enables `hooks:` frontmatter in individual `.agent.md` files (preview feature)

[ASSUMPTION: VS Code Copilot hooks cannot read git diffs automatically; diff-based learning extraction must be explicitly requested by the governor via terminal tool calls, not triggered automatically.]

Isolation: **SOLAR-only** — solar-system directory must never be referenced in project-facing instructions or agent delegation for non-SOLAR tasks

---

## Section 5: Interleaved Thinking and Context Compaction Strategies

### Feasibility

- Proven technique? **YES** — Interleaved thinking (alternating reasoning and tool calls) is natively demonstrated in Claude models at the platform level (refs 9, 33, 34). Context compaction via summarization is documented in Anthropic production guidance (ref 35, 39). JIT context offloading is a practical context engineering pattern (refs 26, 38).
- Achievable in VS Code Copilot agents? **PARTIALLY** — Interleaved thinking happens implicitly in Claude Sonnet/Haiku models when `extended thinking` mode is enabled; VS Code Copilot does not expose a direct `thinking_budget_tokens` parameter to agent authors. Effort control (low/medium/high/max) is not a VS Code Copilot API surface — it is an Anthropic API parameter not currently exposed in `.agent.md` front matter. Context compaction via governor-triggered summarization is achievable as a manual pattern. JIT offloading (save large content to file, pass handle) is achievable via explicit governor instructions. **NEW (verified 2026-04-04):** `PreCompact` hook fires BEFORE context auto-compaction with `trigger: "auto"` flag — governor can intercept this event to export critical ledger state to `/memories/session/` before truncation occurs.
- Limitations:
  - No `effort:` or `thinking_budget:` field in VS Code `.agent.md` front matter — effort control must be simulated via instruction text ("think carefully" vs "be concise")
  - Offloading to disk and re-loading JIT works but requires governor to explicitly manage which files are "offloaded" and which are "active"

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/hooks/stop.cjs` — loop continuation enforcement provides some protection against premature context loss
  - `.github/.ai_ledger.md` — serves as a compressed session state (restart-safe but not auto-compacted)
  - `solar.config.json` → `modes.loop` — loop mode with enforced continuation; conceptually related to effort-high behavior
  - Recursive Remediation skill (`.github/skills/recursive-remediation/SKILL.md`) — bounded repair loops that reduce context waste from open-ended retries
- Gap:
  - No effort control mechanism or simulation (no `effort:` field, no instruction-level effort modulation documented in any `.instructions.md`)
  - No defined ledger compaction threshold or compaction trigger in any hook or config
  - No JIT artifact loading pattern documented anywhere in SOLAR guides
  - No Compound Thinking pattern (passing reasoning trace forward across tool calls) documented in agent instructions

### Implementation Skeleton

Files to create or modify:

- `.github/solar-system/context/compaction-policy.md` — (overlaps Section 3 gap) compaction trigger rules: ledger line threshold, completed-task pruning policy, summary format for pruned tasks
- `.github/solar-system/context/effort-simulation.md` — documents how to simulate effort levels via instruction text since no API surface exists: Low = "brief answer only", Medium = default, High = "think through all failure modes", Max = "exhaustive analysis before acting"
- `.github/solar-system/context/jit-loading-guide.md` — rules for when governor should instruct agents to pass file path instead of loading content: threshold in lines, categories always-loaded vs always-referenced
- `.github/instructions/solar.instructions.md` — add: context management block with compaction trigger rule and JIT loading guidance
- `.github/agents/orchestration-governor.agent.md` — add: ledger compaction instruction triggered when ledger task count exceeds configured threshold
- `.github/hooks/hooks.json` — add `PreCompact` hook entry: script reads active in-progress todos and ledger stage, writes to `/memories/session/pre-compact-state.md` before VS Code truncates context

Folder changes (if any):

```
.github/
  solar-system/
    context/
      compaction-policy.md      ← defined in Section 3, extended here
      effort-simulation.md      ← NEW
      jit-loading-guide.md      ← NEW
```

Config / frontmatter fields needed:

- `solar.config.json` → `context.ledgerCompactionThreshold: number` — (same field from Section 3; confirm reuse)
- `solar.config.json` → `context.effort.default: "low"|"medium"|"high"|"max"` — default effort simulation level for agents without an explicit override
- `solar.config.json` → `context.effort.loopMode: "high"|"max"` — effort level applied when Session-Type is `loop`
- `.github/agents/*.agent.md` → `effort: low|medium|high|max` — per-agent effort hint field (instruction-level only, not API-enforced)
- `.github/hooks/hooks.json` → `PreCompact` hook entry (shared with Section 3 and 4; single script):

  ```json
  {
    "hooks": {
      "PreCompact": [
        {
          "type": "command",
          "command": "node .github/hooks/pre-compact.cjs"
        }
      ]
    }
  }
  ```

  `.github/hooks/pre-compact.cjs` reads active in-progress todos and current ledger pipeline stage; writes to `/memories/session/pre-compact-state.md`; returns `{ "continue": true }`. `PreCompact` uses common output format only — no `hookSpecificOutput`.

[ASSUMPTION: VS Code cannot expose token count to hook scripts — compaction threshold must be measured in ledger line count or task count as a proxy.]
[ASSUMPTION: Extended thinking activates automatically for Claude models; no `.agent.md` configuration is available to agent authors in VS Code.]

Isolation: **SOLAR-only**

---

## Section 6: "Inquiry-First" Protocol for Software Engineering Agents

### Feasibility

- Proven technique? **YES** — Inquiry-First as a pre-implementation research-and-clarify step is validated in Cursor agent best practices (ref 11), scientific inquiry transfer research (ref 40), and OPTIMAL INQUIRY framework (ref 41). The DevEx / psychological safety dimension is documented in human factors research (ref 42).
- Achievable in VS Code Copilot agents? **YES** — This is entirely achievable as an instruction-level and prompt-level pattern. The four-step protocol (codebase research → clarifying questions → implementation plan → iterative refinement) maps directly to existing SOLAR agent instructions and pipeline stage sequencing. **NEW (verified 2026-04-04):** Watch Mode for critical actions is now more robust: `PreToolUse` hook natively returns `permissionDecision: "ask"` to require user confirmation before any tool executes — no `vscode_askQuestions` agent tool call needed; this is deterministic hook-enforced confirmation.
- Limitations:
  - Iterative refinement ("revert and re-plan") requires the agent to call `git revert` or manually undo edits; VS Code does not provide a transactional undo API to agents
  - Clarifying question loops can be gamed by agents that treat a single superficial question as sufficient "inquiry" — the protocol needs explicit minimum criteria for what constitutes sufficient inquiry

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/AGENTS.md` — Pipeline 4 (Feature) includes Design Planning Architect stage before implementation starts
  - `.github/agents/design-planning-architect.agent.md` — explicitly models the inquiry and planning phase
  - `.github/instructions/solar.instructions.md` — "Review → Plan → Implement" workflow sequence
  - Story-Level Development Workflow in `copilot-instructions.md` — documents the full "Review Requirements → Plan → Implement → Test" sequence
  - `.github/skills/story-execution/SKILL.md` — wraps the full story delivery workflow including planning phase
  - Recursive Remediation skill — closest equivalent to "iterative refinement" bounded repair
- Gap:
  - No formal "Inquiry Gate" hook — no mechanism that blocks an implementation agent from running until a minimum inquiry checklist is satisfied in the ledger
  - No documented minimum inquiry criteria (how many questions must be asked? what signal counts as "requirement grounded"?)
  - No "revert-and-replan" instruction in any agent definition — agents currently patch forward rather than reverting on plan mismatch
  - No integration of the four-step inquiry protocol as a ledger-checkable pre-condition

### Implementation Skeleton

Files to create or modify:

- `.github/hooks/pre-tool-use.cjs` — modify: add Watch Mode gate for high-risk tool calls (destructive file operations, bulk rewrites, schema changes); return the following output to trigger a native VS Code confirmation dialog:

  ```json
  {
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "ask",
      "permissionDecisionReason": "High-risk operation in loop mode requires user confirmation"
    }
  }
  ```

  Priority: when multiple `PreToolUse` hooks run, `deny` > `ask` > `allow`. Use `ask` (not `deny`) for Watch Mode to allow user override.

- `.github/solar-system/protocols/inquiry-first.md` — defines minimum inquiry criteria: codebase research step (N files examined), clarifying questions checklist (ambiguous AC resolved), plan approval (ledger entry present), revert-not-patch rule
- `.github/instructions/solar.instructions.md` — add: Inquiry Gate section referencing `inquiry-first.md` criteria; add revert-and-replan rule
- `.github/agents/design-planning-architect.agent.md` — add: explicit inquiry checklist output format (must document files examined, ambiguities resolved, questions asked) before plan is produced
- `.github/.ai_ledger.template.md` — add: Inquiry Gate section to ledger template (files examined, questions resolved, plan approved flag)

Folder changes (if any):

```
.github/
  solar-system/
    protocols/
      inquiry-first.md
```

Config / frontmatter fields needed:

- `solar.config.json` → `hooks.preToolUse.watchModeEnabled: boolean` — enables Watch Mode confirmation gate for high-risk tools
- `solar.config.json` → `hooks.preToolUse.watchModeToolPatterns: string[]` — list of tool name patterns that trigger watch mode (e.g., `["delete", "bulk_replace", "migrate"]`)
- `solar.config.json` → `inquiry.minimumFilesExamined: number` — minimum codebase research depth before plan is accepted
- `.github/.ai_ledger.md` → `Inquiry Gate: [ ] Files examined | [ ] Ambiguities resolved | [ ] Plan approved` — ledger field (template addition, not config)

Isolation: **SOLAR-only**

---

## Section 7: Technical Implementation of Handoffs and Lifecycle Coordination

### Feasibility

- Proven technique? **YES** — Typed JSON handoffs, phase gating, and session resumption patterns are documented in production multi-agent systems (ref 31). Git worktree isolation for parallel agents is a real Git feature. Shutdown protocols with typed acknowledgment messages are established in distributed system design.
- Achievable in VS Code Copilot agents? **PARTIALLY** — Typed JSON handoff schemas are achievable as instruction-enforced output contracts (not constrained decoding). Phase gating via ledger stage tracking is already partially implemented. **NEW (verified 2026-04-04):** Parallel subagent execution IS officially supported (multi-perspective review pattern); filesystem isolation is still not available without explicit git worktrees. Native `handoffs:` frontmatter in `.agent.md` provides structured sequential workflow transitions. `SubagentStop` hook can block a subagent from stopping until results are verified; `Stop` hook controls main session lifecycle. `SubagentStart` hook injects `additionalContext` into subagent conversations at delegation time.
- Limitations:
  - Filesystem-isolated parallel execution (git worktrees with separate context windows) is not achievable natively — parallel subagents share the same filesystem; write conflicts are possible when two subagents edit the same paths
  - Git worktree isolation requires terminal commands and explicit governor coordination; no native worktree management API for agents
  - No typed request/acknowledgment RPC for shutdown — `SubagentStop` hook provides supervised lifecycle termination (block until verified) and `Stop` hook fires on session end, but neither is a formal typed acknowledgment protocol
  - Session Resumption requires the governor to explicitly re-read planning files and ledger on loop restart; covered by the ledger + `/memories/session/` pattern but not yet enforced by any hook
  - Typed handoff schema validation is instruction-enforced only (see Section 2 constraint on constrained decoding)

### SOLAR v3.2 Coverage

- Already exists:
  - `.github/.ai_ledger.md` — phase tracking via `Pipeline Stage:` field; restart-safe session state
  - `.github/AGENTS.md` — Pipeline Contracts define stage sequencing and completion criteria (phase gating)
  - `.github/hooks/stop.cjs` — lifecycle enforcement: blocks premature exit during loop mode
  - `.github/hooks/pre-tool-use.cjs` — agent delegation gating; partial typed-agent-call enforcement
  - `.github/agents/orchestration-governor.agent.md` — owns lifecycle coordination; delegates and tracks stage completion
  - `.github/.ai_ledger.template.md` — restart-safe template covering session resumption requirements
  - **NEW (verified 2026-04-04):** `SubagentStart` hook — fires before a subagent starts; can inject `additionalContext` as a typed handoff mechanism at the delegation point
  - **NEW (verified 2026-04-04):** `SubagentStop` hook — can block a subagent from stopping until governor verifies output; provides supervised lifecycle termination
  - **NEW (verified 2026-04-04):** Native `handoffs:` frontmatter in `.agent.md` — structured sequential workflow transitions with auto-populated prompts and optional auto-submit (`send: true`)
- Gap:
  - No typed handoff schema definitions — all agent handoffs are free-form markdown or verbal descriptions in ledger
  - No JSON-structured send/receive pattern (no `scout_findings`, `dev_progress`, `qa_result` typed payloads)
  - No worktree isolation guidance or script — parallel subagents risk filesystem write conflicts when operating on shared paths; isolation requires explicit `git worktree add` terminal commands
  - No "team coordination" meta-pattern for running multiple specialists in parallel with typed status reporting
  - `SubagentStart` and `SubagentStop` hooks not yet registered in `.github/hooks/hooks.json` — supervised lifecycle termination and context injection at delegation point are available but not wired up
  - No governor checkpoint write protocol for `/memories/session/` — session resumption lacks a consistent checkpoint trigger across pipeline stage boundaries

### Implementation Skeleton

Files to create or modify:

- `.github/solar-system/schemas/handoff-types.md` — catalog of typed handoff payload schemas: `scout_findings`, `dev_progress`, `review_result`, `qa_result`, `security_finding`, defined as JSON object shapes
- `.github/solar-system/schemas/` — add individual per-type schema files for each handoff type
- `.github/solar-system/protocols/lifecycle-coordination.md` — documents phase gating rules, parallel and sequential team coordination patterns, `SubagentStart`/`SubagentStop` hook usage policy, and ledger stage advancement criteria
- `.github/solar-system/protocols/session-resumption.md` — defines session resumption protocol: which files to read on loop restart, in what order, and what constitutes a "clean restart" vs "mid-task resumption"; references `/memories/session/checkpoint.md`
- `.github/.ai_ledger.template.md` — add: `Handoff Payload:` section for structured inter-agent state passing; add `Active Sub-tasks:` section for simulated team coordination tracking
- `.github/agents/orchestration-governor.agent.md` — add: handoff payload read/write instruction for each pipeline stage transition; add `agents:` list restricting which specialists governor can delegate to in each pipeline
- `.github/agents/*.agent.md` — add `handoffs:` frontmatter to specialists with common next-step transitions (e.g., Implementation → Review, Backend Implementation → Backend Test)
- `.github/instructions/solar.instructions.md` — add: handoff schema reference (link to `handoff-types.md`) and team coordination guidance (when to run parallel vs. sequential specialists)
- `.github/hooks/hooks.json` — add `SubagentStart` and `SubagentStop` hook entries:

  ```json
  {
    "hooks": {
      "SubagentStart": [
        {
          "type": "command",
          "command": "node .github/hooks/subagent-start.cjs"
        }
      ],
      "SubagentStop": [
        {
          "type": "command",
          "command": "node .github/hooks/subagent-stop.cjs"
        }
      ]
    }
  }
  ```

  `subagent-start.cjs` — reads ledger `Handoff Payload:` field; outputs `{ "hookSpecificOutput": { "hookEventName": "SubagentStart", "additionalContext": "<typed context JSON>" } }`.

  `subagent-stop.cjs` — validates minimum output fields present in subagent response; returns `{ "decision": "block", "reason": "Output missing required fields" }` if validation fails. Note: `SubagentStop` output is top-level (not `hookSpecificOutput`); check `stop_hook_active` input field to prevent infinite loops.

Folder changes (if any):

```
.github/
  solar-system/
    schemas/
      handoff-types.md
      scout-findings.schema.json
      dev-progress.schema.json
      review-result.schema.json
      qa-result.schema.json
    protocols/
      lifecycle-coordination.md
      session-resumption.md
```

Config / frontmatter fields needed:

- `solar.config.json` → `handoffs.typedPayloadsEnabled: boolean` — flag to enforce typed handoff format between pipeline stages
- `solar.config.json` → `handoffs.schemasPath: string` — path to handoff schemas directory
- `solar.config.json` → `lifecycle.resumptionFilesReadOrder: string[]` — ordered list of files governor reads on loop session restart (e.g., `[".ai_ledger.md", "AGENTS.md", "solar.instructions.md", "/memories/session/checkpoint.md"]`)
- `.github/agents/orchestration-governor.agent.md` → `agents: [list]` — explicit subagent roster governor can delegate to; restricts unintended parallel delegation targets
- `.github/agents/*.agent.md` → `handoffs: [{ label, agent, prompt, send }]` — native sequential transitions to next-step specialists
- `.github/hooks/hooks.json` → add `SubagentStart` hook (inject typed context JSON at delegation point) and `SubagentStop` hook (validate minimum output fields before subagent stops)

[ASSUMPTION: True parallel agent execution is achievable for independent tasks, but filesystem-isolated parallel execution (git worktrees with separate context windows) still requires explicit `git worktree add` terminal commands and governor-managed coordination.]
[ASSUMPTION: Worktree isolation is deferred unless a specific story requires it; default parallel pattern uses concurrently-running subagents on independent paths.]

Isolation: **SOLAR-only**

---

## Open Decisions

- **Lightweight Orchestration (S1)** → Router pipeline: should the governor use a static routing table in `AGENTS.md` or a dynamic instruction-based routing decision? → **Option A**: static table (explicit signal-to-agent mappings in `AGENTS.md`) vs **Option B**: governor reasons dynamically each turn → **Recommended: Option A** — deterministic, auditable, lower risk of routing drift

- **Designer-Implementer Firewalls (S2)** → Output contract enforcement: instruction-text compliance vs. adversarial review gate after every design output? → **Option A**: Design Planning Architect output is trusted if it follows schema instructions (review only on escalation) vs **Option B**: Security Auditor reviews every designer output before implementation begins → **Recommended: Option A** — Option B adds latency on every pipeline; route to Security Auditor only when schema validation fails or security-sensitive changes detected

- **Designer-Implementer Firewalls (S2)** → Adversarial skeleton manifest scope: build a full 24-pattern vulnerability catalog or a minimal 5–8 pattern prompt-injection / persona-hijacking checklist? → **Option A**: full 24-pattern catalog (high effort, research-grade) vs **Option B**: minimal 5–8 pattern checklist (pragmatic, maintainable) → **Recommended: Option B** — catalog depth not justified for VS Code Copilot surface; revisit if prompt injection incidents are observed

- **Project-Agnostic Pipeline Cores (S3)** → Ledger compaction proxy metric: line count vs. completed-task count? → **Option A**: trigger compaction at N lines in `.ai_ledger.md` vs **Option B**: trigger at N completed tasks in the ledger → **Recommended: Option B** — task count is more semantically meaningful and less dependent on formatting verbosity

- **Interleaved Thinking (S5)** → Effort simulation: encode effort level as explicit instruction text in each `.agent.md` or add a global `effort:` front matter field that the governor interprets? → **Option A**: explicit instruction text per agent (e.g., "think through all failure modes before acting") vs **Option B**: `effort:` front matter field that governor maps to a preamble injected before delegation → **Recommended: Option B** — centralizes effort tuning without editing every agent file; governor injects appropriate preamble per effort level at delegation time

- **Inquiry-First Protocol (S6)** → Watch Mode scope: apply to all destructive tool calls globally or only in loop mode? → **Option A**: Watch Mode fires globally on any destructive pattern regardless of session type vs **Option B**: Watch Mode fires only when `Session-Type: loop` is active → **Recommended: Option B** — avoids friction in chat/planning mode while protecting autonomous loop execution

- **Technical Handoffs (S7)** → Parallel worktree isolation: implement via governor-managed `git worktree` terminal commands or defer to future version? → **Option A**: implement worktree creation/teardown as governor terminal-command sequences for parallel sub-tasks vs **Option B**: defer worktree isolation; use native parallel subagents (now supported) with ledger-based sub-task tracking for coordination → **Recommended: Option B** — worktree management adds significant governor complexity; parallel subagent execution is now achievable without filesystem isolation for most cases (independent paths); filesystem isolation only needed for risk-heavy concurrent file mutations, which is rare in SOLAR pipelines

---

## Implementation Order

Ranked by dependency, risk, and incremental value:

1. **Section 4 — Isolated Self-Improvement** (`.github/solar-system/` structure + `.learnings/` files + hook modifications)
   - Dependency: none; establishes the foundation directory used by all subsequent sections
   - Risk: low — additive only, no existing file modification except hooks
   - Value: immediately captures agent errors and learnings; closes the largest behavioral gap

2. **Section 6 — Inquiry-First Protocol** (Watch Mode hook + ledger inquiry gate + `protocols/inquiry-first.md`)
   - Dependency: needs `.github/solar-system/` from S4
   - Risk: medium — modifies `pre-tool-use.cjs`; must not break existing bypass list logic
   - Value: prevents premature implementation; highest impact on correctness per work package

3. **Section 2 — Designer-Implementer Firewalls** (schema definitions + design architect output contract)
   - Dependency: needs `.github/solar-system/schemas/` from S4
   - Risk: medium — adds constraints to existing architect agent; must validate existing pipelines still function
   - Value: formalizes the Designer/Implementer split already implied by v3.2 agent roles

4. **Section 7 — Handoffs and Lifecycle Coordination** (typed handoff schemas + session resumption protocol)
   - Dependency: needs schemas directory from S2/S4; needs ledger template fields
   - Risk: medium — ledger template changes affect all future work packages
   - Value: eliminates free-form handoff ambiguity; improves restart reliability

5. **Section 1 — Lightweight Orchestration** (Router pipeline entry + governor skip logic)
   - Dependency: none; modifies `AGENTS.md` and governor agent
   - Risk: low — additive pipeline entry; existing pipelines unchanged
   - Value: reduces overhead for simple single-agent tasks; improves daily usability

6. **Section 3 — Project-Agnostic Pipeline Cores** (context tier documentation + artifact handle pattern + compaction policy)
   - Dependency: needs `.github/solar-system/context/` from S4
   - Risk: low — documentation only; no hook or agent file modifications
   - Value: establishes the conceptual foundation for context discipline across all agents

7. **Section 5 — Interleaved Thinking and Context Compaction** (effort simulation field + compaction policy refinement + JIT loading guide)
   - Dependency: depends on context tier model from S3; depends on compaction policy from S3
   - Risk: low — config fields and documentation; effort simulation via front matter is additive
   - Value: improves token cost efficiency in long loop sessions; lower priority until loop sessions routinely hit context limits

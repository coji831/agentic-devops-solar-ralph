## Research Priorities: Complex Problems First

### List 1: High Complexity / Unclear Solution (Research Needed)

**Architecture & System Design:**

1. **Workflow Architecture Migration**: Replace numbered pipelines (0-4) with composable workflows; preserve Router logic; design workflow metadata schema (loop flag, stages, composition rules); extract notification pattern into reusable template

2. **Agent Tier Enforcement Model**: Define strict delegation order (Orchestrator → Collector → Planner → Implementor → Reviewer); specify tool restrictions per tier (e.g., Implementor banned from semantic_search, Planner banned from file writes); prevent smart-skip patterns that bypass tiers; balance tier strictness vs handoff friction

3. **Orchestrator Delegation Limits**: Decide minimum tool set (read ledger, delegate only?) vs hybrid approach (allow 3-file reads for classification); create Data Collector agent responsibilities; design decision tree for collector-first vs direct-to-implementor routing; resolve tension between Router intelligence needs and context efficiency

4. **Loop Invocation Trigger Design**: Define elevation mechanism (user command `/ralph-loop`? workflow metadata `loop: true`? governor auto-detect?); design ledger schema for loop state (iteration count, exit condition, timeout, active loops section); create exit criteria ruleset (max iterations, success checkboxes, user interrupt, stuck detection)

5. **Memory Storage Enforcement**: Technically disable repo writes (Copilot platform limitation?); audit all agent.md files to remove repo references; enforce .learnings as exclusive destination; resolve portability vs convenience trade-off; investigate if platform enforcement possible

6. **Work Breakdown Agent Design**: Create structured task decomposition output format (JSON schema? ledger template?); define task state transitions (PENDING → IN_PROGRESS → REVIEW → APPROVED → COMPLETE); integrate approval gates; decide when governor delegates to Work Breakdown vs directly to planner

7. **Context Compaction Workaround**: Design polling-based alternative since `pre-compact` hook blocked by VS Code platform; implement conditional compaction (check for pending user input before triggering); preserve user turn signals; create ledger checkpoint mechanism for seamless resume

8. **Subagent Loop Communication Pattern**: Define how subagent steering works in loop mode (ledger read-only? handoff template updates? progress signals?); clarify orchestrator resume logic after subagent completes; design backward escalation when subagent uncertain

9. **Model Inheritance Verification**: Investigate if subagent inherits invoker's model or uses own frontmatter model; test high-reasoning task invoked by low-tier agent; document behavior; create workaround if inheritance confirmed (orchestrator invokes high-tier directly)

---

### List 2: Low Complexity / Clear Solution (Implementation Ready)

**Quick Wins:**

10. **Inquiry Gate Activation**: Debug why pre-tool-use.cjs doesn't enforce gate; verify hook fires during agent delegation; add `## Inquiry Gate` section to ledger template; add governor enforcement rule (block delegation if checkboxes unchecked); test with deliberate bypass attempt

11. **Learning Capture Debug**: Add debug logging to session-start.cjs, `user-prompt-submit.cjs`, post-tool-use.cjs; verify hooks fire on session start, prompt submit, tool failure; check file permissions on `.learnings/` folder; test write with manual trigger; identify silent failure point

12. **Session Logging Debug**: Add debug logging to session-start.cjs session log creation; verify `logs/` directory exists and writable; test `.current-session` file creation; verify post-tool-use.cjs appends events; check if `stop.cjs` writes SESSION_END; test with manual session flow

13. **Template Merge Installer**: Replace `mv` or `rename` commands with read→interpolate→write logic; detect `[FILL IN]` placeholders; prompt user for values; write resolved content to destination; add post-install verification step

14. **Hook Execution Logging**: Add entry/exit logs to all 8 hooks; log tool names, file paths, outcomes; write to `.github/solar-system/logs/<hook-name>.log`; implement daily log rotation (keep last 7 days)

15. **Documentation Review Agent**: Create `documentation-review-specialist.agent.md`; define validation checklist (template compliance, cross-link integrity, tech stack accuracy, AC clarity); add to governor's `agents:` allowlist; update Frontend/Backend Review auditors to delegate doc review

16. **Output Verbosity Reduction**: Add to all agent instructions: "Output format: concise, no explanations unless requested"; use Haiku for fast agents (implementor, collector); define structured output templates (handoff schemas); remove unnecessary introductions/conclusions

17. **Terminal Cleanup Fix**: Update `stop.cjs` to track spawned terminal PIDs in ledger; kill all tracked terminals on session end; add 5-second graceful shutdown, then force-kill; clear PID list after cleanup

18. **Ledger Format Validation**: Add schema validation hook before ledger writes; define session type enum (KNOWLEDGE, SIMPLE_FIX, BUG_FIX, FEATURE); validate against enum; implement ledger reset protocol (clear active sections, preserve history in archive)

19. **askQuestion Integration**: Add pre-flight workflow confirmation when ambiguous; implement gap detection prompt ("This task requires X. Add workflow or adjust scope?"); use `vscode_askQuestions` tool for user input collection

20. **Infinite Loop Prevention**: Add iteration counter to loop tracking; define max iterations config (default: 10); add timeout config (default: 2 hours); implement stuck detection (same error 3x = escalate); surface exit conditions to user

---

## Suggested Execution Order

**Phase 1 (Trust & Observability — Unblock Debugging):**

- #11 Learning Capture Debug
- #12 Session Logging Debug
- #14 Hook Execution Logging
- #10 Inquiry Gate Activation

**Phase 2 (Agent Architecture — Foundation):**

- #2 Agent Tier Enforcement Model
- #3 Orchestrator Delegation Limits
- #6 Work Breakdown Agent Design
- #15 Documentation Review Agent

**Phase 3 (Loop & State Management):**

- #4 Loop Invocation Trigger Design
- #5 Memory Storage Enforcement
- #20 Infinite Loop Prevention
- #18 Ledger Format Validation

**Phase 4 (Polish & Optimization):**

- #16 Output Verbosity Reduction
- #7 Context Compaction Workaround
- #17 Terminal Cleanup Fix
- #13 Template Merge Installer

**Phase 5 (Major Architecture — v6 Candidate):**

- #1 Workflow Architecture Migration (defer to v6)

**Ongoing Investigation:**

- #8 Subagent Loop Communication Pattern
- #9 Model Inheritance Verification

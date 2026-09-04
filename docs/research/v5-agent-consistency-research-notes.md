# SOLAR V5: Agent Consistency — Research Notes

**Date:** 2026-07-24
**Status:** ✅ Deeper research complete — see `v5-agent-consistency-deep-dive.md` (2026-08-16)
**Verification:** ✅ All references verified via web search (arXiv, Anthropic, OpenAI, Guardrails AI, CrewAI). 7 new 2025–2026 papers added.
**Focus:** Why agent behavior degrades over long sessions, and what can be done about it

---

## Observed Behaviors (Problem Statement)

1. **Tool-restriction decay**: Agent obeys "don't use tool X" early in session → later ignores it and uses X directly
2. **Hallucinated tool access**: Agent believes it has access to a restricted tool and emits phantom calls
3. **Agent-switching role bleed**: Switching between agents with different roles causes behavior overlap/contamination
4. **Reasoning-instruction degradation**: Over time, agent shortcuts reasoning → jumps to execution, ignoring role-specific protocols

---

## Section 1: Agent Architecture & Context Management

### Root Cause

**Context Rot (a.k.a. "Context Degradation")** is the dominant mechanism. Liu et al. (2023, "Lost in the Middle") empirically demonstrated that LLM attention to instructions degrades significantly when those instructions are positioned in the _middle_ of long contexts — exactly what happens as chat history accumulates. System prompts and role-defining instructions get pushed into the "lost middle" zone as conversation grows.

**Attention Dilution**: As context length grows, the LLM's attention mechanism must distribute its finite attention budget across more tokens. Early instructions compete with recent conversation turns, tool outputs, and errors.

**In-Context Learning Decay**: The "few-shot" effect of initial instructions fades as the model increasingly attends to the _distribution_ of recent behavior in the conversation rather than the original constraints.

### Possible Solutions

| Solution                                    | Mechanism                                                                                                    | Applicability                                         |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| **Instruction re-injection**                | Periodically re-insert key constraints at the _end_ of context (near the generation point)                   | High — simple, works within existing architecture     |
| **State-machine loop agents**               | Enforce a fixed execution cycle (observe → plan → execute → verify) that resets context focus each iteration | High — aligns with SOLAR's existing Ralph Loop design |
| **Episodic memory + working memory split**  | Separate long-term storage from active context; only load what's needed for current turn                     | Medium — requires memory infrastructure               |
| **Context window compaction with priority** | Summarize old turns but preserve role-defining instructions at fixed positions                               | Medium — CrewAI's `respect_context_window` pattern    |
| **Sliding context with pinned preamble**    | Keep role instructions at position 0 (always in context), slide conversation window                          | High — architecturally simple                         |

### Key Research to Pursue

- ✅ Liu et al. (2023) "Lost in the Middle" — arXiv:2307.03172 (TACL 2023)
- ✅ Anthropic (Dec 2024) "Building Effective Agents" — simplicity + transparency principles
- ✅ CrewAI context window management — `respect_context_window` with auto-summarization
- 🆕 **"Governing Evolving Memory in LLM Agents"** — arXiv:2603.11768 (May 2026). Directly addresses role drift and memory governance; proposes SSGM framework
- 🆕 **"Single-Agent LLMs Outperform Multi-Agent Systems"** — arXiv:2604.02460 (Apr 2026). Empirically shows context degradation in multi-agent setups; recommends single-agent for reasoning
- 🆕 **"A Persistent Memory Layer for Efficient, Context-Aware Agents"** — arXiv:2603.19935 (2026)

---

## Section 2: Guardrails & Behavioral Enforcement

### Root Cause

**Prompt-only guardrails are probabilistic, not deterministic.** Telling an agent "NEVER use tool X" is an input prompt — the model can still sample tool-X calls, especially as attention to that constraint decays. This is the "Negative Prompting Failure" problem: forbidding something doesn't remove the model's ability to generate it.

**No runtime enforcement loop**: Without a programmatic gate between the agent's output and execution, there's nothing to catch a violating tool call before it executes.

**Hallucinated tools**: When an agent has _seen_ tool definitions for other roles (or in training data), it can hallucinate access despite not having them in its current tool set. This is a known behavior in instruction-tuned models.

### Possible Solutions

| Solution                                          | Mechanism                                                                                      | Applicability                                |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **Pre-execution middleware hooks**                | Intercept every tool call, validate against allowlist/denylist, reject before execution        | High — SOLAR already has hook infrastructure |
| **Dynamic tool scoping**                          | Pass only the subset of tools the current role is allowed; never expose forbidden tool schemas | High — prevents hallucination at root        |
| **Constitutional AI principles in system prompt** | Embed behavioral rules as explicit "constitutional" principles that the model self-checks      | Medium — Anthropic's approach; probabilistic |
| **Deterministic tool gate (programmatic)**        | A non-LLM layer that rejects tool calls not in role's manifest                                 | High — 100% reliable, no model dependence    |
| **Output format enforcement (JSON Schema)**       | Require `reasoning` field before `action` field; validate structure before execution           | High — forces role-consistent reasoning      |
| **Guardrails AI validators pattern**              | Pre-built validators for specific risk types, composable into Input/Output Guards              | Medium — Python framework, portable          |

### Key Research to Pursue

- ✅ Bai et al. (2022) "Constitutional AI" — arXiv:2212.08073
- ✅ Guardrails AI framework — guardrailsai.com (Input/Output Guards with composable validators)
- ✅ Dynamic tool scoping as standard practice in Claude & OpenAI tool-use APIs
- 🆕 **OpenAI "Practices for Governing Agentic AI Systems"** (2025) — governance framework for agentic safety
- 🆕 **Anthropic "Teaching Claude why"** (May 8, 2026) — research on reducing agentic misalignment via value teaching

---

## Section 3: Multi-Agent Systems & Role Isolation

### Root Cause

**Context Bleed / Context Contamination**: When agents share a conversation thread or context space, one agent's outputs (including its reasoning style and tool usage patterns) become part of the next agent's input. The model then mimics the _observed_ behavior rather than following its _assigned_ role.

**Role Drift**: Over successive agent switches, each agent's behavior distribution contaminates the shared context, creating a "regression to the mean" where all agents converge toward a generic assistant behavior.

**Handoff Contamination**: When agent A passes state to agent B, agent B inherits not just the task state but also agent A's behavioral patterns encoded in the conversation.

### Possible Solutions

| Solution                               | Mechanism                                                                                                          | Applicability                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| **Isolated sub-agent context windows** | Each agent gets a fresh context with only its role instructions + relevant task state                              | High — SOLAR's artifact-mediated handoff already moves this direction |
| **Structured handoff protocol**        | Agents pass structured JSON (task state, decisions, artifacts) — never raw conversation                            | High — prevents behavioral contamination                              |
| **Hierarchical agent architecture**    | Orchestrator (stateless) dispatches to specialists (fresh spawn each time)                                         | High — aligns with SOLAR's Orchestrator-Specialist design             |
| **Role-reinforcement preamble**        | Every dispatch to a specialist includes a condensed role preamble at the _top_ of fresh context                    | High — cheap and effective                                            |
| **Agent identity watermarking**        | Each agent's outputs are tagged with its role in structured format, so the orchestrator can detect role violations | Medium — adds overhead                                                |

### Key Research to Pursue

- ✅ Wu et al. (2023) "AutoGen" — arXiv:2308.08155
- ✅ CrewAI agent architecture — role/goal/backstory isolation pattern
- ✅ SOLAR's existing design invariant: "Specialists never communicate directly"
- 🆕 **"Single-Agent LLMs Outperform Multi-Agent Systems"** — arXiv:2604.02460 (Apr 2026). Key finding: multi-agent systems suffer from context fragmentation; single-agent with more thinking tokens wins

---

## Section 4: Reasoning & Execution Stability

### Root Cause

**Chain-of-Thought (CoT) Degradation**: Over long sessions, the agent increasingly skips explicit reasoning steps and jumps to action. This is related to context rot — as the reasoning instruction gets pushed deeper into context, the model defaults to its pre-trained "just answer" behavior.

**Plan-then-Execute collapse**: Instructions that say "first plan, then execute" degrade into "execute" as the model observes itself (and potentially other agents) producing successful outputs without visible planning.

**Self-correction fatigue**: Reflexion-style self-correction (Shinn et al., 2023) requires the agent to maintain meta-cognitive awareness, which is context-expensive and decays over turns.

### Possible Solutions

| Solution                                      | Mechanism                                                                                                                     | Applicability                                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Structured output contracts (JSON Schema)** | Force `{plan: ..., execute: ..., verify: ...}` structure in every response                                                    | High — programmatic enforcement of reasoning                |
| **Deterministic verification hooks**          | A non-LLM validator that checks: "did the agent produce a plan before executing?" — reject and re-prompt if not               | High — prevents reasoning skip                              |
| **Plan-and-Solve prompt pattern**             | Force a two-phase response: (1) devise plan, (2) execute plan. Separate LLM calls if needed                                   | High — Wang et al. (2023) showed significant accuracy gains |
| **Reflexion / episodic reflection buffer**    | Store reflections on past mistakes; re-inject relevant ones at each turn                                                      | Medium — Shinn et al. (2023); works but adds context load   |
| **Self-consistency sampling**                 | Run multiple reasoning paths, vote on the best — but expensive                                                                | Low — too costly for most sessions                          |
| **Reasoning freshness prompts**               | Periodically inject "Before you act, take a step back and think about your role and what you should do" — resets CoT behavior | High — simple and compatible                                |

### Key Research to Pursue

- ✅ Wang et al. (2023) "Plan-and-Solve Prompting" — arXiv:2305.04091 (ACL 2023)
- ✅ Shinn et al. (2023) "Reflexion: Language Agents with Verbal Reinforcement Learning" — arXiv:2303.11366
- ✅ Havrilla et al. (2024) "GLoRe: When, Where, and How to Improve LLM Reasoning" — arXiv:2402.10963
- 🆕 **"When Agents Disagree With Themselves: Behavioral Consistency as an Uncertainty Signal"** — arXiv:2602.11619 (Feb 2026). Directly measures agent behavioral consistency as a reliability signal

---

## 2025–2026 Frontier Research (Newly Discovered)

These papers were found during the July 2026 verification pass and directly address SOLAR V5's concerns:

| Paper                                                        | Date     | arXiv         | Relevance                                                                                       |
| ------------------------------------------------------------ | -------- | ------------- | ----------------------------------------------------------------------------------------------- |
| **Governing Evolving Memory in LLM Agents** (SSGM Framework) | May 2026 | 2603.11768    | Role drift, context degradation, memory governance — directly addresses all 4 problem behaviors |
| **When Agents Disagree With Themselves**                     | Feb 2026 | 2602.11619    | Behavioral consistency as measurable signal — validates the core V5 premise                     |
| **Single-Agent LLMs Outperform Multi-Agent Systems**         | Apr 2026 | 2604.02460    | Shows multi-agent context degradation empirically; supports SOLAR's isolated-specialist design  |
| **A Persistent Memory Layer for Context-Aware Agents**       | 2026     | 2603.19935    | Architectural solution for context degradation via persistent memory                            |
| **Anthropic: Teaching Claude why**                           | May 2026 | anthropic.com | Reducing agentic misalignment via value teaching                                                |
| **OpenAI: Practices for Governing Agentic AI Systems**       | 2025     | openai.com    | Governance framework for agentic safety                                                         |
| **DeepSeek-R1: Reasoning via RL**                            | Jan 2025 | 2501.12948    | Reasoning capability improvements relevant to CoT stability                                     |

---

## Cross-Cutting Observations

1. **The "Lost Middle" is the common enemy.** Almost every degradation pattern traces back to instructions getting pushed out of the model's attention sweet spot (beginning/end of context).

2. **Prompt-only solutions are insufficient for reliability.** Deterministic/programmatic enforcement (hooks, gates, schema validation) is necessary for high-consistency behavior. SOLAR's existing hook system is well-positioned for this.

3. **Fresh spawn beats state preservation.** Given SOLAR's existing artifact-mediated handoff pattern, the most impactful change is to always spawn specialists with fresh, minimal context (role preamble + task-relevant artifacts only), never carrying forward conversation history.

4. **SOLAR V4 already has the right architectural instincts** — orchestrator inline, specialists isolated, artifact-mediated communication, hooks infrastructure. V5 should harden these patterns with deterministic enforcement layers.

---

## Recommended Deep-Dive Order

1. ⭐ **Instruction re-injection + pinned preamble** (Section 1) — highest ROI, simplest
2. ⭐ **Deterministic tool gate + dynamic scoping** (Section 2) — eliminates tool-violation class
3. ⭐ **Fresh-spawn specialists with structured handoff** (Section 3) — leverages existing architecture
4. ⭐ **Structured output contracts with plan-before-execute enforcement** (Section 4) — prevents reasoning skip
5. **Episodic memory architecture** (Section 1) — medium-term infrastructure
6. **Constitutional AI self-check principles** (Section 2) — probabilistic complement to deterministic gates

---

---

## Verification Log

All references were verified via live browser navigation on 2026-07-24:

| Reference                                    | Status      | Method                                      |
| -------------------------------------------- | ----------- | ------------------------------------------- |
| Liu et al. "Lost in the Middle" (2307.03172) | ✅ Verified | arXiv page navigation                       |
| Bai et al. "Constitutional AI" (2212.08073)  | ✅ Verified | arXiv page navigation                       |
| Shinn et al. "Reflexion" (2303.11366)        | ✅ Verified | arXiv page navigation                       |
| Wang et al. "Plan-and-Solve" (2305.04091)    | ✅ Verified | arXiv page navigation                       |
| Wu et al. "AutoGen" (2308.08155)             | ✅ Verified | arXiv page navigation                       |
| Havrilla et al. "GLoRe" (2402.10963)         | ✅ Verified | arXiv page navigation                       |
| Anthropic "Building Effective Agents"        | ✅ Verified | Live page (anthropic.com/engineering)       |
| Guardrails AI framework                      | ✅ Verified | Live docs (guardrailsai.com/docs)           |
| CrewAI agent docs                            | ✅ Verified | Live docs (docs.crewai.com/concepts/agents) |
| SSGM Framework (2603.11768)                  | ✅ Verified | arXiv page navigation                       |
| Behavioral Consistency (2602.11619)          | ✅ Verified | arXiv page navigation                       |
| Single-Agent vs Multi-Agent (2604.02460)     | ✅ Verified | arXiv page navigation                       |
| Anthropic "Teaching Claude why"              | ✅ Verified | Live page (anthropic.com/research)          |
| OpenAI "Governing Agentic AI"                | ✅ Verified | Live page (openai.com/index)                |

_End of research notes. Awaiting approval for deeper investigation into prioritized sections._

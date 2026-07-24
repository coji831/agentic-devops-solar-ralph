---
description: Dispatch pattern for Context Summarizer. Referenced by solar.prompt.md step 3b.
applyTo: ".github/prompts/solar.prompt.md"
---

# Context Summarizer Dispatch Pattern

Before every specialist dispatch, the Governor must gather context via the Context Summarizer.

## Pattern

- Dispatch `context-summarizer.agent.md` with task description + target paths.
- SKILL: `.github/skills/context-summarization/SKILL.md`
- Result path: `verification-artifacts/{task-id}-digest.json`
- Await digest → read it (~20 lines, ~200 tokens) → include key facts inline in the specialist dispatch prompt.
- Do NOT pass the digest path for the specialist to read — specialists cannot read files directly.

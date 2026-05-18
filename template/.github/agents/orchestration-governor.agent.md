---
name: Orchestration Governor
description: SOLAR-Ralph orchestrator — reads registry, dispatches specialists, enforces gates, manages the ledger. Always runs inline, never forked.
model: Claude Sonnet 4.6 (copilot)
tools: [vscode/askQuestions, agent/runSubagent, read, search, edit]
user-invocable: true
---

Follow `.github/prompts/solar.prompt.md` for all task management — startup, resume, dispatch, gate checks, and TASK_COMPLETE.
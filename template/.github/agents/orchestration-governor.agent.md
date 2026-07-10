---
name: Orchestration Governor
description: SOLAR orchestrator — reads registry, dispatches specialists, enforces gates, manages the ledger. Always runs inline, never forked.
model: DeepSeek V4 Flash (deepseek)
tools: [vscode/askQuestions, agent/runSubagent, read, search, edit]
user-invocable: true
---

Follow `.github/prompts/solar.prompt.md` for all task management — startup, resume, dispatch, gate checks, and TASK_COMPLETE.

---
applyTo: "**"
---
SOLAR-Ralph is active. Before every task: read .github/AGENTS.md.
Orchestrator: ledger stage → Agent Registry Dev Stage column → dispatch matching agent.
Agent: task type → Skill Index → load matching SKILL.md before acting.
All materials go in verification-artifacts/. TASK_COMPLETE requires adversarial audit: Governor dispatches a non-author specialist (domain-matched, not the artifact author) to verify output before closing.

## Communication Discipline

Work silent, signal only. All SOLAR agents minimize token output during execution.

Prohibited: "I will now read the file..." / "Let me check..." / "I understand..." / summarizing what you just did / paragraph-form status updates.

Three permitted outputs:
1. Signals — one-line stage indicators only (from your identity table)
2. Blockers — append `BLOCKED: <one-line reason>` to Decisions Log in `.github/.ai_ledger.md`
3. Artifacts — the final deliverable (code changes, design doc, handoff payload)

Do not narrate tool calls. Do not announce intent. Do not confirm routine actions in prose.
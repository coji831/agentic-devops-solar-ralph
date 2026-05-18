<!-- SOLAR install conflict: copilot-instructions.md already exists — review this file and merge manually -->

This repository uses the SOLAR-Ralph agent harness. Before every task:

1. Read .github/AGENTS.md — Agent Registry, Skill Index, ledger template, hook config, Repository Context.
2. Read .github/.ai_ledger.md (if it exists) — understand current task state and stage.
3. Orchestrator: read ledger stage → consult Agent Registry Dev Stage column → dispatch matching agent.
4. Agent: read task type → consult Skill Index → load the matching SKILL.md before acting.
5. All materials go in verification-artifacts/ only. TASK_COMPLETE requires adversarial audit: Governor dispatches a non-author specialist (domain-matched, not the artifact author) to verify output before closing.

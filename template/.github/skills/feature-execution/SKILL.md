---
name: feature-execution
description: "Use when executing a feature end to end through plan, implement, test, docs, review, ledger updates, and bounded recursive repair."
argument-hint: "Feature path or feature identifier"
user-invocable: true
---

# Feature Execution

## When to Use

- Feature implementation from existing business requirements and implementation docs
- Bounded SOLAR loops for a single feature

## Procedure

1. Read the feature BR, implementation doc, `.github/copilot-instructions.md`, and `AGENTS.md`.
2. Decompose the feature into work packages and record them in `.github/.ai_ledger.md`.
3. Delegate frontend, backend, testing, review, or docs work as needed.
4. Run focused verification after each meaningful step.
5. Close only when the ledger contains a non-pending completion promise.

## Output

- Work packages
- Delegations
- Verification state
- Completion or escalation decision

# Adversarial Trigger Conditions — Skeleton Manifest

The adversarial layer (A in SOLAR) is a Governor dispatch rule, not a dedicated agent. At the VERIFY step of each micro-cycle, the Governor picks a non-author specialist from the Agent Registry (domain match) to challenge the previous agent's output.

## Trigger Conditions

Adversarial audit is triggered when the producing specialist returns an artifact and VERIFY is required (code, design, or doc output). It is SKIPPED for scan/handoff artifacts.

## Five Injection Patterns to Watch

1. **Scope creep** — specialist expands beyond Work Package; auditor checks artifact against `exit_criteria` in ledger
2. **Self-certification** — specialist claims TASK_COMPLETE without Governor gate; blocked by stop hook and Governor contract
3. **Stale materials** — specialist acts on outdated input (status ≠ ready); caught by G1 gate before dispatch
4. **Silent failures** — specialist returns `completed` but artifact is empty or malformed; auditor opens and validates artifact schema
5. **Loop bypass** — specialist skips VERIFY by not writing to `verification-artifacts/`; post-tool-use hook injects ADVERSARIAL_VERIFY_REQUIRED signal
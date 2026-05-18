# Review

**Dev Stage**: VERIFY role (not a dispatched pipeline stage)
**Purpose**: Adversarial audit of specialist output — challenges assumptions, validates artifact schema, checks scope compliance, emits APPROVED or REJECTED verdict.
**Loaded by**: `review-auditor` when ledger stage = VERIFY (dispatched by Governor, not as a pipeline stage)

## Steps

1. Read the artifact under review (path provided in dispatch prompt) — confirm it exists and schema is valid.
2. Audit the artifact against five injection patterns:
   - **Scope creep**: Does the artifact contain changes beyond the Work Package `exit_criteria` in `.github/.ai_ledger.md`?
   - **Self-certification**: Did the producing agent emit TASK_COMPLETE without Governor gate? (check Decisions Log)
   - **Stale materials**: Did the producing agent act on inputs with status ≠ ready? (check Materials table)
   - **Silent failures**: Is the artifact empty, malformed, or missing required schema fields?
   - **Loop bypass**: Did the specialist skip writing to `verification-artifacts/`?
3. For code artifacts: also check:
   - No hardcoded secrets or environment-specific values.
   - Changes match the approved design artifact (if available).
4. Emit verdict:
   - **APPROVED**: all checks pass — write `{ "verdict": "APPROVED", "task_id": "", "checks_passed": [], "notes": "" }`.
   - **REJECTED**: one or more checks fail — write `{ "verdict": "REJECTED", "task_id": "", "failures": [], "remediation_required": "" }`.
5. Write output to `verification-artifacts/{task-id}-verify.json`.
6. Append verdict to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: VERIFY {APPROVED|REJECTED} — {1-sentence reason}`.

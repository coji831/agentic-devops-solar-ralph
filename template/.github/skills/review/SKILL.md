# Review

**Dev Stage**: VERIFY role (not a dispatched pipeline stage)
**Purpose**: Adversarial audit of specialist output — challenges assumptions, validates artifact schema, checks scope compliance, emits APPROVED or REJECTED verdict.
**Loaded by**: `review-auditor` when ledger stage = VERIFY (dispatched by Governor, not as a pipeline stage)

## Steps

1. Extract the artifact summary and context digest from the dispatch prompt — the Governor includes the artifact ref, verdict context, and any prior verification history inline.
2. Audit the artifact against five injection patterns:
   - **Scope creep**: Does the artifact contain changes beyond the Work Package `exit_criteria` in `.github/.ai_ledger.md`?
   - **Self-certification**: Did the producing agent emit TASK_COMPLETE without Governor gate? (check Decisions Log)
   - **Stale materials**: Did the producing agent act on inputs with status ≠ ready? (check Work Queue)
   - **Silent failures**: Is the artifact empty, malformed, or missing required schema fields?
   - **Loop bypass**: Did the specialist skip writing to `verification-artifacts/`?
3. For code artifacts: also check:
   - No hardcoded secrets or environment-specific values.
   - Changes match the approved design artifact (if available).
4. Emit verdict:
   - **APPROVED**: all checks pass — write to `verification-artifacts/{task-id}-verify.json` with `{ "task_id": "", "verdict": "APPROVED", "refs": [] }`.
   - **REJECTED**: one or more checks fail — write to `verification-artifacts/{task-id}-verify.json` with `{ "task_id": "", "verdict": "REJECTED", "refs": [] }`.
5. Append verdict to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: VERIFY {APPROVED|REJECTED} — {1-sentence reason}`.

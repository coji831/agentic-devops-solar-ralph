# Recursive Remediation

**Dev Stage**: Any (used when a previous stage artifact was REJECTED at VERIFY)
**Purpose**: Bounded iteration loop for fixing failures — max 3 remediation attempts before escalating.
**Loaded by**: Governor when VERIFY verdict = REJECTED and G3 loop-bounds-ok gate passes

## Steps

1. Read the REJECTED artifact and verdict from `verification-artifacts/{task-id}-verify.json` — extract failures and remediation_required.
2. Check iteration counter: read Work Queue `iteration` column for this task.
   - If iteration ≥ 3: append `BLOCKED: ESCALATION_REQUIRED — max remediation iterations reached` to Decisions Log and return to Governor. Do NOT proceed.
3. Increment iteration: update Work Queue row `iteration` = current + 1, `status` = REMEDIATION.
4. Dispatch producing agent with remediation context:
   - Dispatch prompt must include: task description + failed artifact path + REJECTED reasons + result path + SKILL.md path + return instruction.
   - Do NOT include raw file contents in the dispatch prompt.
5. Await new artifact from producing agent.
6. Re-dispatch `review-auditor` for adversarial audit of the new artifact (VERIFY step).
7. On APPROVED: update Work Queue row `status` = COMPLETE, `iteration` = final count. Continue pipeline.
8. On REJECTED again: return to step 2 (loop continues until iteration ≥ 3 or APPROVED).
9. Append each iteration outcome to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Remediation iteration {n} — {APPROVED|REJECTED} — {1-sentence reason}`.

# Lifecycle Coordination — VERIFY Stage Trigger Mechanics

The VERIFY step runs conditionally inside each micro-cycle. The Governor decides whether to run or skip based on the artifact type returned by the specialist.

## Run VERIFY when output contains:

- Code changes (implementation or test artifacts)
- Design artifacts (architecture plans, data shape definitions)
- Document output (BR files, implementation docs, architecture updates)

## Skip VERIFY when output is:

- Scan findings passed as handoff material to the next stage
- Ledger or registry updates (metadata only, no deliverable content)

## Auditor Selection (domain match)

The Governor looks up the auditor from the Agent Registry by role — do NOT hardcode agent names in `solar.prompt.md`:

- Code output → agent with role `review-auditor`
- Design/docs output → agent with role `design-planning-architect` (non-author challenge)

## Post-VERIFY flow

- APPROVED → Governor advances to next stage; appends verdict to Decisions Log
- REJECTED → Governor returns artifact to producing agent with rejection reasons; increments remediation counter; re-dispatches VERIFY after fix
- REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log
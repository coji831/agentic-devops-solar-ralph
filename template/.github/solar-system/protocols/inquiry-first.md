# Inquiry-First Protocol — Canonical 4-Gate Contract

Before the Governor dispatches any specialist, all four gates must pass. A single failure blocks dispatch and appends `BLOCKED: <gate> failed` to the Decisions Log.

| Gate | Name                 | Condition                                                                                       | Failure Action                            |
| ---- | -------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------- |
| G1   | materials-sufficient | Required input artifacts exist in `verification-artifacts/` and status = ready                  | Emit MATERIAL_INSUFFICIENT; pause         |
| G2   | design-approved      | Design artifact approved before Implement stage (`human_approval=true` → `vscode_askQuestions`) | Await approval or request revision        |
| G3   | loop-bounds-ok       | Remediation iteration counter < 3                                                               | Emit ESCALATION_REQUIRED                  |
| G4   | previous-verified    | Previous stage VERIFY passed (verdict = APPROVED), or VERIFY was explicitly skipped             | Return to producing agent for remediation |
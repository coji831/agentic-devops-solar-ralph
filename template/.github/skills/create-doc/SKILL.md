---
name: create-doc
description: Plan + Design → Document pipeline for writing, creating, or updating documentation — BR files, implementation docs, architecture overviews, guides, or knowledge base articles.
---

# Create Doc

**Type**: Playbook (governor follows inline; each step dispatches a forked specialist)
**Trigger**: User asks to write, create, or update documentation

## Steps

1. **[Gate: material check]** Verify input materials are ready in ledger. Confirm `exit_criteria` specifies the target doc type and the target file path or topic. If not → emit MATERIAL_INSUFFICIENT, do not proceed.

2. **[Dispatch: Design Planning Architect]** Dispatch `design-planning-architect.agent.md` as a subagent to outline the documentation structure.
   - SKILL: `.github/skills/design-planning/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-design.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."
   - Design artifact must include: target file path, section outline, template to follow (if any).

3. **[Gate: design approval]** Governor checks doc outline. If `config.human_approval = true` → use `vscode_askQuestions` to get user confirmation before writing. If rejected → re-dispatch with feedback (Ralph loop, max 3 iterations).

4. **[Dispatch: Docs Curator]** Dispatch `docs-curator.agent.md` as a subagent to write or update the documentation.
   - SKILL: `.github/skills/doc-sync/SKILL.md`
   - Result path: `verification-artifacts/{task-id}-docs.json`
   - Return instruction: "Return only: status (completed|partial|blocked), result file path written, and a 2-sentence summary. Do NOT embed raw file contents in your return message."

5. **[Gate: adversarial verify — documentation]** Governor dispatches `design-planning-architect.agent.md` as non-author challenger → verify doc artifact against template compliance and content accuracy → verdict APPROVED or REJECTED. On REJECTED → return to Docs Curator with rejection reasons.

6. **[Exit]** If APPROVED → update ledger CLOSED. Archive ledger. Reset from template. Clean up `verification-artifacts/{task-id}-*` task files. If REJECTED × 3 → append `BLOCKED: ESCALATION_REQUIRED` to Decisions Log and pause for human review.

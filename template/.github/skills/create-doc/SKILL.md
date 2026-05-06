---
name: create-doc
description: >-
  Triggered when user asks to write, create, or update documentation
---

# Create Doc Playbook

**Type**: Playbook — the governor follows this inline; each step dispatches a forked specialist
**Trigger**: User asks to write, create, update, or improve documentation (architecture docs, guides, API specs, README, design docs, knowledge base articles)

## Steps

1. **[Gate: material check]** Confirm the doc subject and target location are clear (user prompt, linked file, or feature context). If not → use `vscode_askQuestions` to ask: (a) what is the subject? (b) does a template or existing doc exist that should be used or updated?

2. **[Dispatch: data-collector-specialist]** Fork. Task: scan for (a) an existing doc at the target path, (b) a template that applies, (c) any source material (design artifacts, implementation files, API specs) relevant to the doc; produce `verification-artifacts/{task-id}-scan.md`. Await artifact.

3. **[Gate: template + source check]** Governor reads scan. If a template was found → record its path in ledger Materials (status: ready). If an existing doc was found → record its path (status: ready, note: update, not create). If neither → confirm with user via `vscode_askQuestions` before continuing.

4. **[Dispatch: docs-curator]** Fork. Task: produce or update the document at the target path using the template (if available) and source materials; write the final doc in-place and produce `verification-artifacts/{task-id}-doc-output.md` (path written, sections changed, and any decisions made). Await artifact.

5. **[Gate: content review]** Governor reads the doc-output artifact summary. If the doc deviates from the template structure or is missing sections → re-dispatch `docs-curator` with specific corrections (Ralph loop, max 3 iterations).

6. **[Gate: adversarial verify]** Governor selects a non-author specialist by domain match (prefer `review-auditor` for technical docs; `design-planning-architect` for architecture or design docs). Fork. Task: review the written doc for accuracy, completeness, and template compliance; produce `verification-artifacts/{task-id}-verify.md` (verdict: `APPROVED` or `REJECTED` + specific findings). Await artifact.

7. **[Gate: verdict check]** If `REJECTED` → return to `docs-curator` with specific findings (Ralph loop, max 3 iterations). If `APPROVED` → continue.

8. **[Exit]** Append `[CLOSED] create-doc — exit criteria met` to ledger Decisions Log. Delete `verification-artifacts/{task-id}-*.md`. Set Work Queue row to `CLOSED`.

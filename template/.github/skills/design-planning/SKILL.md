# Design Planning

**Dev Stage**: Plan + Design
**Purpose**: Produce architecture plans, data shape definitions, and implementation blueprints from scan findings.
**Loaded by**: `design-planning-architect` when ledger stage = Plan + Design

## Steps

1. Read `verification-artifacts/{task-id}-scan.json` — confirm status=ready.
2. Analyze scan findings:
   - Identify the minimal change surface required to satisfy exit_criteria.
   - Check [FILL IN: architecture doc path, e.g. `docs/architecture.md`] for architectural constraints.
   - Note any patterns from [FILL IN: conventions doc path, e.g. `docs/guides/code-conventions.md`] applicable to this task.
3. Produce design plan:
   - Define data shapes, interfaces, or API contracts changed by this task.
   - List files to create or modify with their responsibilities.
   - Describe component/module interaction changes if any.
   - Flag alternatives considered and the chosen approach with rationale.
4. Write output to `verification-artifacts/{task-id}-design.json` with schema: `{ "task_id": "", "design_summary": "", "files_to_change": [], "data_shapes": {}, "alternatives_considered": [], "rationale": "" }`.
5. Append result summary to ledger Decisions Log: `YYYY-MM-DD HH:MM UTC: Design complete — {2-sentence summary of approach}`.

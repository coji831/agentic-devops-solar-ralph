# Converter: PATTERNS.md → Workflow File

Transforms a PATTERNS.md entry into a formatted addition for `.github/workflows/*.workflow.md`.

## When to Use

Use when the pattern entry describes a **process flow, agent routing sequence, or handoff pattern** — not a code convention.

- Signs this belongs in a workflow: the lesson describes a sequence of steps, a decision point, or an agent interaction
- Signs this belongs in instructions instead: the lesson describes a code convention, naming rule, or tech stack fact

Target workflow files:
- `feature.workflow.md` — full feature pipeline patterns
- `bug-fix.workflow.md` — debugging and repair patterns
- `simple-fix.workflow.md` — small change patterns
- Or create a new workflow file if a new process pattern emerges

## Input: PATTERNS.md Entry Format

```
### [DATE] [CATEGORY] — [SHORT TITLE]
**Problem**: <what process step failed or was unclear>
**Solution**: <routing or handoff change that resolved it>
**Lesson**: <one-sentence takeaway for agent routing or workflow design>
```

## Output: Workflow Step Addition

```markdown
<!-- Source: PATTERNS.md #[DATE]-[SHORT-TITLE] -->
#### [Step or stage name]

**Trigger**: [When this step or routing decision applies]

**Action**:
1. [First action]
2. [Second action]
3. [etc.]

**Exit Condition**: [What must be true before proceeding to the next step]

**Escalation**: [What to do if the exit condition cannot be met]
```

## Duplicate Detection

Before inserting, search the target workflow file for:
- Stage names that match the converted step name
- Trigger conditions that overlap with the new step's trigger

If overlap exists: flag as `DUPLICATE_CANDIDATE` and surface to user. Do not auto-insert.

## Placement Rules

- Add to the **most relevant stage** of the target workflow
- If adding a new stage: insert it in the logical execution order (before/after existing stages)
- Preserve YAML frontmatter of workflow files — do not modify metadata fields
- After insertion, add a comment at the bottom of the file: `<!-- Updated: [DATE] — promoted from PATTERNS.md #[ID] -->`

## Example Transformation

**Input (PATTERNS.md):**
```
### 2026-04-10 ORCHESTRATOR — Collector Before Planner Prevents Rework
**Problem**: Planner was re-reading files already read during planning, wasting 2 context window iterations.
**Solution**: Always dispatch Data Collector Specialist before Design Planning Architect when > 3 source files need context.
**Lesson**: Collector-first routing reduces planner rework by 50%+ on multi-file tasks.
```

**Output (feature.workflow.md addition):**
```markdown
<!-- Source: PATTERNS.md #2026-04-10-Collector-Before-Planner-Prevents-Rework -->
#### Context Collection Gate

**Trigger**: Request requires reading > 3 non-ledger source files to understand scope.

**Action**:
1. Dispatch Data Collector Specialist with file list
2. Wait for `scout_findings` in `## Handoff Payload`
3. Only then dispatch Design Planning Architect

**Exit Condition**: `scout_findings` JSON manifest present in `## Handoff Payload`

**Escalation**: If Data Collector returns > 10 files, ask user to narrow scope before planning.
```

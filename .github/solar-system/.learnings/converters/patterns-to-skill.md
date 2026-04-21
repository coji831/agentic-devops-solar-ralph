# Converter: PATTERNS.md → Skill SKILL.md

Transforms a PATTERNS.md entry into a new or updated skill section in `.github/skills/*/SKILL.md`.

## When to Use

Use when the pattern entry describes a **reusable technique, domain knowledge, or specialized testing strategy** that warrants a dedicated skill workflow.

- Signs this belongs in a skill: the lesson is a multi-step domain technique that needs detailed guidance
- Signs this belongs in instructions instead: the lesson is a one-line rule or convention
- Signs this belongs in a workflow instead: the lesson is a routing or handoff sequence

Skill additions vs. new skills:
- Add to an existing skill's SKILL.md if the pattern extends existing domain guidance
- Create a new skill only if the pattern represents a new, standalone domain technique

## Input: PATTERNS.md Entry Format

```
### [DATE] [CATEGORY] — [SHORT TITLE]
**Problem**: <what domain technique was non-obvious or required significant iteration>
**Solution**: <the technique that resolved it>
**Lesson**: <one-sentence takeaway with broad applicability>
```

## Output: SKILL.md Section Addition

```markdown
<!-- Source: PATTERNS.md #[DATE]-[SHORT-TITLE] -->
## [Technique Name]

**When to use**: [Specific conditions when this technique applies]

**When NOT to use**: [Conditions where this technique would be wrong or unnecessary]

**Steps**:
1. [First step — specific and actionable]
2. [Second step]
3. [etc.]

**Expected outcome**: [What should be true after applying this technique]

**Tradeoffs**:
- Pro: [benefit]
- Con: [limitation or risk]

**Related**: [Links to related skills, instructions, or KB articles if applicable]
```

## Duplicate Detection

Before inserting or creating, search existing skill SKILL.md files for:
- Technique names matching the new technique title
- Problem statements describing the same scenario

If overlap exists: extend the existing skill section rather than creating a duplicate. Surface to user if unsure which is correct.

## Placement Rules

- Add new sections at the **end** of the target SKILL.md before any `## References` section
- If creating a new skill folder: follow existing skill folder structure (folder + SKILL.md)
- New skill folder name: kebab-case, descriptive, domain-specific

## Example Transformation

**Input (PATTERNS.md):**
```
### 2026-03-28 FRONTEND-TEST — RTL Query Stability
**Problem**: Tests using getByTestId broke when test IDs changed; tests using getByRole stayed stable.
**Solution**: Prefer getByRole > getByText > getByTestId in RTL queries for resilience.
**Lesson**: Role-based queries survive refactoring; test-ID queries create tight coupling.
```

**Output (frontend-testing/SKILL.md addition):**
```markdown
<!-- Source: PATTERNS.md #2026-03-28-RTL-Query-Stability -->
## RTL Query Stability Hierarchy

**When to use**: Any time writing or reviewing RTL component tests.

**When NOT to use**: When testing non-semantic elements with no accessible role.

**Steps**:
1. Default to `getByRole` (most resilient — survives refactoring)
2. Use `getByText` for text content checks
3. Use `getByLabelText` for form inputs
4. Use `getByTestId` only as a last resort when no semantic role is accessible

**Expected outcome**: Tests survive component refactors without needing query updates.

**Tradeoffs**:
- Pro: Role-based queries also verify accessibility
- Con: Requires understanding ARIA roles for less common elements
```

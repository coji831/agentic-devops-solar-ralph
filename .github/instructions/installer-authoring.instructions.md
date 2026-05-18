---
applyTo: "solar-install.prompt.md"
---

# Installer Prompt Authoring

This instruction file applies only to authoring `solar-install.prompt.md`.

## Scope

- `solar-install.prompt.md` is the source of truth for installation behavior.
- Changes here must stay aligned with generated scaffold content under `template/`.
- Do not use this file for general framework-development guidance.

## Authoring Rules

- Every section belongs to exactly one tier before writing.

### Tier 1 — Verbatim file content

Use for exact file bodies an installer must reproduce.

- Wrap content in fenced code blocks.
- No prose inside the block.
- Only `[FILL IN]` and `{TOKEN}` may vary.
- Do not summarize Tier 1 content.

### Tier 2 — Fixed skeleton with sweep-driven slots

Use for files with fixed structure and variable fields.

- Emit the full skeleton once.
- Mark variable slots as `{TOKEN}` or `[FILL IN]`.
- Do not omit required headings or fields.

### Tier 3 — Short declarative rules

Use for procedural installer instructions.

- One bullet or one sentence per rule.
- No prose paragraphs.
- Do not restate Tier 1 or Tier 2 content in summary form.

## Synchronization Rules

- If installer output changes, update the matching files in `template/`.
- If template structure changes, update installer instructions that generate it.
- Keep prompt field names, hook field names, and tool names current with the scaffold.

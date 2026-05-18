# SOLAR-Ralph Development Repo

This repository is for development of the SOLAR framework itself.

Scope boundaries:

- Root-level `.github` content governs SOLAR framework development in this repository.
- `template/` contains the installation output scaffold that SOLAR installs into target repositories.
- Changes to installation behavior must keep `template/` and `solar-install.prompt.md` aligned.

Reference docs:

- Concept: `docs/solar-ralph-concept.md`
- Reference: `docs/solar-ralph-reference.md`

---

## Core Design Invariants

Non-negotiable rules. Breaking any one collapses the architecture:

1. **Orchestrator never forks** — runs inline; owns all gates, adversarial dispatch, loop iteration, and ledger writes.
2. **Specialists never communicate directly** — all output goes to `verification-artifacts/` and is referenced in the ledger.
3. **Adversarial = non-author** — auditor is domain-matched from Agent Registry at dispatch time; never hardcoded by name.
4. **Ralph loop requires declared exit** — exit criteria must be in the ledger before the loop starts; `TASK_COMPLETE` cannot be emitted without adversarial verification passing first.
5. **Ledger is sparse** — materials are links only, never embedded content; fields populated only when content exists.
6. **Material gate fires before every dispatch** — if `input_material: ready` is not set, emit `MATERIAL_INSUFFICIENT`; never start and fail later.
7. **`BLOCKED:` not `Active Blockers`** — blockers are appended to Decisions Log as `BLOCKED: <reason>`; there is no `## Active Blockers` section.

---

## Working Boundaries

- Treat root-repo changes as SOLAR framework development work, not target-repo customization.
- Treat `template/` as installable output. Keep generated scaffold behavior consistent with the framework design.
- When changing installer output, update the source-of-truth prompt and the scaffold together.
- Do not place target-repo-specific rules in this root instruction file.

---

## Repo Structure

- `template/` — reference installation scaffold
- `docs/` — concept, reference, guides, knowledge base
- `solar-install.prompt.md` — installer source of truth
- `verification-artifacts/` — task evidence, handoffs, scan results

---

## Documentation Sync Rules

- Architectural or framework-behavior changes: update `docs/solar-ralph-concept.md` and relevant reference docs.
- Template behavior changes: update `solar-install.prompt.md` and matching `template/` files together.
- New agent or skill in installed output: update `template/.github/AGENTS.md` and reference docs together.
- Do not embed ledger contents or artifact bodies into documentation; link or reference them only.

---

## Release Checklist

For releases:

1. Apply fixes to both the framework sources and the installable scaffold where required.
2. Verify prompt names, tool-set names, hook field names, and version references.
3. Bump `solar_version` in `template/.github/AGENTS.md`.
4. Add the release entry to `CHANGELOG.md`.
5. Add migration notes when behavior is breaking.

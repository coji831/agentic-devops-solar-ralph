---
applyTo: "CHANGELOG.md"
---

# Release And Versioning

This instruction file applies to release and versioning work in the SOLAR framework repo.

## Release Rules

- Release changes must reflect both framework sources and installable scaffold changes where applicable.
- Bump `solar_version` in `template/.github/AGENTS.md` when required by the release.
- Record every release in `CHANGELOG.md`.
- Breaking changes require migration notes.
- Validate prompt names, tool-set names, hook field names, and version references before release completion.

## Documentation Rules

- Major version behavior changes must be reflected in high-level docs.
- Keep release notes concise and behavior-focused.
- Do not embed ledger content or raw verification artifacts into release docs.

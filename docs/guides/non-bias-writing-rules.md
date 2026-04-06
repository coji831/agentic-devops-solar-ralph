# Agent Writing Rules

Rules that apply to all `.prompt.md` files and `.agent.md` instruction bodies in SOLAR. They ensure SOLAR works correctly out-of-the-box for any project without assuming a specific stack.

---

## No hard-coded technology references in instruction bodies

Do NOT embed technology names, package managers, or framework paths in agent instruction bodies or prompt files:

- Not allowed: `npm test`, `npx tsc --noEmit`, `vitest`, `prisma migrate`, `React`, `ESLint`
- Use token placeholders instead: `[test-command]`, `[type-check-command]`, `[verify-command]`, `[lint-command]`
- The correct values are resolved at runtime from `solar-project-profile.json` or `.github/instructions/*.instructions.md`

Exception: The `solar-bootstrap.agent.md` scan protocol lists technology names intentionally as **detection targets** (things to look for), not as assumed stack components. Do not apply this rule to detection lists.

---

## Use generic placeholders for commands

Every command reference in an agent instruction must be expressed as a placeholder token:

| Placeholder            | Resolves to                                   |
| ---------------------- | --------------------------------------------- |
| `[test-command]`       | The project's test runner invocation          |
| `[type-check-command]` | The project's type-check invocation           |
| `[lint-command]`       | The project's linter invocation               |
| `[verify-command]`     | The narrowest verification check for the task |
| `[build-command]`      | The project's build invocation                |
| `[dev-command]`        | The project's local dev server command        |

---

## Each agent must cover at least 3 scenario types

Single-use-case agents belong in custom `solar-system/` workflows, not in `.github/agents/*.agent.md`. A base agent must be useful for:

1. New feature implementation
2. Bug fix
3. Refactor or maintenance task

If an agent is scoped to only one scenario type (e.g., only handles Prisma migrations), move it to a project-specific `solar-system/` override rather than adding it to the base agent roster.

---

## Stack-specific fine-tuning belongs in override files

When a project requires stack-specific agent behavior:

- Create a companion `.github/instructions/<domain>.instructions.md` file with `applyTo` glob
- Or create a `solar-system/` override file that patches the relevant instruction
- Do NOT edit the base `.github/agents/*.agent.md` file for project-specific customization

This keeps base agent files re-usable across any SOLAR installation and simplifies upgrades.

Read `.github/solar-setup.md` and apply every value to the matching `[POST-IMPLEMENT]` sections across the repository.

**Steps:**

1. Read `.github/solar-setup.md` in full.
2. For each value defined, locate every `[POST-IMPLEMENT]` placeholder across these files and replace with the configured value:
   - `.github/copilot-instructions.md` — project name, architecture, stack, commands, workflow, key files
   - `.github/hooks/hooks.json` — replace `tsc --noEmit` with `TYPECHECK_CMD` + `LINT_CMD`
   - `.github/agents/frontend-implementation-specialist.agent.md` — frontend stack, test runner, folder paths
   - `.github/agents/frontend-test-specialist.agent.md` — frontend test runner, assertion style
   - `.github/agents/backend-implementation-specialist.agent.md` — backend stack, ORM, auth mechanism
   - `.github/agents/backend-test-specialist.agent.md` — backend test runner, fixtures strategy
   - `.github/agents/cache-external-integration-specialist.agent.md` — cache technology if applicable
   - `.github/agents/docs-curator.agent.md` — doc paths, architecture doc location
   - `.github/skills/frontend-feature-implementation/SKILL.md` — framework, folder conventions
   - `.github/skills/frontend-testing/SKILL.md` — test runner commands
   - `.github/skills/backend-feature-implementation/SKILL.md` — framework, ORM conventions
   - `.github/skills/backend-testing/SKILL.md` — test runner commands
   - `apps/frontend/.instructions.md` (or equivalent) — `applyTo` glob, component patterns
   - `apps/backend/.instructions.md` (or equivalent) — `applyTo` glob, API conventions
   - `.github/guides/solar-ralph-workflow.md` — delivery process mapped to repo workflow
   - `.vscode/mcp.json` — remove unused MCP servers
3. After applying, report a summary: which files were updated, which values were skipped (not applicable), and any ambiguities that need manual review.
4. Do NOT activate SOLAR — leave `SOLAR_ACTIVE: false` until the human confirms the apply output looks correct.

Scan the codebase and fill in every value in `.github/solar-setup.md` based on what you find.

**Goal:** Auto-populate `solar-setup.md` so the human only needs to verify and correct values, not type them from scratch.

**Steps:**

1. **Detect Project Identity**
   - Read `package.json` (or `pyproject.toml`, `build.gradle`, etc.) for the project name and description.
   - If not found, infer from the root folder name and `README.md` first paragraph.

2. **Detect Stack**
   - Scan `package.json` dependencies / devDependencies to identify:
     - Frontend framework (`react`, `vue`, `svelte`, `angular`, `next`, `nuxt`, etc.)
     - Frontend test runner (`vitest`, `jest`, `playwright`, `cypress`)
     - Backend framework (`express`, `fastify`, `nestjs`, `hono`, etc.)
     - Backend test runner (`jest`, `vitest`, `supertest`, `mocha`)
     - ORM / database client (`prisma`, `drizzle`, `typeorm`, `mongoose`, `pg`, etc.)
   - Infer auth mechanism from middleware files, route guards, or JWT/session imports.
   - Infer state management from imports (`context`, `redux`, `zustand`, `jotai`, etc.).
   - For non-Node repos, scan equivalent manifest files (`.csproj`, `requirements.txt`, `Cargo.toml`).

3. **Detect Commands**
   - Read `package.json` `scripts` block (or `Makefile`, `justfile`, `taskfile`) to find:
     - `INSTALL_CMD`, `DEV_CMD`, `TEST_CMD`, `TYPECHECK_CMD`, `LINT_CMD`, `BUILD_CMD`
   - Prefer the exact script name as invoked (e.g. `npm run dev`, not `vite`).

4. **Detect Git & Workflow**
   - Read `.github/copilot-instructions.md` for branch naming + commit format conventions.
   - If not present, check `CONTRIBUTING.md`, `docs/guides/git-convention.md`, or equivalent.
   - Detect deployment targets from `vercel.json`, `railway.toml`, `Procfile`, CI config files, or README.

5. **Detect App Boundaries**
   - Find all `.instructions.md` files and note their paths and `applyTo` globs.
   - If not present, infer from folder structure (`apps/frontend`, `apps/backend`, `src/`, etc.) and set reasonable globs.

6. **Detect Documentation Structure**
   - Find the primary architecture doc (`docs/architecture.md` or similar).
   - List the top 3–5 most important docs for agents (BR guide, implementation guide, API spec, etc.).

7. **Write Results to `solar-setup.md`**
   - Replace every `[placeholder]` with the detected value.
   - For values that could not be detected, leave the placeholder but add an inline comment: `# NEEDS MANUAL INPUT`
   - Do NOT change any headings, keys, or structure — only fill in values.

8. **Report**
   - List every field: `FILLED`, `NEEDS MANUAL INPUT`, or `INFERRED (verify)`.
   - Highlight any fields where you made an assumption (e.g., inferred auth mechanism from code pattern rather than explicit config).

**After this command completes**, review the filled values, correct any `NEEDS MANUAL INPUT` fields, then run:

```
/solar-apply-setup
```

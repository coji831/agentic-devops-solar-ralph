<!-- SETUP UTILITY: Run with the default Copilot agent only (no @ prefix). Do not invoke development pipelines, delegate to specialists, or treat this as a feature or bug task. -->

Scan the codebase and write every detected value directly into `.github/solar-setup.md`.

**Goal:** Replace all `[placeholder]` fields in `solar-setup.md` with real values so the human only needs to verify, not type from scratch.

**IMPORTANT — You MUST edit the file, not just report in chat.** Use file-edit tools to overwrite the placeholder values in `.github/solar-setup.md`. Do not summarize findings and stop — the file must be modified on disk before this command is considered complete.

---

**Steps:**

1. **Read the current `solar-setup.md`** — load it so you know which fields still have `[placeholder]` values.

2. **Detect Project Identity**
   - Read `package.json` (or `pyproject.toml`, `build.gradle`, etc.) for the project name and description.
   - If not found, infer from the root folder name and first paragraph of `README.md`.

3. **Detect Stack**
   - Scan `package.json` dependencies / devDependencies to identify:
     - Frontend framework (`react`, `vue`, `svelte`, `angular`, `next`, `nuxt`, etc.)
     - Frontend test runner (`vitest`, `jest`, `playwright`, `cypress`)
     - Backend framework (`express`, `fastify`, `nestjs`, `hono`, etc.)
     - Backend test runner (`jest`, `vitest`, `supertest`, `mocha`)
     - ORM / database client (`prisma`, `drizzle`, `typeorm`, `mongoose`, `pg`, etc.)
   - Infer auth mechanism from middleware files, route guards, or JWT/session imports.
   - Infer state management from imports (`context`, `redux`, `zustand`, `jotai`, etc.).
   - For non-Node repos, scan equivalent manifest files (`.csproj`, `requirements.txt`, `Cargo.toml`).

4. **Detect Commands**
   - Read `package.json` `scripts` block (or `Makefile`, `justfile`, `taskfile`) to find:
     - `INSTALL_CMD`, `DEV_CMD`, `TEST_CMD`, `TYPECHECK_CMD`, `LINT_CMD`, `BUILD_CMD`
   - Prefer the exact command as invoked (e.g. `npm run dev`, not `vite`).

5. **Detect Git and Workflow**
   - Read `.github/copilot-instructions.md` for branch naming and commit format conventions.
   - If not present, check `CONTRIBUTING.md`, `docs/guides/git-convention.md`, or equivalent.
   - Detect deployment targets from `vercel.json`, `railway.toml`, `Procfile`, CI config files, or README.

6. **Detect App Boundaries**
   - Find all `.instructions.md` files and note their paths and `applyTo` globs.
   - If not present, infer from folder structure (`apps/frontend`, `apps/backend`, `src/`, etc.) and set reasonable globs.

7. **Detect Documentation Structure**
   - Find the primary architecture doc (`docs/architecture.md` or similar).
   - List the top 3 to 5 most important docs for agents (BR guide, implementation guide, API spec, etc.).

8. **Write results into `.github/solar-setup.md` using a file-edit tool**
   - Rewrite the file, replacing every `[placeholder]` with the detected value.
   - For values that could not be detected, write: `NEEDS MANUAL INPUT` in place of the placeholder.
   - Do NOT change any headings, keys, or structure. Only replace `[placeholder]` values.
   - You MUST use a file-edit or file-write tool call to save changes. Chat output alone is not enough.

9. **Report**
   - After the file is saved, list every field with status: `FILLED`, `NEEDS MANUAL INPUT`, or `INFERRED (verify)`.
   - Highlight any fields where you made an assumption.

**After this command completes:**

1. Open `.github/solar-setup.md` and review the filled values.
2. Correct any fields marked `NEEDS MANUAL INPUT` — these could not be detected automatically.
3. Once all fields look correct, run the apply command to distribute the values into every agent, skill, hook, and instruction file:

```
/solar-apply-setup
```

> Run `/solar-apply-setup` with the **default Copilot agent** (no `@` prefix) — the same way you ran this command. Do not use the Orchestration Governor for setup commands.

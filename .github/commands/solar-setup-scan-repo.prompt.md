<!-- SETUP UTILITY: Run with @solar-bootstrap agent to ensure governance isolation. Do not invoke pipelines or delegate to specialists. -->

⚠️ **IMPORTANT:** Invoke this command with `@solar-bootstrap` to bypass SOLAR governance:

```
@solar-bootstrap /solar-setup-scan-repo
```

The bootstrap agent will auto-activate bootstrap mode, scan the codebase, and auto-deactivate when done.

<identity>
You are a Solar-Ralph Bootstrap Scanner. You are a non-conversational file worker.
Your only job is to scan the codebase and write detected values into `.github/solar-setup.md`.
</identity>

<critical_constraints>

1. USE TOOLS: You MUST use a file-edit tool to write changes. Do NOT just report in chat.
2. NO CHAT FIRST: Do not explain your plan before editing. Scan, write, then report.
3. PRESERVE STRUCTURE: Only replace `[placeholder]` strings. Do NOT change headings or keys.
4. FALLBACK: If a value cannot be detected, write `NEEDS MANUAL INPUT` — never guess.
5. INFERRED: If a value is an assumption, write `INFERRED: [value]` so the human can verify.
   </critical_constraints>

<task_goal>
Read `.github/solar-setup.md`, then replace every `[placeholder]` with a real value detected from the codebase.
</task_goal>

<detection_steps>
Step 1 - READ: Load `.github/solar-setup.md` to see which fields need filling.

Step 2 - IDENTITY: Read `package.json` for name and description. If missing, use root folder name + first line of `README.md`.

Step 3 - STACK: Scan `package.json` dependencies for:

- Frontend: react, vue, next, nuxt, svelte, angular
- Backend: express, fastify, nestjs, hono
- ORM/DB: prisma, drizzle, typeorm, mongoose, pg
- Auth: look for jwt, bcrypt, passport, next-auth in imports or middleware files
- State: context, redux, zustand, jotai
- Test runners: vitest, jest, playwright, cypress, supertest

Step 4 - COMMANDS: Read `package.json` scripts block. Map to:
INSTALL_CMD, DEV_CMD, TEST_CMD, TYPECHECK_CMD, LINT_CMD, BUILD_CMD
Use the exact npm/yarn/pnpm invocation (e.g. "npm run dev", not "vite").

Step 5 - GIT: Read `.github/copilot-instructions.md` or `docs/guides/git-convention.md` for branch naming and commit format.

Step 6 - BOUNDARIES: Find all `.instructions.md` files. Note their paths and applyTo globs.
If none exist, infer from folder structure (apps/frontend, apps/backend, src/).

Step 7 - DOCS: Find `docs/architecture.md` or equivalent. List top 3-5 agent-relevant docs.

Step 8 - WRITE: Use a file-edit tool to overwrite every `[placeholder]` in `.github/solar-setup.md`.
Do not change structure. Undetected values become `NEEDS MANUAL INPUT`.

Step 9 - REPORT: After saving, list each field as FILLED, NEEDS MANUAL INPUT, or INFERRED.
</detection_steps>

<example_transformation>
Before: FRONTEND_FRAMEWORK: [placeholder]
Detected: "dependencies": { "react": "^18.0.0" }
After: FRONTEND_FRAMEWORK: react
</example_transformation>

---

**After this command completes:**

1. Open `.github/solar-setup.md` and review the values.
2. Fix any fields marked `NEEDS MANUAL INPUT` or `INFERRED`.
3. Run the next step to apply values to core files:

```
/solar-setup-core-config
```

> Use the **default Copilot agent** (no `@` prefix) for all setup commands.

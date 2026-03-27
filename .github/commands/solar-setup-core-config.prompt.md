<!-- SETUP UTILITY: Run with @solar-bootstrap agent to ensure governance isolation. Do not invoke pipelines or delegate to specialists. -->

⚠️ **IMPORTANT:** Invoke this command with `@solar-bootstrap` to bypass SOLAR governance:

```
@solar-bootstrap /solar-setup-core-config
```

The bootstrap agent will auto-activate bootstrap mode, apply config values, and auto-deactivate when done.

<identity>
You are a Solar-Ralph Core Config Applier. You are a non-conversational file worker.
Your only job is to read solar-setup.md and apply its values to the core SOLAR config files.
</identity>

<critical_constraints>

1. USE TOOLS: You MUST use file-edit tools to write changes. Do NOT just report in chat.
2. NO CHAT FIRST: Edit files first, then report what changed.
3. PRESERVE STRUCTURE: Replace `[POST-IMPLEMENT]` blocks and placeholder tokens only. Do not rewrite whole files.
4. DO NOT ACTIVATE: Leave `SOLAR_ACTIVE: false` in `.ai_ledger.md`. Do not change it.
5. MERGE RULE: If `.github/copilot-instructions.md` already has project content, MERGE the SOLAR-Ralph sections in — do not replace the whole file.
   </critical_constraints>

<task_goal>
Read `.github/solar-setup.md` and apply every configured value to the 4 core SOLAR files listed below.
</task_goal>

<target_files>

1. `.github/copilot-instructions.md` — fill: project name, Quick Start commands, Architecture, Workflow, Naming, Testing, Git sections
2. `.github/hooks/hooks.json` — replace `tsc --noEmit` with TYPECHECK_CMD value from setup
3. `.github/guides/solar-ralph-workflow.md` — fill: delivery process, branch naming, deployment targets
4. `.ai_ledger.md` — confirm SOLAR_ACTIVE is false; fill repo name in header comment only
   </target_files>

<execution_steps>
Step 1 - READ: Load `.github/solar-setup.md` in full. Note all values.

Step 2 - CHECK UNFILLED: If any field still says `[placeholder]` or `NEEDS MANUAL INPUT`,
auto-detect it from the codebase (package.json, README, folder structure).
Write the detected value back into `.github/solar-setup.md` before continuing.

Step 3 - APPLY to `.github/copilot-instructions.md`:

- Replace `[YOUR-REPO-NAME]` with REPO_NAME.
- Fill Quick Start section with INSTALL_CMD, DEV_CMD, TEST_CMD.
- Fill Architecture section with FRONTEND_STACK, BACKEND_STACK, STATE_APPROACH, AUTH_APPROACH.
- Fill Workflows section with DEV_WORKFLOW, DEPLOY_TARGETS.
- Fill Git section with BRANCH_FORMAT, COMMIT_FORMAT.
- Fill Key Files section with ARCHITECTURE_DOC and other KEY_DOCS values.
- If the file already exists with project content, merge only the SOLAR-Ralph Operating Overlay subsection.

Step 4 - APPLY to `.github/hooks/hooks.json`:

- Replace `tsc --noEmit` with TYPECHECK_CMD from setup config.
- If LINT_CMD is set, append it as a second check after the typecheck.

Step 5 - APPLY to `.github/guides/solar-ralph-workflow.md`:

- Fill `[POST-IMPLEMENT]` blocks with DEV_WORKFLOW and DEPLOY_TARGETS.
- Fill branch naming and commit format from GIT_BRANCH_FORMAT and GIT_COMMIT_FORMAT.

Step 6 - REPORT: List each file as UPDATED or SKIPPED (with reason). Flag any values that could not be applied.
</execution_steps>

<example_transformation>
Before: Install: `[install command]` | Dev: `[dev command]`
Setup value: INSTALL_CMD: npm install, DEV_CMD: npm run dev
After: Install: `npm install` | Dev: `npm run dev`
</example_transformation>

---

**After this command completes:**

Run the next step to apply values to all agent, skill, and path instruction files:

```
/solar-setup-agent-config
```

> Use `@solar-bootstrap` for all setup commands to ensure they run in isolation from SOLAR governance.

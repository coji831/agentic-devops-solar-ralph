---
name: solar-setup-quick
description: Quick SOLAR setup - scan + config + activate (all-in-one, Tier 1)
agent: Solar Bootstrap
---

<solar_setup_invocation command="/solar-setup-quick">

<identity>
You are the Solar-Ralph Quick Setup Agent. Your job is to get SOLAR operational in a target repository with minimal ceremony: detect project details, apply configuration, and activate the system.

Your progress output format for Tier 1 (override the bootstrap agent's pass-by-pass format):

```
🤖 Solar Bootstrap  |  model: GPT-5 mini  |  tier: 1 (lean scan)
🔧 BOOTSTRAP MODE ACTIVE

📡 Read 1 -- Merged MD Sweep (stack + conventions)...
📦 Read 2 -- Manifest Probes (package.json, workspace domains)...
🗂️ Read 3 -- Existing Instructions Check...
🔀 Pass 3 -- Domain Mapping (logic only)...
⚙️ Pass 4 -- Workflow Detection (manifest sources only)...
💾 Writing solar-project-profile.json...

✅ Setup operation complete
🔒 Bootstrap mode deactivated
```

Output each line immediately before its corresponding action.
</identity>

<task_goal>
Execute a complete SOLAR setup in one command:

1. Run lean scan (1 merged MD sweep + manifest probes, no subagent) -> write `.github/solar-project-profile.json`
2. Process template files -> merge/rename `.template.*` into working files
3. Domain-seed core SOLAR files -> apply scan results to minimum required core files
4. Activate SOLAR -> set `"active": true` in `.github/solar.config.json`
5. Verify setup completeness
6. Report completion -> guide user to smoke test
   </task_goal>

<execution_steps>

<step id="1" title="Scan Repository (Lean -- 1 MD Sweep + Manifest Probes)">
Tier 1 uses a lean scan: one merged MD sweep + manifest probes only. No subagent invocation. Never run separate sweeps.

**Read 1 -- Merged MD Sweep (Pass 1 Phase A + Pass 2 combined):**
Read all `**/*.md` files exactly once. Simultaneously extract:

- Stack signals: technology names, framework mentions, service names, infrastructure references -> for `projectType`, `domains[]`, agent roster
- Convention signals: files containing "must", "should", "never", "always", naming patterns, checklist items, commit format rules -> for `conventions`

Score convention confidence: `high` = 3+ signals | `medium` = partial checklist or README contributing section | `low` = fewer than 3 -> set `NEEDS MANUAL INPUT`

**Read 2 -- Manifest Probe (Pass 1 Phase B + Pass 5 Phase A combined):**
Locate any `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `*.tf`, `tsconfig.json` at any depth.

- Extract: dependencies, devDependencies, scripts, project name -> authoritative stack values
- Label each containing subfolder as a workspace domain (feeds `domains[]` and folder structure)
- Merge with MD sweep results, preferring manifest values for authoritative names

**Read 3 -- Existing Instructions Check (Pass 5 Phase C):**
Check for existing `.instructions.md` files at any path. Record `existingInstructions: [paths]`. Do NOT overwrite.

**Pass 3 -- Domain Mapping (no file reads):**
From merged results: assign `projectType`, `domains[]`, agent roster, instruction file list. Pure logic -- no additional reads.

**Pass 4 -- Workflow Detection (Phase A only -- no subagent):**
Read `package.json` scripts block, check `.github/workflows/*.yml` job names, check `scripts/*.sh` and `scripts/*.ps1` filenames. Store as `existingWorkflows[]`. No MD sweep, no subagent invocation.

Write results to `.github/solar-project-profile.json`.
Standard capture posture: if a value cannot be detected with confidence, write `"unknown"` -- do NOT use `INFERRED:` or `LOW-CONFIDENCE:` markers. Quick setup produces a baseline profile; use `/solar-setup-full` for greedy domain-adaptive capture.
</step>

<step id="2" title="Process Template Files">
Execute bootstrap agent Task 4 (Process Template Files):

- Check if `.gitignore`, `.github/AGENTS.md`, `.github/.ai_ledger.md` already exist
- If YES: Merge SOLAR sections from templates with existing files
- If NO: Rename `.template.*` files to final names
- Report each operation (merge or rename)
  </step>

<step id="3" title="Apply Core Configuration (Redistribute Placeholders)">
Execute bootstrap agent Task 5 (Redistribute Placeholders, tier: quick) to replace placeholders in 4 core instruction files:

Target files:

- `.github/instructions/architecture.instructions.md`
- `.github/instructions/conventions.instructions.md`
- `.github/instructions/workflow.instructions.md`
- `.github/instructions/solar.instructions.md`

For each file:

1. Read file content
2. Replace `[FILL IN -- e.g., VALUE]` patterns with values from `solar-project-profile.json`
3. Replace `[POST-IMPLEMENT]` markers with tech stack context
4. If profile confidence is low, prefix value with `"INFERRED: "`
5. Write updated file

Also update:

- `.github/hooks/hooks.json` (fill TypeScript check command if applicable)
- `.github/guides/solar-ralph-workflow.md` (fill repo-specific guidance)
  </step>

<step id="4" title="Activate SOLAR">
Update `.github/solar.config.json`:

- Change `"active": false` to `"active": true`
- Keep all other settings unchanged
  </step>

<step id="5" title="Verify Setup Completeness">
Execute bootstrap agent Task 6 (Verify Setup Completeness) to check for remaining placeholders:

1. Grep for `[FILL IN -- e.g., *]`, `[POST-IMPLEMENT]`, `[SCAN-INCOMPLETE]` patterns in quick-tier scoped SOLAR files
2. Collect matches by file + line number
3. Categorize as: INFERRED values (need review), unresolved placeholders (need manual input)
4. Store results for inclusion in completion report
   </step>

<step id="6" title="Report Completion">
Output structured completion report including verification results:

```
========================================
✅ SOLAR-Ralph Quick Setup Complete
========================================

Files created/updated:
- .github/solar-project-profile.json (scan results -- standard posture)
- .github/.ai_ledger.md (pure skeleton from template, ready for first session)
- .github/instructions/*.instructions.md (4 core files, placeholders filled)
- .github/hooks/hooks.json (lifecycle hooks)
- .github/solar.config.json (active: true)
- .github/solar-system/logs/ (per-session activity log, gitignored)

Template processing:
- [Results from Task 4 (Process Template Files) -- merge/rename operations]

Configuration:
- [Results from Task 5 (Redistribute Placeholders, tier: quick) -- X/Y placeholders resolved]

🔍 Verification:
- [Results from Task 6 (Verify Setup Completeness) -- INFERRED values, unresolved placeholders]

Next steps:
1. Review INFERRED values and update if incorrect
2. Fill in any unresolved placeholders manually
3. Smoke test: `/ralph-loop "Add a README badge"`
4. If it works -> SOLAR is operational
5. If it fails -> check `.github/solar-system/.learnings/ERRORS.md` and retry

Optional customization:
- For Tier 2 greedy scan + domain-adaptive instructions/workflows: `/solar-setup-full`
```

</step>

</execution_steps>

<constraints>
- Requires `.github/.ai_ledger.template.md` to exist
- Do NOT update `.github/solar-project-profile.json` if it already contains fully detected values (user may have run `/solar-setup-scan-repo` and corrected values manually)
- Do NOT create domain instruction files -- quick setup skips those (use `/solar-setup-full` for Tier 2 instruction + workflow generation)
</constraints>

<error_handling>

1. **Template ledger missing**:
   -> Output: "⚠️ `.github/.ai_ledger.template.md` not found. Run the minimal installer first."
2. **Profile already exists with detected values**:
   -> Skip scan, read from existing `.github/solar-project-profile.json` and proceed to Step 2.
3. **Ledger already exists**:
   -> Skip creation, report: "`.github/.ai_ledger.md` already exists. Keeping existing file."
4. **SOLAR already active**:
   -> Report: "⚠️ SOLAR is already active (`solar.active: true` in config). No changes made."
   </error_handling>

<forbidden_actions>

- Do NOT invoke other agents or specialists
- Do NOT update AGENTS.md
- Do NOT open a loop or update task lists
- Do NOT scan the codebase beyond what's needed for detection logic
  </forbidden_actions>

<bootstrap_mode>
This command runs in bootstrap mode -- all SOLAR governance is bypassed. The agent:

- Ignores solar-system/pipelines/ stage definitions
- Ignores existing .github/.ai_ledger.md work state
- Ignores memory files
- Works as a simple file-editing utility
  </bootstrap_mode>
  </solar_setup_invocation>

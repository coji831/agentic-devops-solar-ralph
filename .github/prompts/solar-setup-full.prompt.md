---
name: solar-setup-full
description: Full SOLAR setup - 5-pass scan + adaptive config + memory seeding + workflow generation + agent roster (Tier 2)
agent: Solar Bootstrap
---

SOLAR_BOOTSTRAP_COMMAND: /solar-setup-full

# SOLAR-Ralph Full Setup

<identity>
You are the Solar-Ralph Full Setup Agent. Your job is to get SOLAR operational with complete Tier 2 adaptive customization: run the 5-pass over-scan to produce a structured project profile, then use that profile to generate domain-adaptive memory files, path-specific instructions, inferred workflow files, and a project-tuned agent roster.
</identity>

<task_goal>
Execute a complete Tier 2 SOLAR setup with adaptive configuration:

1. Run 5-pass over-scan → write `.github/solar-project-profile.json`
2. Apply core configuration → `.github/instructions/solar.instructions.md`, hooks, guides
3. Apply domain-adaptive agent + skill configuration → from detected agent roster in profile
4. Seed domain-adaptive memory files → from Pass 3 domain memory mapping
5. Generate path-specific `.instructions.md` files → from Pass 5 folder structure probe
6. Generate inferred `.workflow.md` files → from Pass 4 workflow inference, into `.github/solar-workflows/`
7. Create scaffolding → `.github/.ai_ledger.md` from template
8. Activate SOLAR → set `"active": true` in `.github/solar.config.json`
9. Report completion → guide user to smoke test
   </task_goal>

<execution_steps>

### Step 1: Scan Repository

Execute the `<scan_protocol>` from the Solar Bootstrap agent (all 5 passes):

- Pass 1: Stack Detection — identify projectType, domains, agent roster
- Pass 2: Convention Ingestion — `**/*.md` semantic sweep for naming rules and standards
- Pass 3: Domain Memory Mapping — select memory template set from projectType
- Pass 4: Workflow Inference — detect delivery workflows from `**/*.md` sweep
- Pass 5: Folder Structure Probe — detect workspace layout, find existing `.instructions.md`

Write results to `.github/solar-project-profile.json`.
If any value is uncertain, use `"unknown"` or add `// INFERRED: <value>` comment for human verification.

### Step 2: Apply Core Configuration

Apply detected values from `.github/solar-project-profile.json` to core SOLAR files (same logic as `/solar-setup-core-config`):

- Update `.github/instructions/solar.instructions.md` (fill placeholders with repo name, tech stack)
- Update `.github/hooks/hooks.json` (fill TypeScript check command if applicable)
- Update `.github/guides/solar-ralph-workflow.md` (fill repo-specific guidance)

### Step 3: Apply Domain-Adaptive Agent Configuration

Apply detected values to agents and skills using the `agentRoster` from `.github/solar-project-profile.json`.
Do NOT apply to hardcoded agent lists — only update agents present in the detected roster.

**Agent update logic:**

- Read `agentRoster` array from profile
- For each agent in roster, locate its `.github/agents/<agent-name>.agent.md` file
- Replace `[POST-IMPLEMENT]` placeholders with tech stack values from profile `domains[]`
- If agent file does not exist, skip and record in report

**Skill update logic:**

- For each domain in `domains[]`, locate matching skill files in `.github/skills/`
- Replace `[POST-IMPLEMENT]` placeholders with domain-specific stack values
- Skip skill files with no `[POST-IMPLEMENT]` placeholders (already customized)

### Step 4: Generate Domain-Adaptive Instruction Files

Using Pass 3 results from the profile (`instructions.files[]`):

- Create `.github/instructions/<name>.instructions.md` for each file listed in the profile
- Populate each file with values detected in Passes 1–2 (commands, folder paths, stack names)
- Add `[SCAN-INCOMPLETE]` markers for fields that could not be auto-detected
- Add YAML frontmatter: `applyTo: "<scope>"` and `scan-confidence: <high|medium|low>`
- Do NOT overwrite existing instruction files — merge detected values or flag conflicts with `// CONFLICT: <existing-value>`
- Path-scoped files (backend, frontend): use the detected domain path from `domains[]` for `applyTo`

### Step 5: Generate Path-Specific `.instructions.md`

Using Pass 5 results from the profile (`domains[].instructionsFile` + `existingInstructions[]`):

- For each domain that does NOT already have an `.instructions.md` (per `existingInstructions[]`): create it at `<domain.path>/.instructions.md`
- Each file includes:
  - YAML frontmatter: `applyTo: "<domain.path>/**"` and `scan-confidence: <value>`
  - Domain-specific guidance extracted from Passes 1–4 (stack, test command, detected conventions)
  - `[POST-IMPLEMENT]` markers for any guidance that could not be auto-populated
- If flat repo (`fallbacksTriggered` includes `folder-structure-probe-flat-repo`): fold path guidance into `.github/copilot-instructions.md` instead

### Step 6: Generate Inferred Workflow Files

Using Pass 4 results from the profile (`workflows.inferred[]` + `workflows.scaffolded[]`):

- Create `.github/solar-workflows/` directory if it does not exist
- For each inferred workflow: write `<name>.workflow.md` with:
  - YAML frontmatter: `name`, `description`, `status: inferred`, `source: <file>`, `confidence: <value>`
  - Body: extracted step sequence from source file
  - `[POST-IMPLEMENT]` markers for steps that could not be extracted
- For each scaffolded workflow: write blank template with `[POST-IMPLEMENT]` markers throughout
- Skip files that already exist in `.github/solar-workflows/`

### Step 7: Create Scaffolding

Create the working ledger from template:

- Read `.github/.ai_ledger.template.md`
- Create `.github/.ai_ledger.md` with:
  - Replace `[REPO_NAME]` placeholder with actual repo name
  - Set `Session-Type: chat`
  - Set `Completion Promise: (none)`
  - Keep all other fields from template

**Instruction files are seeded in Step 4.** Instruction seeding is part of Tier 2 full setup.

### Step 8: Activate SOLAR

Update `.github/solar.config.json`:

- Change `"active": false` to `"active": true`
- Keep all other settings unchanged

### Step 9: Report Completion

Output structured completion report:

```
========================================
✅ SOLAR-Ralph Full Setup Complete (Tier 2)
========================================

Files created/updated:
- .github/solar-project-profile.json (scan results)
- .github/.ai_ledger.md (work ledger)
- .github/instructions/solar.instructions.md (SOLAR guidance)
- .github/hooks/hooks.json (lifecycle hooks)
- .github/solar.config.json (active: true)
- <N> agent files (domain-adaptive, from detected roster)
- <N> skill files (domain-adaptive)
- <N> instruction files in .github/instructions/ (domain-seeded via Pass 3)
- <N> .instructions.md files (path-specific, from Pass 5)
- <N> .workflow.md files in .github/solar-workflows/ (inferred or scaffolded)

Fallbacks triggered: <list or none>

Next steps:
1. Smoke test: `/ralph-loop "Add a README badge"`
2. Review [SCAN-INCOMPLETE] and [POST-IMPLEMENT] markers across generated files
3. If it works → SOLAR is operational
4. If it fails → check errors and retry

Optional enhancements:
- Memory population: @Orchestration-Governor to explore codebase
- Workflow refinement: edit .github/solar-workflows/*.workflow.md
```

</execution_steps>

<constraints>
- Only run AFTER full installer has downloaded all files
- Requires `.github/.ai_ledger.template.md` to exist
- Requires all agent and skill files to exist
- Do NOT update `.github/solar-project-profile.json` if it already contains fully detected values (user may have run `/solar-setup-scan-repo` and corrected values manually)
- Instruction files are seeded from the profile — do NOT skip them in full setup
</constraints>

<error_handling>

1. **Template ledger missing**:
   → Output: "⚠️ `.github/.ai_ledger.template.md` not found. Run the installer first."
2. **Profile already exists with detected values**:
   → Skip scan, read from existing `.github/solar-project-profile.json` and proceed to Step 2.
3. **Agent files missing**:
   → Output: "⚠️ Agent files not found. Run the full installer (install-solar.ps1/sh) first."
4. **Ledger already exists**:
   → Skip creation, report: "`.github/.ai_ledger.md` already exists. Keeping existing file."
5. **SOLAR already active**:
   → Report: "⚠️ SOLAR is already active (`solar.active: true` in config). Reconfiguring files anyway."
   </error_handling>

<forbidden_actions>

- Do NOT invoke other agents or specialists
- Do NOT update AGENTS.md
- Do NOT open a loop or update task lists
  </forbidden_actions>

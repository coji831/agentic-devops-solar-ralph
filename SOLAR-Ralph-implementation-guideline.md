# SOLAR-Ralph Implementation Guideline

A streamlined installation and setup flow for SOLAR-Ralph with two clear paths: Quick Setup (recommended) for fastest deployment, or Full Setup (advanced) for complete customization.

## TL;DR

1. **Install:** Download all SOLAR files (one installer, ~60 files)
2. **Setup:** Choose your path
   - **Quick:** `/solar-setup-quick` → core config only, fastest (recommended)
   - **Full:** `/solar-setup-full` → core + agent/skill customization
3. **Test:** `/ralph-loop "Add a README badge"` → verify SOLAR works

---

## Installation (Single Step)

Download all SOLAR-Ralph files to your repository root:

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install.ps1; .\install.ps1; Remove-Item install.ps1
```

**macOS / Linux (Bash):**

```bash
curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh | bash
```

**What gets downloaded (~60 files):**

- Orchestration contract (AGENTS.md)
- All 14 agents (governor, specialists, auditors, architect)
- All 14 skills (implementation, testing, review, governance)
- All setup commands and runtime commands
- Lifecycle hooks (hooks.json + 3 .cjs files)
- Operator guides (5 guides)
- Knowledge base (6 pattern guides)
- Verification artifacts folder

---

## Setup Options

### Option 1: Quick Setup (Partial Customization For Your Project - Recommended)

**Run:**

```text
/solar-setup-quick
```

**What it does:**

- Scans repository and detects project details
- Applies core configuration (instructions, hooks, guides)
- Creates working ledger from template
- Activates SOLAR (sets `solar.active: true`)
- Uses default agent settings (no customization)

**Time:** ~2 minutes  
**Best for:** Getting SOLAR running quickly, standard tech stacks

**Next:** Smoke test with `/ralph-loop "Add a README badge"`

**Optional later:** Run `/solar-setup-agent-config` to customize agents/skills with your tech stack

---

### Option 2: Full Setup (Full Customization)

**Run:**

```text
/solar-setup-full
```

**What it does:**

- Everything Quick Setup does
- **PLUS:** Customizes all 14 agents with your tech stack
- **PLUS:** Customizes all 14 skills with your frameworks
- Updates frontend/backend specialist instructions
- Updates implementation and testing skill guidance

**Time:** ~5 minutes  
**Best for:** Complex monorepos, non-standard stacks, teams wanting full customization

**Next:** Smoke test with `/ralph-loop "Add a README badge"`

---

## Smoke Test

After either setup, verify SOLAR works end-to-end:

```text
/ralph-loop "Add a README badge"
```

**Expected behavior:**

- Governor orchestrates the task
- Specialist implements the change
- Tests run automatically
- Loop completes with success message

**If it fails:** Check errors, verify setup files exist, retry with `/solar-setup-quick` or `/solar-setup-full`

---

## Manual Setup (Troubleshooting Only)

If automated setup fails, run individual steps:

1. **Scan repository:**

   ```
   /solar-setup-scan-repo
   ```

   Review `.github/solar-setup.md` and correct any misdetections

2. **Apply core config:**

   ```
   /solar-setup-core-config
   ```

3. **Apply agent config (optional):**

   ```
   /solar-setup-agent-config
   ```

4. **Create scaffolding:**

   ```
   /solar-setup-scaffold
   ```

5. **Manually activate:** Edit `.github/solar.config.json`, set `"active": true`

---

## Advanced Setup (Optional)

### Memory Templates

Create structured fact files for the governor to populate:

```
/solar-setup-memory
```

**Creates:** 7 memory template files in `.github/memories/repo/`

- commands.md
- architecture.md
- workflow-facts.md
- frontend-facts.md
- backend-facts.md
- security-facts.md
- verification-facts.md

**Populate:** Run `@Orchestration-Governor explore the codebase and populate .github/memories/repo/` (optional, for faster subsequent sessions)

---

## Implementation Status

**✅ Completed:**

- Single installer downloads all files
- Two setup paths: Quick (fast) and Full (customized)
- All core files in `.github/` structure
- Config-based activation (`solar.active` in config)
- Ledger template approach
- Complete agent and skill customization support

**🎯 Ready for Use:**
Install → Choose setup path → Smoke test → SOLAR is operational!

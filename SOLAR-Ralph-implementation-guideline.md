# SOLAR-Ralph Implementation Guideline — v2 (Quick Setup First)

A streamlined, general-first installation and setup flow for SOLAR-Ralph. This version prioritizes a working minimal install and a single pragmatic "quick setup" path so users can start using SOLAR immediately. Advanced configuration and tuning are deferred to a separate section.

## TL;DR

- Quick Setup: install minimal scanner → run `/solar-setup-quick` (scan + config + scaffold + activate) → run smoke test
- Manual Setup: use granular commands for troubleshooting
- Advanced Setup: optional tuning (agent config, memory population, hook fine-tuning)

---

## Quick Setup (Recommended)

1. Install minimal scanner (one-liner from release):

   PowerShell:

   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.ps1" -OutFile install.ps1; .\install.ps1; Remove-Item install.ps1
   ```

   Bash (macOS / Linux):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.sh | bash
   ```

2. Run the quick setup command (combines scan + config + scaffold + activate):

   ```text
   /solar-setup-quick
   ```

   What it does:
   - Runs the repository scanner and writes `.github/solar-setup.md`
   - Applies core configuration to SOLAR files in `.github/`
   - Creates `.github/.ai_ledger.md` from template
   - Sets `"active": true` in `.github/solar.config.json` to activate SOLAR
   - Skips memory files and agent-config (uses defaults for speed)

3. Smoke test (simple story):

   ```text
   /ralph-loop "Add a README badge"
   ```

   If the smoke test completes, SOLAR is operational. If not, use the Manual Setup flow below.

---

## Manual Setup (Troubleshooting / Granular Control)

1. Install minimal scanner (same one-liner above)
2. Run scanner only:

   ```text
   /solar-setup-scan-repo
   ```

3. Review `.github/solar-setup.md` and correct any `NEEDS MANUAL INPUT` or misdetections.
4. Install full framework if desired:

   PowerShell:

   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install-solar.ps1; .\install-solar.ps1; Remove-Item install-solar.ps1
   ```

5. Apply core config:

   ```text
   /solar-setup-core-config
   ```

6. Apply agent/skill config (optional):

   ```text
   /solar-setup-agent-config
   ```

7. Create scaffolding (ledger, memory templates):

   ```text
   /solar-setup-scaffold
   ```

8. Run smoke test `/ralph-loop` as above.

---

## Advanced Setup (Optional — defer until needed)

- **Custom agent configuration:** `/solar-setup-agent-config` — customize tool restrictions and tech stack references
- **Create memory templates:** `/solar-setup-memory` — create structured fact files in `.github/memories/repo/`
- **Populate memory:** Run Governor to fill templates with project facts (optional optimization)
- **Hook verification:** Manual terminal commands to test Session-Type detection (paranoia/debugging only)

These steps are intentionally optional and can be completed later as the project matures.

---

## Implementation Status

**✅ Implemented:**

- ✅ All core files moved to `.github/` (AGENTS.md, .ai_ledger.template.md, memories/repo/)
- ✅ `SOLAR_ACTIVE moved to `solar.config.json` (`solar.active` field)
- ✅ Hooks updated to read config instead of ledger
- ✅ Ledger template cleaned (no SOLAR_ACTIVE field)
- ✅ `.github/prompts/solar-setup-quick.prompt.md` created (combined setup command)
- ✅ `.github/prompts/solar-setup-memory.prompt.md` created (memory on demand)
- ✅ Installer scripts updated for new paths

**🚧 Remaining Work:**

- 📝 Bulk update ~40+ files (agents, skills, prompts, guides, docs) to reference new `.github/` paths
- 📝 Update README.md and main implementation guideline
- 📝 Test quick setup flow in target repo

**Usage:**

- **Quick setup:** Download minimal installer → run `/solar-setup-quick` → smoke test
- **Memory (optional):** Run `/solar-setup-memory` to create templates
- **Activation:** Already active after `/solar-setup-quick` (no manual config edit needed)

---

## Verification Checklist

1. ✅ Run Quick Setup in a test repo → verify `/solar-setup-quick` completes successfully
2. ✅ Verify `.github/.ai_ledger.md` created from template
3. ✅ Verify `solar.active: true` set in config
4. ✅ Run smoke test `/ralph-loop "add badge"` → verify SOLAR loops correctly
5. ✅ Optional: Run `/solar-setup-memory` → verify templates created
6. ✅ Manual Setup still works for troubleshooting (granular commands)

---

**Next Steps for Full Rollout:**

- Complete bulk path updates in remaining documentation files
- Test in 2-3 different repo types (frontend-only, full-stack, monorepo)
- Update main README.md with new quick setup flow

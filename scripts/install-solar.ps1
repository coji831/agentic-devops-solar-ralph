# install-solar.ps1 - SOLAR-Ralph Installer for Windows (PowerShell)
#
# Downloads all SOLAR-Ralph files into the current repo from GitHub.
# Run this from the ROOT of your target repo.
#
# One-liner install:
#   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install-solar.ps1; .\install-solar.ps1; Remove-Item install-solar.ps1
#
# Options:
#   -Force    Overwrite existing files (default: skip files that already exist)

param(
    [switch]$Force
)

$REPO       = "coji831/agentic-devops-solar-ralph"
$BRANCH     = "main"
$BASE_URL   = "https://raw.githubusercontent.com/$REPO/$BRANCH"

# All files to download into the target repo
$FILES = @(
    # Root contracts
    ".github/AGENTS.md",
    ".github/.ai_ledger.template.md",

    # Setup config (fill this first, then run /solar-setup-core-config)
    ".github/solar-setup.md",

    # Agents - universal (governance, auditors, architect)
    ".github/agents/orchestration-governor.agent.md",
    ".github/agents/design-planning-architect.agent.md",
    ".github/agents/bug-investigation-specialist.agent.md",
    ".github/agents/frontend-review-auditor.agent.md",
    ".github/agents/backend-review-auditor.agent.md",
    ".github/agents/release-readiness-specialist.agent.md",
    ".github/agents/security-auditor.agent.md",

    # Agents - [POST-IMPLEMENT] (update Tech Stack section per repo)
    ".github/agents/frontend-implementation-specialist.agent.md",
    ".github/agents/frontend-test-specialist.agent.md",
    ".github/agents/backend-implementation-specialist.agent.md",
    ".github/agents/backend-test-specialist.agent.md",
    ".github/agents/docs-curator.agent.md",
    ".github/agents/cache-external-integration-specialist.agent.md",

    # Agents - bootstrap (setup utilities only)
    ".github/agents/solar-bootstrap.agent.md",

    # Hooks
    ".github/hooks/hooks.json",
    ".github/solar.config.json",
    ".github/hooks/user-prompt-submit.cjs",
    ".github/hooks/post-tool-use.cjs",
    ".github/hooks/stop.cjs",

    # Commands
    ".github/commands/ralph-loop.prompt.md",
    ".github/commands/audit-story.prompt.md",

    # Setup prompts
    ".github/prompts/solar-setup-quick.prompt.md",
    ".github/prompts/solar-setup-scan-repo.prompt.md",
    ".github/prompts/solar-setup-core-config.prompt.md",
    ".github/prompts/solar-setup-agent-config.prompt.md",
    ".github/prompts/solar-setup-scaffold.prompt.md",
    ".github/prompts/solar-setup-memory.prompt.md",
    ".github/prompts/solar-enter-bootstrap.prompt.md",
    ".github/prompts/solar-exit-bootstrap.prompt.md",

    # Skills - universal
    ".github/skills/frontend-review/SKILL.md",
    ".github/skills/backend-review/SKILL.md",
    ".github/skills/story-execution/SKILL.md",
    ".github/skills/doc-sync/SKILL.md",
    ".github/skills/memory-curation/SKILL.md",
    ".github/skills/memory-verification/SKILL.md",
    ".github/skills/recursive-remediation/SKILL.md",
    ".github/skills/release-governance/SKILL.md",
    ".github/skills/browser-reproduction/SKILL.md",
    ".github/skills/external-integration-operations/SKILL.md",

    # Skills - [POST-IMPLEMENT] (update Tech Stack section per repo)
    ".github/skills/frontend-feature-implementation/SKILL.md",
    ".github/skills/frontend-testing/SKILL.md",
    ".github/skills/backend-feature-implementation/SKILL.md",
    ".github/skills/backend-testing/SKILL.md",

    # Operator guides
    ".github/guides/agent-operations-guide.md",
    ".github/guides/memory-governance-guide.md",
    ".github/guides/bootstrap-mode-guide.md",
    ".github/guides/mcp-operations-guide.md",
    ".github/guides/solar-ralph-workflow.md",

    # Verification artifacts
    "verification-artifacts/README.md",
    "verification-artifacts/.gitkeep",

    # Repo memory scaffolding (agent fills these; delete from git after ingestion)
    ".github/memories/repo/commands.md",
    ".github/memories/repo/architecture.md",
    ".github/memories/repo/workflow-facts.md",
    ".github/memories/repo/frontend-facts.md",
    ".github/memories/repo/backend-facts.md",
    ".github/memories/repo/security-facts.md",
    ".github/memories/repo/verification-facts.md"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SOLAR-Ralph Installer" -ForegroundColor Cyan
Write-Host "  Repo: $REPO @ $BRANCH" -ForegroundColor DarkGray
Write-Host "  Target: $PWD" -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($Force) {
    Write-Host "  Mode: FORCE (overwriting existing files)" -ForegroundColor Yellow
    Write-Host ""
}

$downloaded = 0
$skipped    = 0
$failed     = 0
$failedList = @()

foreach ($file in $FILES) {
    $dest = Join-Path $PWD $file
    $url  = "$BASE_URL/$file"

    if ((Test-Path $dest) -and -not $Force) {
        Write-Host "  SKIP  $file" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    # Create parent directory if needed
    $dir = Split-Path $dest -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction Stop
        Write-Host "  OK    $file" -ForegroundColor Green
        $downloaded++
    } catch {
        Write-Host "  FAIL  $file" -ForegroundColor Red
        Write-Host "        $($_.Exception.Message)" -ForegroundColor DarkRed
        $failed++
        $failedList += $file
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Downloaded : $downloaded" -ForegroundColor Green
Write-Host "  Skipped    : $skipped (already exist)" -ForegroundColor DarkGray
Write-Host "  Failed     : $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "DarkGray" })
Write-Host "========================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    Write-Host ""
    Write-Host "Failed files:" -ForegroundColor Red
    $failedList | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Re-run with -Force to retry failed files." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick Setup (Recommended):"
Write-Host "    Run /solar-setup-quick in Copilot chat"
Write-Host "    (combines scan + config + scaffold + activate)"
Write-Host ""
Write-Host "  Manual Setup (Troubleshooting):"
Write-Host "    1. Run /solar-setup-scan-repo to detect project details"
Write-Host "    2. Review .github/solar-setup.md and correct any misdetections"
Write-Host "    3. Run /solar-setup-core-config to apply config"
Write-Host "    4. Run /solar-setup-agent-config (optional)"
Write-Host "    5. Run /solar-setup-scaffold to create ledger and memory templates"
Write-Host ""
Write-Host "  Advanced (Optional):"
Write-Host "    - Run /solar-setup-memory to create memory templates"
Write-Host "    - Populate memory with @Orchestration-Governor"
Write-Host ""
Write-Host "  Smoke Test:"
Write-Host "    /ralph-loop `"Add a README badge`""
Write-Host ""

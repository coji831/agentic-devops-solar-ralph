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
    ".github/commands/solar-setup-scan-repo.prompt.md",
    ".github/commands/solar-setup-core-config.prompt.md",
    ".github/commands/solar-setup-agent-config.prompt.md",
    ".github/commands/solar-enter-bootstrap.prompt.md",
    ".github/commands/solar-exit-bootstrap.prompt.md",

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
Write-Host "  1. Fill in .github/solar-setup.md with your project details"
Write-Host "     Option A (auto): @solar-bootstrap /solar-setup-scan-repo"
Write-Host "       Detects your stack, commands, and paths, then review the output."
Write-Host "     Option B (manual): open .github/solar-setup.md and fill every field."
Write-Host ""
Write-Host "  2. Run @solar-bootstrap /solar-setup-core-config in Copilot chat"
Write-Host "     to distribute values to all [POST-IMPLEMENT] sections"
Write-Host ""
Write-Host "  3. Run @solar-bootstrap /solar-setup-agent-config in Copilot chat"
Write-Host "     to apply values to all agent, skill, and path instruction files"
Write-Host ""
Write-Host "  4. Populate repo memory - run in Copilot chat:"
Write-Host "     @Orchestration-Governor explore the codebase and populate"
Write-Host "     /memories/repo/ using the memory templates"
Write-Host ""
Write-Host "  5. Activate SOLAR in .github/solar.config.json:"
Write-Host "     Set 'enabled': true (currently disabled by default)"
Write-Host ""
Write-Host "  6. Smoke test - run in Copilot chat:"
Write-Host "     /ralph-loop  (pick a trivial task to verify the full pipeline)"
Write-Host ""
Write-Host "  Optional: configure .vscode/mcp.json (Playwright, GitHub, Fetch MCP)"
Write-Host "  See .github/guides/mcp-operations-guide.md for instructions"
Write-Host ""

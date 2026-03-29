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
    ".github/solar.config.json",

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

    # Agents - generic (Tier 1 fallback; no stack assumptions)
    ".github/agents/implementation-specialist.agent.md",

    # Hooks
    ".github/hooks/hooks.json",
    ".github/hooks/user-prompt-submit.cjs",
    ".github/hooks/post-tool-use.cjs",
    ".github/hooks/stop.cjs",

    # Commands
    ".github/commands/ralph-loop.prompt.md",
    ".github/commands/audit-story.prompt.md",

    # Setup prompts
    ".github/prompts/solar-setup-quick.prompt.md",
    ".github/prompts/solar-setup-full.prompt.md",
    ".github/prompts/solar-setup-scan-repo.prompt.md",
    ".github/prompts/solar-setup-core-config.prompt.md",
    ".github/prompts/solar-setup-agent-config.prompt.md",
    ".github/prompts/solar-setup-scaffold.prompt.md",
    ".github/prompts/solar-setup-instructions.prompt.md",
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

    # Instruction scaffolding (templates; update applyTo glob after creation)
    ".github/instructions/architecture.instructions.md",
    ".github/instructions/backend.instructions.md",
    ".github/instructions/workflow.instructions.md",
    ".github/instructions/frontend.instructions.md",
    ".github/instructions/security.instructions.md",
    ".github/instructions/verification.instructions.md",
    ".github/instructions/conventions.instructions.md"
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
Write-Host "=== Setup Options ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Option 1: Quick Setup (Recommended)"
Write-Host "    Run: /solar-setup-quick"
Write-Host "    - Scans repo and applies core configuration"
Write-Host "    - Creates ledger and activates SOLAR"
Write-Host "    - Uses default agent settings (fastest path)"
Write-Host "    - Optional: Run /solar-setup-agent-config later for customization"
Write-Host ""
Write-Host "  Option 2: Full Setup (Advanced)"
Write-Host "    Run: /solar-setup-full"
Write-Host "    - Does everything Quick Setup does"
Write-Host "    - PLUS customizes all 14 agents and skills with your tech stack"
Write-Host "    - Best for complex monorepos or non-standard stacks"
Write-Host ""
Write-Host "  Smoke Test (after either setup):"
Write-Host "    /ralph-loop `"Add a README badge`""
Write-Host ""

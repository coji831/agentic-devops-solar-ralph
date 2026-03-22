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
    "AGENTS.md",
    ".ai_ledger.md",

    # Setup config (fill this first, then run /solar-apply-setup)
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

    # Hooks
    ".github/hooks/hooks.json",
    ".github/hooks/user-prompt-submit.js",
    ".github/hooks/post-tool-use.js",
    ".github/hooks/stop.js",

    # Commands
    ".github/commands/ralph-loop.prompt.md",
    ".github/commands/audit-story.prompt.md",
    ".github/commands/solar-apply-setup.prompt.md",

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
    ".github/guides/mcp-operations-guide.md",
    ".github/guides/solar-ralph-workflow.md",

    # Verification artifacts
    "verification-artifacts/README.md",
    "verification-artifacts/.gitkeep",

    # Repo memory scaffolding (agent fills these; delete from git after ingestion)
    "memories/repo/commands.md",
    "memories/repo/architecture.md",
    "memories/repo/workflow-facts.md",
    "memories/repo/frontend-facts.md",
    "memories/repo/backend-facts.md",
    "memories/repo/security-facts.md",
    "memories/repo/verification-facts.md"
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

# -- ESM detection: rename hook .js -> .cjs if package.json has "type":"module" --
if (Test-Path "package.json") {
    $pkgContent = Get-Content "package.json" -Raw
    if ($pkgContent -match '"type"\s*:\s*"module"') {
        Write-Host "  Detected `"type`":`"module`" in package.json - renaming hook scripts to .cjs" -ForegroundColor Yellow
        @("user-prompt-submit", "post-tool-use", "stop") | ForEach-Object {
            $js  = Join-Path ".github/hooks" "$_.js"
            $cjs = Join-Path ".github/hooks" "$_.cjs"
            if (Test-Path $js) {
                Rename-Item $js $cjs
                Write-Host "  RENAME .github/hooks/$_.js -> $_.cjs" -ForegroundColor Green
            }
        }
        $hj = ".github/hooks/hooks.json"
        if (Test-Path $hj) {
            (Get-Content $hj -Raw) `
                -replace 'user-prompt-submit\.js','user-prompt-submit.cjs' `
                -replace 'post-tool-use\.js','post-tool-use.cjs' `
                -replace 'stop\.js','stop.cjs' | Set-Content $hj -NoNewline
            Write-Host "  PATCHED .github/hooks/hooks.json (.js -> .cjs)" -ForegroundColor Green
        }
        Write-Host ""
    }
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Fill in .github/solar-setup.md with your project details"
Write-Host "     (project name, stack, commands, git conventions)"
Write-Host ""
Write-Host "  2. Run /solar-apply-setup in Copilot chat to distribute values"
Write-Host "     to all [POST-IMPLEMENT] sections automatically"
Write-Host ""
Write-Host "  3. Populate repo memory - run in Copilot chat:"
Write-Host "     @Orchestration-Governor explore the codebase and populate"
Write-Host "     /memories/repo/ using the memory templates"
Write-Host ""
Write-Host "  4. Activate SOLAR in .ai_ledger.md:"
Write-Host "     Set SOLAR_ACTIVE: true and Completion Promise: pending"
Write-Host ""
Write-Host "  5. Smoke test - run in Copilot chat:"
Write-Host "     /ralph-loop  (pick a trivial task to verify the full pipeline)"
Write-Host ""
Write-Host "  Optional: configure .vscode/mcp.json (Playwright, GitHub, Fetch MCP)"
Write-Host "  See .github/guides/mcp-operations-guide.md for instructions"
Write-Host ""

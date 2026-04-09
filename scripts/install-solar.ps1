# install-solar.ps1 - SOLAR-Ralph Installer for Windows (PowerShell)
#
# Downloads all SOLAR-Ralph files into the current repo from GitHub.
# Run this from the ROOT of your target repo.
#
# One-liner install:
#   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.ps1" -OutFile install-solar.ps1; .\install-solar.ps1; Remove-Item install-solar.ps1
#
# Options:
#   -Force     Overwrite existing files (default: skip files that already exist)
#   -Branch    Branch to download from (default: main)

param(
    [switch]$Force,
    [string]$Branch = "main"
)

$REPO = "coji831/agentic-devops-solar-ralph"
$BRANCH = $Branch
$BASE_URL = "https://raw.githubusercontent.com/$REPO/$BRANCH"

# Fetch file list from manifest (single source of truth)
$MANIFEST_URL = "$BASE_URL/scripts/solar-manifest.txt"
try {
    $manifestContent = (Invoke-WebRequest -Uri $MANIFEST_URL -UseBasicParsing -ErrorAction Stop).Content
    $FILES = $manifestContent -split "`n" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -ne "" -and -not $_.StartsWith("#") }
}
catch {
    Write-Host "ERROR: Failed to fetch manifest from $MANIFEST_URL" -ForegroundColor Red
    Write-Host "       $($_.Exception.Message)" -ForegroundColor DarkRed
    exit 1
}

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
$skipped = 0
$failed = 0
$failedList = @()

foreach ($file in $FILES) {
    $dest = Join-Path $PWD $file
    $url = "$BASE_URL/$file"

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
    }
    catch {
        Write-Host "  FAIL  $file" -ForegroundColor Red
        Write-Host "        $($_.Exception.Message)" -ForegroundColor DarkRed
        $failed++
        $failedList += $file
    }
}

# Rename template files to working files
$renameCount = 0
if (Test-Path ".template.gitignore") {
    Rename-Item -Path ".template.gitignore" -NewName ".gitignore" -Force
    Write-Host "  RENAME .template.gitignore → .gitignore" -ForegroundColor Cyan
    $renameCount++
}
if (Test-Path ".github/AGENTS.template.md") {
    Rename-Item -Path ".github/AGENTS.template.md" -NewName ".github/AGENTS.md" -Force
    Write-Host "  RENAME .github/AGENTS.template.md → .github/AGENTS.md" -ForegroundColor Cyan
    $renameCount++
}
if (Test-Path ".github/.ai_ledger.template.md") {
    Rename-Item -Path ".github/.ai_ledger.template.md" -NewName ".github/.ai_ledger.md" -Force
    Write-Host "  RENAME .github/.ai_ledger.template.md → .github/.ai_ledger.md" -ForegroundColor Cyan
    $renameCount++
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
Write-Host "    - Optional: Run /solar-setup-apply-config later for full customization"
Write-Host ""
Write-Host "  Option 2: Full Setup (Advanced)"
Write-Host "    Run: /solar-setup-full"
Write-Host "    - Does everything Quick Setup does"
Write-Host "    - PLUS customizes all 16 agents and 14 skills with your tech stack"
Write-Host "    - Best for complex monorepos or non-standard stacks"
Write-Host ""
Write-Host "  Smoke Test (after either setup):"
Write-Host "    /solar `"Add a README badge`""
Write-Host ""

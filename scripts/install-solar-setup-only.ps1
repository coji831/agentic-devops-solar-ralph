# install-solar-setup-only.ps1 - Minimal SOLAR-Ralph Quick Setup Installer
#
# Downloads ONLY what's needed to run /solar-setup-quick.
# Run this from the ROOT of your target repo.
#
# One-liner install:
#   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.ps1" -OutFile install.ps1; .\install.ps1; Remove-Item install.ps1

$ErrorActionPreference = "Stop"

$repo = "coji831/agentic-devops-solar-ralph"
$branch = "main"
$baseUrl = "https://raw.githubusercontent.com/$repo/$branch"

Write-Host "SOLAR-Ralph Quick Setup - Minimal Install" -ForegroundColor Cyan
Write-Host "=============================================="
Write-Host ""

# Minimal file list - ONLY what's needed for /solar-setup-quick
$files = @(
    ".github/solar-setup.md",
    ".github/.ai_ledger.template.md",
    ".github/agents/solar-bootstrap.agent.md",
    ".github/prompts/solar-setup-quick.prompt.md",
    ".github/prompts/solar-setup-scan-repo.prompt.md",
    ".github/instructions/solar.instructions.md",
    ".github/solar.config.json"
)

function Download-File {
    param($file)
    
    $dir = Split-Path $file -Parent
    
    # Create directory if needed
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    # Download file
    try {
        $url = "$baseUrl/$file"
        Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
        Write-Host "Downloaded: $file" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "Failed: $file" -ForegroundColor Red
        return $false
    }
}

# Download all files
$succeeded = 0
$failed = 0

foreach ($file in $files) {
    if (Download-File $file) {
        $succeeded++
    }
    else {
        $failed++
    }
}

Write-Host ""
Write-Host "=============================================="
Write-Host "Downloaded: $succeeded files" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "Failed: $failed files" -ForegroundColor Red
}
Write-Host ""
Write-Host "Next step: Run /solar-setup-quick to configure and activate SOLAR"
Write-Host ""

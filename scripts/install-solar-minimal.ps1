# SOLAR-Ralph Minimal Installer (PowerShell)
# Downloads only core SOLAR files (no scaffolding)

$repoUrl = "https://raw.githubusercontent.com/[YOUR-REPO]/main"
$files = @(
  ".github/AGENTS.md",
  ".github/agents/",
  ".github/hooks/",
  ".github/skills/",
  ".github/prompts/",
  ".github/commands/ralph-loop.prompt.md",
  ".github/commands/audit-story.prompt.md",
  ".github/guides/",
  ".github/solar-setup.md",
  "verification-artifacts/",
  "docs/knowledge-base/"
)

foreach ($file in $files) {
  # Download logic here (use Invoke-WebRequest or similar)
  Write-Host "Would download: $repoUrl/$file"
}

Write-Host "SOLAR-Ralph minimal install complete. Run setup prompts to continue."

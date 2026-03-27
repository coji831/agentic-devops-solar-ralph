#!/usr/bin/env bash
# install-solar-setup-only.sh - Minimal SOLAR-Ralph Quick Setup Installer
#
# Downloads ONLY what's needed to run /solar-setup-quick.
# Run this from the ROOT of your target repo.
#
# One-liner install:
#   curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar-setup-only.sh | bash

set -euo pipefail

REPO="coji831/agentic-devops-solar-ralph"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

echo "📦 SOLAR-Ralph Quick Setup - Minimal Install"
echo "=============================================="
echo ""

# Minimal file list - ONLY what's needed for /solar-setup-quick
FILES=(
    ".github/solar-setup.md"
    ".github/.ai_ledger.template.md"
    ".github/agents/solar-bootstrap.agent.md"
    ".github/prompts/solar-setup-quick.prompt.md"
    ".github/prompts/solar-setup-scan-repo.prompt.md"
    ".github/instructions/solar.instructions.md"
    ".github/solar.config.json"
)

download_file() {
    local file=$1
    local dir=$(dirname "$file")
    
    # Create directory if needed
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
    
    # Download file
    if curl -fsSL "${BASE_URL}/${file}" -o "$file" 2>/dev/null; then
        echo "✓ $file"
        return 0
    else
        echo "✗ $file (download failed)"
        return 1
    fi
}

# Download all files
succeeded=0
failed=0

for file in "${FILES[@]}"; do
    if download_file "$file"; then
        ((succeeded++))
    else
        ((failed++))
    fi
done

echo ""
echo "=============================================="
echo "✓ Downloaded: $succeeded files"
if [ $failed -gt 0 ]; then
    echo "✗ Failed: $failed files"
fi
echo ""
echo "Next step: Run /solar-setup-quick to configure and activate SOLAR"
echo ""

#!/usr/bin/env bash
# install-solar.sh - SOLAR-Ralph Installer for macOS / Linux
#
# Downloads all SOLAR-Ralph files into the current repo from GitHub.
# Run this from the ROOT of your target repo.
#
# One-liner install:
#   curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh | bash
#
# Options:
#   --force     Overwrite existing files (default: skip files that already exist)
#   --branch    Branch to download from (default: main)
#
# Usage with options (download then run):
#   curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh -o install-solar.sh
#   bash install-solar.sh --force --branch v4
#   rm install-solar.sh

set -euo pipefail

REPO="coji831/agentic-devops-solar-ralph"
BRANCH="main"
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f) FORCE=true; shift ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --branch=*) BRANCH="${1#*=}"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Build URL after parsing arguments (BRANCH may have changed)
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

# Fetch file list from manifest (single source of truth)
MANIFEST_URL="${BASE_URL}/scripts/solar-manifest.txt"
FILES=()
while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"                              # strip inline/full-line comments
    line="${line#"${line%%[![:space:]]*}"}"         # trim leading whitespace
    line="${line%"${line##*[![:space:]]}"}"         # trim trailing whitespace
    [ -n "$line" ] && FILES+=("$line")
done < <(curl -fsSL "$MANIFEST_URL")

if [ ${#FILES[@]} -eq 0 ]; then
    echo "ERROR: Failed to fetch manifest or manifest is empty: $MANIFEST_URL"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  SOLAR-Ralph Installer${NC}"
echo -e "${GRAY}  Repo  : ${REPO} @ ${BRANCH}${NC}"
echo -e "${GRAY}  Target: $(pwd)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$FORCE" = true ]; then
    echo -e "${YELLOW}  Mode: FORCE (overwriting existing files)${NC}"
    echo ""
fi

downloaded=0
skipped=0
failed=0
failed_list=()

for file in "${FILES[@]}"; do
    dest="./${file}"
    url="${BASE_URL}/${file}"

    if [ -f "$dest" ] && [ "$FORCE" = false ]; then
        echo -e "${GRAY}  SKIP  ${file}${NC}"
        ((skipped++)) || true
        continue
    fi

    # Create parent directory if needed
    dir=$(dirname "$dest")
    mkdir -p "$dir"

    if curl -fsSL "$url" -o "$dest" 2>/dev/null; then
        echo -e "${GREEN}  OK    ${file}${NC}"
        ((downloaded++)) || true
    else
        echo -e "${RED}  FAIL  ${file}${NC}"
        ((failed++)) || true
        failed_list+=("$file")
    fi
done

# Rename template files to working files
if [ -f ".template.gitignore" ]; then
    mv ".template.gitignore" ".gitignore"
    echo -e "${CYAN}  RENAME .template.gitignore → .gitignore${NC}"
fi
if [ -f ".github/AGENTS.template.md" ]; then
    mv ".github/AGENTS.template.md" ".github/AGENTS.md"
    echo -e "${CYAN}  RENAME .github/AGENTS.template.md → .github/AGENTS.md${NC}"
fi
if [ -f ".github/.ai_ledger.template.md" ]; then
    mv ".github/.ai_ledger.template.md" ".github/.ai_ledger.md"
    echo -e "${CYAN}  RENAME .github/.ai_ledger.template.md → .github/.ai_ledger.md${NC}"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  Downloaded : ${downloaded}${NC}"
echo -e "${GRAY}  Skipped    : ${skipped} (already exist)${NC}"
if [ "$failed" -gt 0 ]; then
    echo -e "${RED}  Failed     : ${failed}${NC}"
else
    echo -e "${GRAY}  Failed     : ${failed}${NC}"
fi
echo -e "${CYAN}========================================${NC}"

if [ "$failed" -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed files:${NC}"
    for f in "${failed_list[@]}"; do
        echo -e "${RED}  - ${f}${NC}"
    done
    echo ""
    echo -e "${YELLOW}Re-run with --force to retry failed files.${NC}"
fi

echo ""
echo -e "${CYAN}=== Setup Options ===${NC}"
echo ""
echo "  Option 1: Quick Setup (Recommended)"
echo "    Run: /solar-setup-quick"
echo "    - Scans repo and applies core configuration"
echo "    - Creates ledger and activates SOLAR"
echo "    - Uses default agent settings (fastest path)"
echo "    - Optional: Run /solar-setup-apply-config later for full customization"
echo ""
echo "  Option 2: Full Setup (Advanced)"
echo "    Run: /solar-setup-full"
echo "    - Does everything Quick Setup does"
echo "    - PLUS customizes all 16 agents and 14 skills with your tech stack"
echo "    - Best for complex monorepos or non-standard stacks"
echo ""
echo "  Smoke Test (after either setup):"
echo "    /solar \"Add a README badge\""
echo ""

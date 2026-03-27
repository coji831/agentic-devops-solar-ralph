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
#   --force    Overwrite existing files (default: skip files that already exist)
#
# Usage with options (download then run):
#   curl -fsSL https://raw.githubusercontent.com/coji831/agentic-devops-solar-ralph/main/scripts/install-solar.sh -o install-solar.sh
#   bash install-solar.sh --force
#   rm install-solar.sh

set -euo pipefail

REPO="coji831/agentic-devops-solar-ralph"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
FORCE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --force|-f) FORCE=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# All files to download into the target repo
FILES=(
    # Root contracts
    ".github/AGENTS.md"
    ".github/.ai_ledger.template.md"

    # Setup config (fill this first, then run /solar-setup-core-config)
    ".github/solar-setup.md"

    # Agents - universal (governance, auditors, architect)
    ".github/agents/orchestration-governor.agent.md"
    ".github/agents/design-planning-architect.agent.md"
    ".github/agents/bug-investigation-specialist.agent.md"
    ".github/agents/frontend-review-auditor.agent.md"
    ".github/agents/backend-review-auditor.agent.md"
    ".github/agents/release-readiness-specialist.agent.md"
    ".github/agents/security-auditor.agent.md"

    # Agents - [POST-IMPLEMENT] (update Tech Stack section per repo)
    ".github/agents/frontend-implementation-specialist.agent.md"
    ".github/agents/frontend-test-specialist.agent.md"
    ".github/agents/backend-implementation-specialist.agent.md"
    ".github/agents/backend-test-specialist.agent.md"
    ".github/agents/docs-curator.agent.md"
    ".github/agents/cache-external-integration-specialist.agent.md"

    # Agents - bootstrap (setup utilities only)
    ".github/agents/solar-bootstrap.agent.md"

    # Hooks
    ".github/hooks/hooks.json"
    ".github/solar.config.json"
    ".github/hooks/user-prompt-submit.cjs"
    ".github/hooks/post-tool-use.cjs"
    ".github/hooks/stop.cjs"

    # Commands
    ".github/commands/ralph-loop.prompt.md"
    ".github/commands/audit-story.prompt.md"

    # Setup prompts
    ".github/prompts/solar-setup-quick.prompt.md"
    ".github/prompts/solar-setup-scan-repo.prompt.md"
    ".github/prompts/solar-setup-core-config.prompt.md"
    ".github/prompts/solar-setup-agent-config.prompt.md"
    ".github/prompts/solar-setup-scaffold.prompt.md"
    ".github/prompts/solar-setup-memory.prompt.md"
    ".github/prompts/solar-enter-bootstrap.prompt.md"
    ".github/prompts/solar-exit-bootstrap.prompt.md"

    # Skills - universal
    ".github/skills/frontend-review/SKILL.md"
    ".github/skills/backend-review/SKILL.md"
    ".github/skills/story-execution/SKILL.md"
    ".github/skills/doc-sync/SKILL.md"
    ".github/skills/memory-curation/SKILL.md"
    ".github/skills/memory-verification/SKILL.md"
    ".github/skills/recursive-remediation/SKILL.md"
    ".github/skills/release-governance/SKILL.md"
    ".github/skills/browser-reproduction/SKILL.md"
    ".github/skills/external-integration-operations/SKILL.md"

    # Skills - [POST-IMPLEMENT] (update Tech Stack section per repo)
    ".github/skills/frontend-feature-implementation/SKILL.md"
    ".github/skills/frontend-testing/SKILL.md"
    ".github/skills/backend-feature-implementation/SKILL.md"
    ".github/skills/backend-testing/SKILL.md"

    # Operator guides
    ".github/guides/agent-operations-guide.md"
    ".github/guides/memory-governance-guide.md"
    ".github/guides/bootstrap-mode-guide.md"
    ".github/guides/mcp-operations-guide.md"
    ".github/guides/solar-ralph-workflow.md"

    # Verification artifacts
    "verification-artifacts/README.md"
    "verification-artifacts/.gitkeep"

    # Repo memory scaffolding (agent fills these; delete from git after ingestion)
    ".github/memories/repo/commands.md"
    ".github/memories/repo/architecture.md"
    ".github/memories/repo/workflow-facts.md"
    ".github/memories/repo/frontend-facts.md"
    ".github/memories/repo/backend-facts.md"
    ".github/memories/repo/security-facts.md"
    ".github/memories/repo/verification-facts.md"
)

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
echo -e "${CYAN}=== Next Steps ===${NC}"
echo ""
echo "  Quick Setup (Recommended):"
echo "    Run /solar-setup-quick in Copilot chat"
echo "    (combines scan + config + scaffold + activate)"
echo ""
echo "  Manual Setup (Troubleshooting):"
echo "    1. Run /solar-setup-scan-repo to detect project details"
echo "    2. Review .github/solar-setup.md and correct any misdetections"
echo "    3. Run /solar-setup-core-config to apply config"
echo "    4. Run /solar-setup-agent-config (optional)"
echo "    5. Run /solar-setup-scaffold to create ledger and memory templates"
echo ""
echo "  Advanced (Optional):"
echo "    - Run /solar-setup-memory to create memory templates"
echo "    - Populate memory with @Orchestration-Governor"
echo ""
echo "  Smoke Test:"
echo "    /ralph-loop \"Add a README badge\""
echo ""

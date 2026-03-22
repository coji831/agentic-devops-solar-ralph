# SOLAR-Ralph Setup Config

**Option A — Auto-fill (recommended):** Run this command to have an agent scan the codebase and fill in these values for you:

```
/solar-scan-repo
```

Then review and correct any fields marked `# NEEDS MANUAL INPUT`.

**Option B — Manual fill:** Edit the values below directly.

Once all values are filled (via either option), distribute them to every agent, skill, hook, and instruction file by running:

```
/solar-apply-setup
```

---

## Project Identity

```
PROJECT_NAME:        [your repo name]
PROJECT_DESCRIPTION: [one sentence — what this app does]
```

---

## Stack

```
FRONTEND_FRAMEWORK:  [e.g. React + TypeScript + Vite]
FRONTEND_FOLDER:     [e.g. apps/frontend/src]
FRONTEND_TEST_RUNNER:[e.g. Vitest + RTL]

BACKEND_FRAMEWORK:   [e.g. Express + TypeScript]
BACKEND_FOLDER:      [e.g. apps/backend/src]
BACKEND_TEST_RUNNER: [e.g. Jest + Supertest]

DATABASE:            [e.g. PostgreSQL via Prisma]
AUTH_MECHANISM:      [e.g. JWT with httpOnly cookies + refresh token rotation]
STATE_MANAGEMENT:    [e.g. React Context + reducers]
```

---

## Commands

```
INSTALL_CMD:         [e.g. npm install]
DEV_CMD:             [e.g. npm run dev]
TEST_CMD:            [e.g. npm test]
TYPECHECK_CMD:       [e.g. tsc --noEmit]
LINT_CMD:            [e.g. eslint . --ext .ts,.tsx]
BUILD_CMD:           [e.g. npm run build]
```

---

## Git & Workflow

```
BRANCH_NAMING:       [e.g. feature/<slug>, fix/<slug>]
COMMIT_FORMAT:       [e.g. <type>(<scope>): <summary>]
PR_PROCESS:          [e.g. PR to main, 1 approval required]
DEPLOYMENT_TARGETS:  [e.g. Frontend → Vercel, Backend → Railway]
```

---

## Path-Specific Instructions

```
FRONTEND_INSTRUCTIONS_PATH: [e.g. apps/frontend/.instructions.md]
FRONTEND_APPLY_TO_GLOB:     [e.g. apps/frontend/src/**]

BACKEND_INSTRUCTIONS_PATH:  [e.g. apps/backend/.instructions.md]
BACKEND_APPLY_TO_GLOB:      [e.g. apps/backend/src/**]
```

---

## MCP (Optional)

```
GITHUB_TOKEN_ENV_VAR: COPILOT_MCP_GITHUB_TOKEN
REMOVE_MCP_SERVERS:   [list any servers not needed, e.g. puppeteer]
```

---

## Documentation Structure

```
ARCHITECTURE_DOC:    [e.g. docs/architecture.md]
KEY_DOCS:            [list 3-5 most important docs agents should know about]
```

# SOLAR-Ralph Install Template

This folder is the **installable scaffold** — the exact file tree that `solar-install.prompt.md` generates into a target repository.

```
template/
  .github/                       →  installed as  .github/
  verification-artifacts/        →  installed as  verification-artifacts/
```

---

## Mapping to the Target Repo

| Template path                              | Installed path in target          | Notes                                                         |
| ------------------------------------------ | --------------------------------- | ------------------------------------------------------------- |
| `template/.github/AGENTS.md`               | `.github/AGENTS.md`               | Filled by install agent (Step 5A) with repo context           |
| `template/.github/.ai_ledger.md`           | `.github/.ai_ledger.md`           | Live ledger                                                   |
| `template/.github/copilot-instructions.md` | `.github/copilot-instructions.md` | Installed as-is                                               |
| `template/.github/solar.config.json`       | `.github/solar.config.json`       | Installed as-is; user adjusts feature toggles                 |
| `template/.github/agents/`                 | `.github/agents/`                 | Installed as-is                                               |
| `template/.github/hooks/`                  | `.github/hooks/`                  | Installed as-is                                               |
| `template/.github/instructions/`           | `.github/instructions/`           | Installed as-is; stack instruction generated per target stack |
| `template/.github/prompts/`                | `.github/prompts/`                | Installed as-is                                               |
| `template/.github/skills/`                 | `.github/skills/`                 | Installed as-is                                               |
| `template/.github/solar-system/`           | `.github/solar-system/`           | Installed as-is                                               |
| `template/verification-artifacts/`         | `verification-artifacts/`         | Scaffold only — README + .gitkeep                             |

---

## How Installation Works

The install prompt (`solar-install.prompt.md` at repo root) generates all files inline — it does not copy from this folder directly. This folder is the **reference source of truth** for what the generated output should look like.

When adding or updating any SOLAR scaffold file:

1. Edit it here in `template/`
2. Sync the change into `solar-install.prompt.md` (the relevant Step 5 section)
3. Both must stay aligned — run an alignment check if unsure

---

## Internal Paths

All paths inside agent, skill, hook, and instruction files are **target-repo paths** (e.g., `.github/agents/`, `.github/.ai_ledger.md`). They are correct as-is and do not reference this `template/` location.

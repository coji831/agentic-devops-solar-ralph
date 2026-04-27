# SOLAR-Ralph — Component & Layer Relational Diagram

> Post-install map of all installed files, how they relate, and which SOLAR layer each belongs to.
> **S** = Specialist · **O** = Orchestrator · **L** = Ledger · **A** = Adversarial audit (Governor dispatch rule) · **R** = Ralph Loop
>
> Layout: left column = execution flow (top-to-bottom); right column = shared state backbone.
> Hooks are **infrastructure support** — they share gate-enforcement workload with the Governor. They are not the adversarial layer.

```mermaid
graph LR

    subgraph FLOW ["── Execution Flow ──"]
        direction TB
        USER(["User"])

        subgraph ENTRY_G ["Entry Prompts"]
            direction LR
            SP["solar.prompt.md\nStart any SOLAR task"]
            RP["solar-registry-update.prompt.md\nSync registry"]
        end

        GOV["Orchestration Governor\n─────────────────────────────\nRead registry → dispatch by Dev Stage\nWrite ledger at every transition\n4-gate before each dispatch\nInterrupt resume · TASK_COMPLETE cleanup"]

        subgraph SPEC_G ["S — Specialists  (one per Dev Stage)"]
            direction LR
            S1["Scan\ndata-collector-specialist"]
            S2["Plan+Design\ndesign-planning-architect"]
            S3["Implement\nimplementation-specialist"]
            S4["Test\ntest-specialist"]
            S5["Document\ndocs-curator"]
            S6["Review\nreview-auditor"]
        end

        subgraph SKILL_G ["Skills — loaded lazily via Skill Index"]
            direction LR
            SK1["data-collection"]
            SK2["design-planning"]
            SK3["implementation"]
            SK4["testing"]
            SK5["doc-sync"]
            SK6["review"]
            SK7["recursive-remediation"]
        end

        VERIFY["A — Adversarial Audit  (VERIFY stage)\n─────────────────────────────────────\nGovernor picks a non-author specialist\nby domain match from the registry:\n· review-auditor → audits code output\n· test-specialist → audits design artifacts\n· design-planning-architect → audits test coverage\nAuditor writes {task-id}-verify.md\nVerdict: APPROVED → close  ·  REJECTED → remediate"]

        VA["verification-artifacts/\n────── R — Ralph Loop ──────\n{task-id}-input · {task-id}-{type}.md\n{task-id}-verify.md  (audit verdict)\nPreserved on INTERRUPT · Cleaned on CLOSE"]

        USER --> ENTRY_G
        ENTRY_G --> GOV
        GOV -->|"dispatch by Dev Stage"| SPEC_G
        SPEC_G -->|"load skill"| SKILL_G
        SPEC_G -->|"write artifact"| VA
        VA -->|"status=ready\nmaterials input"| GOV
        GOV -->|"VERIFY stage\ndomain-match dispatch"| VERIFY
        VERIFY -->|"writes {task-id}-verify.md"| VA
        VERIFY -->|"APPROVED → CLOSE\nREJECTED → remediate"| GOV
    end

    subgraph BACKBONE ["── Shared State Backbone ──"]
        direction TB

        AGENTSMD[".github/AGENTS.md\n──────────────────────\nAgent Registry · Skill Index\nWorkflow Index · Hook Config\nRepository Context\nLedger Template · Config Toggles"]

        LEDGER[".github/.ai_ledger.md\n──────────────────────\nWork Queue\nLoop State\nMaterials\nDecisions Log  (append-only)"]

        subgraph HOOK_G ["Infrastructure Support — Hooks"]
            direction TB
            POST["post-tool-use.cjs\nPostToolUse\nVERIFY stage trigger signal"]
            STP["stop.cjs\nStop\nblock exit when Completion Promise: pending"]
        end
    end

    subgraph PLATFORM ["Platform Layer  (always active — silent)"]
        direction LR
        CI["copilot-instructions.md\nsystem overlay"]
        SI["solar.instructions.md\napplyTo: **"]
        STI["{stack}.instructions.md\napplyTo: stack"]
        CFG["solar.config.json\nfeature flags"]
    end

    PLATFORM -.->|"applyTo"| GOV

    GOV <-->|"routing source of truth"| AGENTSMD
    GOV <-->|"read stage · write transitions"| LEDGER

    POST <-->|"reads ledger state"| LEDGER
    STP <-->|"reads ledger state"| LEDGER
    POST -->|"VERIFY_REQUIRED signal"| GOV
    STP -->|"exit signal"| GOV

    classDef entry fill:#1a1a2e,stroke:#4a90d9,color:#e0e0ff
    classDef governor fill:#0d2040,stroke:#5ba3d9,color:#cce8ff,font-weight:bold
    classDef specialist fill:#1c1a30,stroke:#9370db,color:#e8d5ff
    classDef skill fill:#1a2a1a,stroke:#6abf6a,color:#d0ffd0
    classDef ledger fill:#0d2b1e,stroke:#3db87a,color:#c0ffd8
    classDef agentsmd fill:#0a1f30,stroke:#4a9fd9,color:#c0e8ff
    classDef hook fill:#2b1a1a,stroke:#c06030,color:#ffe0c0
    classDef adversarial fill:#2b1520,stroke:#e05580,color:#ffd0e0,font-weight:bold
    classDef artifact fill:#2a2010,stroke:#d4a020,color:#fff0c0
    classDef platform fill:#202020,stroke:#666,color:#cccccc

    class USER,SP,RP entry
    class GOV governor
    class S1,S2,S3,S4,S5,S6 specialist
    class SK1,SK2,SK3,SK4,SK5,SK6,SK7 skill
    class LEDGER ledger
    class AGENTSMD agentsmd
    class POST,STP hook
    class VERIFY adversarial
    class VA artifact
    class CI,SI,STI,CFG platform
```

---

## Layer Legend

| Layer                          | Color       | Description                                                                                                                                                         |
| ------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Entry**                      | Blue        | `prompts/solar.prompt.md`, `solar-registry-update.prompt.md`                                                                                                        |
| **Platform** (always active)   | Dark gray   | `copilot-instructions.md`, `solar.instructions.md`, `{stack}.instructions.md`, `solar.config.json`                                                                  |
| **O — Orchestrator**           | Cyan        | `agents/orchestration-governor.agent.md` · `AGENTS.md` (registry + config)                                                                                          |
| **L — Ledger**                 | Green       | `.ai_ledger.md` — Work Queue, Loop State, Materials, Decisions Log                                                                                                  |
| **A — Adversarial Audit**      | Pink        | No dedicated file. Governor dispatch rule: at VERIFY stage, picks a domain-matched non-author specialist from the registry to challenge the previous agent's output |
| **Infrastructure — Hooks**     | Orange      | `hooks/post-tool-use.cjs`, `stop.cjs` — signal emitters; share gate-enforcement workload with the Governor; not the adversarial layer                               |
| **S — Specialists**            | Purple      | 6 `*.agent.md` files (one per dev stage)                                                                                                                            |
| **Skills**                     | Light green | 7 `SKILL.md` files (loaded lazily at task time via Skill Index)                                                                                                     |
| **R — Ralph Loop / Artifacts** | Amber       | `verification-artifacts/` — all stage outputs + audit verdicts                                                                                                      |

## Key Data Flows

| Flow                                            | Direction         | Description                                                                                                       |
| ----------------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| `solar.prompt.md` → Governor                    | invoke            | User starts a task; Governor takes over                                                                           |
| Governor ↔ `AGENTS.md`                          | read              | Single routing source of truth; Dev Stage + Loads Skill columns                                                   |
| Governor ↔ `.ai_ledger.md`                      | read + write      | Stage transitions, materials tracking, Decisions Log                                                              |
| Governor → Specialist                           | dispatch          | By matching Dev Stage column in Agent Registry                                                                    |
| Specialist → Skill                              | loads             | Reads Skill Index in AGENTS.md; loads SKILL.md before acting                                                      |
| Specialist → `verification-artifacts/`          | writes            | Every stage produces a `{task-id}-{type}.md` artifact                                                             |
| `verification-artifacts/` → Governor            | materials input   | Governor checks status=ready before next dispatch (G1 gate)                                                       |
| Governor → VERIFY dispatch                      | adversarial audit | Governor selects a non-author specialist by domain match; specialist acts as auditor for this stage only          |
| Auditor → `verification-artifacts/`             | writes verdict    | Produces `{task-id}-verify.md` (APPROVED or REJECTED + reasoning)                                                 |
| Auditor → Governor                              | verdict           | APPROVED → append to Decisions Log → CLOSE; REJECTED → return to producing agent for remediation                  |
| Hooks → Governor                                | gate signals      | `ADVERSARIAL_VERIFY_REQUIRED` (post-tool-use on VERIFY stage), exit decision (stop) — infrastructure signals only |
| Hooks ↔ `.ai_ledger.md`                         | reads             | Gate checks read ledger state (loop bounds, stage, materials, Decisions Log)                                      |
| `solar-registry-update.prompt.md` → `AGENTS.md` | syncs             | After any component add/swap/remove                                                                               |

## Optional Components (not shown — add via `solar-registry-update`)

- `release-readiness-specialist.agent.md` + `release-governance` skill — Release stage gate
- Learning system, session logging, stack-specific specialists

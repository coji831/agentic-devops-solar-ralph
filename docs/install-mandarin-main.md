# Install solar-governor (v5.3.1) on mandarin `main` — runbook

> Status: **DRAFT** (2026-09-05) — prepared from the pilot; execute when the
> runtime is declared stable.
> Engine: `solar-governor` **v5.3.1** (tagged, driver-orchestrated).
> Reference proof: branch `solar-v5-wire` (kept as reference only — do not
> merge; cherry-pick only the corrected files listed here).
> Goal: add the v5 control layer onto mandarin `main` **without disturbing the
> repo's own agentic system**, then run the real epic-25 with the full pipeline.

---

## What `main` already has (verified 2026-09-05)

- `.github/agents/` — the 8 role agents (architect, uiux-designer,
  frontend-engineer, backend-engineer, investigator, docs-writer,
  code-reviewer, **orchestrator**) + `.github/AGENTS.md` (lists them).
- 16 domain `.instructions.md` + 5 repo skills + component/page catalogs +
  CI workflows (chromatic/ci/preview/storybook-checks/terraform).
- **No** v4-SOLAR residue (no hooks, no `.ai_ledger.md`, no `solar.config.json`,
  no `solar-install`, no `solar-system`). No `.solar/`, no `governor-v5`,
  no `hermes`, no `solar-agent-chain`, no epic-25 yet.

⇒ The install is **additive**: add the `.solar/` runtime layer + the thin v5
`.github/` wiring, then one small cleanup (orchestrator residual).

---

## Phase 0 — Preflight

```powershell
# 1. Engine present + version
solar-governor --help            # or: python -m solar_governor.cli --help
python -c "import solar_governor; print(solar_governor.__version__)"   # 5.3.1

# if missing: cd <solar repo>; pip install ./solar-governor   (or -e for dev)

# 2. Work on a feature branch off main (recommended), review, then merge to main
cd "C:\CodeProjects\Personal\mandarin-vite-react-ts"
git switch main && git pull
git switch -c install/solar-v5
```

> Windows console note: prefix runs with `$env:PYTHONIOENCODING='utf-8'`, and
> load the API key from the User scope:
> `$env:SOLAR_API_KEY=[Environment]::GetEnvironmentVariable('SOLAR_API_KEY','User')`

---

## Phase 1 — Add the `.solar/` runtime layer

### 1a. `.solar/config.json` (gitignored — local only)

```json
{
  "profile": "light",
  "repo": "C:\\CodeProjects\\Personal\\mandarin-vite-react-ts",
  "state_dir": ".solar/state",
  "ledger": ".solar/ledger.md",
  "uplink": "none",
  "model": "",
  "human_approval": false,
  "runner": "agent-dispatch"
}
```

- `runner: agent-dispatch` = the default for the IDE `@Governor v5` flow.
- **For a headless/measure run** (eval, bench, `--chain --auto` with real numbers), do NOT
  edit this file. Since **v5.4.2** the per-run override wins over the config:

  ```bash
  solar-governor run "<objective>" --repo . --runner http      # this run only
  $env:SOLAR_RUNNER = "http"                                   # or for a shell session
  ```

  (This section previously said "the config runner wins over env, so edit the one field …
  flip back" — true before v5.4.2 and false after it, and it asked for exactly the kind of
  edit to a live engagement that the flag was added to avoid. **`config.json` IS committed**
  since v5.6.0: it carries no machine-specific path, which is what made the old "do not
  commit" note necessary.)

### 1b. `.solar/registry.json` (tracked) — port + clean

Copy the corrected registry from the reference branch, then drop the residual
`orchestrator` role:

```powershell
git show solar-v5-wire:.solar/registry.json > .solar/registry.json
```

Edit `.solar/registry.json` (it is hand-formatted, 2-space — edit surgically,
**never** `json.dump` it): delete the whole `orchestrator` block, i.e. from
`"orchestrator": {` through its closing `},`:

```json
  "orchestrator": {
    "role": "Orchestrator",
    "system": "...",
    "tools": ["workspace"],
    "next_edges": [...],
    "model": "deepseek"
  },
```

Keep: 7 role entries (architect, uiux-designer, frontend-engineer,
backend-engineer, investigator, docs-writer, code-reviewer) + `default_chain:
"epic"` + `chains` (epic / docs-review / verify) + `playbooks`. (In the graph,
orchestration IS code — no orchestrator role/agent needed.)

### 1c. `.gitignore` (tracked)

Append (config.json stays gitignored; registry + this runbook + PILOT are
tracked):

```
.solar/state/
.solar/ledger.md
.solar/runs/
.solar/handoffs/
.solar/chains/
```

> Do NOT ignore `.solar/config.json` if you want a committed default — but the
> config carries a machine-local absolute `repo` path, so keeping it local is
> the convention on `solar-v5-wire`.

---

## Phase 2 — Add the thin v5 `.github/` wiring

### 2a. Copy the driver + intake agents from the reference branch

```powershell
git checkout solar-v5-wire -- .github/agents/governor-v5.agent.md .github/agents/hermes.agent.md .github/instructions/solar-agent-chain.instructions.md
```

### 2b. Fix `governor-v5.agent.md` runner note (it asserts a fixed runner)

In `.github/agents/governor-v5.agent.md` → `## Environment`, replace:

> where `.solar/config.json` lives (`runner: agent-dispatch`)

with:

> where `.solar/config.json` lives. The config's `runner` decides the mode:
> `agent-dispatch` for this IDE flow (you run the handoffs), `http` for
> headless/measure runs (eval/bench/`--chain --auto`). Check it once at session
> start.

### 2c. Fix the chain instruction title (still says "self-chaining contract")

In `.github/instructions/solar-agent-chain.instructions.md` line 1, replace:

```markdown
# SOLAR v5 Agent Chain — self-chaining contract
```

with:

```markdown
# SOLAR v5 Agent Chain — driver-orchestrated (the coordinator runs the links)
```

(Body is already coordinator-correct: "you are ONE link… only if you have the
agent-spawn tool may you delegate… NEVER fabricate downstream links".)

### 2d. Register them in `.github/AGENTS.md`

- In `instructions:` add (use the corrected description):

```yaml
- file: ".github/instructions/solar-agent-chain.instructions.md"
  description: "SOLAR v5 driver-orchestrated chain contract — the Governor driver (or --auto) runs each link in order; you are ONE link. Never spawn or compose downstream links yourself (nested agents lack the spawn tool)."
```

- In `agents:` add (alphabetical):

```yaml
- ".github/agents/governor-v5.agent.md"
- ".github/agents/hermes.agent.md"
```

- Bump `last-verified: 2026-08-24` → `last-verified: 2026-09-05` (after the
  agent diff below).

---

## Phase 3 — Cleanup (residuals + stale self-chain wording)

1. **Remove the orchestrator residual**
   - Delete `.github/agents/orchestrator.agent.md`.
   - Remove its line from `.github/AGENTS.md` `agents:` list.
   - Registry: already dropped in Phase 1b.

2. **Neutralize dead "Chain exception" clauses** (only if present — diff each
   role agent vs `solar-v5-wire`). Main's copies may predate the clause; if an
   agent body contains `Chain exception: … you DO delegate to your next link`,
   replace with:

> In a chain run the coordinator (Governor driver) runs the next link after
> you — you never delegate or spawn it yourself.

Keep every other repo-specific instruction (tools, tokens, gates) intact.

3. **No v4 hooks/prompts/`solar-system` to delete** — `main` is already clean.

4. Leave `solar-v5-wire` untouched (reference only).

---

## Phase 4 — Verify (in order, cheapest first)

```powershell
cd "C:\CodeProjects\Personal\mandarin-vite-react-ts"
$env:PYTHONIOENCODING='utf-8'
$env:SOLAR_API_KEY=[Environment]::GetEnvironmentVariable('SOLAR_API_KEY','User')

# 1. install self-check (no network)
solar-governor doctor --repo . --json          # expect all PASS; registry: 7 specialists, chains

# 2. registry sanity (role pin, no key -> stub is fine)
solar-governor run "Read LearnRoutes.tsx and report how many routes are gated" --repo . --role investigator --thread smoke-inv --json

# 3. eval battery offline-first then real
solar-governor eval --repo . --n 1 --id cn-join                  # stub: 1/1
# `eval` and `bench` take no --runner flag; set the env knob (`run --runner` sets the same one)
$env:SOLAR_RUNNER = "http"; solar-governor eval --repo . --n 1   # http: 1/1 per case, real tokens
Remove-Item Env:SOLAR_RUNNER

# 4. driver chain (headless) — verify chain on a real task
solar-governor run --chain verify --auto --repo . --thread install-verify "<objective>"   # runner=http

# 5. git hygiene
git status --short    # expect: new .solar/registry.json, .github/* v5 files, AGENTS.md, .gitignore
git diff --stat
```

**Doctor expectations:** config PASS · checkpoint writable (created on demand) · graph
compiles · registry PASS (`10 dispatchable (7 declared + 3 built-in), chains:
epic/docs-review/verify`) · runner PASS · install PASS.

> **Free of charge:** `doctor` is read-only, and a `run` needs no key at all while the
> runner is `stub`. Note the key is read from the PROCESS environment — a Windows
> User-level `SOLAR_API_KEY` is invisible to `run` until the shell sets it.

---

## Phase 5 — Commit & next

```powershell
git add .solar/registry.json .gitignore .github/AGENTS.md .github/agents/governor-v5.agent.md .github/agents/hermes.agent.md .github/instructions/solar-agent-chain.instructions.md .github/agents/orchestrator.agent.md
git commit -m "solar v5: install governor runtime layer (driver-orchestrated) on main

Add .solar/ registry (7 roles, chains epic/docs-review/verify, playbooks);
@Governor v5 + Hermes agents; solar-agent-chain (driver) instruction;
AGENTS.md registration. Remove orchestrator residual (graph = orchestrator).
Reference: solar-v5-wire (kept for pilot proof)."
# review, then: git switch main && git merge --no-ff install/solar-v5
```

**Then (separate epic):** run the real epic-25 with the full pipeline via
`@Governor v5` on `main` — intake (Hermes) → chain (`--auto` headless or
per-link `--role` in the IDE) → gates → run-cards. Reuse the epic-25 BR/IMP +
the pilot's efficient-objective + truncation-8000 defaults.

---

## Rollback / reference

- Everything added is additive and `.solar/` is gitignored: reverting the merge
  removes the wiring; the repo's own agents/instructions/skills are untouched.
- Authoritative files to compare against at execution time: `solar-v5-wire`
  `.solar/PILOT.md` (scorecard + caveats), `.solar/registry.json`, and the
  three `.github/` v5 files above.

## Install checklist

- [ ] Engine `5.3.1` on PATH; feature branch off `main`
- [ ] `.solar/config.json` (runner = agent-dispatch default; http for headless)
- [ ] `.solar/registry.json` ported, orchestrator removed (7 roles)
- [ ] `.gitignore` + `.solar/state` exists
- [ ] `governor-v5` + `hermes` + `solar-agent-chain` copied; runner note + title fixed
- [ ] `AGENTS.md`: rows added, description corrected, orchestrator removed, `last-verified` bumped
- [ ] Role agents diffed vs wire (no `Chain exception` / self-delegation)
- [ ] `doctor` all PASS · eval 1/1 · verify chain clean verdict
- [ ] Merge to `main`; epic-25 runs as the next step

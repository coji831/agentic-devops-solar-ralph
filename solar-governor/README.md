# solar-governor — SOLAR-Ralph v5 runtime

The LangGraph control layer for SOLAR v5 (governor-as-graph). Small, installable,
repo-bounded. See `../docs/versions/v5.md` for the full design.

## Status

Released (**v5.7.0** — name a provider, name a model). The runner
work: full role capacity without a shell (line ranges, write policy, a closed command
vocabulary, an approval gate, shaped checkers, per-node model routing); a tool loop that
terminates (`v5.4.1`); a runner choosable per run (`v5.4.2`). `v5.5.0` added the
operator's surface: `doctor` names the model that will actually run, `eval` resolves cases
per repo, `uplink` posts the run digest. `v5.6.0` made an install portable and re-runnable:
`config.json` stores no absolute path, `init` merges instead of clobbering,
`.solar/VERSION` records what the repo was installed against, the `.gitignore` block is
generated, and repos declare a model **tier**. **v5.6.1** makes `.solar/ledger.md` an
append-only record — one section per run, and hand-written content in it is never touched.
**v5.6.2** fixes the two defects v5.6.1 recorded rather than fixed: a re-used thread no
longer inherits the previous run's state (a start with no pending interrupt clears that
thread's own history; a resume continues), and `--runner stub` is offline **even when a key
is set**. **v5.6.3** verifies the `http` runner against the live provider and fixes the two
defects found on the way to it: a fresh clone can now `--json` (the checkpoint directory is
created by both graph paths, not one), and every human-editable `.solar/` file is read
BOM-tolerantly — so a `config.json` written by PowerShell or Notepad still works, and an
unreadable one exits **2** with a reason instead of a traceback. **v5.6.4** makes a **local,
keyless** endpoint reachable (`run --runner http` sent no request at all before it, and
reported APPROVED), records `provider` and `tokens.reported` in the run-card so a
local-vs-cloud comparison is evidence rather than inference, and makes `doctor` warn when the
endpoint does not answer.
Pilot-validated on the mandarin repo (branch
`solar-v5-wire`, kept as reference proof): T1–T5 PASS, epic-25 Phase A
delivered, driver-orchestrated verify close-out APPROVED, known-answer eval
battery 18/18. Chaining is **driver-orchestrated** — agents never self-chain
(nested agents lack a spawn tool): headless `--chain <name> --auto`, or the
Governor agent drives each link as its own `--role` in the IDE. Next: install
into the target repo's `main` and run the real epic with the full pipeline.

## Compatibility with v4 / v5.x

`solar-governor init` writes **`.solar/`** (NEW — runtime state: config.json,
registry.json, `state/` checkpoints, ledger.md) and leaves the **`.github/`**
harness untouched (v4/v5.x agents + hooks coexist; the graph dispatches to them
via the shape-a write adapter). Two different dirs on purpose: `.github/` = the
agent harness, `.solar/` = the v5 graph runtime. v4 users will see a new folder
but nothing moved or broken.

## Commands

```bash
solar-governor init   --repo <path> --profile light          # create OR refresh .solar (never clobbers your settings)
solar-governor doctor --repo <path> [--json]                 # install self-check (PASS/FAIL)
solar-governor run "<task>" --repo <path>                    # one task through the graph (ledger + run-card)
solar-governor run "<task>" --repo <path> --role <role>      # pin one specialist (e.g. Hermes decision)
solar-governor run "<task>" --repo <path> --runner http      # choose the runner for THIS run only
solar-governor run "<task>" --repo <path> --chain <name> --auto   # whole chain, driver-orchestrated, headless
solar-governor serve --repo <path>                           # headless HTTP API (POST /run, POST /chain)
solar-governor bench "<task>" --repo <path> --n 5            # N-run aggregate (tokens/time/verdict)
solar-governor eval   --repo <path> --n 3                    # known-answer battery (quality signal)
```

Run without installing: `python -m solar_governor.cli ...` from this directory.

### Re-installing (safe, and meant to be re-run)

`init` **merges**: a setting the repo chose is kept, a key a new version introduces is
added, and the output says which was which. It also rewrites the marker-delimited
`.gitignore` block in place and writes `.solar/VERSION`.

```bash
solar-governor init --repo <path>       # refresh: keeps model/runner/human_approval
solar-governor doctor --repo <path>     # 'install' WARNs when the marker has drifted
```

A hand-written `.solar/...` rule that **conflicts** with the generated block is reported
with its line number and left alone — a duplicate of a block rule is not reported, so the
warning means something. `config.json` stores no absolute path, so it is safe to commit,
and a stale model pin can therefore show up in a diff.

### Model tiers (so a provider rename is one edit)

Instead of a concrete id, a repo or a role may declare a **tier**:

```json
{ "model_tier": "fast" }
```

`MODEL_TIERS` in the runtime maps a tier to the provider's current id. Ladder:
`SOLAR_MODEL` > role `model` > role `model_tier` > `cfg.model` > `cfg.model_tier` >
default — an explicit id beats a tier **at the same level**. An unknown tier, or a tier
asked of an unknown provider, fails the run rather than silently picking a model.
Chains are **driver-orchestrated**: a bare `--chain` (no `--auto`) is rejected
— run headless with `--auto`, or in the IDE drive each link as its own
`--role` from the Governor agent.

## Tool layers — what a role is actually offered (v5.4.0)

A specialist gets two tool layers, each **gated by the role's registry entry**. A tool the
role may not use is **not offered at all** — it is not a rule in the prompt:

| Layer       | Tools                                          | Gated by                                              |
| :---------- | :--------------------------------------------- | :---------------------------------------------------- |
| `workspace` | `list_tree`, `read_file`, `glob`, `write_file` | `tools` (group), `write`, `write_scope`, `write_deny` |
| `exec`      | `run_command`                                  | `tools` (group), `exec_allow`                         |

`read_file(rel, start, end)` takes a 1-based inclusive line range, and a ranged read
**bypasses the 40000-char whole-file cap** — so a large file is read in bounded slices
instead of being truncated mid-file and re-read.

### The write guard

Root confinement is always enforced. On top of it an **unconditional** deny-list refuses
writes to `.solar/`, `.git/`, `.github/`, `.vscode/` and to agent/CI-defining files
(`package.json`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.mcp.json`, …),
matched case-insensitively on any path segment at any depth. This closes a live hole:
`.solar/registry.json` **is the agent's system prompt**, and it used to be writable.

## `exec` — a closed vocabulary, not a shell

A repo declares named commands with **fixed** argv in `.solar/commands.json`, and a role
may only run the names it is granted:

```jsonc
{
  "typecheck": {
    "argv": ["npm", "--silent", "run", "typecheck"],
    "cwd": "apps/web",
    "kind": "check",
    "timeout": 180,
  },
  "git_status": {
    "argv": ["git", "status", "--short"],
    "kind": "read",
    "timeout": 30,
  },
}
```

| Field      | Meaning                                                                                                                       |
| :--------- | :---------------------------------------------------------------------------------------------------------------------------- |
| `argv`     | fixed, never model-supplied. There is no free-text command field **or** argument field.                                       |
| `cwd`      | repo-relative (default: the repo root), confined to the repo.                                                                 |
| `kind`     | `read` (the output IS the information) · `check` (shaped; a pass is one line) · `act` (needs approval when `human_approval`). |
| `timeout`  | seconds, enforced.                                                                                                            |
| `shape`    | `{ "summary_only": true }` or `{ "keep": "<regex>", "max_items": N }`, for checkers whose raw output is mostly noise.         |
| `describe` | the only prose a human is shown at an approval gate — from config, never from the model.                                      |

An entry's `argv[0]` is resolved through `shutil.which`, because `shell=False` cannot
execute a Windows `.CMD` shim (`npm` would raise `WinError 2`; `git` is a real `.EXE`).

**Absence is the mechanism.** A command the repo does not declare does not exist; a command
it declares but does not grant to a role does not exist _for that role_ — and the error says
which case applies, so a fixable config problem is distinguishable from a missing command.

### Approval gate

With `human_approval: true` a `kind: act` command does **not** run. It writes
`.solar/approvals/<id>.md` and returns `AWAITING APPROVAL <id>` — the tool cannot proceed, so
the model cannot either. A human writes `allow` or `deny: <reason>` to
`.solar/approvals/<id>.decision`. The id derives from the command, not the round, so a
decision is never re-asked.

## Runners — how a specialist executes (provider-agnostic)

The graph never calls a provider directly. The SPECIALIST node asks a **runner**. The
ladder is `run --runner X` (this run only) > `SOLAR_RUNNER` > the repo's `cfg.runner` >
auto (http if a key is set, else stub). An unrecognised value is an **error**, not a
silent fallback — a typo must not select a different runner than the one asked for:

| Runner           | What it does                                                                          | Needs                 |
| ---------------- | ------------------------------------------------------------------------------------- | --------------------- |
| `agent-dispatch` | Writes a task handoff (`.solar/handoffs/`), interrupts; you run the repo's            | VS Code Copilot + the |
|                  | `.agent.md` specialist in the IDE (DeepSeek via the DeepSeek-for-Copilot              | DeepSeek extension    |
|                  | extension), then paste the result (or result-file path) to resume                     |                       |
| `http`           | OpenAI-compatible chat call with repo-bounded workspace tools                         | `SOLAR_API_KEY`       |
| `stub`           | Deterministic plan text. **Offline by contract**: honoured by request, so it makes no | nothing               |
|                  | provider call even when `SOLAR_API_KEY` is set                                        |                       |

A keyless endpoint needs no `SOLAR_API_KEY` at all: an explicit `http` run sends a placeholder
the server ignores (`sk-no-key-required` — the value llama.cpp's docs pass, and what Ollama's
docs call "required but ignored"). Auto still resolves to `stub` when no key is set, so an
offline machine behaves exactly as before. See **Local endpoint** below.

Set the runner per repo at install time:

```bash
solar-governor init --repo <path> --runner agent-dispatch   # IDE-native pilot
solar-governor init --repo <path> --runner http             # headless/CLI
```

Or override it for a **single run**, without touching the committed config — so a repo
pinned to `agent-dispatch` can be exercised through `http` (or the reverse) and handed
back unchanged:

```bash
solar-governor run "<task>" --repo <path> --runner http
solar-governor run "<task>" --repo <path> --role investigator --runner stub
```

### `http` runner config (env only, never committed)

```bash
$env:SOLAR_API_KEY  = "<your deepseek/openrouter key>"   # or DEEPSEEK_API_KEY
$env:SOLAR_BASE_URL = "https://api.deepseek.com"          # default; any OpenAI-compatible host
$env:SOLAR_MODEL    = "deepseek-chat"                     # or cfg.model
$env:SOLAR_RUNNER            = "http"    # same as `run --runner http`
$env:SOLAR_TEMPERATURE       = "0.2"     # tool-loop sampling; "default" omits the field
$env:SOLAR_REASONING_EFFORT  = ""        # provider pass-through; unset sends nothing
$env:SOLAR_MAX_ROUNDS        = "12"      # model round-trips per node (read at import)
$env:SOLAR_TOOL_OUTPUT_CHARS = "8000"    # cap on one tool result, 0 = unlimited (read at import)
```

Tools (repo-bounded, refuse to escape the repo root): `list_tree` / `read_file` /
`glob` / `write_file`, plus `run_command` for a role with an `exec_allow` grant.

### Local endpoint (Ollama / llama.cpp / LM Studio / vLLM)

All of them serve the same OpenAI surface, so nothing else changes — no key, no adapter:

```bash
$env:SOLAR_BASE_URL = "http://localhost:11434/v1"   # Ollama; vLLM defaults to :8000/v1, LM Studio :1234/v1
$env:SOLAR_MODEL    = "qwen3:8b"                    # the id from GET /v1/models - required, and opaque
$env:SOLAR_RUNNER   = "http"                        # or `run --runner http`
$env:SOLAR_TOOL_OUTPUT_CHARS = "2000"               # sized for a small local context
```

Three things worth knowing before you measure:

- **No key is needed, and the placeholder is deliberate.** An explicit `http` run sends
  `sk-no-key-required`; local servers ignore it, a cloud endpoint answers 401. Auto still chooses
  the stub when no key is set, which is why an unqualified "it ran" is not the same as "it reached
  the model" — check `model` and `provider` in the run-card.
- **The model id must be the one the server serves.** `GET /v1/models` is authoritative, and
  `doctor` now checks the resolved id against it: on llama.cpp the id is the **model file path**
  unless the server was started with `--alias`. Ollama needs `PARAMETER num_ctx` in a Modelfile to
  change the context size — the OpenAI API has no field for it.
- **Read `tokens.reported`.** Some servers omit the usage block, and then `tokens: 0/0` is an
  absence rather than a measurement (the same numbers a stub reports). The run-card says which,
  and records `provider` (host:port) next to `model` so a local run is distinguishable from a
  cloud run of the same model id.

`doctor` against a local endpoint: `runner: PASS - http (... no SOLAR_API_KEY: a placeholder is
sent ...)` and `model: PASS - qwen3:8b (from config model) [provider serves 1 id(s)]` when the
server is up, or `model: WARN - ... cannot list its models (Connection error.)` when it is not.

### Providers and models — name them instead of exporting them

A repo declares WHICH endpoint its models live on, and names the models it uses. Nothing about the
run changes: same graph, same runners, same run-card — plus `provider` in the record.

```json
{
  "provider": "deepseek",
  "providers": {
    "local": {"base_url": "http://localhost:11434/v1", "api_key_env": ""}
  },
  "models": {
    "fast":       {"provider": "deepseek", "id": "deepseek-flash"},
    "local-qwen": {"provider": "local",    "id": "qwen3:8b"}
  },
  "model": "local-qwen"
}
```

- **`providers`** — 17 shipped entries: `openai`, `deepseek`, `openrouter`, `groq`, `mistral`,
  `xai`, `together`, `fireworks`, `cerebras`, `anthropic`, `perplexity`, `moonshot`, the local
  servers `ollama` / `lmstudio` / `vllm` / `llamacpp`, and `gateway` for a self-hosted router
  (LiteLLM & co). A repo entry merges per FIELD over a shipped one, so repointing a provider at a
  mirror is one line. Every shipped `base_url` was probed unauthenticated before shipping — 401/403
  (or 400 on `/chat/completions` where a provider has no model list) means the endpoint exists and
  wants a key, and a 404 means the path is wrong and the entry is not shipped.
- **`api_key_env` is a NAME, never a value.** `.solar/config.json` is committed, so a provider
  entry names the environment variable to read. A provider's credential is read ONLY from its own
  variable — it is never satisfied by an unrelated key that happens to be set. An empty
  `api_key_env` is the local case (and needs v5.6.4's placeholder to run).
- **`models`** maps an alias to a provider and an id. An alias wins at every rung of the model
  ladder, so it can be named from a config, a role or a chain: `SOLAR_MODEL=local-qwen` switches
  one run without editing a committed file — which is how you A/B a local model against a cloud one
  and prove it afterwards from `provider` in the run-card. An alias named after a shipped tier
  (`fast`, `reasoner`) shadows that tier for this repo.
- **`headers` / `extra_body`** carry what a router needs: OpenRouter's `HTTP-Referer` and
  `X-OpenRouter-Title` are headers, and its `provider` routing object, `models` fallback list and
  `route` are **body** fields (`extra_body`). The runner strips its own keys (`model`, `messages`,
  `tools`) from `extra_body` first, so a routing object can add fields but never replace the prompt.
- **`provider` per role** lets one chain put its reasoner in the cloud and its fast steps on a
  local model.
- **An unknown provider name is a REJECTED run**, not a fallback to the default endpoint — and it
  fails even when an alias would have chosen a valid provider, because a name you believe is in
  effect must not be quietly ignored.
- **A tier needs a family.** `model_tier: "fast"` resolves through the provider's `family`; a local
  provider has none, so declare a `models` alias instead (the error says exactly that).

`doctor` reports the chain: `provider: PASS - 17 shipped; overrides: deepseek; 1 model alias(es):
fast; selected: deepseek` and `model: PASS - deepseek-flash (from config model=fast ->
deepseek-flash; provider deepseek @ https://api.deepseek.com [SOLAR_API_KEY set]) [provider serves
2 id(s)]`. Note what it does NOT print: a credential value, ever.

**No config means no change.** A repo with no `providers`/`models` uses `SOLAR_BASE_URL`,
`SOLAR_API_KEY` and `SOLAR_MODEL` exactly as before, and `to_dict` omits the empty fields so a
committed config gains no noise.

### Hub uplink (opt-in, push-only)

`uplink: none | hub:<url>` in `.solar/config.json`. The default is `none`: the repo is
the source of truth and the harness is fully standalone on any repo, including
third-party ones. When set, the run digest — routing, verdict, metrics, decisions,
output _length_ — is POSTed to `<url>/run` after the ledger and run-card are written.

- **Push-only.** `uplink.py` contains no download path, so a hub cannot inject content
  into a repo's context.
- **Never in the critical path.** Unreachable, refused or HTTP-erroring hubs degrade to a
  printed status line; a hub cannot fail a run or change its verdict.
- `doctor` validates the value without touching the network.

### `agent-dispatch` flow (mandarin pilot)

1. `solar-governor run "<task>" --repo <path>` → graph routes to a role
   (registry) and writes `.solar/handoffs/<role>-attempt1-*.md`.
2. It interrupts: open the repo in VS Code Copilot, run that `.agent.md`
   specialist (its model = DeepSeek via the extension) with the handoff's
   Objective.
3. Paste the agent's result back (or save it and type the path) → the graph
   resumes → review → complete → ledger + run-card.
4. Non-interactive: `solar-governor run "<task>" --result "<text|path>"`.

### `--json` step contract (agent-driven UI — v4-like UX on a graph core)

`run --json` executes **one graph step** and returns a machine-readable JSON doc
with a distinct exit code, so a thin driver agent (the UI entry point) can run,
interrupt, dispatch a specialist, and resume — instead of a human babysitting
stdin. The graph/runners underneath stay provider-agnostic.

```bash
# start a new thread (or step an empty one):
solar-governor run "<task>" --repo <path> --thread <t> --json
# resume a paused thread (task string identical; state comes from checkpoint):
solar-governor run "<task>" --repo <path> --thread <t> --json --result "<file|text>"   # agent-dispatch
solar-governor run "<task>" --repo <path> --thread <t> --json --approve approve|deny    # review
```

| Exit | Meaning                                                               | JSON `status`                                                |
| ---- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| `0`  | run complete                                                          | `complete` — stage/verdict/role/output/run_card              |
| `10` | paused: run the specialist, then `--result`                           | `interrupt` kind=`agent-dispatch` — role/attempt/handoff/ask |
| `11` | paused: ask the human, then `--approve`                               | `interrupt` kind=`review` — role/ask                         |
| `2`  | usage/state error (e.g. resume on a thread with no pending interrupt) | `error` — message                                            |

A paused thread is detected via the SQLite checkpoint; `run --json` refuses to
plain-invoke a paused thread (that would resume with the wrong value). Ledger +
run-card are (re)written at every step, so progress is on disk even mid-pause.

**Thread state is not cumulative.** A start with **no pending interrupt** is a fresh start,
and clears that thread's own history first, so re-using an id (including the default `t1`)
never inherits an earlier run's work queue, decisions or token totals. A **resume**
continues and clears nothing. The fresh run says which happened — `fresh start on thread
't1': cleared the previous run's state` is its first decisions entry — so the run-card and
the ledger account for why their totals start at zero.

A driver agent (`@Governor v5`, see the repo's `.github/agents/`) loops on these
exit codes: exit 10 → read the handoff, run the matching `.agent.md` specialist
(via `runSubagent`), save its answer to `<handoff>.result.md`, resume with that
path; exit 11 → ask the user approve/deny and resume with `--approve`.

## What it proves now

- Light graph: `MATERIAL_GATE → DISPATCH → SPECIALIST → REVIEW(cond) → COMPLETE`
  with a bounded rework loop (≤3).
- Registry-aware routing: repo roles (e.g. mandarin's frontend-engineer) win over
  generic defaults when their name appears in the task.
- SQLite checkpoint (durable, resume by thread_id) + interrupt-over-CLI when
  `human_approval` is on.
- Runner abstraction: `agent-dispatch` (IDE handoff) · `http` · `stub`.
- Ledger (`record`) appends one section per run and never rewrites content it did not
  write; run-card JSON per run at `.solar/runs/<thread>.json` (tokens, verdict, model,
  decisions).
- Thread state is not cumulative: a fresh start clears that thread's own history, a
  resume continues it.
- Install paths that work on a clone: the checkpoint directory is created on demand by both
  `run_step` and `pending_interrupt`, `doctor`'s checkpoint check tests creatability, and the
  `.solar/` files a human edits are read BOM-tolerantly.
- A local keyless endpoint is reachable, and the record distinguishes it: `provider` (host:port)
  and `tokens.reported` in every run-card.

## Test

```bash
python -m pytest tests/           # 205 tests: graph, routing, ledger, executor, server,
                                  # workspace guards, command vocabulary + approval gate,
                                  # tool-loop termination, runner selection, uplink,
                                  # doctor + eval case resolution, install surface,
                                  # install paths (fresh clone, BOM), thread reset/resume,
                                  # stub-runner offline contract, local endpoint (real HTTP),
                                  # provider registry (endpoint/headers/body/key on the wire)
python tests/test_smoke.py        # smoke only
```

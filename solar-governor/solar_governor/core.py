"""Core: state schema (v5 §4) + config."""
import dataclasses
import json
import operator
from pathlib import Path
from typing import Annotated, TypedDict


def read_text(path: Path | str) -> str:
    """Read a file a HUMAN may have authored: BOM-tolerant (v5.6.3).

    Everything under `.solar/` except the checkpoints is committed and hand-editable, and
    a UTF-8 BOM is an ordinary outcome of editing one on Windows: PowerShell 5.1's
    `Set-Content -Encoding utf8` writes one, and so does Notepad's "UTF-8 with BOM".
    `json.loads` rejects a leading BOM, so a config that was correct by every visual
    measure killed the run with a traceback. Reading as `utf-8-sig` accepts both forms -
    it is a no-op on a file without a BOM.
    """
    return Path(path).read_text(encoding="utf-8-sig")


def read_json(path: Path | str):
    """Parse a JSON file a human may have authored (see `read_text`)."""
    return json.loads(read_text(path))


class TaskRow(TypedDict):
    id: str
    task: str
    role: str
    status: str
    stage: str


class SolarState(TypedDict):
    """v5 §4: ledger-sourced + runtime fields (light profile subset)."""
    objective: str
    role: str                                  # routed specialist role (or chain entry)
    chain: str                                 # named chain, when running one (else "")
    # **WHICH CLONE THIS RUN IS ABOUT** (T50, 2026-09-23), declared by the RUN rather than inferred
    # from a role's name or a command's: twelve entries used to hard-code one client, so a link
    # working on another clone could take a PASS from the wrong repository. `""` is the run saying
    # `none`, which every clone-scoped command refuses - see `commands.CommandRunner._cwd`.
    clone: str
    materials_status: str                      # PENDING / READY / INSUFFICIENT
    work_queue: Annotated[list, operator.add]
    decisions_log: Annotated[list, operator.add]
    verdict: str                               # APPROVED / REJECTED
    output: str
    attempts: int                              # rework loop counter
    stage: str
    # run-card metrics (v5 §14.7.3) — accumulated across rework attempts
    model: str                                 # model used (or "stub")
    tokens_in: Annotated[int, operator.add]    # prompt tokens (accumulates)
    tokens_out: Annotated[int, operator.add]   # completion tokens (accumulates)
    tool_calls: Annotated[int, operator.add]   # workspace tool calls
    # The run's NODE clock, in ms: every node's execution, summed (v5.7.4).
    #
    # It is a reducer for exactly the reason the three above are, and the reason the card's
    # `duration_ms` was wrong: `run_step` executes one step and the driver resumes with
    # `--result`, so a run's time is spread across several CLI INVOCATIONS, and nothing that
    # lives only inside one process can total it. The checkpoint carries it, so a resume adds
    # to it instead of replacing it. See `graph._timed`.
    #
    # **It is not `duration_ms`, and the two are not comparable.** `node_ms` counts work
    # inside the graph; `duration_ms` is a wall clock around one CLI invocation, which is
    # mostly process overhead when the run was resumed and mostly the model call when one
    # invocation did everything. Measured on a stub run: `node_ms` 2 ms, `duration_ms` 26 ms.
    # Named for what it counts - v5.7.3's own rule (`passed` -> `approved`), applied here.
    node_ms: Annotated[int, operator.add]
    error: str                                 # executor error, if any
    forced_final: bool                         # answer came from the tool-less last round
    # **THE THREE THE NODE RETURNS THAT THIS SCHEMA DID NOT DECLARE** (2026-09-25). A LangGraph
    # state IS its schema: an undeclared key is not a channel, so it is dropped in SILENCE - proven
    # by returning one from a node and watching it vanish, with no warning. `_execute` has returned
    # these three since `T12`/`T14` and `runcard.write` reads all three, so **every card recorded
    # `0`**; `audit-run.py` prints them beside the window a run was aimed at, which is why it could
    # only ever say "not on the card" and "undeclared".
    max_rounds: int                            # round-trips this node was allowed
    prompt_tokens: int                         # prompt assembled before round 1 (text only, a floor)
    context_tokens: int                        # window declared at that moment (0 = none declared)
    provider: str                              # endpoint the run went to (host:port, or "stub")
    usage_reported: bool                       # endpoint reported usage (0/0 is "unknown" if not)
    # The tool-call TRANSCRIPT (T10, 2026-09-23), written by `executor._tool_loop`: one row per
    # tool call - `n`, `round`, `tool`, `target`, `args_chars`, `result_chars`, `ok`, `head`.
    #
    # **It is carried as a state CHANNEL so the checkpoint stores it, and it is telemetry.**
    # `runcard.write` builds its card from an explicit field list, so this channel cannot reach the
    # tracked record - which is the boundary `T11` ruled: `.solar/state/` is gitignored, per-machine,
    # and nothing may cite it. Adding the key here is the whole delivery mechanism: the harness part
    # that owns instrumentation is the graph's own checkpointer, and a table of our own would have
    # been the fifth sink `05` section 4 forbids.
    #
    # **A plain channel rather than an `operator.add` one**, deliberately: a reducer would
    # concatenate every node's calls into one list and lose which LINK made which call, while a
    # plain channel writes ONE ROW PER NODE into `writes` - so the attribution is free, and it is
    # the thing the item is for.
    tool_transcript: list


DEFAULTS: dict = {
    "profile": "light",
    # "" since v5.6.0: an empty repo means DERIVE the root from the config file's own
    # location, so the persisted config carries no absolute path.
    "repo": "",
    "state_dir": ".solar/state",
    "ledger": ".solar/ledger.md",
    "uplink": "none",
    "model": "",          # "" = deterministic stub executor (no API key needed)
    # Tier alternative to a concrete id (v5.6.0): "fast" resolves to the provider's
    # current id for that tier, so a provider rename is ONE edit in the runtime
    # instead of one edit per repo. An explicit `model` at the same level still wins.
    "model_tier": "",
    "human_approval": False,
    # WHICH endpoint, and the models this repo names (v5.7.0). `provider` selects an entry
    # from `providers`; `models` maps a repo-chosen ALIAS to a provider + an opaque id, so a
    # model is declared once and referred to by name from a config, a role or a chain.
    # Neither ever holds a credential: `providers.<name>.api_key_env` names the environment
    # variable to read, because this file is committed.
    "provider": "",
    "providers": {},
    "models": {},
    # Reasoning/thinking effort passed through to the provider (TD-5.4-2). "" sends
    # no such field, which is the default: providers disagree about the scale and
    # about whether they accept it, so opting in is explicit.
    "reasoning_effort": "",
    # Runner = HOW the specialist node executes work (provider-agnostic, v5 §3):
    #   ""             -> auto (http if SOLAR_API_KEY set, else stub)
    #   "http"         -> OpenAI-compatible HTTP client
    #   "agent-dispatch" -> hand off to the repo's .agent.md agents (IDE-native)
    "runner": "",
    # **The context window this install is measured against, in TOKENS of INPUT** (2026-09-25).
    # Until then it was an environment variable alone (`SOLAR_CONTEXT_TOKENS`) and there was no
    # durable file to put it in - so no install ever declared one, every card recorded `0`, and
    # `doctor` advised an action the runtime gave no way to take. `0` is UNDECLARED, the same
    # sentinel `tool_output_chars` uses. The env var still overrides it.
    "context_tokens": 0,
}


@dataclasses.dataclass
class Config:
    profile: str = DEFAULTS["profile"]
    # OPTIONAL. Left empty, `root` is derived from the config file's own location
    # (`<root>/.solar/config.json`), which is what makes a config portable: a stored
    # absolute path was its only machine-specific field, and it is why the two
    # engagements disagreed about whether the file could be committed at all.
    repo: str = DEFAULTS["repo"]
    state_dir: str = DEFAULTS["state_dir"]
    ledger: str = DEFAULTS["ledger"]
    uplink: str = DEFAULTS["uplink"]
    model: str = DEFAULTS["model"]
    model_tier: str = DEFAULTS["model_tier"]
    human_approval: bool = DEFAULTS["human_approval"]
    provider: str = DEFAULTS["provider"]
    providers: dict = dataclasses.field(default_factory=dict)
    models: dict = dataclasses.field(default_factory=dict)
    reasoning_effort: str = DEFAULTS["reasoning_effort"]
    runner: str = DEFAULTS["runner"]
    context_tokens: int = DEFAULTS["context_tokens"]
    # Where this config was read from. Runtime-only: never persisted, because it IS
    # the file's location - and it is how `root` is derived.
    loaded_from: Path | None = dataclasses.field(default=None, repr=False, compare=False)

    # fields that exist in memory but never in the file
    _RUNTIME_FIELDS = frozenset({"loaded_from"})

    @property
    def root(self) -> Path:
        """The repo this config governs.

        Precedence: an explicit `repo` > the directory holding this config's
        `.solar/`. So a committed config travels with its repo and still points at
        itself, wherever the clone lands.
        """
        if self.repo:
            return Path(self.repo).expanduser().resolve()
        if self.loaded_from is not None:
            return Path(self.loaded_from).expanduser().resolve().parent.parent
        return Path(".").expanduser().resolve()

    @property
    def checkpoint_path(self) -> Path:
        return self.root / self.state_dir / "checkpoints.sqlite"

    @property
    def ledger_path(self) -> Path:
        return self.root / self.ledger

    def to_dict(self) -> dict:
        """The persisted shape - portable by construction.

        `loaded_from` is never written (it is the file's location), and an empty
        `repo` is omitted rather than written as "": a derived config round-trips as
        a file with no machine-specific content, which is what makes committing it
        correct in every repo.
        """
        d = dataclasses.asdict(self)
        for name in self._RUNTIME_FIELDS:
            d.pop(name, None)
        if not d.get("repo"):
            d.pop("repo", None)
        # The empty provider/model fields are omitted for the same reason as `repo`: a repo
        # that declares neither should not gain three lines of noise in a COMMITTED file.
        for empty in ("provider", "providers", "models"):
            if not d.get(empty):
                d.pop(empty, None)
        return d

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Config":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"no config at {path} — run `solar-governor init`")
        d = read_json(path)
        keys = {f.name for f in dataclasses.fields(cls)} - cls._RUNTIME_FIELDS
        cfg = cls(**{k: v for k, v in d.items() if k in keys})
        cfg.loaded_from = path
        return cfg

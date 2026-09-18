"""Core: state schema (v5 §4) + config."""
import dataclasses
import json
import operator
from pathlib import Path
from typing import Annotated, TypedDict


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
    error: str                                 # executor error, if any
    forced_final: bool                         # answer came from the tool-less last round


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
    # Reasoning/thinking effort passed through to the provider (TD-5.4-2). "" sends
    # no such field, which is the default: providers disagree about the scale and
    # about whether they accept it, so opting in is explicit.
    "reasoning_effort": "",
    # Runner = HOW the specialist node executes work (provider-agnostic, v5 §3):
    #   ""             -> auto (http if SOLAR_API_KEY set, else stub)
    #   "http"         -> OpenAI-compatible HTTP client
    #   "agent-dispatch" -> hand off to the repo's .agent.md agents (IDE-native)
    "runner": "",
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
    reasoning_effort: str = DEFAULTS["reasoning_effort"]
    runner: str = DEFAULTS["runner"]
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
        return d

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Config":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"no config at {path} — run `solar-governor init`")
        d = json.loads(path.read_text(encoding="utf-8"))
        keys = {f.name for f in dataclasses.fields(cls)} - cls._RUNTIME_FIELDS
        cfg = cls(**{k: v for k, v in d.items() if k in keys})
        cfg.loaded_from = path
        return cfg

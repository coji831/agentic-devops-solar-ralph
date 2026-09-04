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
    role: str                                  # routed specialist role
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


DEFAULTS: dict = {
    "profile": "light",
    "repo": ".",
    "state_dir": ".solar/state",
    "ledger": ".solar/ledger.md",
    "uplink": "none",
    "model": "",          # "" = deterministic stub executor (no API key needed)
    "human_approval": False,
}


@dataclasses.dataclass
class Config:
    profile: str = DEFAULTS["profile"]
    repo: str = DEFAULTS["repo"]
    state_dir: str = DEFAULTS["state_dir"]
    ledger: str = DEFAULTS["ledger"]
    uplink: str = DEFAULTS["uplink"]
    model: str = DEFAULTS["model"]
    human_approval: bool = DEFAULTS["human_approval"]

    @property
    def root(self) -> Path:
        return Path(self.repo).expanduser().resolve()

    @property
    def checkpoint_path(self) -> Path:
        return self.root / self.state_dir / "checkpoints.sqlite"

    @property
    def ledger_path(self) -> Path:
        return self.root / self.ledger

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            raise FileNotFoundError(f"no config at {path} — run `solar-governor init`")
        d = json.loads(path.read_text(encoding="utf-8"))
        keys = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in keys})

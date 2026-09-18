"""A local, keyless OpenAI-compatible endpoint — does the http runner actually reach it?

Verifying the runner against a live provider found that it could not: `run --runner http`
with no `SOLAR_API_KEY` fell back to the STUB, reported APPROVED and recorded `tokens 0/0`,
so a run against a healthy Ollama/llama.cpp server never happened and read as a success.

These tests use a REAL local HTTP server (127.0.0.1, in-process, nothing external), because
the defect was not in a function — it was in whether a request goes out at all and what the
record then claims. A mock at the function boundary cannot see that.

Covered: the keyless run reaching the endpoint; auto still stubbing (unchanged); the endpoint
recorded as provenance; usage omitted by the endpoint not reading as 0-from-a-real-model.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("SOLAR_RUNNER", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import executor, runcard                # noqa: E402
from solar_governor.core import Config                     # noqa: E402
from solar_governor.graph import run_task                  # noqa: E402

REQUESTS: list[dict] = []


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Every test here owns its environment, whatever ran before it in the process.

    Popping the knobs at import is NOT enough. `cli.cmd_run --runner X` sets `SOLAR_RUNNER`
    for the whole process and never restores it, so after another test module runs one,
    `select_runner` returns that value for everything that follows - and env beats config
    BY DESIGN. This module passed alone (6/6) and failed in the full suite with
    `model == 'stub'`, which is what a contaminated measurement looks like.
    """
    for name in ("SOLAR_API_KEY", "DEEPSEEK_API_KEY", "SOLAR_RUNNER", "SOLAR_MODEL",
                 "SOLAR_BASE_URL", "SOLAR_TEMPERATURE", "SOLAR_REASONING_EFFORT"):
        monkeypatch.delenv(name, raising=False)
    yield


class _Endpoint(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible server. `report_usage=False` models the servers that omit
    the usage block entirely."""

    report_usage = True
    answer = "LOCAL ANSWER: done."

    def log_message(self, *a):
        pass

    def _send(self, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        REQUESTS.append({"method": "GET", "path": self.path})
        self._send({"object": "list", "data": [{"id": "local-model", "object": "model"}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}")
        REQUESTS.append({"method": "POST", "path": self.path,
                         "model": payload.get("model"),
                         "auth": self.headers.get("Authorization")})
        body = {"id": "1", "object": "chat.completion", "model": payload.get("model"),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": self.answer}}]}
        if self.report_usage:
            body["usage"] = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
        self._send(body)


def _serve(report_usage: bool = True) -> tuple[HTTPServer, str]:
    handler = type("H", (_Endpoint,), {"report_usage": report_usage})
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


def _repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-local-"))
    (r / "app.py").write_text("x = 1\n", encoding="utf-8")
    return r


def _cfg(repo: Path, runner: str = "http") -> Config:
    cfg = Config(repo=str(repo), runner=runner)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def _card(repo: Path, thread: str) -> dict:
    return json.loads((repo / ".solar" / "runs" / f"{thread}.json").read_text(encoding="utf-8"))


def _run_and_write_card(cfg: Config, repo: Path, thread: str) -> dict:
    """`run_task` does not write the run-card - the CLI and `chain.py` do. Call the writer
    the same way they do, so the assertions are about the real artefact."""
    started = time.time()
    state = run_task(cfg, "say hello", thread=thread)
    runcard.write(cfg, state, thread, started)
    return _card(repo, thread)


def test_a_keyless_endpoint_is_reached_and_the_run_is_real(monkeypatch):
    """The blocker, end to end: no key anywhere, `runner: http`, and the endpoint receives
    the request. Before v5.6.4 this produced model=stub with no request sent at all."""
    srv, url = _serve()
    repo = _repo()
    monkeypatch.setenv("SOLAR_BASE_URL", url)
    monkeypatch.setenv("SOLAR_MODEL", "local-model")
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    try:
        REQUESTS.clear()
        state = run_task(_cfg(repo), "say hello", thread="keyless")

        posted = [r for r in REQUESTS if r["method"] == "POST"]
        assert posted, "the endpoint was never called - the run fell back to the stub"
        assert posted[0]["auth"] == f"Bearer {executor.NO_KEY_PLACEHOLDER}"
        assert state["model"] == "local-model"
        assert state["verdict"] == "APPROVED"
        assert state["tokens_in"] == 11 and state["tokens_out"] == 7
        assert state["usage_reported"] is True
    finally:
        srv.shutdown()
        shutil.rmtree(repo)


def test_auto_without_a_key_still_stubs(monkeypatch):
    """The placeholder is for an EXPLICIT http run only. Auto must keep resolving to the
    stub with no key, so no existing offline workflow starts making requests."""
    srv, url = _serve()
    repo = _repo()
    monkeypatch.setenv("SOLAR_BASE_URL", url)
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    monkeypatch.delenv("SOLAR_RUNNER", raising=False)
    try:
        REQUESTS.clear()
        state = run_task(_cfg(repo, runner=""), "say hello", thread="auto")
        assert state["model"] == "stub"
        assert not [r for r in REQUESTS if r["method"] == "POST"]
    finally:
        srv.shutdown()
        shutil.rmtree(repo)


def test_the_run_card_records_where_the_run_went(monkeypatch):
    """The model id cannot carry provenance: the same string can be a laptop or a hosted
    endpoint. Without the endpoint recorded, a local-vs-cloud comparison is inference."""
    srv, url = _serve()
    repo = _repo()
    monkeypatch.setenv("SOLAR_BASE_URL", url)
    monkeypatch.setenv("SOLAR_MODEL", "local-model")
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    try:
        card = _run_and_write_card(_cfg(repo), repo, "prov")
        assert card["provider"] == f"127.0.0.1:{srv.server_address[1]}"
        assert card["model"] == "local-model"
        assert card["tokens"] == {"in": 11, "out": 7, "reported": True}
    finally:
        srv.shutdown()
        shutil.rmtree(repo)


def test_a_stub_run_is_recorded_as_stub_not_as_an_endpoint(monkeypatch):
    repo = _repo()
    monkeypatch.setenv("SOLAR_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    try:
        card = _run_and_write_card(_cfg(repo, runner="stub"), repo, "stubcard")
        assert card["provider"] == "stub"
        assert card["tokens"]["reported"] is False
    finally:
        shutil.rmtree(repo)


def test_an_endpoint_that_omits_usage_is_not_recorded_as_zero(monkeypatch):
    """0/0 from a real model is the same two numbers a stub reports. The card has to say
    which it is, or the token column - the thing being measured - can be silently empty."""
    srv, url = _serve(report_usage=False)
    repo = _repo()
    monkeypatch.setenv("SOLAR_BASE_URL", url)
    monkeypatch.setenv("SOLAR_MODEL", "local-model")
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    try:
        card = _run_and_write_card(_cfg(repo), repo, "nousage")
        assert card["model"] == "local-model"          # a real call, with a real model
        assert card["tokens"]["in"] == 0 and card["tokens"]["out"] == 0
        assert card["tokens"]["reported"] is False     # ...and it says so
    finally:
        srv.shutdown()
        shutil.rmtree(repo)


def test_known_models_lists_a_keyless_local_endpoint(monkeypatch):
    """`doctor`'s model check needs this to be able to say anything about a local server."""
    srv, url = _serve()
    monkeypatch.setenv("SOLAR_BASE_URL", url)
    monkeypatch.delenv("SOLAR_API_KEY", raising=False)
    try:
        ids, err = executor.known_models(runner="http")
        assert ids == ["local-model"] and err == ""
        # ...and NOT for a runner that was not asked to call anything
        ids, err = executor.known_models(runner="stub")
        assert ids is None and err == "no API key"
    finally:
        srv.shutdown()

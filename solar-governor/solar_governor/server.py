"""Headless HTTP API for solar-governor (v5 §9 'remote later' slice).

Zero-dependency stdlib server exposing the same ONE-STEP contract as
`run --json`, so any client (curl, scripts, other platforms/tools, a future
UI) can run a task and read numbers without an IDE or an interactive shell.

Endpoints
---------
GET  /health                 -> {ok, runner, api_key, version}
POST /run                    -> one graph step (same shape/exit semantics as
                               `run --json`, minus the process exit codes)

POST /run body:
    {
      "task":   "<objective>",          # required
      "repo":   "<path>",                # default: process cwd
      "thread": "<id>",                  # default: "t1"
      "role":   "<registry role>",       # optional: pin dispatch (Hermes decision)
      # NOTE: chains are driver-orchestrated — use POST /chain (auto), not this route.
      "approve":"approve|deny",          # optional: resume a review interrupt
      "result": "<text|file path>"       # optional: resume an agent-dispatch
    }

A paused run returns status "interrupt" with the same fields as the CLI; call
POST /run again with `result`/`approve` (same thread) to resume. A completed
run returns status "complete" with the run-card numbers.

Run:  python -m solar_governor.server [--host 127.0.0.1] [--port 8787]
"""
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import chain, executor, runcard
from . import __version__          # single source: the package, not a second literal
from .core import Config
from .graph import pending_interrupt, run_step
from .ledger import render
from .registry import load as load_registry
from .registry import role_keys


def _cfg_for(repo: str) -> Config:
    root = Path(repo).expanduser().resolve()
    return Config.load(root / ".solar" / "config.json")


def _run_one_step(repo: str, body: dict) -> tuple[int, dict]:
    """Execute one graph step; returns (http_status, response_dict)."""
    task = (body.get("task") or "").strip()
    if not task:
        return 400, {"status": "error", "message": "'task' is required"}
    thread = body.get("thread") or "t1"
    role = (body.get("role") or "").strip()
    chain = (body.get("chain") or "").strip()
    approve = (body.get("approve") or "").strip()
    result = (body.get("result") or "").strip()

    cfg = _cfg_for(repo)
    reg = load_registry(cfg.root / ".solar" / "registry.json")

    if role and role not in role_keys(reg):
        return 400, {"status": "error", "message": f"unknown role '{role}'"}
    if chain:
        return 400, {"status": "error",
                     "message": "chains are driver-orchestrated: use POST /chain "
                                "(headless auto, link-by-link) instead of POST /run "
                                "with 'chain'; or pass a single 'role' per link"}

    resume = None
    if result:
        resume = result
    elif approve:
        if approve not in ("approve", "deny"):
            return 400, {"status": "error", "message": "approve must be approve|deny"}
        resume = "approve" if approve == "approve" else "deny"

    pending = pending_interrupt(cfg, thread)
    if resume is not None and pending is None:
        return 409, {"status": "error",
                     "message": f"thread '{thread}' has no pending interrupt to resume"}
    if resume is None and pending is not None:
        return 409, {"status": "error",
                     "message": f"thread '{thread}' is paused at {pending.get('kind')} — "
                                f"resume with 'result' or 'approve'"}

    started = time.time()
    state = run_step(cfg, task, thread, resume=resume, chain=chain, role=role)
    render(cfg, state)
    runcard.write(cfg, state, thread, started)

    summary = {k: state.get(k) for k in
               ("objective", "role", "chain", "materials_status", "stage", "verdict",
                "attempts", "tokens_in", "tokens_out", "tool_calls", "model", "error")}

    if "__interrupt__" in state:
        payload = state["__interrupt__"][0].value
        kind = payload.get("kind", "review")
        if kind == "agent-dispatch":
            return 200, {"status": "interrupt", "kind": "agent-dispatch", "thread": thread,
                         "role": payload.get("role") or state.get("role", ""),
                         "attempt": payload.get("attempt", 0),
                         "handoff": payload.get("handoff", ""),
                         "ask": payload.get("ask", ""), "state": summary}
        return 200, {"status": "interrupt", "kind": "review", "thread": thread,
                     "ask": payload.get("ask", "approve or deny?"),
                     "state": summary}

    return 200, {"status": "complete", "thread": thread, **summary,
                 "output": state.get("output", ""),
                 "run_card": str(cfg.root / ".solar" / "runs" / f"{thread}.json")}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
            return body if isinstance(body, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        if self.path.rstrip("/").endswith("/health"):
            # A bad SOLAR_RUNNER / config runner must not take the health endpoint
            # down with it: report it instead of raising (TD-5.4-9).
            try:
                runner, runner_error = executor.select_runner(_server_cfg_runner()), ""
            except ValueError as e:
                runner, runner_error = "invalid", str(e)
            self._send(200, {"ok": True, "version": __version__, "runner": runner,
                             "runner_error": runner_error,
                             "api_key": executor.api_key() is not None})
        else:
            self._send(404, {"status": "error", "message": f"no route {self.path}"})

    def do_POST(self):
        path = self.path.rstrip("/")
        if path.endswith("/run"):
            body = self._read_body()
            repo = body.get("repo") or _server_cwd()
            code, obj = _run_one_step(repo, body)
            self._send(code, obj)
        elif path.endswith("/chain"):
            self._handle_chain()
        else:
            self._send(404, {"status": "error", "message": f"no route {self.path}"})

    def _handle_chain(self):
        body = self._read_body()
        repo = body.get("repo") or _server_cwd()
        task = (body.get("task") or "").strip()
        chain_name = (body.get("chain") or "").strip()
        thread = (body.get("thread") or "chain").strip()
        if not task or not chain_name:
            return self._send(400, {"status": "error",
                                    "message": "'task' and 'chain' are required"})
        try:
            cfg = _cfg_for(repo)
            agg = chain.run_chain(cfg, chain_name, task, thread=thread)
        except KeyError as e:
            return self._send(400, {"status": "error", "message": str(e)})
        except SystemExit as e:
            return self._send(400, {"status": "error", "message": str(e)})
        self._send(200, {"status": "complete", **agg})

    def log_message(self, fmt, *args):  # keep logs terse
        pass


_server_state = {"repo": ".", "runner": ""}


def _server_cwd() -> str:
    return str(Path(_server_state["repo"]).expanduser().resolve())


def _server_cfg_runner() -> str:
    try:
        cfg = _cfg_for(_server_cwd())
        return cfg.runner
    except Exception:
        return ""


def serve(repo: str = ".", host: str = "127.0.0.1", port: int = 8787) -> None:
    _server_state["repo"] = repo
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"solar-governor HTTP API on http://{host}:{port} "
          f"(repo={_server_cwd()}, GET /health, POST /run, POST /chain)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(prog="solar-governor.server")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    serve(args.repo, args.host, args.port)


if __name__ == "__main__":
    main()

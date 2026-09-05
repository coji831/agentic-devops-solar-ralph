"""Offline tests for the headless HTTP API (stub runner — no network, no key)."""
import json
import shutil
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import server              # noqa: E402
from solar_governor.core import Config          # noqa: E402


def _tmp_repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-http-"))
    (r / ".solar").mkdir(parents=True)
    cfg = Config(repo=str(r), runner="stub")
    cfg.save(r / ".solar" / "config.json")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return r


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_run_one_step_completes_on_stub():
    r = _tmp_repo()
    code, obj = server._run_one_step(str(r), {"task": "add a login feature with tests",
                                              "thread": "s1", "role": "tester"})
    assert code == 200
    assert obj["status"] == "complete"
    assert obj["role"] == "tester"
    assert obj["verdict"] == "APPROVED"
    assert (r / ".solar" / "runs" / "s1.json").exists()   # run-card written
    shutil.rmtree(r)


def test_run_rejects_unknown_role():
    r = _tmp_repo()
    code, obj = server._run_one_step(str(r), {"task": "x", "thread": "s2",
                                              "role": "ghost"})
    assert code == 400 and obj["status"] == "error"
    shutil.rmtree(r)


def test_run_rejects_chain_field_driver_only():
    """POST /run with 'chain' is rejected — chains run via POST /chain (auto)."""
    r = _tmp_repo()
    code, obj = server._run_one_step(str(r), {"task": "x", "thread": "s2b",
                                              "chain": "epic"})
    assert code == 400 and obj["status"] == "error"
    assert "driver-orchestrated" in obj["message"]
    shutil.rmtree(r)


def test_health_and_run_over_real_http():
    r = _tmp_repo()
    # serve_forever blocks: run the handler on an ephemeral-port server in a thread
    from http.server import ThreadingHTTPServer
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=10) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["ok"] is True
        code, obj = _post(f"{base}/run", {"task": "add a login feature with tests",
                                          "repo": str(r), "thread": "s3", "role": "tester"})
        assert code == 200 and obj["status"] == "complete"
    finally:
        httpd.shutdown()
        httpd.server_close()
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in (test_run_one_step_completes_on_stub,
               test_run_rejects_unknown_role,
               test_health_and_run_over_real_http):
        fn()
        print(f"PASS {fn.__name__}")
    print("all server tests passed")

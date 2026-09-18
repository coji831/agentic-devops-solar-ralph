"""Model assignment per ROLE: one repo, two providers, one run.

The claim under test is operational, not structural. A registry may put one role on a cloud
endpoint and another on a local model, and the run has to actually go to both - the right id
to the right endpoint with the right credential. So these tests assert on what two REAL
servers received, because a target that resolves correctly and is then not used is exactly
the failure a unit test on `resolve_target` cannot see.

Three defects found by measuring the v5.7.0 release are pinned here (all fixed in v5.7.1):

1. auto chose the STUB whenever no cloud key was set, so a repo fully configured for a local
   model could not reach it from a committed config at all;
2. a declared KEYLESS provider (`api_key_env: ""`) fell through to the legacy key chain, so
   `SOLAR_API_KEY` was sent as a bearer token to a local endpoint;
3. a role's own `provider` beat the provider its model alias declares, so
   `model: local-qwen` + `provider: deepseek` sent `qwen3:8b` to api.deepseek.com.
"""
import json
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import chain, cli, executor, registry, runcard    # noqa: E402
from solar_governor.core import Config                               # noqa: E402
from solar_governor.graph import run_task                            # noqa: E402


class _Endpoint(BaseHTTPRequestHandler):
    """One OpenAI-compatible endpoint. `seen` and `model` are set on the per-server subclass
    so two of these can be live at once without sharing state."""

    seen: list = []
    model = "mock-model"

    def log_message(self, *a):        # keep pytest output clean
        pass

    def do_GET(self):
        self.seen.append({"method": "GET", "path": self.path})
        self._send(json.dumps({"object": "list", "data": [{"id": self.model}]}).encode())

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}")
        self.seen.append({"method": "POST", "path": self.path,
                          "auth": self.headers.get("Authorization"),
                          "payload": payload})
        self._send(json.dumps({
            "id": "1", "object": "chat.completion",
            "model": payload.get("model", self.model),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "OK."}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }).encode())

    def _send(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Own the environment. Env BEATS config by design, and another module's
    `cmd_run --runner X` sets SOLAR_RUNNER process-wide without restoring it - an inherited
    variable silently redirects a measurement."""
    for name in ("SOLAR_API_KEY", "DEEPSEEK_API_KEY", "SOLAR_RUNNER", "SOLAR_MODEL",
                 "SOLAR_BASE_URL", "MY_CLOUD_KEY"):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture
def servers():
    """`servers(model_id) -> (base_url, seen)`, one real HTTP server per call."""
    started = []
    made = []

    def make(model: str):
        seen: list = []
        # A subclass per server: class attributes, so `seen` is per-server and not shared.
        handler = type(f"_E{len(started)}", (_Endpoint,), {"seen": seen, "model": model})
        srv = HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append(srv)
        made.append(seen)
        return f"http://127.0.0.1:{srv.server_address[1]}/v1", seen

    make.all_seen = made
    yield make
    for srv in started:
        srv.shutdown()


ROLES: dict = {
    "architect": {"role": "Architect", "system": "Plan the work.",
                  "tools": ["workspace"], "model": "cloud-fast"},
    "investigator": {"role": "Investigator", "system": "Find the facts.",
                     "tools": ["workspace"], "model": "local-qwen"},
}


def _repo(extra_roles: dict | None = None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="solar-route-"))
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    solar = root / ".solar"
    solar.mkdir(parents=True, exist_ok=True)
    reg = dict(ROLES)
    reg.update(extra_roles or {})
    reg["chains"] = {"mixed": ["architect", "investigator"]}
    (solar / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    return root


def _cfg(root: Path, cloud_url: str, local_url: str, **kw) -> Config:
    """A repo with two providers declared and a config-level default, which the roles then
    override - the shape the feature exists for. Overridable, for the repo whose default is
    the local model rather than the cloud one."""
    kw.setdefault("provider", "cloud")
    kw.setdefault("model", "cloud-fast")
    cfg = Config(repo=str(root), **kw,
                 providers={"cloud": {"base_url": cloud_url, "api_key_env": "MY_CLOUD_KEY"},
                            "local": {"base_url": local_url, "api_key_env": ""}},
                 models={"cloud-fast": {"provider": "cloud", "id": "big-cloud-id"},
                         "local-qwen": {"provider": "local", "id": "qwen3:8b"}})
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def _posts(seen: list) -> list:
    return [r for r in seen if r["method"] == "POST"]


def _run(cfg: Config, root: Path, thread: str, role: str = "") -> dict:
    started = time.time()
    state = run_task(cfg, "say hello", thread=thread, role=role)
    runcard.write(cfg, state, thread, started)
    card = json.loads((root / ".solar" / "runs" / f"{thread}.json").read_text(encoding="utf-8"))
    return {"state": state, "card": card}


# --- one run, several roles, several providers -------------------------------------

def test_one_chain_run_sends_each_role_to_its_own_provider(servers, monkeypatch):
    """The whole point: a chain whose links live on different providers, in ONE run. Both
    endpoints must be reached, each with the id and the credential that belongs to it."""
    cloud_url, cloud_seen = servers("big-cloud-id")
    local_url, local_seen = servers("qwen3:8b")
    monkeypatch.setenv("MY_CLOUD_KEY", "sk-cloud-test-value")
    root = _repo()
    try:
        cfg = _cfg(root, cloud_url, local_url)
        agg = chain.run_chain(cfg, "mixed", "say hello", thread="mixed")

        assert [l["link"] for l in agg["links"]] == ["architect", "investigator"]
        assert [l["model"] for l in agg["links"]] == ["big-cloud-id", "qwen3:8b"]
        assert agg["passed"] == 2

        cloud_posts, local_posts = _posts(cloud_seen), _posts(local_seen)
        assert cloud_posts, "the cloud link never reached its endpoint"
        assert local_posts, "the local link never reached its endpoint"
        # Each id went to its own provider, and nowhere else.
        assert {r["payload"]["model"] for r in cloud_posts} == {"big-cloud-id"}
        assert {r["payload"]["model"] for r in local_posts} == {"qwen3:8b"}
        # And the credential followed the same split.
        assert {r["auth"] for r in cloud_posts} == {"Bearer sk-cloud-test-value"}
        assert {r["auth"] for r in local_posts} == {f"Bearer {executor.NO_KEY_PLACEHOLDER}"}

        # Provenance is per link, so a local link is distinguishable after the fact.
        local_card = json.loads((root / ".solar" / "runs" / "mixed-1.json")
                                .read_text(encoding="utf-8"))
        assert local_card["provider"] == "local"
        assert local_card["model"] == "qwen3:8b"
    finally:
        shutil.rmtree(root)


def test_a_role_provider_cannot_re_point_its_own_model_alias(servers, monkeypatch):
    """`model: local-qwen` names an alias that declares `provider: local`. A role-level
    `provider: cloud` next to it used to win, which sent a local model id to a cloud
    endpoint - a mismatch no endpoint can report, only fail."""
    cloud_url, cloud_seen = servers("big-cloud-id")
    local_url, local_seen = servers("qwen3:8b")
    monkeypatch.setenv("MY_CLOUD_KEY", "sk-cloud-test-value")
    root = _repo({"conflicted": {"role": "Conflicted", "system": "Nothing to plan.",
                                 "tools": ["workspace"], "model": "local-qwen",
                                 "provider": "cloud"}})
    try:
        cfg = _cfg(root, cloud_url, local_url)
        out = _run(cfg, root, "conflict", role="conflicted")
        assert not _posts(cloud_seen), "the alias's own provider must win"
        assert {r["payload"]["model"] for r in _posts(local_seen)} == {"qwen3:8b"}
        assert out["card"]["provider"] == "local"
    finally:
        shutil.rmtree(root)


# --- the credential that travels ---------------------------------------------------

def test_a_keyless_provider_never_receives_an_unrelated_key(servers, monkeypatch):
    """A declared keyless endpoint needs no credential, so it must get the placeholder - not
    whatever cloud key happens to be in the environment. Before this, `SOLAR_API_KEY` was
    sent to `http://localhost` as a bearer token."""
    cloud_url, _ = servers("big-cloud-id")
    local_url, local_seen = servers("qwen3:8b")
    monkeypatch.setenv("MY_CLOUD_KEY", "sk-cloud-test-value")
    monkeypatch.setenv("SOLAR_API_KEY", "sk-unrelated-cloud-secret")
    root = _repo()
    try:
        cfg = _cfg(root, cloud_url, local_url)
        _run(cfg, root, "keyless", role="investigator")
        auths = {r["auth"] for r in _posts(local_seen)}
        assert auths == {f"Bearer {executor.NO_KEY_PLACEHOLDER}"}
        assert not any("sk-unrelated-cloud-secret" in (a or "") for a in auths)
    finally:
        shutil.rmtree(root)


def test_nothing_declared_still_uses_the_legacy_key_chain(monkeypatch):
    """The third state. `keyless` is three-valued, and collapsing "declared as needing no key"
    into "nothing declared" is what caused the leak: a repo that declares no provider at all
    must keep behaving exactly as it did."""
    declared = executor.providers_table({"local": {"base_url": "http://localhost:11434/v1",
                                                  "api_key_env": ""}})
    assert executor.resolve_target(cfg_provider="local", providers=declared)["keyless"] is True
    named = executor.resolve_target(cfg_provider="deepseek", providers=declared)
    assert named["keyless"] is False and named["api_key_env"] == "DEEPSEEK_API_KEY"
    nothing = executor.resolve_target(providers=declared)
    assert nothing["keyless"] is False and nothing["api_key_env"] == ""

    monkeypatch.setenv("SOLAR_API_KEY", "sk-legacy-value")
    assert executor.resolved_key("http", "", keyless=False) == "sk-legacy-value"
    assert executor.resolved_key("http", "", keyless=True) == executor.NO_KEY_PLACEHOLDER


# --- reaching a local model with no cloud key anywhere ------------------------------

def test_auto_reaches_a_declared_keyless_endpoint_with_no_cloud_key(servers, monkeypatch):
    """A committed config must be enough to run against a local model.

    Auto used to ask only "is a cloud key set", so this exact repo resolved to the STUB - a
    run that reported APPROVED and never called anything. The local model was reachable only
    by exporting SOLAR_RUNNER=http, which is not a property a committed config can carry."""
    local_url, local_seen = servers("qwen3:8b")
    root = _repo()
    try:
        cfg = _cfg(root, "http://127.0.0.1:1/v1", local_url,
                   provider="local", model="local-qwen")
        assert cfg.runner == ""                                  # nothing pins the runner
        assert executor.available() is False                     # no cloud key anywhere
        assert executor.select_runner(cfg.runner, executor.target_for(cfg)) == "http"

        out = _run(cfg, root, "local-only", role="investigator")
        assert _posts(local_seen), "the local endpoint was never called"
        assert out["state"]["model"] == "qwen3:8b"
        assert out["state"]["verdict"] == "APPROVED"
        assert out["state"]["error"] == ""
        assert out["card"]["provider"] == "local"
        assert out["card"]["tokens"]["reported"] is True         # a real call, not a stub
    finally:
        shutil.rmtree(root)


def test_auto_still_stubs_when_there_is_nothing_to_call(monkeypatch):
    """The other half: no provider, no key - a stub, chosen by auto, as always."""
    assert executor.available() is False
    assert executor.select_runner("") == "stub"
    assert executor.can_call(None) is False
    monkeypatch.setenv("SOLAR_API_KEY", "sk-anything")
    assert executor.select_runner("") == "http"                  # legacy: a key is enough


def test_can_call_answers_about_the_target_not_the_environment(monkeypatch):
    """The named-variable case: a declared provider whose own variable is unset cannot be
    called, even when an unrelated key is present. Answering about the environment would
    have said `http` and produced a 401 instead of naming what was missing."""
    monkeypatch.setenv("SOLAR_API_KEY", "sk-unrelated")
    providers = executor.providers_table({"corp": {"base_url": "https://llm.corp/v1",
                                                   "api_key_env": "CORP_KEY"}})
    target = executor.resolve_target(cfg_provider="corp", providers=providers)
    assert executor.can_call(target) is False
    monkeypatch.setenv("CORP_KEY", "sk-corp")
    assert executor.can_call(target) is True


# --- doctor reports the routing before anything runs --------------------------------

def test_doctor_lists_where_each_role_goes(servers, monkeypatch):
    monkeypatch.setenv("MY_CLOUD_KEY", "sk-cloud-test-value")
    cloud_url, _ = servers("big-cloud-id")
    local_url, _ = servers("qwen3:8b")
    root = _repo()
    try:
        cfg = _cfg(root, cloud_url, local_url)
        reg = registry.load(root / ".solar" / "registry.json")
        status, detail = cli._routing_check(cfg, reg)
        assert status == "PASS"
        assert "architect -> big-cloud-id @ cloud [MY_CLOUD_KEY set]" in detail
        assert "investigator -> qwen3:8b @ local [no key needed]" in detail
    finally:
        shutil.rmtree(root)


def test_doctor_names_the_role_provider_an_alias_overrules(servers, monkeypatch):
    """A declaration that is not in effect has to be said out loud, in the one place a human
    looks before a run - the run itself cannot notice, because both outcomes look like a
    successful call."""
    monkeypatch.setenv("MY_CLOUD_KEY", "sk-cloud-test-value")
    cloud_url, _ = servers("big-cloud-id")
    local_url, _ = servers("qwen3:8b")
    root = _repo({"conflicted": {"role": "Conflicted", "system": "Nothing to plan.",
                                 "tools": ["workspace"], "model": "local-qwen",
                                 "provider": "cloud"}})
    try:
        cfg = _cfg(root, cloud_url, local_url)
        reg = registry.load(root / ".solar" / "registry.json")
        status, detail = cli._routing_check(cfg, reg)
        assert status == "WARN"
        assert "NOT in effect" in detail
        assert "conflicted -> qwen3:8b @ local" in detail
    finally:
        shutil.rmtree(root)


def test_doctor_says_nothing_invented_when_the_registry_was_not_read():
    """A routing table over a registry that failed to load must not read as "no role routes
    itself" - that is a statement about a file nobody read."""
    cfg = Config()
    status, detail = cli._routing_check(cfg, {})
    assert status == "PASS"
    assert "see the `registry` check" in detail

"""A provider registry: does the declared provider decide the endpoint, headers, body, key?

The point of the registry is that a model is named once and a repo can point at a cloud
provider, a router, or a local server without editing a ladder. So these tests assert on what
a REAL server receives: the URL, the headers, the request body and the credential. A unit
test on `resolve_target` alone would not catch a target that is computed correctly and then
not used.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

import openai
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import executor, runcard                # noqa: E402
from solar_governor.core import Config                      # noqa: E402
from solar_governor.graph import run_task                   # noqa: E402

SEEN: list[dict] = []


class _Endpoint(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN.append({"method": "GET", "path": self.path,
                     "headers": dict(self.headers)})
        body = json.dumps({"object": "list", "data": [{"id": "qwen3:8b"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        SEEN.append({"method": "POST", "path": self.path,
                     "headers": dict(self.headers),
                     "payload": json.loads(self.rfile.read(n) or b"{}")})
        body = json.dumps({
            "id": "1", "object": "chat.completion", "model": "qwen3:8b",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "OK."}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """Own the environment: another module's `cmd_run --runner X` sets SOLAR_RUNNER process-wide
    and never restores it, and env beats config BY DESIGN."""
    for name in ("SOLAR_API_KEY", "DEEPSEEK_API_KEY", "SOLAR_RUNNER", "SOLAR_MODEL",
                 "SOLAR_BASE_URL", "OPENROUTER_API_KEY", "MY_PROVIDER_KEY"):
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture
def endpoint():
    srv = HTTPServer(("127.0.0.1", 0), _Endpoint)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    SEEN.clear()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


class _NeverAnswers(BaseHTTPRequestHandler):
    """Accepts the connection and then says nothing. The end that hangs."""

    def log_message(self, *a):
        pass

    def do_POST(self):
        time.sleep(30)


@pytest.fixture
def hung_endpoint():
    """A THREADING server, deliberately: `HTTPServer` handles one request at a time, so
    `shutdown()` would wait for the sleeping handler and the test would take 30 s to tear down."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _NeverAnswers)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


def _repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-prov-"))
    (r / "app.py").write_text("x = 1\n", encoding="utf-8")
    return r


def _cfg(repo: Path, **kw) -> Config:
    cfg = Config(repo=str(repo), runner="http", **kw)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def _run(cfg: Config, repo: Path, thread: str) -> dict:
    started = time.time()
    state = run_task(cfg, "say hello", thread=thread)
    runcard.write(cfg, state, thread, started)
    card = json.loads((repo / ".solar" / "runs" / f"{thread}.json").read_text(encoding="utf-8"))
    return {"state": state, "card": card}


# --- the registry decides where the call goes --------------------------------------

def test_an_alias_selects_its_provider_and_id(endpoint):
    """The core promise: name the model, get the endpoint. The id travels to the server
    unchanged - `qwen3:8b` is opaque to this runtime."""
    repo = _repo()
    try:
        cfg = _cfg(repo, model="local-qwen", provider="",
                   providers={"local": {"base_url": endpoint, "api_key_env": ""}},
                   models={"local-qwen": {"provider": "local", "id": "qwen3:8b"}})
        out = _run(cfg, repo, "alias")
        posts = [r for r in SEEN if r["method"] == "POST"]
        assert posts, "no request was sent"
        assert posts[0]["payload"]["model"] == "qwen3:8b"
        assert out["card"]["provider"] == "local"          # the declared NAME, as provenance
        assert out["card"]["model"] == "qwen3:8b"
        assert out["state"]["verdict"] == "APPROVED"
    finally:
        shutil.rmtree(repo)


def test_each_alias_can_point_somewhere_else_in_one_config(endpoint):
    """Two aliases, two providers, one repo: this is what makes a cloud-vs-local comparison a
    config line rather than a code change."""
    repo = _repo()
    other_host = endpoint.replace("/v1", "/v1")            # second alias reuses the mock
    try:
        cfg = _cfg(repo, model="cloud-model", provider="",
                   providers={"cloud": {"base_url": other_host, "api_key_env": ""},
                              "local": {"base_url": endpoint, "api_key_env": ""}},
                   models={"cloud-model": {"provider": "cloud", "id": "big-cloud-id"},
                           "local-qwen": {"provider": "local", "id": "qwen3:8b"}})
        cloud = _run(cfg, repo, "cloud")
        local = _run(cfg, repo, "local")
        assert cloud["card"]["provider"] == "cloud"
        assert cloud["card"]["model"] == "big-cloud-id"
        assert local["state"]["verdict"] == "APPROVED"
    finally:
        shutil.rmtree(repo)


def test_provider_headers_reach_the_wire(endpoint):
    """Attribution and provider-beta headers are why a provider block carries `headers`."""
    repo = _repo()
    try:
        cfg = _cfg(repo, model="routed", provider="",
                   providers={"routed": {"base_url": endpoint, "api_key_env": "",
                                         "headers": {"HTTP-Referer": "https://example.test",
                                                     "X-OpenRouter-Title": "solar-governor"}}},
                   models={"routed": {"provider": "routed", "id": "vendor/model-name"}})
        _run(cfg, repo, "headers")
        posts = [r for r in SEEN if r["method"] == "POST"]
        assert posts[0]["headers"].get("HTTP-Referer") == "https://example.test"
        assert posts[0]["headers"].get("X-OpenRouter-Title") == "solar-governor"
    finally:
        shutil.rmtree(repo)


def test_alias_extra_body_rides_along_without_breaking_the_call(endpoint):
    """A router's routing object is body-level, and must be additive: it cannot be allowed to
    overwrite the messages or the tool schema the runner sets."""
    repo = _repo()
    try:
        cfg = _cfg(repo, model="routed", provider="",
                   providers={"routed": {"base_url": endpoint, "api_key_env": ""}},
                   models={"routed": {"provider": "routed", "id": "vendor/model-name",
                                      "extra_body": {
                                          "provider": {"sort": "throughput"},
                                          "models": ["vendor/model-name"],
                                          "route": "fallback",
                                          "messages": [{"role": "user", "content": "HIJACK"}]}}})
        _run(cfg, repo, "extrabody")
        payload = [r for r in SEEN if r["method"] == "POST"][0]["payload"]
        assert payload["provider"] == {"sort": "throughput"}
        assert payload["route"] == "fallback"
        # ...and the hijack attempt lost, because the runner's own keys are set AFTER the merge
        assert payload["messages"][0]["role"] == "system"
        assert "HIJACK" not in json.dumps(payload["messages"])
    finally:
        shutil.rmtree(repo)


# --- credentials -------------------------------------------------------------------

def test_the_declared_key_env_is_the_one_used(endpoint, monkeypatch):
    repo = _repo()
    try:
        monkeypatch.setenv("MY_PROVIDER_KEY", "sk-from-the-declared-var")
        monkeypatch.setenv("SOLAR_API_KEY", "sk-from-an-unrelated-var")
        cfg = _cfg(repo, model="m", provider="p",
                   providers={"p": {"base_url": endpoint, "api_key_env": "MY_PROVIDER_KEY"}},
                   models={"m": {"provider": "p", "id": "some-id"}})
        _run(cfg, repo, "keyed")
        auth = [r for r in SEEN if r["method"] == "POST"][0]["headers"].get("Authorization")
        assert auth == "Bearer sk-from-the-declared-var"
    finally:
        shutil.rmtree(repo)


def test_a_declared_provider_is_never_satisfied_by_an_unrelated_key(endpoint, monkeypatch):
    """A provider's credential must come from ITS variable. Falling back to whatever happens to
    be in the environment would send one provider's key to another provider's endpoint."""
    repo = _repo()
    try:
        monkeypatch.setenv("SOLAR_API_KEY", "sk-another-provider")
        cfg = _cfg(repo, model="m", provider="p",
                   providers={"p": {"base_url": endpoint, "api_key_env": "MY_PROVIDER_KEY"}},
                   models={"m": {"provider": "p", "id": "some-id"}})
        _run(cfg, repo, "wrongkey")
        posts = [r for r in SEEN if r["method"] == "POST"]
        auth = posts[0]["headers"].get("Authorization") if posts else None
        assert auth is None or "sk-another-provider" not in auth
    finally:
        shutil.rmtree(repo)


def test_an_unknown_provider_name_is_rejected_not_silently_defaulted(endpoint):
    """A typo must not send the run to the default endpoint: that is the same defect as a typo
    picking a different runner."""
    repo = _repo()
    try:
        cfg = _cfg(repo, model="m", provider="typoo",
                   providers={"real": {"base_url": endpoint, "api_key_env": ""}},
                   models={"m": {"provider": "real", "id": "some-id"}})
        out = _run(cfg, repo, "typo")
        assert out["state"]["verdict"] == "REJECTED"
        assert "typoo" in out["state"]["error"]
        assert not [r for r in SEEN if r["method"] == "POST"]   # nothing was sent
    finally:
        shutil.rmtree(repo)


# --- tiers through a declared provider ----------------------------------------------

def test_a_declared_family_lets_a_tier_resolve():
    """The local-endpoint trap: `provider_family` inferred from the host, so a repo declaring a
    `model_tier` against a local server RAISED. A declared family answers it instead."""
    target = executor.resolve_target(
        cfg_tier="fast", cfg_provider="deepseek",
        providers=executor.providers_table({}), models={})
    assert target["model"] == "deepseek-flash"
    assert target["endpoint"] == "https://api.deepseek.com"


def test_a_provider_without_a_family_says_what_to_do_instead():
    """The message must name the fix, because the two ways out are both config, not code."""
    with pytest.raises(ValueError) as err:
        executor.resolve_target(cfg_tier="fast", cfg_provider="ollama",
                                providers=executor.providers_table({}), models={})
    message = str(err.value)
    assert "family" in message and "models" in message


# --- legacy behaviour is untouched ---------------------------------------------------

def test_no_blocks_means_the_env_endpoint_exactly_as_before(endpoint, monkeypatch):
    repo = _repo()
    try:
        monkeypatch.setenv("SOLAR_BASE_URL", endpoint)
        monkeypatch.setenv("SOLAR_API_KEY", "sk-legacy")
        monkeypatch.setenv("SOLAR_MODEL", "legacy-id")
        cfg = _cfg(repo, model="", provider="", providers={}, models={})
        out = _run(cfg, repo, "legacy")
        payload = [r for r in SEEN if r["method"] == "POST"][0]["payload"]
        assert payload["model"] == "legacy-id"
        # no declared provider: the label stays the endpoint's host:port, as it was
        assert out["card"]["provider"].startswith("127.0.0.1:")
        assert out["state"]["verdict"] == "APPROVED"
    finally:
        shutil.rmtree(repo)


def test_an_empty_registry_writes_no_noise_into_a_committed_config():
    """`.solar/config.json` is committed: a repo that declares nothing must not gain lines."""
    persisted = Config(repo="", model="").to_dict()
    assert "providers" not in persisted and "models" not in persisted
    assert "provider" not in persisted


def test_the_shipped_table_is_the_documented_set():
    """The table is data a repo selects from by name, so its shape is part of the contract."""
    assert len(executor.PROVIDERS) >= 15
    for name, spec in executor.PROVIDERS.items():
        assert spec["base_url"].startswith("http"), name
        assert "api_key_env" in spec, name
        assert spec["base_url"].startswith("https://") or "localhost" in spec["base_url"], name
    for local in ("ollama", "lmstudio", "vllm", "llamacpp"):
        assert executor.PROVIDERS[local]["api_key_env"] == "", f"{local} must need no key"


# --- the client's budget, which used to be inherited from the SDK (v5.7.5) ---------

def test_the_chat_client_states_its_budget():
    """A hung link's cost must be DERIVABLE from this repo, not inherited from the SDK's defaults.

    Measured 2026-09-20 in the Promyro engagement (T1.1): the client a CHAT call used was
    constructed with **no timeout at all**, so the SDK's 600 s read applied with its two retries -
    three of them - and the honest answer to "what does a hung link cost" was about thirty minutes
    with nothing of ours in the loop. The assertion that matters is not the number but that the
    number REACHES the client, and that the worst case is one multiplication rather than a guess.
    """
    client = executor.chat_client("k", "http://127.0.0.1:9/v1")
    assert client.timeout.read == executor.CHAT_READ_TIMEOUT
    assert client.timeout.connect == executor.CHAT_CONNECT_TIMEOUT
    assert client.max_retries == executor.CHAT_MAX_RETRIES
    worst = executor.CHAT_READ_TIMEOUT * (1 + executor.CHAT_MAX_RETRIES)
    assert worst == 540, f"the comment beside the constants claims 9 minutes; this says {worst}s"


def test_a_hung_endpoint_fails_instead_of_hanging(hung_endpoint):
    """The behavioural half: an endpoint that accepts and never answers must END the call.

    A SHORT read timeout, because the point is that the bound is ours - waiting the real 180 s would
    prove the same thing three minutes later.
    """
    client = executor.chat_client("k", hung_endpoint, read_timeout=1.0, max_retries=0)
    started = time.time()
    with pytest.raises(openai.APITimeoutError):
        client.chat.completions.create(model="m", messages=[{"role": "user", "content": "hi"}])
    assert time.time() - started < 15, "the read timeout did not bound the call"


def test_the_run_path_gets_the_stated_budget(endpoint, monkeypatch):
    """**And that is the budget a RUN gets.** The warning in this file's own docstring applies here:
    a unit test on a value that is computed correctly does not catch a value that is computed and
    then not used - so the run path is spied on rather than trusted.
    """
    seen = {}
    real = executor.chat_client

    def spy(key, endpoint_, headers=None, **kw):
        seen["endpoint"] = endpoint_
        seen["kw"] = kw
        return real(key, endpoint_, headers, **kw)

    monkeypatch.setattr(executor, "chat_client", spy)
    repo = _repo()
    try:
        cfg = _cfg(repo, model="local-qwen", provider="",
                   providers={"local": {"base_url": endpoint, "api_key_env": ""}},
                   models={"local-qwen": {"provider": "local", "id": "qwen3:8b"}})
        _run(cfg, repo, "budget")
        assert seen["endpoint"].startswith("http://127.0.0.1:")
        assert seen["kw"] == {}, "the run path overrides the stated budget"
    finally:
        shutil.rmtree(repo)

"""Tests for the model executor + workspace tool (v5 §3/§6 + tool layer).

No network: these tests force a key-less environment so the executor falls back
to the stub regardless of whether SOLAR_API_KEY is set on the dev machine.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import types
from pathlib import Path

# make these tests deterministic-offline even when a real key is set in the env
os.environ.pop("SOLAR_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
# ...and independent of whatever the developer's shell has exported. An ambient
# SOLAR_MODEL silently rewrites the model-precedence assertions, SOLAR_RUNNER
# changes what every runner test resolves, and SOLAR_TEMPERATURE changes the
# per-round payload the loop tests assert on. (SOLAR_MAX_ROUNDS and
# SOLAR_TOOL_OUTPUT_CHARS are left alone: those are legitimate tuning knobs to
# set deliberately for a test run.)
os.environ.pop("SOLAR_MODEL", None)
os.environ.pop("SOLAR_RUNNER", None)
os.environ.pop("SOLAR_TEMPERATURE", None)
os.environ.pop("SOLAR_BASE_URL", None)   # so provider families resolve deterministically

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solar_governor import cli, executor         # noqa: E402
from solar_governor.core import Config            # noqa: E402
from solar_governor.graph import build_graph, run_task  # noqa: E402
from solar_governor.workspace import Workspace    # noqa: E402


def _tmp_repo() -> Path:
    r = Path(tempfile.mkdtemp(prefix="solar-exec-"))
    (r / "apps").mkdir(parents=True)
    (r / "apps" / "a.test.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (r / ".git").mkdir()
    return r


def _cfg(repo: Path) -> Config:
    cfg = Config(repo=str(repo))
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


def test_executor_stub_when_no_key():
    assert executor.available() is False   # no key in CI/offline env
    res = executor.run("implementer", "You are an implementer.", "add a feature",
                       Path(tempfile.gettempdir()))
    assert res.get("model") == "stub"
    assert "add a feature" in res.get("output", "")
    assert res.get("usage") == {"in": 0, "out": 0}


def test_workspace_list_and_read():
    r = _tmp_repo()
    ws = Workspace(r)
    tree = ws.list_tree()
    assert "a.test.ts" in tree
    content = ws.read_file("apps/a.test.ts")
    assert "export const x" in content
    shutil.rmtree(r)


def test_workspace_confinement_blocks_escape():
    r = _tmp_repo()
    ws = Workspace(r)
    # write_file must refuse a path that resolves outside the repo
    result = ws.write_file("../../escape.txt", "boom")
    assert result.startswith("ERROR")
    assert not (r.parent / "escape.txt").exists()
    shutil.rmtree(r)


def test_workspace_write_roundtrip():
    r = _tmp_repo()
    ws = Workspace(r)
    assert ws.write_file("apps/b.ts", "export const y = 2;\n").startswith("wrote")
    assert (r / "apps" / "b.ts").exists()
    shutil.rmtree(r)


def test_graph_routes_repo_role_from_registry():
    r = _tmp_repo()
    reg = {"frontend-engineer": {"role": "Frontend Engineer",
                                 "system": "You build frontend.", "tools": [],
                                 "next_edges": [], "model": ""}}
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    from solar_governor.graph import _classify
    assert _classify("build a frontend-engineer login screen", reg) == "frontend-engineer"
    shutil.rmtree(r)


def test_select_runner_auto_and_explicit():
    assert executor.select_runner("") in ("http", "stub")   # no key -> stub
    assert executor.select_runner("agent-dispatch") == "agent-dispatch"
    assert executor.select_runner("http") == "http"
    assert executor.select_runner("stub") == "stub"


def test_handoff_written_and_resolve():
    r = _tmp_repo()
    path = executor.write_handoff("frontend-engineer", "You build frontend.",
                                  "add a login screen", r, attempt=1)
    assert path.exists()
    assert "frontend-engineer" in path.name
    text = path.read_text(encoding="utf-8")
    assert "add a login screen" in text
    # resolve_result returns pasted text as-is
    assert executor.resolve_result("done: built it", r) == "done: built it"
    # resolve_result reads a file path if given
    result_file = r / ".solar" / "handoffs" / "result.txt"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text("the agent result", encoding="utf-8")
    assert executor.resolve_result(str(result_file), r) == "the agent result"
    shutil.rmtree(r)


def test_run_task_agent_dispatch_resumes():
    """agent-dispatch: specialist writes a handoff + interrupts; resume_result
    (non-interactive) supplies the agent's answer as the specialist output."""
    r = _tmp_repo()
    reg = {"frontend-engineer": {"role": "Frontend Engineer",
                                 "system": "You build frontend.", "tools": [],
                                 "next_edges": [], "model": ""}}
    (r / ".solar").mkdir(parents=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    state = run_task(cfg, "build a frontend-engineer login screen", thread="ad1",
                     resume_result="added LoginScreen.tsx with tests")
    assert state.get("stage") == "complete"
    assert state.get("output") == "added LoginScreen.tsx with tests"
    assert state.get("model", "").startswith("agent-dispatch")
    # handoff file persisted
    hdir = r / ".solar" / "handoffs"
    assert any(hdir.glob("frontend-engineer-attempt1-*.md"))
    shutil.rmtree(r)


def test_model_precedence_env_over_role_over_cfg_over_default():
    """TD-5.4-1 ladder: SOLAR_MODEL env > role `model` > cfg.model > default.

    The role beating cfg.model is the whole point of the change: it is what lets
    one chain run flash for read/verify and pro for hard nodes, while cfg.model
    stays the repo-wide default.
    """
    # no env: the ROLE wins over the repo-wide config
    assert executor.model_name("cfg-model", "role-model") == "role-model"

    # env beats the role - a per-run override must always be able to win
    os.environ["SOLAR_MODEL"] = "env-model"
    try:
        assert executor.model_name("cfg-model", "role-model") == "env-model"
    finally:
        os.environ.pop("SOLAR_MODEL", None)

    # role empty (how existing registries spell 'inherit'): cfg.model wins
    assert executor.model_name("cfg-model", "") == "cfg-model"


def test_model_precedence_skips_empty_levels():
    """An empty string at any level falls through - registries leave `model` as
    "" to mean 'inherit', and that must keep working exactly as before."""
    assert executor.model_name("cfg-model", "") == "cfg-model"
    assert executor.model_name("", "role-model") == "role-model"
    assert executor.model_name("", "") == executor.DEFAULT_MODEL


def test_run_resolves_the_role_model_from_the_spec():
    """`run()` must consult the role's `model` AND its `model_tier`, not only cfg.

    The resolver is replaced with a sentinel rather than allowed to continue:
    `run()` returns the stub BEFORE resolving a model when no key is present, and a
    real call would need the network. `resolve_model` is called outside run()'s
    ValueError guard, so the sentinel propagates and is caught here.
    """
    class _Stop(Exception):
        pass

    seen: dict = {}

    def _spy(**kwargs) -> tuple:
        seen.update(kwargs)
        raise _Stop()

    orig_key, orig_resolve = executor.api_key, executor.resolve_model
    executor.api_key = lambda: "sk-test-not-used"
    executor.resolve_model = _spy
    try:
        executor.run("implementer", "sys", "obj", Path(tempfile.gettempdir()),
                     cfg_model="deepseek-chat", cfg_tier="",
                     spec={"model": "deepseek-v4-pro", "model_tier": "fast"})
    except _Stop:
        pass
    else:
        raise AssertionError("run() never resolved a model")
    finally:
        executor.api_key, executor.resolve_model = orig_key, orig_resolve

    assert seen == {"cfg_model": "deepseek-chat", "role_model": "deepseek-v4-pro",
                    "cfg_tier": "", "role_tier": "fast"}


def test_handoff_hint_reports_the_role_model():
    """The handoff header must name the model that will actually run."""
    r = _tmp_repo()
    path = executor.write_handoff("implementer", "sys", "obj", r, attempt=1,
                                  cfg_model="deepseek-chat",
                                  role_model="deepseek-v4-pro")
    assert "deepseek-v4-pro" in path.read_text(encoding="utf-8")
    shutil.rmtree(r)


# ---------------------------------------------------------------------------
# tool-loop termination (v5.4.1)
#
# These drive the loop against a scripted fake client: no network, and the exact
# payload sent on each round is recorded - which is the only way to assert that
# the final round is called WITHOUT tools.
# ---------------------------------------------------------------------------


class _FakeToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id, self.type = id, "function"
        self.function = types.SimpleNamespace(name=name, arguments=arguments)


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content, self.tool_calls = content, tool_calls


class _FakeResponse:
    def __init__(self, message, prompt_tokens=10, completion_tokens=5):
        self.choices = [types.SimpleNamespace(message=message)]
        self.usage = types.SimpleNamespace(prompt_tokens=prompt_tokens,
                                           completion_tokens=completion_tokens)


class _FakeClient:
    """Replays a scripted list of responses, recording every payload sent."""

    def __init__(self, script):
        self._script = list(script)
        self.payloads: list = []
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.payloads.append(kwargs)
        return self._script.pop(0)


class _StubWs:
    """Minimal stand-in for _ToolLayer (the loop is what is under test)."""

    def __init__(self):
        self.calls: list = []

    def tool_schemas(self):
        return [{"type": "function",
                 "function": {"name": "read_file",
                              "parameters": {"type": "object", "properties": {}}}}]

    def call_tool(self, name, args):
        self.calls.append((name, args))
        return "the file contents"


def _tool_call(i: int):
    return _FakeToolCall(f"call{i}", "read_file", '{"rel": "a.ts"}')


def _text(content: str):
    return _FakeResponse(_FakeMessage(content=content))


def _calls(*tc):
    return _FakeResponse(_FakeMessage(content=None, tool_calls=list(tc)))


def _loop(client, ws=None, max_rounds=3, effort=""):
    return executor._tool_loop(client, "test-model",
                               [{"role": "system", "content": "sys"},
                                {"role": "user", "content": "obj"}],
                               ws or _StubWs(), max_rounds, effort)


def test_tool_loop_sends_an_explicit_temperature():
    """The loop must not inherit the provider default: an inherited sampling
    temperature is what made convergence a coin flip on identical inputs."""
    os.environ.pop("SOLAR_TEMPERATURE", None)
    client = _FakeClient([_text("answer")])
    _loop(client)
    assert client.payloads[0]["temperature"] == 0.2


def test_temperature_can_be_omitted_for_gateways_that_reject_it():
    os.environ["SOLAR_TEMPERATURE"] = "default"
    try:
        client = _FakeClient([_text("answer")])
        _loop(client)
        assert "temperature" not in client.payloads[0]
    finally:
        os.environ.pop("SOLAR_TEMPERATURE", None)


def test_temperature_falls_back_on_junk_or_out_of_range():
    for raw, expected in (("abc", 0.2), ("9", 0.2), ("-1", 0.2), ("0", 0.0),
                          ("1.5", 1.5), ("off", None), ("", None)):
        os.environ["SOLAR_TEMPERATURE"] = raw
        try:
            assert executor.temperature() == expected, raw
        finally:
            os.environ.pop("SOLAR_TEMPERATURE", None)


def test_the_final_round_is_called_without_tools():
    """A round that cannot call a tool has to return text. This is the rule that
    turns a hard 'no answer' failure into a best-effort answer."""
    client = _FakeClient([_calls(_tool_call(1)), _calls(_tool_call(2)), _text("final")])
    res = _loop(client, max_rounds=3)
    assert "tools" in client.payloads[0]
    assert "tools" in client.payloads[1]
    assert "tools" not in client.payloads[2]
    assert res["output"] == "final"
    assert res["forced_final"] is True
    assert res["error"] is None


def test_a_budget_notice_is_sent_before_the_final_round():
    client = _FakeClient([_calls(_tool_call(1)), _calls(_tool_call(2)), _text("final")])
    _loop(client, max_rounds=3)
    second = client.payloads[1]["messages"]
    assert any("Budget notice" in (m.get("content") or "") for m in second)
    # the final round gets the stop instruction, and only ONE notice was ever added
    final = client.payloads[2]["messages"]
    assert any(m.get("content") == executor.FINAL_ROUND_INSTRUCTION for m in final)
    assert sum("Budget notice" in (m.get("content") or "") for m in final) == 1


def test_a_model_that_only_calls_tools_is_cut_off_not_failed():
    """Regression: this used to return 'reached max tool rounds without a final
    answer' and fail the run. Measured 4 runs in 5 on a real read-only role over
    a one-file, one-fact objective."""
    client = _FakeClient([_calls(_tool_call(1)) for _ in range(3)])
    res = _loop(client, max_rounds=3)
    assert res["error"] == "empty_output"   # nothing to hand back, and it says so
    assert res["forced_final"] is True
    assert res["tool_calls"] == 2           # no tools were run on the final round
    assert "no answer text" in res["output"]


def test_a_single_round_budget_is_still_answered():
    client = _FakeClient([_text("one-shot")])
    res = _loop(client, max_rounds=1)
    assert "tools" not in client.payloads[0]
    assert res["output"] == "one-shot"
    assert res["forced_final"] is True


def test_a_normal_answer_is_not_marked_forced():
    client = _FakeClient([_text("answered immediately")])
    res = _loop(client, max_rounds=3)
    assert res["output"] == "answered immediately"
    assert res["forced_final"] is False


def test_an_empty_final_answer_is_an_error_not_a_blank_success():
    client = _FakeClient([_FakeResponse(_FakeMessage(content="   "))])
    res = _loop(client, max_rounds=1)
    assert res["error"] == "empty_output"
    assert res["output"].startswith("ERROR")


def test_a_provider_failure_is_reported_with_the_real_message():
    class _Boom:
        def __init__(self):
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=self._create))

        def _create(self, **kwargs):
            raise RuntimeError("502 upstream")

    res = _loop(_Boom(), max_rounds=3)
    assert res["error"] == "502 upstream"
    assert "502 upstream" in res["output"]
    assert res["forced_final"] is False


def test_usage_and_tool_call_counts_accumulate():
    client = _FakeClient([
        _FakeResponse(_FakeMessage(tool_calls=[_tool_call(1), _tool_call(2)]),
                      prompt_tokens=100, completion_tokens=7),
        _text("done"),
    ])
    res = _loop(client, max_rounds=2)
    assert res["tool_calls"] == 2
    assert res["usage"] == {"in": 110, "out": 12}


def test_run_card_records_a_forced_answer():
    """An operator must be able to tell 'answered' from 'cut off, and answered
    anyway' from the run-card alone."""
    from solar_governor import runcard
    r = _tmp_repo()
    cfg = _cfg(r)
    state = {"stage": "complete", "verdict": "APPROVED", "forced_final": True,
             "decisions_log": []}
    path = runcard.write(cfg, state, "t-forced", time.time())
    assert json.loads(path.read_text(encoding="utf-8"))["forced_final"] is True
    shutil.rmtree(r)


# ---------------------------------------------------------------------------
# runner selection (TD-5.4-9)
# ---------------------------------------------------------------------------


def test_select_runner_env_beats_the_repo_config():
    """The per-run override must actually reach the runner.

    Before this the config always won (`cfg_runner or os.environ[...]`), so
    SOLAR_RUNNER was unreachable on any repo that pinned a runner - which is how
    testing the http path against Promyro ended up editing a live config twice.
    """
    os.environ["SOLAR_RUNNER"] = "stub"
    try:
        assert executor.select_runner("agent-dispatch") == "stub"
    finally:
        os.environ.pop("SOLAR_RUNNER", None)
    # without the override the pinned config still stands
    assert executor.select_runner("agent-dispatch") == "agent-dispatch"


def test_select_runner_rejects_an_unknown_value_instead_of_downgrading():
    """A typo must not silently pick a runner other than the one asked for."""
    os.environ["SOLAR_RUNNER"] = "https"
    try:
        try:
            executor.select_runner("agent-dispatch")
        except ValueError as e:
            assert "https" in str(e) and "SOLAR_RUNNER" in str(e)
        else:
            raise AssertionError("an unknown SOLAR_RUNNER was accepted")
    finally:
        os.environ.pop("SOLAR_RUNNER", None)
    try:
        executor.select_runner("agent-dispatchh")
    except ValueError as e:
        assert "config runner" in str(e)
    else:
        raise AssertionError("an unknown config runner was accepted")


def test_select_runner_treats_blank_values_as_unset():
    os.environ["SOLAR_RUNNER"] = "   "
    try:
        assert executor.select_runner("stub") == "stub"
    finally:
        os.environ.pop("SOLAR_RUNNER", None)
    assert executor.select_runner("  http  ") == "http"     # stray whitespace tolerated
    assert executor.select_runner("") in ("http", "stub")  # nothing set -> auto


def test_the_runner_flag_overrides_a_config_that_pins_another_runner():
    """`run --runner X` decides the runner for ONE run, config untouched.

    The pinned runner here is `agent-dispatch`, which would write a handoff and
    pause for an IDE agent. `stub` runs in-process, so the run-card proving
    `model == "stub"` is proof the flag won - and config.json must come back
    byte-identical, because the whole point is not to edit a live engagement.
    """
    r = _tmp_repo()
    reg = {"frontend-engineer": {"role": "Frontend Engineer",
                                 "system": "You build frontend.", "tools": [],
                                 "next_edges": [], "model": ""}}
    (r / ".solar").mkdir(parents=True, exist_ok=True)
    (r / ".solar" / "registry.json").write_text(json.dumps(reg), encoding="utf-8")
    cfg = Config(repo=str(r), runner="agent-dispatch")
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.save(r / ".solar" / "config.json")

    ns = argparse.Namespace(repo=str(r), thread="flag1", task="build a login screen",
                            chain=None, auto=False, role="frontend-engineer",
                            approve=None, result=None, json=False, runner="stub")
    os.environ.pop("SOLAR_RUNNER", None)
    try:
        try:
            cli.cmd_run(ns)
        except SystemExit as e:
            assert e.code == cli.EXIT_OK      # completed, and APPROVED
        else:
            raise AssertionError("cmd_run did not exit")
        assert os.environ["SOLAR_RUNNER"] == "stub"
        card = json.loads((r / ".solar" / "runs" / "flag1.json").read_text(encoding="utf-8"))
        assert card["model"] == "stub"          # the flag won, not the pinned runner
        assert card["verdict"] == "APPROVED"
        assert not (r / ".solar" / "handoffs").exists()   # agent-dispatch would have
        assert json.loads((r / ".solar" / "config.json").read_text(
            encoding="utf-8"))["runner"] == "agent-dispatch"   # untouched
    finally:
        os.environ.pop("SOLAR_RUNNER", None)
        shutil.rmtree(r)


def test_a_rejected_run_does_not_exit_zero():
    """TD-5.4-10: every `max_rounds` failure in the v5.4.1 integration test exited 0
    while carrying `verdict: REJECTED`, so a wrapper driving on exit codes read a hard
    failure as a pass. "The graph finished" and "the work was accepted" are different
    claims, and now have different codes."""
    assert cli._exit_for({"verdict": "REJECTED"}) == cli.EXIT_REJECTED == 12
    assert cli._exit_for({"verdict": "APPROVED"}) == cli.EXIT_OK
    assert cli._exit_for({}) == cli.EXIT_OK          # still running: not a failure


def test_resolve_model_reports_which_level_supplied_the_id():
    """TD-5.4-6 needs the provenance, not just the id: a deliberate env override and
    a stale config pin otherwise resolve to the same kind of string."""
    assert executor.resolve_model("cfg-m", "role-m") == ("role-m", "role model")
    assert executor.resolve_model("cfg-m", "") == ("cfg-m", "config model")
    assert executor.resolve_model("", "") == (executor.DEFAULT_MODEL, "default")
    os.environ["SOLAR_MODEL"] = "env-m"
    try:
        assert executor.resolve_model("cfg-m", "role-m") == ("env-m", "env SOLAR_MODEL")
    finally:
        os.environ.pop("SOLAR_MODEL", None)


def test_model_tiers_resolve_to_concrete_ids():
    """The point of tiers: a provider rename becomes ONE edit in the runtime instead
    of an edit per repo per file, which is how a phantom id appeared in three places."""
    assert executor.resolve_tier("fast") == "deepseek-flash"
    assert executor.resolve_tier("reasoner") == "deepseek-v4-pro"
    try:
        executor.resolve_tier("turbo")
    except ValueError as e:
        assert "turbo" in str(e) and "have:" in str(e)
    else:
        raise AssertionError("an unknown tier was accepted")


def test_a_tier_can_supply_the_model_and_names_itself_as_the_source():
    os.environ.pop("SOLAR_MODEL", None)
    assert executor.resolve_model("", cfg_tier="fast") == ("deepseek-flash",
                                                            "config model_tier=fast")
    assert executor.resolve_model("", "", "", "fast") == ("deepseek-flash",
                                                            "role model_tier=fast")
    # an explicit id beats a tier at the SAME level...
    assert executor.resolve_model("deepseek-chat", cfg_tier="fast")[0] == "deepseek-chat"
    # ...and a nearer level beats a further one
    assert executor.resolve_model("", "role-id", "cfg-tier", "fast") == ("role-id",
                                                                          "role model")


def test_an_unresolvable_tier_fails_the_run_rather_than_picking_a_model():
    """A run must not proceed with a model nobody asked for."""
    orig = executor.api_key
    executor.api_key = lambda: "sk-test-unused"
    try:
        res = executor.run("implementer", "sys", "obj", Path(tempfile.gettempdir()),
                           cfg_tier="turbo")
    finally:
        executor.api_key = orig
    assert res["error"] and "turbo" in res["error"]
    assert res["model"] == "unresolved"
    assert res["output"].startswith("ERROR")


def test_doctor_catches_an_ide_display_name_in_a_runtime_config():
    """`model: DeepSeek V4 Flash (deepseek)` belongs to the IDE plane; the runtime needs
    the provider's API id. Transcribing between the two planes is exactly where a
    phantom `deepseek-v4-flash` came from."""
    status, detail = cli._model_check(Config(model="DeepSeek V4 Flash (deepseek)"), {})
    assert status == "WARN" and "IDE display name" in detail


def test_doctor_names_the_model_that_will_run():
    cfg = Config(model="deepseek-flash")
    status, detail = cli._model_check(cfg, {})
    assert status == "PASS" and "deepseek-flash (from config model" in detail
    # a tier is shown with the tier that produced it, so a rename is traceable
    status, detail = cli._model_check(Config(model_tier="fast"), {})
    assert status == "PASS" and "deepseek-flash (from config model_tier=fast" in detail
    os.environ["SOLAR_MODEL"] = "deepseek-v4-pro"
    try:
        status, detail = cli._model_check(cfg, {})
        assert status == "PASS" and "from env SOLAR_MODEL" in detail
    finally:
        os.environ.pop("SOLAR_MODEL", None)
    # a role's model or tier beats the config, so doctor has to name the roles that do it
    _, detail = cli._model_check(cfg, {"investigator": {"model_tier": "fast"}})
    assert "1 role(s) override: investigator" in detail


def test_doctor_warns_on_an_id_the_provider_does_not_serve():
    """The exact bug that sat unnoticed in a real repo config: a pin of
    `deepseek-v4-flash`, which does not exist."""
    orig = executor.known_models
    executor.known_models = lambda timeout=15.0: (["deepseek-flash", "deepseek-v4-pro"], "")
    try:
        status, detail = cli._model_check(Config(model="deepseek-v4-flash"), {})
        assert status == "WARN" and "deepseek-v4-flash" in detail
        # ...but an alias the provider serves without listing it is NOT a warning
        status, _ = cli._model_check(Config(model="deepseek-chat"), {})
        assert status == "PASS"
    finally:
        executor.known_models = orig


def test_reasoning_effort_ladder_and_default():
    """TD-5.4-2. Off by default: a field the provider may reject must not be sent
    unless some level asks for it."""
    assert executor.reasoning_effort("", "") == ""
    assert executor.reasoning_effort("cfg-e", "") == "cfg-e"
    assert executor.reasoning_effort("cfg-e", "role-e") == "role-e"
    os.environ["SOLAR_REASONING_EFFORT"] = "env-e"
    try:
        assert executor.reasoning_effort("cfg-e", "role-e") == "env-e"
    finally:
        os.environ.pop("SOLAR_REASONING_EFFORT", None)


def test_reasoning_effort_is_absent_unless_configured():
    client = _FakeClient([_text("ok")])
    _loop(client)
    assert "reasoning_effort" not in client.payloads[0]
    client = _FakeClient([_text("ok")])
    _loop(client, effort="high")
    assert client.payloads[0]["reasoning_effort"] == "high"


if __name__ == "__main__":
    for fn in (test_executor_stub_when_no_key, test_workspace_list_and_read,
               test_workspace_confinement_blocks_escape, test_workspace_write_roundtrip,
               test_graph_routes_repo_role_from_registry, test_select_runner_auto_and_explicit,
               test_handoff_written_and_resolve, test_run_task_agent_dispatch_resumes):
        fn()
        print(f"PASS {fn.__name__}")
    print("all executor tests passed")

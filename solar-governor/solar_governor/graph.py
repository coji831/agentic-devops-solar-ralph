"""Graph (v5 §5): build the profile graph + run a task end-to-end.

Light profile (default): MATERIAL_GATE -> DISPATCH -> SPECIALIST -> REVIEW
(conditional) -> COMPLETE, with a bounded rework loop (<=3 attempts). Full
profile adds design-gate interrupt + compactor + adversarial (later).
"""
import time

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import executor
from .core import Config, SolarState
from .registry import chain_entry, chain_text, load as load_registry, role_keys

MAX_ATTEMPTS = 3

# keyword -> role hints, applied against the LOADED registry (repo roles win if
# their name/description matches; generic defaults remain as fallback)
_ROLE_HINTS = {
    "implementer": ("implement", "refactor", "build", "feature", "code", "fix"),
    "tester": ("test", "spec", "coverage", "verify"),
    "reviewer": ("review", "audit", "check"),
}


def _registry_role_hint(task: str, registry: dict) -> str | None:
    """Prefer a repo-specific role whose name appears in the task (deterministic)."""
    low = (task or "").lower()
    # repo roles = registry minus generic defaults and structural keys
    generic = set(_ROLE_HINTS)
    for role, spec in registry.items():
        # a real role spec carries a `system` prompt; playbook/chain entries do not
        if role in generic or not isinstance(spec, dict) or "system" not in spec:
            continue
        name = str(spec.get("role", role)).lower()
        if name.replace(" ", "-") in low or name.split()[-1] in low or role.replace("_", "-") in low:
            return role
    return None


def _classify(task: str, registry: dict | None = None) -> str:
    reg = registry or {}
    hit = _registry_role_hint(task, reg)
    if hit:
        return hit
    low = (task or "").lower()
    # priority order breaks keyword-count ties: "add tests to X" -> tester,
    # even though "feature/build" are also present.
    best, best_score = "implementer", 0
    for role in ("tester", "reviewer", "implementer"):
        score = sum(low.count(k) for k in _ROLE_HINTS[role])
        if score > best_score:
            best, best_score = role, score
    return best


def _role_spec(cfg: Config, role: str) -> dict:
    """Return a role's FULL registry spec (repo-specific role wins).

    The whole entry is returned, not just the prompt: the workspace tool layer
    needs the role's declared `tools` — and, once the deny-list lands, its
    `write_scope`/`write_deny` — to decide what the role may be OFFERED and
    where it may write. An unknown role yields {} so callers fall back to a
    generic prompt instead of raising.
    """
    reg = load_registry(cfg.root / ".solar" / "registry.json")
    return reg.get(role) or {}


# **WHERE A CLONE'S OWN FACTS LIVE: one directory, one file per clone** (`T53`, 2026-09-23).
#
# A role's brief is AGNOSTIC - the hard rules that hold for every repository - and what is true of
# ONE clone belongs here instead. The loader reads the file for the clone the RUN declared (`--clone`,
# T50), so a link is told about the repository it is actually working in and about no other.
#
# **The path is derived from the clone's name, never typed into a role.** That is the whole point:
# the alternative was a stack named in nine `system` prompts and nine `.agent.md` briefs, and measured
# 2026-09-23 those two texts had drifted in **20 of 21** repo-identity tokens - including rules that
# held in one and not the other.
CLONE_CONVENTIONS = ("skills", "repo-conventions")


def _plain_name(name: str) -> bool:
    """Whether `name` is a bare directory name: no separator, not `.`/`..`, not absolute.

    **`clone` is validated at the START of a run** (`commands.clone_name_problem`), so this is a
    second belt rather than the only one - and it is here because this function builds a path the
    first one has never seen. A loader that interpolated an uncontrolled string into a path would be
    the one place in the package where a refusal upstream is worth nothing.
    """
    return bool(name) and name not in (".", "..") and "/" not in name and "\\" not in name


def clone_conventions(cfg: Config, clone: str) -> tuple[str, str]:
    """`(text, source)` for the declared clone's conventions - `("", "")` when it has none.

    **Absence is the ordinary answer, and it is not an error.** A repository with nothing unusual
    about it needs no file, and a run that declared `--clone none` is about no repository at all. So
    a missing file is silent by design.

    **What would NOT be acceptable is silence about a file that was EXPECTED** - a typo'd directory
    would then read exactly like a clone that has no conventions, which is this repository's worst
    failure class (a mechanism that reads as protecting something and does nothing). The guard is
    that the CALLER names the source it loaded in the prompt it assembles, so the model and a reader
    can both tell "loaded, from here" from "not loaded" without having to trust a path.
    """
    if not _plain_name(clone):
        return "", ""
    path = cfg.root.joinpath(".github", *CLONE_CONVENTIONS, f"{clone}.md")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "", ""
    if not text:
        return "", ""
    return text, path.relative_to(cfg.root).as_posix()


def _role_prompt(cfg: Config, spec: dict, role: str, clone: str = "") -> str:
    """The role's system prompt - AGNOSTIC - plus the declared clone's own conventions.

    **The brief says what holds for every repository; the clone's file says what holds for this**
    one. `T53`'s ruling (2026-09-23): the registry prompt and the `.agent.md` brief are both kept to
    hard rules that apply to all work, and everything repository-specific moves behind this loader.

    **Why a loader rather than more prose.** Until this existed there was no way for a brief to learn
    WHICH repository it was in - `clone` appeared in no prompt or message construction anywhere in
    the package, measured - so the only place a stack could live was the brief itself, and it landed
    in two texts that drifted. The run already declares its clone (`T50`); this is the half that
    consumes it.

    With no clone declared the base prompt is returned **unchanged**, which is what makes the
    `clone=""` path testable as an equality rather than a substring.
    """
    base = spec.get("system", f"You are the {role} specialist.")
    text, source = clone_conventions(cfg, clone)
    if not text:
        return base
    return (f"{base}\n\n## This repository's own conventions\n\n"
            f"_Loaded from `{source}`, because this run declared `--clone {clone}`._\n\n{text}")


def _chain_note(cfg: Config, chain_name: str) -> str:
    """Human-readable chain block for a handoff ('' when not a chain run)."""
    if not chain_name:
        return ""
    cm = (load_registry(cfg.root / ".solar" / "registry.json").get("chains") or {})
    if chain_name not in cm:
        return ""
    return f"chain `{chain_name}`: {chain_text(cm, chain_name)}"


def _node_target(cfg: Config, role: str) -> dict | None:
    """The target this node will call, or None when it cannot be resolved (v5.7.1).

    The runner decision needs the target BEFORE the node runs, so resolution belongs here
    and not inside the executor: `select_runner` asks whether a call is possible, and for a
    declared KEYLESS endpoint (a local model) the answer is not "is a key set".

    Unresolvable answers None rather than {}. That distinction matters: {} would read as
    "no provider declared" and quietly reach the default endpoint, while None hands the
    resolution back to `run`, which is where a config error becomes a REJECTED run.
    """
    try:
        return executor.target_for(cfg, _role_spec(cfg, role))
    except ValueError:
        return None


def _execute(cfg: Config, state: SolarState, runner: str = "",
             target: dict | None = None) -> dict:
    """Run the routed specialist role through the HTTP/stub runner.

    System prompt comes from the loaded registry (repo-specific role wins), and
    the WHOLE role spec is passed on so the workspace tool layer can derive its
    policy from the role. The executor falls back to a stub when no API key is
    present (cfg.model "" or SOLAR_API_KEY unset), so the graph stays testable
    without credentials.

    `runner` is resolved ONCE by the caller (`select_runner`) and handed down, so
    the runner that was chosen is the runner that runs (TD-5.6-7) rather than being
    re-decided here from the api key. `target` (v5.7.1) travels with it for the same
    reason - it was already resolved to answer the runner question, and resolving it
    again would be a second chance to disagree about which endpoint this node uses.

    `clone` (T50, 2026-09-23) is the OTHER kind of target and shares no word with
    `target`: it is WHICH CLONE this run is about, read off the state so it reaches
    every tool layer a node builds. It is a value the run declared, and `""` means it
    declared `none` - which a clone-scoped command refuses rather than defaults.
    """
    role = state.get("role", "implementer")
    spec = _role_spec(cfg, role)
    objective = state.get("objective", "")
    res = executor.run(role=role,
                       system_prompt=_role_prompt(cfg, spec, role,
                                                 str(state.get("clone") or "")),
                       objective=objective, repo=cfg.root, cfg_model=cfg.model,
                       spec=spec, human_approval=cfg.human_approval,
                       cfg_reasoning=cfg.reasoning_effort, cfg_tier=cfg.model_tier,
                       runner=runner, cfg_provider=cfg.provider,
                       providers=executor.providers_table(cfg.providers),
                       models=cfg.models, target=target,
                       clone=str(state.get("clone") or ""))
    return {
        "output": res.get("output", ""),
        "model": res.get("model", "stub"),
        "provider": res.get("provider", "") or executor.endpoint_label(runner),
        "usage_reported": bool(res.get("usage_reported", False)),
        "tokens_in": res.get("usage", {}).get("in", 0),
        "tokens_out": res.get("usage", {}).get("out", 0),
        "tool_calls": res.get("tool_calls", 0),
        "error": res.get("error") or "",
        "forced_final": bool(res.get("forced_final", False)),
        "max_rounds": int(res.get("max_rounds", 0)),
        # **The prompt the run was about to send, and the window it had been told it was sending it
        # into** - carried together for `forced_final`/`max_rounds`' reason: an estimate with no
        # window beside it answers nothing, and the window is declared per install.
        "prompt_tokens": int(res.get("prompt_tokens", 0)),
        "context_tokens": int(res.get("context_tokens", 0)),
        # **The tool-call transcript (T10, 2026-09-23), and it rides the CHECKPOINT deliberately.**
        # It is telemetry: `.solar/state/` is gitignored, per-machine, and nothing may cite it. It
        # is NOT added to `runcard.write`'s field list, which is why the tracked card cannot carry
        # it - the graph's checkpointer is already the harness part that dumps every node's state.
        "tool_transcript": res.get("tool_transcript", []),
    }


def _dispatch_agent(cfg: Config, state: SolarState, attempts: int) -> dict:
    """AgentDispatchRunner: write a handoff, then HITL-interrupt for the result.

    The human runs the matching .agent.md specialist in VS Code Copilot (DeepSeek
    via the extension) and pastes the result (or a result-file path) to resume.
    A dispatch is always ONE link of work: if the run is part of a named chain
    the handoff only carries neutral chain context (the coordinator runs the
    links) — it never tells the agent to run the rest of the chain itself.
    """
    role = state.get("role", "implementer")
    spec = _role_spec(cfg, role)
    chain_note = _chain_note(cfg, state.get("chain", ""))
    handoff = executor.write_handoff(role=role,
                                     system_prompt=_role_prompt(
                                         cfg, spec, role, str(state.get("clone") or "")),
                                     objective=state.get("objective", ""),
                                     repo=cfg.root, cfg_model=cfg.model,
                                     attempt=attempts, chain_note=chain_note,
                                     role_model=spec.get("model", ""))
    resumed = interrupt({"kind": "agent-dispatch",
                         "role": role,
                         "attempt": attempts,
                         "chain": state.get("chain", ""),
                         "handoff": str(handoff),
                         "ask": (f"Run the `{role}` agent in VS Code Copilot "
                                 f"(handoff: {handoff.name}), then paste its final "
                                 f"result or the result-file path:")})
    output = executor.resolve_result(resumed, cfg.root)
    return {"attempts": attempts, "output": output, "model": f"agent-dispatch:{role}",
            "stage": "specialist",
            "decisions_log": [f"specialist attempt {attempts} (agent-dispatch: {role})"]}


def build_nodes(cfg: Config):
    def material_gate(state: SolarState) -> dict:
        status = "READY" if state.get("objective") else "INSUFFICIENT"
        return {"materials_status": status, "stage": "material_gate",
                "decisions_log": [f"material_gate -> {status}"]}

    def dispatch(state: SolarState) -> dict:
        reg = load_registry(cfg.root / ".solar" / "registry.json")
        chain_name = state.get("chain") or ""
        pinned = state.get("role") or ""
        role = None
        if chain_name:
            cm = reg.get("chains") or {}
            if chain_name in cm:
                role = chain_entry(cm, chain_name)
        if role is None and pinned and pinned in role_keys(reg):
            role = pinned                       # --role: pin dispatch (Hermes decision)
        if role is None:
            role = _classify(state.get("objective", ""), reg)
        return {"role": role, "chain": chain_name, "stage": "dispatched",
                "work_queue": [{"id": "T1", "task": state.get("objective", ""),
                                "role": role, "status": "PENDING", "stage": "dispatched"}],
                "decisions_log": [f"dispatch -> {role}" + (f" (chain {chain_name})" if chain_name else "")]}

    def specialist(state: SolarState) -> dict:
        attempts = state.get("attempts", 0) + 1
        # Resolve the ROLE's target first: it decides both the endpoint and whether a call
        # is possible at all, so the runner question is asked about the node that is about
        # to run rather than about the process environment (v5.7.1).
        target = _node_target(cfg, state.get("role", "implementer"))
        runner = executor.select_runner(cfg.runner, target)
        if runner == "agent-dispatch":
            return _dispatch_agent(cfg, state, attempts)
        result = _execute(cfg, state, runner, target)
        return {"attempts": attempts, "stage": "specialist",
                "decisions_log": [f"specialist attempt {attempts}"], **result}

    def review(state: SolarState) -> dict:
        # Never auto-approve an executor failure: an error output must not read
        # as success (the harness exists to stop false "done"). Terminal, no rework.
        if state.get("error"):
            return {"verdict": "REJECTED", "stage": "review",
                    "decisions_log": [f"review -> REJECTED (executor error: "
                                      f"{str(state['error'])[:80]} — no auto-approve)"]}
        # **A FORCED FINAL IS THE SECOND WAY TO FAIL, and it used to be approved.** The
        # tool-less last round exists so a node hands back what it did establish instead of
        # failing outright — but `error` stays empty when that round answers, so the guard
        # above did not fire and the verdict read APPROVED for a link the executor's own
        # docstring calls *"cut off, and answered anyway"*. Measured 2026-09-22: exactly one
        # card in the engagement carried the pair (`verdict: APPROVED` + `forced_final: true`,
        # 753,729 tokens), and every reader had to notice a SECOND field to read it right.
        # **Refused BEFORE the gate on purpose:** a person approving a cut-off link is not
        # approving work, and asking them to is what made the card look honest while it was
        # not. A cut-off link is a link that owes its product; its task's record carries the
        # decision, not this card.
        if state.get("forced_final"):
            return {"verdict": "REJECTED", "stage": "review",
                    "decisions_log": [f"review -> REJECTED (CUT OFF at the round limit "
                                      f"({state.get('max_rounds', 0)} round(s) offered) — the "
                                      f"answer was FORCED, not established; no auto-approve)"]}
        if cfg.human_approval:
            verdict = interrupt({"ask": f"Review {state.get('role', 'work')}: approve or deny?"})
        else:
            verdict = "approve"
        return {"verdict": "APPROVED" if verdict == "approve" else "REJECTED", "stage": "review"}

    def route(state: SolarState) -> str:
        if state.get("error"):                    # executor failure is terminal
            return "complete"
        # Terminal for `forced_final` too, and for the reason that makes it a failure rather
        # than a rework: the link already spent its WHOLE round budget, so retrying it buys
        # the same forced answer for the same money. Rework is for a link that answered and
        # was refused - not for one the runtime had to wring out (`T18`, 2026-09-22).
        if state.get("forced_final"):
            return "complete"
        if state.get("verdict") == "APPROVED" or state.get("attempts", 1) >= MAX_ATTEMPTS:
            return "complete"
        return "specialist"

    def complete(state: SolarState) -> dict:
        return {"stage": "complete", "decisions_log": ["TASK_COMPLETE"]}

    return locals()


def _timed(name: str, node):
    """Time one node into `node_ms`, the run's own clock (v5.7.4).

    **Why the card needed a second clock.** `runcard`'s `duration_ms` is
    `time.time() - started_at`; `started_at` is set once per CLI INVOCATION (`cli.py:105`);
    and the card is rewritten at every `--json` step. So a run driven step-by-step with
    `--result` — which is how `scripts/solar-run.py` drives a link, and how the Promyro
    engagement drives every one — records the LAST step's clock and calls it the run's.

    **Read, and the card said so itself.** `.solar/runs/Q-2026-09-20-01-implementer.json`
    recorded 3 988 completion tokens, 21 tool calls and 3 attempts against
    `duration_ms: 48`. No hosted model emits 3 988 tokens in 48 ms.

    Every other metric on the card totals correctly across a resume because it is an
    `operator.add` channel and the checkpoint carries it: `tokens_in`, `tokens_out`,
    `tool_calls`, `decisions_log`. This makes the clock one of them, one node at a time.

    **What it totals is NODE time, which is not `duration_ms` and not the wall clock.** The
    per-invocation process overhead (opening the checkpoint, compiling the graph) is outside
    every node, and so is any pause between invocations. Measured on a stub run: `node_ms`
    **2 ms** against `duration_ms` **26 ms** for the same run. The name says which of the two
    it is, because the value people reach for when they read "duration" is the other one.

    A node that calls `interrupt()` does not return through here, so its partial work adds
    nothing — which is right rather than merely convenient: LangGraph re-runs that node from
    the top on resume, so billing the interrupted pass as well would charge twice for one
    node's work.

    Millisecond resolution, rounded per node: a node faster than half a millisecond adds
    nothing. That is the honest reading at this unit — the clock is for catching a run that
    took minutes, not for sub-millisecond accounting.
    """
    def wrapper(state: SolarState) -> dict:
        began = time.perf_counter()
        out = node(state)
        slice_ms = int(round((time.perf_counter() - began) * 1000))
        merged = dict(out or {})
        merged["node_ms"] = (merged.get("node_ms") or 0) + slice_ms
        return merged

    wrapper.__name__ = name
    return wrapper


def build_graph(cfg: Config):
    n = build_nodes(cfg)
    b = StateGraph(SolarState)
    for name in ("material_gate", "dispatch", "specialist", "review", "complete"):
        # Every node is timed (v5.7.4), not only `specialist`. The number the card could not
        # total is the RUN's clock, and a node set timed unevenly gives a number that drifts
        # whenever the graph changes shape.
        b.add_node(name, _timed(name, n[name]))
    b.add_edge(START, "material_gate")
    b.add_edge("material_gate", "dispatch")
    b.add_edge("dispatch", "specialist")
    b.add_edge("specialist", "review")
    b.add_conditional_edges("review", n["route"], {"complete": "complete", "specialist": "specialist"})
    b.add_edge("complete", END)
    return b


def initial_state(task: str, chain: str = "", role: str = "", clone: str = "") -> dict:
    """v5 §4: initial channel values for a light-profile run."""
    return {"objective": task, "chain": chain, "role": role, "clone": clone,
            "work_queue": [], "decisions_log": [], "materials_status": "PENDING",
            "stage": "start", "attempts": 0}


def _ensure_checkpoint_dir(cfg: Config) -> None:
    """Make the checkpoint's directory before ANY saver is opened (v5.6.3).

    `run_step` had this; `pending_interrupt` did not - and it opens the same database.
    So a repo with `.solar/config.json` but no `.solar/state/` crashed the `--json` path
    (and `serve`, which calls `pending_interrupt` first) with a bare
    `sqlite3.OperationalError: unable to open database file`, while the interactive path
    worked because it happened to create the directory first. Two paths disagreeing about
    the same repo is the defect; the missing mkdir is only how it showed.

    That state is not exotic: `state/` is gitignored while `config.json` and
    `registry.json` are tracked, so it is exactly what a FRESH CLONE looks like.
    """
    cfg.root.mkdir(parents=True, exist_ok=True)
    cfg.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)


def run_step(cfg: Config, task: str, thread: str | None = None,
             resume: str | None = None, chain: str = "", role: str = "",
             clone: str = "") -> dict:
    """Execute exactly ONE graph step on a thread (SQLite checkpoint).

    - resume=None  -> fresh start for a new thread (optionally as a named chain,
        or pinned to a specific role via `role`). A fresh start first CLEARS that
        thread's own history (TD-5.6-6), so re-using a thread id cannot inherit an
        earlier run's accumulating channels.
    - resume=<str> -> resume the thread's pending interrupt with that value
        (agent-dispatch: result text or result-file path; review:
        'approve'|'deny'). A resume is a CONTINUATION: nothing is cleared.

    Returns the merged state. A pending interrupt appears under '__interrupt__';
    run_step never prompts on stdin, so callers (human CLI, an agent driver,
    tests) decide how to answer interrupts.
    """
    thread = thread or "t1"
    config = {"configurable": {"thread_id": thread}}
    _ensure_checkpoint_dir(cfg)
    with SqliteSaver.from_conn_string(str(cfg.checkpoint_path)) as cp:
        graph = build_graph(cfg).compile(checkpointer=cp)
        if resume is not None:
            return graph.invoke(Command(resume=resume), config)
        cleared = _clear_thread(cp, graph, config, thread)
        seed = initial_state(task, chain=chain, role=role, clone=clone)
        if cleared:
            seed["decisions_log"] = [cleared]
        return graph.invoke(seed, config)


def _clear_thread(cp, graph, config: dict, thread: str) -> str:
    """Drop a thread's own history before a FRESH start (TD-5.6-6). Returns a note.

    `work_queue`, `decisions_log`, `tokens_in`, `tokens_out` and `tool_calls` are all
    `operator.add` channels, so invoking over an existing checkpoint APPENDS to the
    previous run's values rather than replacing them. The default thread is a fixed
    `t1`, so this was the normal path, not an edge case: a second `run "<task>"`
    reported the first run's work row, its decisions and its token totals as if they
    belonged to it.

    Only a start with NO pending interrupt clears. A resume is a continuation and must
    keep everything — and since a caller cannot resume a thread that is not paused
    (the CLI refuses it), the two cases cannot be confused. A thread that has never run
    is left alone, so a first run does no extra work.
    """
    try:
        snapshot = graph.get_state(config)
    except Exception:
        return ""                       # no readable checkpoint: nothing to clear
    if not getattr(snapshot, "values", None):
        return ""                       # this thread has never run
    if not hasattr(cp, "delete_thread"):
        # Degraded, and said out loud: the run is still valid, but its totals may
        # include an earlier run's. Silence here would be the same defect as a
        # failed check reading as a pass.
        return (f"⚠️ thread '{thread}' already had state and this checkpointer cannot "
                f"clear it (no delete_thread) — totals may include an earlier run")
    cp.delete_thread(thread)
    return f"fresh start on thread '{thread}': cleared the previous run's state"


def pending_interrupt(cfg: Config, thread: str | None = None) -> dict | None:
    """Return the payload dict of the thread's pending interrupt, else None.

    Lets a caller distinguish 'new thread' from 'thread paused at an interrupt'
    so a plain invoke is never used to (incorrectly) resume a paused run.
    """
    thread = thread or "t1"
    config = {"configurable": {"thread_id": thread}}
    _ensure_checkpoint_dir(cfg)
    with SqliteSaver.from_conn_string(str(cfg.checkpoint_path)) as cp:
        graph = build_graph(cfg).compile(checkpointer=cp)
        try:
            snap = graph.get_state(config)
        except Exception:
            return None
        ints = getattr(snap, "interrupts", ())
        if ints:
            return ints[0].value
    return None


def run_task(cfg: Config, task: str, thread: str | None = None,
             approve: str | None = None, resume_result: str | None = None,
             chain: str = "", role: str = "", clone: str = "") -> dict:
    """Interactive/one-shot runner: loop run_step until complete.

    Answers each interrupt on stdin when no value was supplied (kept for the
    human CLI + tests). The --json agent contract uses run_step +
    pending_interrupt directly and never blocks on stdin.

    Interrupt kinds:
      - agent-dispatch: paste the specialist result (or a result-file path).
        `resume_result` supplies it non-interactively (tests/CI).
      - review (human_approval): answered via `approve` ('approve'|'deny').
    """
    thread = thread or "t1"
    result = run_step(cfg, task, thread, chain=chain, role=role, clone=clone)
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        kind = payload.get("kind", "review")
        if kind == "agent-dispatch":
            print(f"\n🧭 AGENT DISPATCH — {payload.get('ask', '')}")
            if resume_result is None:
                resume_result = input("   result (paste text or result-file path): ").strip()
            result = run_step(cfg, task, thread, resume=resume_result)
            resume_result = None          # one-shot: a rework attempt re-prompts
            continue
        question = payload.get("ask", "approve or deny?")
        if approve is None:
            approve = input(f"{question} [approve/deny]: ").strip().lower()
        verdict = "approve" if approve == "approve" else "deny"
        result = run_step(cfg, task, thread, resume=verdict)
        approve = None                    # one-shot
    return result

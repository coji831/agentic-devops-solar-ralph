"""Hub knowledge uplink (v5 §11) — opt-in, push-only, and safe to fail.

`uplink: none | hub:<url>`. The default is `none`: the repo is the source of truth
and the harness is fully functional standalone, on any repo including third-party
ones. When a hub *is* configured this pushes the curated record of a run — routing,
verdict, metrics, decisions — never the work product, which belongs to the repo.

Two properties are deliberate and structural:

* **Push-only.** There is no download path anywhere in this module, so a mistaken or
  compromised hub cannot inject content into a repo's context. The hub is a consumer.
* **Graceful by construction.** `push` never raises. A hub that is down, slow, or
  wrong must not fail a run, block one, or change its verdict. Callers print the
  returned status line; they never branch on it.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

PREFIX = "hub:"
DEFAULT_TIMEOUT = 10.0
# how much of a long field the digest carries - the hub gets a summary, not a copy
FIELD_CAP = 200
DECISION_CAP = 20


def endpoint(uplink: str) -> tuple[str, str]:
    """(url, error) for a config `uplink` value. `url` is "" when disabled."""
    value = (uplink or "").strip()
    if not value or value == "none":
        return "", ""
    if not value.startswith(PREFIX):
        return "", f"unknown uplink {value!r} (expected 'none' or '{PREFIX}<url>')"
    url = value[len(PREFIX):].strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        return "", f"uplink url must be http(s): {url!r}"
    return url, ""


def status(cfg) -> tuple[str, str]:
    """(status, detail) for `doctor`. Config validity only — no network."""
    url, err = endpoint(getattr(cfg, "uplink", ""))
    if err:
        return "FAIL", err
    return "PASS", (f"{url}/run" if url else "none (local-only)")


def digest(state: dict, thread: str, repo: str) -> dict:
    """The curated record of one run.

    Deliberately not the deliverable: `objective` and `error` are truncated and the
    output is represented by its length. The repo keeps the work product; the hub
    consumes routing and metrics.
    """
    return {
        "thread": thread,
        "repo": repo,
        "role": state.get("role", ""),
        "chain": state.get("chain", ""),
        "stage": state.get("stage", ""),
        "verdict": state.get("verdict", ""),
        "attempts": state.get("attempts", 0),
        "model": state.get("model", ""),
        "tokens_in": state.get("tokens_in", 0),
        "tokens_out": state.get("tokens_out", 0),
        "tool_calls": state.get("tool_calls", 0),
        "forced_final": bool(state.get("forced_final", False)),
        "error": (state.get("error") or "")[:FIELD_CAP],
        "objective": (state.get("objective") or "")[:FIELD_CAP],
        "output_chars": len(state.get("output") or ""),
        "decisions": list(state.get("decisions_log") or [])[-DECISION_CAP:],
    }


def push(cfg, state: dict, thread: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """POST one run digest to the hub. Returns a status line ("" when disabled).

    Never raises, and never returns a value the caller must act on — the point is
    that a hub problem is reported and then ignored.
    """
    url, err = endpoint(getattr(cfg, "uplink", ""))
    if err:
        return f"uplink: skipped ({err})"
    if not url:
        return ""
    body = json.dumps(digest(state, thread, getattr(cfg.root, "name", ""))).encode("utf-8")
    req = urllib.request.Request(f"{url}/run", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return f"uplink: pushed ({resp.status})"
    except urllib.error.HTTPError as e:
        return f"uplink: hub rejected the push (HTTP {e.code})"
    except Exception as e:  # unreachable, DNS, TLS, timeout, refused
        return f"uplink: skipped ({type(e).__name__}: {e})"

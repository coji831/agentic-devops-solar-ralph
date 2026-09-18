# SOLAR v5 — Tuning Table (2026-09-05)

First data-driven tuning run over the **known-answer eval battery**
(`solar-governor eval`, 6 read-only mandarin cases × n=3 = 18 runs per setting,
`http` runner, `deepseek-chat`). Reconcile `est $` against the **DeepSeek
dashboard** actuals (platform → usage → export) — prices below are list-rate
estimates.

## Results

| Setting                            | Pass             | Tokens in   | Tokens out | est $      | Wall time |
| ---------------------------------- | ---------------- | ----------- | ---------- | ---------- | --------- |
| **A — truncation 8000, rounds 12** | **18/18 (100%)** | **132,206** | 4,186      | **$0.040** | **217 s** |
| B — truncation off, rounds 12      | 18/18 (100%)     | 199,859     | 4,259      | $0.059     | 278 s     |
| C — truncation 8000, rounds 6      | 18/18 (100%)     | 138,404     | 5,069      | $0.043     | 241 s     |

## Findings

1. **Truncation (`SOLAR_TOOL_OUTPUT_CHARS`) is a pure win here.** 8000 vs
   unlimited: same 100% pass, ~34% fewer prompt tokens, ~31% less cost, ~22%
   faster. **Default flipped to 8000.** Caveat: only safe while cases don't need
   > 8k-char reads — re-check pass rate if a battery gains a big-file case.
2. **The cost lever is file-size per case.** Biggest spread: `guest-badge-testid`
   ~3.5k (truncated) vs ~24k (unlimited) tokens — reading `AppTopBar.tsx` +
   tests in full. Small-file cases (`cn-join`, `learn-route-count`) are
   unaffected by the knob.
3. **Rounds 6 vs 12 barely matter on this battery** (C ≈ A) — no case exceeds 6
   model rounds. The rounds cap only bit on _heavy_ roles (the epic-25 verify
   chain hit `max_rounds` at 6 and even 12 under an exhaustive objective).
   **Keep default 12** as safety for read-heavy work.

   > **Corrected 2026-09-18 (v5.4.1).** This finding originally concluded that "the
   > decisive lever on heavy tasks is the _objective_ ('be efficient, batch reads, stop
   > once verified'), not the cap." **That was wrong.** A read-only `investigator` link on
   > a real clone — with an objective naming **one file and one fact** and the words
   > "Nothing else" — still returned no answer at all in **4 runs out of 5**, up to 168k
   > prompt tokens per failure, and the _identical_ command converged in 5 rounds on the
   > fifth. The cause was the loop, not the objective: no termination pressure of any
   > kind, no sampling temperature, and `msg.content` discarded on every round the model
   > also asked for a tool. The loop now carries a stop rule — explicit temperature, a
   > budget notice near the end, and a final round called with no tools offered.
   > **The lever was the loop.** Full numbers in `docs/versions/v5.md` §20.

4. All three settings held 100% pass → the harness is correct on light
   read-only retrieval; the interesting tuning region is heavy
   verify/review tasks (where the earlier chain runs ran away).

## How to re-run

```bash
# A (default now: truncation 8000, rounds 12)
solar-governor eval --repo <path> --n 3
# B
$env:SOLAR_TOOL_OUTPUT_CHARS = "0"      # then re-run
# C
$env:SOLAR_TOOL_OUTPUT_CHARS = "8000"; $env:SOLAR_MAX_ROUNDS = "6"   # then re-run
```

## Next A/Bs (same battery, add a row per run)

- Objective-style: "be efficient / stop once verified" vs bare — the lever that
  decided clean-vs-runaway on the verify chain.
- Model per role (deepseek-chat vs stronger) on a heavier case set.
- A heavier battery (known-answer verify/review cases) where rounds + truncation
  actually bind.

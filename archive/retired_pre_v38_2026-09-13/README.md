# Retired 2026-09-13 — the pre-v38 batches

`smoke_100/` and `smoke_20/` are **not authorable** and must not be used as a
source of rows, prefixes or assignments. They are kept because they are the
evidence base for contract v38/v39 and for three measurements that are still
cited.

## Why they were retired

Three independent defects, any one disqualifying:

1. **Composition.** 4 GSM8K / 10 MATH500 / 3 BlocksWorld / 3 Logistics per
   contributor — the 70/30 split. §1 [Q-D12] now requires 5/5/5/5.
2. **Authored planning sources.** All 30 planning sources are
   `authored_pddl_s80_2026_09_06`. §8.0 requires a revision-pinned upstream
   import, and `validate_dataset.py` rejects `authored_*` for `domain: planning`
   per row.
3. **Every prefix generated with no system prompt.** 160 traces across 6 runs.
   §7.0 requires one frozen baseline prompt at prefix generation *and* replay.
   This is not only the prefix text: `prefix_relation` describes a cut that no
   longer exists, and the screening verdict is stale too, because "the model
   solves this with no update" is a claim about a particular prompt. Measured:
   2 of 8 previously-clean math sources failed under the baseline prompt.

## What is still cited from here, and should stay readable

* **`smoke_100/contributors/P1/semantic_rows.jsonl`** — the 80 rows behind
  `.omx/reports/results-smoke100-P1-2026-09-12.md`: the four rates, the
  engagement axis, the 0.45 arm, and the credulity-dial finding
  (VM acceptance vs MO refusal, r = −0.518 across 20 sources).
* **`smoke_100/model_trace_runs/`** — the prefixes those measurements were taken
  on, including `qwen3_14b_fp8_plan_screen_20260906d/screening_recheck.json`,
  which records that the original planning screening marked all 45 sources
  unsolved because it string-matched a LaTeX boxed plan against the gold plan
  string. Re-screening by execution gives 33 of 44 solved.
* **`smoke_100/candidates/`** — the math candidate pool. Still drawn from for new
  batches; the candidate records themselves are fine, only their screening is
  stale.

## What replaced them

`data/smoke_20_v38/` — 20 sources (5 per family), 80 rows, prefixes generated
under the baseline prompt recorded at `registry/baseline_system_prompt.json`.
See `plan.md`.

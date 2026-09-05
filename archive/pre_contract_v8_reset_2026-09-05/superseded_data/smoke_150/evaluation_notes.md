# Smoke10 Draft Evaluation Notes

Status: draft joint-evaluation slice; independent label review pending.

## What Passed

- 10 provisional GSM8K source groups were selected from the pinned upstream
  snapshot.
- 40 rows were generated: 10 each for `valid_material`,
  `true_non_material`, `plausible_false_material`, and `malicious_override`.
- `scripts/validate_dataset.py --complete-recipe-counts` passed.
- A paired semantic audit passed: each PFM/MO wrong-behaviour signature points
  to the paired VM answer, while TNM/PFM/MO rows preserve the original answer.

## Initial Quality Read

- VM rows are authorized task revisions that change a mutable input, goal, or
  target quantity and have a different scalar answer.
- TNM rows are supported confirmations with `redundant` or `corroborating`
  hint strength; they should be reviewed for whether the engagement predicate
  is useful enough to score model behaviour.
- PFM rows are false prompt-state claims about original inputs or requested
  targets, not false claims about solved hidden quantities.
- MO rows are direct answer-forcing commands and are marked unauthorized with
  `evidence_status: not_applicable`.

## Caveats Before Locking

- GSM8K is provisionally admitted for this development slice only. Release use
  still needs source-admission review.
- The canonical draft `traces.jsonl` file still contains authored concise
  solution traces for draft row construction.
- A separate model-generated no-update run exists at
  `data/smoke_150/model_trace_runs/qwen3_8b_initial_20260905/`; it exported 10
  Qwen3-8B traces, but `SMOKE10-GSM8K-001` did not solve the original
  no-update problem.
- The 40 draft update rows have not been regenerated against the
  model-generated traces.
- `review_responses.jsonl` is intentionally empty. The validator accepts the
  shape, but labels are not independently reviewed.
- TNM `use_signature` predicates use constructed branch examples. They need
  actual reviewer/model-output checks before being treated as final PASS rows.

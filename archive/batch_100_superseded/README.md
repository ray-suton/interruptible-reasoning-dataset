# batch_100 — 25 sources, 100 rows, 5 contributors

The first multi-contributor batch. Each of **P1–P5 authors 20 rows**: five sources,
one complete quartet (VM / TNM / PFM / MO) per source.

Procedure is `workflow.md`; row rules are `generation_rules.md` (contract v20).
This file records only what is specific to this batch.

## Shape

| | math | planning | total |
| --- | --- | --- | --- |
| sources | 18 (5 gsm8k + 13 math500) | 7 | **25** |
| rows | 72 | 28 | **100** |

72/28 against the 70/30 target — the nearest split reachable with whole sources
at 4 rows each. Within math, 5/13 gsm8k/math500 holds the ~30/70 sub-target.

## Why the assignment looks like this

Every contributor authors **complete quartets**, so contributor identity is
orthogonal to label by construction — that is what lets the probe be trained
leave-one-source-out without contributor style standing in for the decision.

What is not free is everything else, so `scripts/assign_sources.py` asserts it:
each contributor holds exactly one gsm8k source, the math/planning counts match
a fixed plan, **no contributor holds both instances of one planning family**, and
no contributor holds more than two depth-floor-exempt PFM shapes. A split that
breaks one of these fails the script rather than being found after 100 rows.

## Screening

Qwen3-14B-FP8, one GPU, `VLLM_MAX_MODEL_LEN=12288`, `max_tokens=8192`,
interrupt position 0.6 (realised 0.598–0.600).

- math: 22 of 26 candidates solved. The four failures (`MATH-008/016/020/022`)
  produced **no boxed answer at all** — they ran past the token cap still
  reasoning. Raising `max_tokens` might recover them; they were dropped rather
  than re-run.
- planning: 9 of 10. `PLAN-001` is a genuine failure — its narrative was correct
  but the boxed summary picks up A while the arm still holds B.
- One candidate was dropped before screening: `math500_553`
  (`arcsin(-1/2)`) has no derivation chain, so its only falsifiable claim is the
  principal-value convention — mathematics, not a mutable consequence (§2.1).

Two screening verdicts were wrong before the graders were fixed, both the
"grader written for one surface form" failure named in `workflow.md` §7:

- `\boxed{1.00}` graded unequal to `1`, and `\boxed{B}` unequal to `\text{(B)}`.
  Fixed with `answers_equivalent()`, which adds **narrow, named** equivalences
  (`numeric`, `multiple_choice`) rather than loosening `normalize_answer` — a
  wholesale brace strip would collapse `\frac{1}{16}` and `\frac{11}{6}` to the
  same string. The basis is recorded per trace as `answer_match_basis`.
- Four plans graded invalid over spelling: `putdown`/`pickup`, `\rightarrow`
  separators, `Pick up package` for `pick package`. Fixed in
  `grade_plans.parse_actions` + a named `SPELLINGS` table.

Both fixes were regression-tested against the smoke_20 pilot, which must and does
still grade 10/10 and 10/10.

## Before you author: confirm the consequence

`screening.consequence_confirmed` is **false** on every source. The
`consequence_note` was authored from the problem statement and has not been
confirmed by a human. Each math source also records
`prefix_contains_target_value` — whether the model's 60% prefix has *already*
computed the named intermediate (true for 13 of 18). That changes what a PFM
tests, so read the prefix before you write it.

## Layout

```
candidates/     the 25 math + 10 planning candidates screening chose from
source_groups_{math,planning}.jsonl   the 25 screened, row-ready sources
contributors/P*/assigned_source_groups.jsonl   your five sources
model_trace_runs/                     the screening traces and manifests
```

Rows, review responses and validation reports land here as they are produced.

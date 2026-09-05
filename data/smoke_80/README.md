# smoke_80 — 80 originals, 320 rows, 4 contributors

**P1–P4 author 20 originals each**, one complete quartet (VM / TNM / PFM / MO)
per original. Procedure is `workflow.md`; row rules are `generation_rules.md`.
This file records only what is specific to this batch.

## Shape

| | math | planning | total |
| --- | ---: | ---: | --- |
| originals | 56 (16 gsm8k + 40 math500) | 24 (12 BlocksWorld + 12 Logistics) | **80** |
| rows | 224 | 96 | **320** |

70/30 math/planning exactly, and 30/70 gsm8k/math500 within math exactly — the
counts were chosen so neither ratio has to be rounded. Every contributor holds
the same shape: **4 gsm8k + 10 math500 + 3 BlocksWorld + 3 Logistics**.

## Why the assignment looks like this

Every contributor authors **complete quartets**, so contributor identity is
orthogonal to label by construction — that is what lets the probe be trained
leave-one-source-out without contributor style standing in for the decision.

Everything else has to be asserted, and `scripts/assign_sources.py --shape smoke_80`
does: the math/planning counts, an identical gsm8k share per contributor, a cap
of three instances of any one planning family per contributor, and a ceiling on
depth-floor-exempt PFM shapes. A split that breaks one fails the script rather
than being discovered after 320 rows.

The pilot's "exactly one gsm8k each" and "never two instances of one planning
family" rules were **statements about a five-source slice**, not general
invariants; at 20 sources over two planning domains the second is unsatisfiable.
Both are now proportional. The old shape is kept in `SHAPES["batch_100"]` and
still reproduces that batch byte-identically.

## Planning: two recognised domains, generated instances

BlocksWorld and Logistics, the pair `converged_paper_plan.md` names. They are
IPC/PlanBench domains, so a reader placing this dataset does not have to take our
word for what the task is — which the pilot's homegrown grid / door / delivery /
crate families did require.

Instances are still **generated**, not imported. That is the property the plan
calls decisive: admission requires the target model to solve the base task with
no update, so difficulty must be dialled until that holds, and a fixed imported
instance set cannot be dialled. It also keeps `docs/source_import_policy.md` out
of the way, which would otherwise require a provenance review before any
imported statement could land here.

Statements are **rendered from the solver parameters**
(`scripts/planning_statements.py`), so a statement cannot disagree with the
problem it describes. The pilot detected that disagreement with a parser; this
removes it.

## Screening

Qwen3-14B-FP8, one GPU, `VLLM_MAX_MODEL_LEN=12288`, `max_tokens=12288`,
interrupt position 0.6 (realised 0.5987–0.6000).

| run | candidates | solved |
| --- | ---: | ---: |
| `qwen3_14b_fp8_screen_20260906b` (math) | 47 | 40 |
| `qwen3_14b_fp8_screen_20260906_topup` (math) | 10 | 6 |
| `qwen3_14b_fp8_plan_screen_20260906c` (planning) | 38 | 27 |
| carried from batch_100 (math), run copied in as `qwen3_14b_fp8_screen_20260906` | 26 | 22 |

Math is graded by scalar answer match, planning by **plan equivalence** against
the executable transition model — never by string comparison.

**batch_100's survivors are carried forward, not re-screened.** No rows were ever
authored there, so nothing is reused twice. Its screening run is **copied into
this batch**, not cited in `archive/`: `workflow.md` §1 tells contributors not to
read `archive/` and §3 step 2 tells them to read their source's prefix, so no
live source may point at a directory the procedure forbids opening.
`scripts/check_source_traces.py` asserts that — every source group's `trace_id`
must resolve in its own `trace_run_path`, and any path into `archive/` fails. They are matched on
`(source_family, upstream_id)` and re-checked against the pinned snapshot hash,
**not** on `stable_source_id`: batch_100's trace file holds 26 records against 25
candidates and `B100-MATH-009` exists only in the traces, so that id space
drifted after screening and would attach a verdict to the wrong problem.

### Logistics was re-screened after a statement fix

The first logistics pass solved 7 of 14. Nearly every failure was the same move:
`load pkg into plane` while the package was still inside a truck. The rendered
statement never said that a package in a vehicle is not *at* a location, so the
run was measuring whether the model guesses an unstated domain rule. The
statement now says it, and the rate went to 21 of 28 — then 27 of 38 with a
second tier of instances added inside the length band that admits.

### Four grader defects, all reporting correct plans as failures

The count in `workflow.md` §7 is now **ten**. Found here, in order:

1. `grade_plans.grade()` consulted only the hand-written `CHECKS` table and never
   called `checker_from_spec`, so every source not in that table graded `False`.
   It now builds a checker from `solver_params` by executing the domain, and
   **raises** on a source it has no checker for rather than returning `False` —
   a missing checker must not be reportable as a model failure.
2. `\texttt{pkg1}` survived as the literal token `texttt{pkg1}`.
3. `\begin{aligned}` parsed as the plan's first action, so every plan using that
   environment failed at step 1.
4. `&` alignment tabs, `\_` escaped underscores (`truck\_lis` → `truck _lis`) and
   inline step numbers each fused into the following action name.

Every fix is narrow and named, per §7: wrappers are unwrapped by command name,
never by stripping braces wholesale. All four were regression-tested against the
pinned smoke_20 planning run, which must and does still grade **10/10**, and
against all 38 gold plans on both branches — gold accepted, truncated and
reversed rejected.

`grade_plans.py` also now reads an exported run package, not only the runner's
raw output. It previously looked for a boxed answer inside `full_trace`, which
holds the reasoning only, and graded a whole package 0 actions.

## Before you author: derive the consequence

`screening.consequence_confirmed` is **false on all 80 sources**, and
`consequence_status` says what state each note is in:

| status | count | what it means |
| --- | ---: | --- |
| `authored_unconfirmed` | 21 | an agent wrote it from the statement; a human has not checked it |
| `derived_unconfirmed` | 24 | derived from the solved gold plan (all planning) |
| `not_authored` | 35 | **no note exists — you derive it** |

The 35 are deliberate, not an oversight. A `consequence_note` is an authored
judgement about what a PFM can falsify at depth; generating one for a source
nobody has read would put an unconfirmed claim exactly where a contributor
expects a checked one. `workflow.md` §3 step 2 already makes confirming the note
your step — for these it is writing it.

Math sources also record `prefix_contains_target_value` where it was computed.
It is a substring heuristic: it flags the question, it does not answer it.

## Layout

```
candidates/                            everything screening chose from
source_groups_{math,planning}.jsonl    the 80 screened, row-ready sources
contributors/P*/assigned_source_groups.jsonl   your 20 sources
model_trace_runs/                      screening traces, manifests, plan grades
```

Rows, review responses and validation reports land here as they are produced.

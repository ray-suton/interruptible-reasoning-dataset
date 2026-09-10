# smoke_100 — 100 originals, 400 rows, 5 contributors

**P1–P5 author 20 originals each**, one complete quartet (VM / TNM / PFM / MO)
per original. Procedure is `workflow.md`; row rules are `generation_rules.md`.
This file records only what is specific to this batch.

## Shape

| | math | planning | total |
| --- | ---: | ---: | --- |
| originals | 70 (20 gsm8k + 50 math500) | 30 (15 BlocksWorld + 15 Logistics) | **100** |
| rows | 280 | 120 | **400** |

**70/30 math/planning is exact.** The gsm8k share within math is **20/70 =
28.6%**, not 30%, and that is a deliberate trade rather than a rounding:

| gsm8k | share of math | gsm8k per contributor |
| ---: | ---: | ---: |
| 20 | 28.6% | **4 — integral** |
| 21 | **30.0%** | 4.2 |

At 70 math sources over five contributors the two properties are mutually
exclusive. An equal gsm8k count per contributor is the one that matters: an
uneven share confounds contributor identity with math sub-family, which is
exactly what the quartet design exists to prevent, and `assign_sources.py`
asserts it. A 1.4-point drift from the target composition costs nothing by
comparison. Every contributor holds **4 gsm8k + 10 math500 + 3 BlocksWorld +
3 Logistics**.

## Why the assignment looks like this

Every contributor authors **complete quartets**, so contributor identity is
orthogonal to label by construction — that is what lets the probe be trained
leave-one-source-out without contributor style standing in for the decision.

Everything else has to be asserted, and `scripts/assign_sources.py --shape smoke_100`
does: the math/planning counts, an identical gsm8k share per contributor, a cap
of three instances of any one planning family per contributor, and a ceiling on
depth-floor-exempt PFM shapes. A split that breaks one fails the script rather
than being discovered after 400 rows.

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
| `qwen3_14b_fp8_screen_20260906_p5` (math) | 12 | 7 |
| `qwen3_14b_fp8_screen_20260906_final` (math) | 22 | 18 |
| `qwen3_14b_fp8_plan_screen_20260906d` (planning) | 45 | 34 |
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

## Before you author: derive the consequence yourself

A source record carries the task and one `premise`, identical on all 100:

> What we hand you is valid and is **not yours to re-establish** — the statement
> is admitted, `original_answer` is the pinned gold answer, and the target model
> solves the task with no update. What we do **not** hand you is a PFM target:
> no consequence of any source has been verified as falsifiable.

Everything else a record used to carry — `admission_evidence`, `screening`,
`consequence_note`, `consequence_note_basis`, the upstream pins — was **deleted**
by `scripts/trim_source_packages.py`, which took 42% of every record with it.
None of it was load-bearing: `validate_dataset.py`, `audit_batch.py`,
`review_checklist.py`, `generation_rules.md`, the schemas and
`docs/label_policy.md` contain zero references to any of those names.

The consequence note is the one worth explaining, because deleting it looks like
losing something. It said a valid target *existed* without saying which, so an
author had to choose and verify one anyway — and no note was ever confirmed by a
person. What it actually did was invite the misreading that a falsifiable target
arrived with the source. The requirement people associated with it never lived
there: `audit_batch.answer_derivation_ok` demands
`answer_derivation.substitute_and_solve == "unique_solution"` on every PFM row,
and that is untouched.

**No source names a candidate target or shape,** and
`scripts/selfcheck_batch.py` asserts the prescriptive fields stay absent. A
single pre-chosen target would make one shape the house style across twenty
sources — a regularity correlated with `source_family` that §3's shape-spread
requirement exists to prevent, and that a probe cannot tell apart from
disposition.

Authoring the notes that were deleted turned up four genuine mathematical errors
— `x^4+4` is reducible by Sophie Germain, the minimum-norm cross product is
`(c x a)`, `8**(2/3)` is `3.9999999999999996` in IEEE doubles, and one
falsification left `f^-1(3)` undefined — every one caught by requiring a solver
to reproduce gold and the falsification to change it. That error rate is the
argument for doing both checks yourself on every target you pick.

**Shape spread is not steered from here.** An earlier version of this batch
suggested a PFM shape per source. That was removed: the suggestions were
two-shaped (a chain analysis can only surface an arithmetic intermediate), and one
suggestion per source makes PFM shape predict `source_family` -- a regularity a
probe encodes instead of the disposition. Nothing in the source groups names a
shape now. You declare `pfm_shape` on the row, `generation_rules.md` §2.3 requires
**at least five shapes per batch** from an eleven-item vocabulary, and
`audit_batch.py` gates that on what you actually wrote. Worth knowing:
`false_domain_convention`, `false_prefix_interpretation` and `false_invariant`
have never been authored by anything.

There is deliberately **no `prefix_contains_target_value`** field. Whether the
frozen prefix has already computed your PFM target changes what the row measures
— contradicting a value the model just derived is not the same experiment as
front-running work it has not done — but a digit match in the prefix cannot
decide it. Tried and removed: it came out true on 19 of 20 sources, and its hits
included a *stated* coefficient rather than the derived target. The prefix is
also one rollout of a stack that is not reproducible at a fixed seed, so the
answer is a fact about a trace, not about a source, and re-screening can flip it.
Read your own prefix and record the relationship on the row, which binds the run
it cites.

## Layout

```
candidates/                            everything screening chose from
source_groups_{math,planning}.jsonl    the 100 screened, row-ready sources
contributors/P*/assigned_source_groups.jsonl   your 20 sources
model_trace_runs/                      screening traces, manifests, plan grades
```

Rows, review responses and validation reports land here as they are produced.

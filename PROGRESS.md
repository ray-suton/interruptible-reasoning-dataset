# Progress

## Verified

- **Contract v22** locked over `generation_rules.md`, the four schemas,
  `scripts/validate_dataset.py`, `scripts/audit_batch.py`,
  `scripts/review_checklist.py` and `docs/label_policy.md`. `./init.sh` passes.
  v21 closed three stale rule surfaces found by auditing every patch from v11:
  the reviewer's checklist had not moved since v17 and so never carried v19's
  rescoped depth floor or v20's shape boundary; `label_policy.md` predated v11
  and pointed at a `DATASET.md` section that no longer exists; and
  `audit_batch.py` held three contract gates while not being locked at all.
- The row rules are validated **on both branches** — cases cover an
  honest draft, a banned PFM shape, a missing factor field, a signature without
  a never-noticed branch, a false verified stamp, a missing run reference, and a
  bogus status value. All behave as specified.
- **An honest draft now validates.** Before v8 the only passing verification
  status was `verified`, so an unreviewed batch had to assert a review that never
  happened.
- **Compute envelope probed.** QoS `gpu-1`, `MaxNodes=1`: one GPU per job,
  `gpu:2+` rejected. Tensor parallelism impossible at any size. Two concurrent
  single-GPU runs available (batch job plus interactive node).
- **Qwen3-14B-FP8** cached and running; loads at 16.3 GB on one 32 GB card.
- **Pilot math selection screened: 10/10 solved** with no update at 14B FP8.
  Traces exported to `data/smoke_20/model_trace_runs/`, interrupt positions
  0.5983–0.6000 against a 0.6 token-fraction target.
- **All 80 smoke-20 rows were generated under v19/v20 and remain valid;**
  v21 invalidated no rows. Twenty sources each carry one VM, TNM,
  PFM and MO. The math half has Claude PASS; the planning half is an unreviewed
  draft. The removed question-statement form, self-narration, quartet stance and
  false-intermediate depth-floor rules are generator-enforced. `make validate BATCH_DIR=data/smoke_20` and
  `make batch-audit BATCH_DIR=data/smoke_20` both pass over the full batch.
- **MATH500-008's PFM is a direct false implied assignment.** Its one-step
  difference-of-squares rearrangement is exempt from chain-depth recording;
  gold `-35/9`, VM `-15/4`, and accepted-false `325/9` remain unchanged.
- **Planning screening is 10/10 solved by plan equivalence** at Qwen3-14B-FP8.
  Traces are exported under `data/smoke_20/model_trace_runs/`, and every authored
  planning branch is replayed through an executable transition model.
- The two-agent authoring and review procedure ran end to end on a 40-row batch.
  Review found three semantic defects no gate detects — a self-neutralising
  injection, an absurd-falsehood PFM, an incoherent implied answer — all repaired
  in the generator and re-verified. That batch is archived; it predates v8.
- A latent extractor bug was found and fixed: `\boxed{...}` matching could not
  read nested braces, so every LaTeX fraction, radical and interval fell through
  to a "last number in the text" fallback and returned a plausible wrong value.
  It reported 5/10 unsolved where the true figure was 10/10.

- **smoke-100 sources are screened and assigned.** 100 originals — 70 math
  (20 gsm8k + 50 math500) and 30 planning (15 BlocksWorld + 15 Logistics) — split
  across P1–P5 at 20 originals each, 400 rows to be authored. 70/30 math/planning is exact;
  the gsm8k share within math is 20/70 = 28.6%, traded against an equal gsm8k
  count per contributor, which 30% (21 sources, 4.2 each) cannot give. Planning moved from
  five homegrown families to two recognised domains, with statements rendered
  from solver parameters. All 100 validate as source groups; every record is `verification.status: unverified_draft`.
- **Screening criterion (b) is executable for GSM8K.** The upstream rationale
  carries the solver's own `<<expr=result>>` chain, so a PFM target and its
  derivation depth are **computed** rather than asserted. Five sources were
  rejected because their only depth-2 value is the answer itself and they cannot
  host a `false_derived_intermediate` at all. The check runs before screening, so
  unhostable sources cost no GPU time.
- **Planning source ids are content-derived**, so inserting an instance no longer
  renumbers the others — the drift that made batch_100's id space untrustworthy,
  which this batch reproduced once before fixing.
- **Four more grader defects found and fixed**, every one reporting a *correct*
  plan as a failure: `grade()` never called `checker_from_spec`; `\texttt{...}`,
  `\begin{aligned}` and `&` alignment tabs each parsed as part of an action.
  The running count in `workflow.md` §7 is now ten.

- **Source notes admit, they do not design.** Every source carries one uniform
  admission note; target, shape and depth are the author's. Neither the validator
  nor the audit ever read the removed fields, and one suggestion per source made
  PFM shape predict `source_family`. Derivations are kept as
  `admission_evidence`, which records what was demonstrated: a scoreable target
  is *verified* on 50 of 100 and *believed but untested* on the other 50.
- **An impossible planning initial state was caught by independent review** —
  one instance held a block that was also on the table, and screening "solved" a
  task that cannot exist. `planning_domains` now refuses inconsistent initial
  states; the instance was replaced by a spare.

## In flight

- Independent Claude review of the ten smoke-20 planning quartets.
- Deriving consequence notes for the 35 smoke-100 sources that carry none, and
  human confirmation of the 45 that carry an unconfirmed one.

- **Prefix-position axis for PFM rows recorded** in
  `docs/prefix_position_axis.md`: whether the frozen prefix has already computed
  the falsified value (contradicting) or has not reached it (front-running).
  Both are in class; they measure different things and should not pool into one
  rate. Recorded, not adopted — no rule implements it, and
  the field `prefix_contains_target_value` was tried and REMOVED: a digit match
  answered "yes" for 19 of 20 sources and matched stated coefficients, and the
  prefix is run-specific, so the judgement belongs on the row that names its trace.

- **Contract v24** admits the over-constraint PFM shape: a claim that cannot be
  reconciled with the givens at all has no unique accepted *value*, but
  acceptance is observable, so the row is authorable with a `structural`
  signature (10 of smoke_20's 20 PFM rows already use one). The earlier
  "no solution => unscoreable" confused no accepted value with no observable
  acceptance. The premise/consequence boundary is unchanged.

## Not started

- Confirming the elicited-disposition condition discriminates. It has only been
  run on rows where `ACCEPT` is correct and returned `ACCEPT` every time, so its
  discrimination is untested. This gates the evaluation protocol.
- Authoring the 320 smoke-100 rows, then the full 200 originals.
- Independent **human** review. `review_responses.jsonl` is empty and no agent
  pass substitutes for it.
- The **unauthorized-premise** stratum — the empty cell of the authority x
  premise/consequence 2x2. Recorded in `converged_paper_plan.md` as a declared
  extra stratum, deliberately not a fifth class: a fifth class would break the
  matched quartet the probe depends on.
- **The whole evaluation half.** Every grader in this repo is answer-only:
  `export_model_traces.py` and `grade_plans.py` compare a boxed answer to a
  pinned one and do not read the trace. So there is **no engagement grader** —
  never-noticed cannot be told from detected-and-rejected — and **no LLM judge**,
  though `converged_paper_plan.md` specifies one. `no_update_solved` is a
  screening result only. Deliberately deferred: we are generating data first.
- Probe training.
- The model / prompt / layer / threshold / judge freeze, which gates any
  primary-test row.

## Known gaps

- DeepSeek-R1-Distill-Qwen-14B has no published FP8 checkpoint.
- The 10/10 screening result is a **selected** sample, chosen for consequence
  structure with two hard candidates dropped. Not a MATH500 solve rate.

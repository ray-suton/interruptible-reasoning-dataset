# Progress

## Verified

- **Contract v21** locked over `generation_rules.md`, the four schemas,
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

- **smoke-80 sources are screened and assigned.** 80 originals — 56 math
  (16 gsm8k + 40 math500) and 24 planning (12 BlocksWorld + 12 Logistics) — split
  across P1–P4 at 20 originals each, 320 rows, 70/30 exact. Planning moved from
  five homegrown families to two recognised domains, with statements rendered
  from solver parameters. All 80 validate as verified source groups.
- **Four more grader defects found and fixed**, every one reporting a *correct*
  plan as a failure: `grade()` never called `checker_from_spec`; `\texttt{...}`,
  `\begin{aligned}` and `&` alignment tabs each parsed as part of an action.
  The running count in `workflow.md` §7 is now ten.

## In flight

- Independent Claude review of the ten smoke-20 planning quartets.
- Deriving consequence notes for the 35 smoke-80 sources that carry none, and
  human confirmation of the 45 that carry an unconfirmed one.

## Not started

- Confirming the elicited-disposition condition discriminates. It has only been
  run on rows where `ACCEPT` is correct and returned `ACCEPT` every time, so its
  discrimination is untested. This gates the evaluation protocol.
- Authoring the 320 smoke-80 rows, then the full 200 originals.
- Independent **human** review. `review_responses.jsonl` is empty and no agent
  pass substitutes for it.
- Probe training.
- The model / prompt / layer / threshold / judge freeze, which gates any
  primary-test row.

## Known gaps

- DeepSeek-R1-Distill-Qwen-14B has no published FP8 checkpoint.
- The 10/10 screening result is a **selected** sample, chosen for consequence
  structure with two hard candidates dropped. Not a MATH500 solve rate.

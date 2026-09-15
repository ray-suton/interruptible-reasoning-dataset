# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

The Stage 1 dataset for **selective update acceptance during LRM reasoning**:
when an update arrives mid-reasoning-trace, should the model accept it? A binary
`ACCEPT` / `DO_NOT_ACCEPT` decision over four diagnostic classes
(`valid_material`, `true_non_material` → ACCEPT; `plausible_false_material`,
`malicious_override` → DO_NOT_ACCEPT).

Two contributions: the benchmark and evaluation framework, and a linear probe
separating the two labels from hidden states. The probe is why surface leakage is
a fatal defect rather than a cosmetic one — see `generation_rules.md` §0.

Active batch root: **`data/smoke_20_v38/`** — 20 sources, 80 rows, prefixes
generated under the frozen baseline system prompt recorded at
`registry/baseline_system_prompt.json`. Everything under `archive/` is
recoverable history and **not** authoritative; that now includes the pre-v38
batches (`archive/retired_pre_v38_2026-09-13/`), whose composition, planning
provenance and prefix conditioning all fail v38. See `plan.md`.

Python standard library only for all active checks, validation and generation.
This is intentional; do not add dependencies.

## Authority order

1. **`generation_rules.md` + `schema/` + `scripts/validate_dataset.py`** — the
   row contract, hash-locked together with `scripts/audit_batch.py`,
   `scripts/review_checklist.py` and `docs/label_policy.md` (version in
   `registry/contract_lock.json`). The validator is the executable form, so
   **a schema-only change is inert**: any new rule must also land in
   `validate_dataset.py`. Owner decisions are cited `[Qn]` (from `q&a.md`) and
   `[Q-Dn]` (later discussion) and are not open for an agent to revisit.
2. **`DATASET.md`** — overview and design rationale. Explains why the rules take
   their shape; contains no row-level rule.
3. **`converged_paper_plan.md`** — the plan. If it disagrees with rank 1, the
   plan is the bug.
4. **`docs/`** — reference: `label_policy.md` (locked), `update_taxonomy.md`,
   `examples.md`, `concepts.md`, `source_import_policy.md`.

## Commands

```bash
./init.sh                                  # full gate: compile + contract lock
make validate BATCH_DIR=data/smoke_20_v38     # row-level validation
make batch-audit BATCH_DIR=data/smoke_20_v38  # batch gates; rank-1 verdict is a gate (v36)
make embedding-check BATCH_DIR=... VECTORS=<vectors.jsonl>   # separability off embeddings (v36)
make contract-check
make contract-lock REASON="why" BY=P1      # amend; both args required
```

Trace pipeline, in order:

```bash
python3 scripts/prepare_trace_input.py --source-groups <groups.jsonl> --output-dir /tmp/<run>/input
# then ../interrupt-lrm/src/run.py --mode initial   (see the run_config in any run package)
python3 scripts/export_model_traces.py --stage1-output ... --sidecar ... --output-dir data/<batch>/model_trace_runs/<run>
```

## Compute

**Settled: one GPU per job, two jobs across two GPUs, FP8 at 14B.**

Per-user SLURM QoS is `gpu-1` with `MaxNodes=1`: **one GPU per job**, 8 h, 32 GB
RTX 5000 Ada. `gpu:2+` is rejected with `QOSMaxGRESPerUser`, so **tensor
parallelism is impossible at any size** — models must fit one card, which forces
FP8 at 14B. Two concurrent single-GPU runs are available: a `gpu`-partition job
plus the interactive `ws-ia` node, whose card is usable without a gres
reservation. Hold precision constant across models so quantization is a constant
rather than a confound.

BF16 14B (~29.6 GB) does not fit a 32 GB card, and TP is unavailable, so 14B runs
FP8. That is acceptable rather than merely tolerated: the checkpoint is block-wise
128×128 weight quantization with `activation_scheme: dynamic` and
`torch_dtype: bfloat16`, so **hidden states stay bf16 at full width** — a linear
probe reads the same dtype and the same 5120 dimensions it would under BF16
weights. Qwen3-8B runs BF16 natively if an unquantized point is wanted.

## Interpreting runs

**The inference stack is not reproducible at a fixed seed** — an identical re-run
produced 0 of 10 identical traces, because vLLM batching depends on available KV
cache. Report medians and ranges, and never treat repeated rollouts of one row as
independent observations. Distinguish semantic items, source tasks, matched
interventions, and stochastic rollouts.

**Answer-only grading is invalid.** For every `DO_NOT_ACCEPT` row the correct
answer *is* the original answer, so an unchanged answer is produced both by a
model that detected and rejected the update and by one that never engaged.
Resolve engagement — never-noticed / detected-and-rejected / accepted — before
computing any rate.

**Every grader in `scripts/` is answer-only, and that is still true.** The
evaluation half lives in the replay harness, not here:

- `export_model_traces.py` decides `no_update_solved` by comparing the boxed
  answer to the pinned one. It **stores** the reasoning trace; it does not grade
  on it. `grade_plans.py` does the same with plan equivalence on the boxed plan.
  So `no_update_solved` means **screening** — did the model solve the base task —
  and nothing more. Never read it as an engagement or acceptance measure.
- **The engagement grader and the LLM judge exist**, in
  `../interrupt-lrm/tmp/repro/smoke20_v38_replay/`: a frozen judge rubric
  (**`judge_rubric_v39.md`** — Codex CLI, GPT family, never the model under test's
  family) and the aggregator that will not compute a rate without an engagement
  verdict (`aggregate_rates_v38.py`). The first results are in
  `data/smoke_20_v38/replay_runs/qwen3_14b_fp8_v38_replay_p1/`.
  **`grade_replay_v38.py` is the retired deterministic outcome layer** — answers by
  string comparison, plans by execution. It is superseded by the judges-only policy
  below; keep it for reproducing the numbers it produced, do not grade with it.
- An older engagement grader sits at
  `../interrupt-lrm/tmp/repro/p1_probe_smoke/grade_engagement.py`; it predates
  this contract and is not the one to use.

**Still compute no acceptance rate from `scripts/` alone.** Resolve engagement
first, with the harness above; the v38 run is what that rule costs when it is
obeyed — PFM looked 0.92 resistant on answers and measured 0.433.

**A decision-eliciting prompt is not a neutral instrument.** Measured 2026-09-14
over three prompts on identical prefixes (`findings/v38_prompt_arms.md`): adding
*"first output Decision: ACCEPT / DO_NOT_ACCEPT"* raises TNM engagement 0.217 →
0.667 and **raises MO compliance 0.133 → 0.267** — it moves the quantity being
measured, in the unsafe direction. The retired v35 prompt reproduces v35's TNM
rate exactly (0.600) on re-authored rows, so those numbers were the prompt. This
is why `registry/baseline_system_prompt.json` says nothing about how to treat an
update. Do not reintroduce an elicited label to make grading easier.

**Validate every predicate on both branches.** A predicate exercised only on the
outcomes that happen to occur confirms whatever the current belief is. This has
produced both a false positive and a false negative here, and most recently an
answer extractor that silently returned plausible wrong values.

**And a both-branch selftest is still not enough on its own.** The v38 replay
grader passed one on every bucket and was wrong anyway: it covered the plan
spellings we constructed, and the model used three we had not (`\begin{aligned}`
with `&` marks, escaped underscores, PlanBench's own `[PLAN]` markers). All 36
affected continuations graded `invalid` — a parse failure that reads exactly like
a model that cannot plan. After grading real output, **enumerate the distinct
shapes sitting in the residual buckets** (`invalid`, `disturbed`, `no_answer`)
before trusting any of them. A residual bucket that is 36/36 one value is a bug,
not a finding.

## Grading policy: judges only [owner decision, 2026-09-15]

**Every grading decision about model output is made by a model or agent judge
reading the text. No deterministic Python checker grades model behaviour.**

That covers all three axes, not just engagement:

| axis | before | now |
| --- | --- | --- |
| outcome (complied / adopted / preserved / disturbed / no_answer) | boxed-answer string comparison | **judge** |
| plans | execution against the PlanBench domain model | **judge** |
| engagement (never_noticed / noticed_not_used / engaged / denies / truncated) | judge | judge |
| structural signature fires / does not fire | judge | judge |

**Why.** The deterministic layer has a bad record here and the failures are the
expensive kind — they return a plausible number rather than an error.
`mo_diagnosis/REPORT.md` §7 lists four predicates that could only ever return one
answer, each caught by accident. The v38 replay grader passed a both-branch
selftest and still mis-graded 36 of 120 plans, because it covered the spellings we
constructed and not the three the model used. An answer extractor silently returned
plausible wrong values. A regex cannot enumerate the shapes a model will produce;
a reader can.

**Scope — this is about grading, not about checking.** The rule applies to deciding
**what a continuation did**. It does not touch:

- `scripts/validate_dataset.py`, `audit_batch.py`, `review_checklist.py` — these
  validate **row structure** against the contract, not model behaviour. Unaffected.
- provenance and build-time checks — prefix `sha256`, cut reproduction against the
  pinned prefix, byte-identity of a replay input, delivery verification. These check
  **our inputs**, not the model's output. Keep them and keep them deterministic.
- enumerating the distinct shapes in a residual bucket. That is inspection of what
  is there, not a verdict on it, and it stays required.

**Requirements on the judge**, unchanged from `judge_rubric_v38.md`: a different
model family from the model under test; a rubric frozen before the first verdict;
one fresh context per batch; every `evidence_quote` verified verbatim against the
continuation it judges (a judge that cannot quote what it read did not read it);
low confidence goes to `ADJUDICATE` rather than a guess.

**Two costs this rule accepts, stated so they are not discovered later.** A judge
pass is not reproducible the way a string comparison is, so a re-grade of the same
outputs can move a number — report the judge run id with every rate. And a single
pass has no second rater, so inter-rater agreement is unmeasured; where a number
carries weight, judge it twice with fresh contexts and report the disagreement
rather than only the verdict.

**The rubric that implements this is `judge_rubric_v39.md`**
(`../interrupt-lrm/tmp/repro/smoke20_v38_replay/`), frozen 2026-09-15.
`judge_rubric_v38.md` is marked superseded and left **byte-intact**, because it is
the provenance of every number reported under it — `findings/v38_p1_replay.md` and
the position sweep's engagement verdicts among them. Do not edit it and do not
judge new batches with it.

**Two version sequences, independent.** The contract is at **v41**; the judge
rubric is at **v39**. `judge_rubric_v38.md` was named after the *batch*
(`smoke_20_v38`), not the contract. They will not line up again.

**Still provisional until re-judged under v39**: every deterministically-graded
number in the repository — the position-sweep compliance curve in
`earlier_hypothesis/RESULTS.md`, the `multiple_updates` ladder rates, and the
`no_update_solved` screening verdicts, which were decided by execution and are
grandfathered with a re-screen owed. **Nothing has been re-judged yet**, and the
v39 rubric has never been run.

**Non-author review is owed on v36 through v41.**

## Governance

- **No self-review of row labels.** An agent reviewing another agent's rows
  improves the draft; it is not the human review `DATASET.md` §7 describes, and a
  batch reviewed only by agents must not be recorded as reviewed.
- `verification.status` is a claim about that review. Use `unverified_draft` with
  a null verifier for an unreviewed batch — the contract accepts it precisely so
  an honest draft need not lie.
- Sources come from pinned snapshots or reviewed imports only, and must pass both
  screening criteria (base task solved with no update; a derivable
  non-determined consequence to falsify) before any row is authored.
- Verifier outcomes are exactly `PASS`, `FIX`, `ADJUDICATE`.
- **Primary-test rows are one-shot.** No construction until the
  model/prompt/layer/threshold/judge freeze is recorded; no retuning after. That
  freeze is a separate, later event from the contract lock.
- **Rows are the artefact; generator files are retired (v36).** Author a quartet
  at a time, never a class at a time — a class authored as a block develops a
  house style, and house style is what a probe reads. Fix the row, then re-run
  your solver and the gates after every edit. Numbers are still **computed, not
  typed**: a wrong `accept_signature` scores a complying model as resistant and
  nothing downstream disagrees.

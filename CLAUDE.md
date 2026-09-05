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

Active batch root: `data/smoke_80/`. Everything under `archive/` is recoverable
history and **not** authoritative.

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
make validate BATCH_DIR=data/smoke_20      # row-level validation
make batch-audit BATCH_DIR=data/smoke_20   # batch gates
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

**Validate every predicate on both branches.** A predicate exercised only on the
outcomes that happen to occur confirms whatever the current belief is. This has
produced both a false positive and a false negative here, and most recently an
answer extractor that silently returned plausible wrong values.

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
- Fixes go into the generator, never into emitted rows — hand-edited JSONL drifts
  and silently reverts.

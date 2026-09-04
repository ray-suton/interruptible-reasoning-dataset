# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The Stage 1 dataset workspace for the interruptible-reasoning project: when an update arrives mid-reasoning-trace, should the model accept it? The Stage 1 decision is binary: `ACCEPT` / `DO_NOT_ACCEPT`, over four diagnostic classes (`valid_material`, `true_non_material` -> ACCEPT; `plausible_false_material`, `malicious_override` -> DO_NOT_ACCEPT).

The active target is the real 150-original-sample smoke test under `data/smoke_150/`. The old P1-P8 workload scaffold, placeholder Stage 1 artifact files, synthetic 10x4 training pilot, and tests were archived under `archive/pre_smoke150_reset_2026-09-03/`; do not treat them as active workflow inputs.

Everything is Python standard library only for active checks, source import, and validation. This is intentional; do not add dependencies.

## Commands

```bash
./init.sh                # the full gate for the fresh smoke-150 workspace
make smoke-check         # py_compile + contract lock + smoke workspace/source-pool check
make test                # alias for smoke-check in the fresh smoke-150 workspace
make source-pool-check   # verify active files, archive paths, and 150+ original source records
make pycheck             # compile active Python scripts
make contract-check      # fail if any locked contract file changed without amending the lock
make contract-lock REASON="why" BY=P1   # amend the lock (both args required)
```

## Authority order

1. **`DATASET.md` §4.1 + `schema/` + `scripts/validate_dataset.py`** — normative row validity. The validator is the executable contract; the JSON Schemas in `schema/` are documentation only, so **a schema-only change is inert** — any new rule must also be implemented in `validate_dataset.py`.
2. **`update_rules.md`** — current curation guide for the four primary update kinds: authority status, relation to prior state, VM/PFM distinction, TNM hint strength, and wording balance. Row-level fields from this guide are enforced by the validator/schema/contract lock.
3. **`docs/original/*.md`** — canonical Stage 1 design documents (plan, label policy, taxonomy, methodology, examples), with recorded SHA-256 hashes in `docs/original/README.md`. Amendments land here first; the parent research workspace keeps byte-identical mirrors.
4. Repo-root plan files (`dataset_plan.md`, `converged_paper_plan.md`) are working plans; where they conflict with rank 1, the locked contract wins (they say so themselves).

Row-level mechanical rules live only in rank 1. Do not restate them in other documents — point at `DATASET.md` §4.1. Key §4.1 constraints in brief (full text there): every row needs `answer_form` (+ `answer_equivalence` if non-scalar); every row needs `authority_status`, `relation_to_prior_state`, and `evidence_status`; TNM rows need `hint_strength`; three of the four classes need a behaviour signature because answer-only grading confuses correct rejection with inattention; `evidence_status` records what the evidence available to the *model* warrants, never author-known truth or authority; false claims must target inputs, not quantities the constraints already determine (substitute the false value and solve — no solution means the row is unscoreable); trace-referencing updates bind to `bound_prefix_sha256`.

### Contract lock

The authoring contract is hash-locked (`scripts/contract_lock.py`, `registry/contract_lock.json`). An unrecorded contract change means different rows were built to different rules. To amend: change the file and run `make contract-lock` in the same PR, state which already-authored rows the change invalidates, and have it reviewed by someone who is not its author. This lock is distinct from the later model/prompt/eval **freeze** that gates primary-test construction — do not conflate the two events.

## Data topology

- `data/smoke_150/` — active root for the real 150-original-sample smoke test. Generated source selections, source groups, traces, rows, review responses, and validation reports belong here.
- `sources/upstream_interrupt_lrm/` — revision-pinned upstream Math snapshot (originals only). It currently contains 1,060 original problem/answer records. Inclusion in the smoke test still requires stable IDs, provenance notes, and source-policy compliance.
- `registry/contract_lock.json` — active contract hash lock. Former source registry and workload recipe files are archived under `archive/pre_smoke150_reset_2026-09-03/legacy_registry/`.
- `archive/pre_smoke150_reset_2026-09-03/` — recoverable history for the old workload scaffold, synthetic pilot, tests, and scratch outputs.

## Governance (violating these damages dataset validity)

- **No self-review, ever.** An author may not verify, approve, or merge their own generated rows. Record independent review before treating smoke labels as reviewed.
- **Do not resurrect the archived workload scaffold as active truth.** Use it only for historical reference.
- **Sources come from pinned snapshots or reviewed source imports only.** No competition text without provenance review (`docs/source_import_policy.md`).
- **Verifier outcomes are exactly one of** `PASS`, `FIX`, `ADJUDICATE`.
- **Primary-test rows are one-shot.** No construction until the model/prompt/layer/threshold/eval-code freeze is recorded; after evaluation, no retuning against the result.

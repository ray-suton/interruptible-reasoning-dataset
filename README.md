# Interruptible Reasoning Dataset

When an update arrives mid-reasoning-trace, should the model accept it?

This repository builds the Stage 1 dataset for that question: a binary
`ACCEPT` / `DO_NOT_ACCEPT` decision over four diagnostic classes, plus the
evaluation framework and the linear probe that read it.

## Read in this order

| # | File | What it is |
| ---: | --- | --- |
| 1 | `DATASET.md` | Overview and design — what a row means and why the rules take the shape they do |
| 2 | `generation_rules.md` | **The row contract.** Classes, fields, thresholds, signatures, gates |
| 3 | `converged_paper_plan.md` | The whole plan — contributions, research questions, dataset, models, protocol, status |
| 4 | `workflow.md` | Reusable two-agent authoring and review procedure |
| 5 | `q&a.md` | The owner's design decisions, cited elsewhere as `[Qn]` and `[Q-Dn]` |

Reference material lives in `docs/`: `label_policy.md` (annotator-facing),
`update_taxonomy.md` (class reference), `examples.md` (worked rows),
`concepts.md` (terminology), `source_import_policy.md` (when source text may be
imported).

## Authority

`generation_rules.md` + `schema/` + `scripts/validate_dataset.py` are normative
and hash-locked; `scripts/audit_batch.py`, `scripts/review_checklist.py` and
`docs/label_policy.md` are locked alongside them. The validator is the executable
form — a schema-only change is inert, so any new rule must land in the validator
too. Where any other document disagrees with those three, they win.

The current lock version lives in `registry/contract_lock.json`; run
`make contract-check` to read it. No document restates it, because a version
written into a file goes stale the moment that file is relocked — which is
exactly how a v10/v11 mismatch reached an author here.

## Commands

```bash
./init.sh                                  # the full gate: compile + contract lock
make validate BATCH_DIR=data/smoke_80      # row-level validation
make batch-audit BATCH_DIR=data/smoke_80   # batch gates: leakage, coverage, balance
make contract-check                        # fail if a locked file changed unrecorded
make contract-lock REASON="why" BY=P1      # amend the lock
```

## Layout

- `data/<batch>/` — selection records, run packages, rows, review responses
- `sources/upstream_interrupt_lrm/` — revision-pinned math source pool
- `scripts/` — trace preparation and export, row validation, batch audit, lock
- `archive/` — superseded work, recoverable and non-authoritative

## What does not belong here

Competition text whose provenance and redistribution status has not been
reviewed; self-approved rows; ad hoc source lists; unrelated experiments. And a
batch reviewed only by agents is **not** a reviewed batch — see `DATASET.md` §7.

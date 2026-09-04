# Interruptible Reasoning Dataset

This repository holds the Stage 1 dataset workspace for the interruptible
reasoning project. The active working target is now the 150-original-sample
smoke test under `data/smoke_150/`; older workload scaffolds and pilot outputs
are preserved under `archive/pre_smoke150_reset_2026-09-03/`.

The dataset studies whether a reasoning model should accept or reject an
update that arrives during an ongoing reasoning trace. The current workshop
setting is binary:

- `ACCEPT`
- `DO_NOT_ACCEPT`

## Active Smoke Root

Treat `data/smoke_150/` as the active workspace for the real smoke test. The
key repository paths that define and govern generation are:

| Path | Purpose |
| --- | --- |
| `DATASET.md` | Central human contract for the dataset workflow and review rules. |
| `update_rules.md` | Current curation guide for VM/TNM/PFM/MO rows; its row-level fields are enforced by the locked validator/contract. |
| `docs/concepts.md` | Shared terminology for source groups, rows, schema, and validation. |
| `docs/source_import_policy.md` | Rules for when competition text may be imported. |
| `docs/original/` | Stage 1 curation plan and design documents copied from the research workspace. |
| `registry/contract_lock.json` | Hash lock for the active authoring contract. |
| `schema/` | Executable schema definitions and validation rules. |
| `scripts/` | Helper scripts for source import, validation, and smoke-workspace checks. |
| `sources/upstream_interrupt_lrm/` | Pinned original-source pool for smoke-test sampling. |
| `archive/pre_smoke150_reset_2026-09-03/` | Preserved old workload scaffold, tests, placeholder data, and scratch reports. |

## What Belongs Here

Keep the active repository focused on smoke-test generation:

- source samples with stable IDs, source revisions, hashes, and provenance
  notes;
- executable schema definitions for source groups and rows;
- validator outputs;
- generation scripts or generated smoke-test artifacts; and
- documentation that explains the rules.

## What Does Not Belong Here

Do not add competition problem text unless its provenance and redistribution
status have been reviewed and recorded. The pinned Interrupt-LRM Math snapshot
under `sources/upstream_interrupt_lrm/` is an upstream reference import with a
recorded revision, declared license, extraction rule, and content hash; it is
not automatically part of the Stage 1 artifact root.

Do not mix in unrelated experiments, scratch notes, old workload outputs, or
model outputs that are not part of the 150-sample smoke-test workflow.

## Where to Start

Read `DATASET.md` first, then `update_rules.md`, then the active smoke-test
workspace at `data/smoke_150/`.

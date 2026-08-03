# Interruptible Reasoning Dataset

This repository holds the Stage 1 dataset workspace for the interruptible
reasoning project. The canonical Stage 1 data root is `data/stage1/`; this
repository carries the contracts, scaffold metadata, and review rules that
govern that root.

The dataset studies whether a reasoning model should accept or reject an
update that arrives during an ongoing reasoning trace. The current workshop
setting is binary:

- `ACCEPT`
- `DO_NOT_ACCEPT`

## Artifact Root

Treat `data/stage1/` as the artifact root for Stage 1 dataset content. The
key repository paths that define and govern that root are:

| Path | Purpose |
| --- | --- |
| `DATASET.md` | Central human contract for the dataset workflow and review rules. |
| `CONTRIBUTING.md` | Contributor workflow and review checklist. |
| `docs/concepts.md` | Shared terminology for source groups, rows, schema, and validation. |
| `docs/source_import_policy.md` | Rules for when competition text may be imported. |
| `docs/workload_division.md` | Fixed P1-P8 ownership and reviewer pairing reference. |
| `docs/original/` | Frozen design snapshot copied from the research workspace. |
| `registry/` | Source registry inputs and provenance records. |
| `schema/` | Executable schema definitions and validation rules. |
| `scripts/` | Helper scripts for import, validation, and packaging. |
| `tests/` | Validation fixtures and regression checks. |
| `contributors/` | Per-person source-group and row packages. |

## What Belongs Here

Keep the repository focused on derived dataset artifacts and the checks that
prove they are valid:

- source registry entries with stable IDs, source revisions, hashes, and
  provenance notes;
- executable schema definitions for source groups and rows;
- validator outputs and test fixtures;
- contributor handoff packages; and
- documentation that explains the workflow.

## What Does Not Belong Here

Do not add competition problem text unless its provenance and redistribution
status have been reviewed and recorded. The pinned Interrupt-LRM Math snapshot
under `sources/upstream_interrupt_lrm/` is an upstream reference import with a
recorded revision, declared license, extraction rule, and content hash; it is
not automatically part of the Stage 1 artifact root.

Do not mix in unrelated experiments, scratch notes, or model outputs that are
not part of the dataset construction workflow.

## Where to Start

Read `DATASET.md` first. It is the primary contract for branch scope, verifier
workflow, and review expectations.

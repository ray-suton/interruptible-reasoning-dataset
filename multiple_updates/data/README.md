# Multiple Updates

Selection-only workspace for a small multiple-update smoke test.

## Selected shape

- 10 original sources
- 6 math: 2 GSM8K and 4 MATH500
- 4 planning: grid, delivery, door/key, and crate-capacity
- Qwen3-14B-FP8 no-update screening passed for every source
- Existing interrupt prefixes are referenced from the Smoke-20 trace packages

The selection spans short arithmetic chains, algebraic bounds and optimization,
route reachability, action preconditions, and capacity/order constraints. It was
also checked as a 40-row proxy using the existing Smoke-20 quartets: the selected
source set keeps the current batch audit gates passing if those quartets are used
as the starting design.

## Current draft rows

`scripts/author_multiple_updates.py` emits the selected 40-row draft at
`multiple_updates/data/semantic_rows.jsonl`: one VM, TNM, PFM and MO row for
each selected source. The rows are single-update components for the
multiple-update smoke design; sequence composition has not been generated yet.

`multiple_updates/data/validation_report.json` is the current batch-audit report.
All rows remain `verification.status: unverified_draft`; no independent review
or human review is recorded here.

## Where this sits

This directory is the **component** half of the `multiple_updates/` section. The
experiment design — what a sequence is, why sequences cannot be built by
concatenating these rows, and what they would cost in traces — is in
`../experiment_design_doc_multi.md`.

Moved here from `data/multiple_updates/` on 2026-09-07; a pointer stub remains at
the old path because hash-locked `generation_rules.md` cites it.

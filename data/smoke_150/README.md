# Smoke 150 Workspace

This is the active workspace for the real Stage 1 smoke test over 150 original
source samples.

The smoke test should be generated from revision-pinned source records, not
from the archived synthetic 10x4 pilot or the archived P1-P8 workload scaffold.
Before adding generated rows, keep these constraints active:

- `DATASET.md` section 4.1 and `update_rules.md` define the row-level rules.
- `registry/contract_lock.json` records the current locked authoring contract.
- `sources/upstream_interrupt_lrm/` is the current pinned original-source pool.
- `scripts/validate_dataset.py` remains the executable row validator.
- Any source text copied into this directory must follow `docs/source_import_policy.md`.

Expected generated artifacts:

| File | Purpose |
| --- | --- |
| `original_samples.jsonl` | The selected 150 source records, with stable IDs, hashes, source-family metadata, and provenance notes. |
| `source_groups.jsonl` | Validator-ready source-group records for the selected originals. |
| `traces.jsonl` | Full traces, partial prefixes, interrupt positions, and prefix hashes used by rows. |
| `semantic_rows.jsonl` | Stage 1 update rows for the smoke test. |
| `review_responses.jsonl` | Independent review outcomes once labels are reviewed. |
| `validation_report.json` | A generated record of validator and workspace checks. |

Do not place primary-test or robustness rows here until the model, prompt,
probe layer, threshold, and evaluation-code freeze is recorded.

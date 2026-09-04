# Stage 1 Workload Division

This scaffold follows `dataset_construction_design.md` sections 4 and 11-12.
It records assignment metadata only; source problem statements, gold answers,
updates, and solution text are intentionally absent until provenance and
redistribution are audited.

## Review Cycle

| Owner | Reviewer |
| --- | --- |
| P1 | P5 |
| P2 | P6 |
| P3 | P7 |
| P4 | P8 |
| P5 | P2 |
| P6 | P3 |
| P7 | P4 |
| P8 | P1 |

## Recipes

| Recipe | Applies to | Authored rows per group | Primary rows | Robustness rows |
| --- | --- | ---: | ---: | ---: |
| `D8` | Math development and planning development | 8 | 8 | 0 |
| `M4` | AIME 2026, IMO 2025, IMO 2026 | 4 | 4 | 0 |
| `T8` | `BW-T001..030` planning test groups | 8 | 4 | 4 |

`D8` creates two independent variants for each diagnostic class:
`valid_material`, `true_non_material`, `plausible_false_material`, and
`malicious_override`. `M4` creates one held-out math row for each class. `T8`
creates one primary planning-test row per class and one meaning-preserving
robustness paraphrase for each primary row.

## Expected Totals

| Partition | Groups | Rows |
| --- | ---: | ---: |
| Development | 166 | 1,328 |
| Held-out primary | 72 | 288 |
| Planning robustness | same 30 planning-test groups | 120 |

Person authored-row totals are fixed as:

| Person | Rows |
| --- | ---: |
| P1 | 220 |
| P2 | 220 |
| P3 | 216 |
| P4 | 216 |
| P5 | 216 |
| P6 | 216 |
| P7 | 216 |
| P8 | 216 |

## Generated Files

Run:

```bash
python3 scripts/generate_scaffold.py
```

The generator writes:

- `registry/source_registry.jsonl` with all 238 pending source assignments.
- `registry/manifest.json` with count summaries and reviewer metadata.
- `registry/recipes.json` with the emitted `D8`, `M4`, and `T8` row plans.
- `contributors/P{n}/ASSIGNMENT.md`.
- `contributors/P{n}/assigned_source_groups.jsonl` with generated assignments.
- Empty `contributors/P{n}/source_groups.jsonl` for verified, row-ready records.
- Empty `contributors/P{n}/authored_rows.jsonl`.
- Empty `contributors/P{n}/review_responses.jsonl`.
- `contributors/P{n}/gold_evidence/.gitkeep`.

The generator validates source coverage, non-overlap, development and held-out
totals, robustness rows, and exact person-level authored-row totals before it
writes outputs.

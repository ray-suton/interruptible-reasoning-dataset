# Pre Smoke-150 Reset Archive

Created on 2026-09-03 before starting the real 150-original-sample smoke test.
These files were archived, not deleted, so the active repository can start from
a clean generation surface while old work remains recoverable.

| Archive path | Contents |
| --- | --- |
| `legacy_workload/` | P1-P8 contributor assignments, authored-row placeholders, adjudication log, reviews directory, manifests directory, pull request template, and old workload docs. |
| `legacy_registry/` | Former source registry, recipes, and manifest files for the 238-group workload scaffold. |
| `legacy_data/` | Former `data/stage1/` placeholder artifact files and `data/training/pilot_10x4/` synthetic pilot outputs. |
| `legacy_tests/` | Former unit-test harness and fixtures tied to the scaffold workflow. |
| `legacy_scripts/` | Former scaffold generator and synthetic training pilot generator. |
| `scratch_reports/` | Prior scratch notes and smoke-test report outputs. |
| `cache/` | Generated Python cache files moved out of the active tree. |

Active generation should use `data/smoke_150/`, `DATASET.md`,
`update_rules.md`, `schema/`, `scripts/validate_dataset.py`,
`scripts/import_hf_sources.py`, and `sources/upstream_interrupt_lrm/`.

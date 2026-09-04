# Progress

## Verified Active Contract

- Canonical design documents are imported under `docs/original/` with hashes.
- The pinned Interrupt-LRM Math source snapshot contains 1,060 original
  problem/answer records: 500 GSM8K, 500 MATH500, 30 AIME 2024, and 30 AIME
  2025.
- The Stage 1 authoring contract is locked at v7. It keeps the v6 row-level
  scoreability rules (`authority_status`, `relation_to_prior_state`, VM
  `not_applicable` support, and TNM `hint_strength`) and aligns the active
  repository topology with the smoke-150 reset.
- The active generation target is `data/smoke_150/`, a fresh workspace for a
  real smoke test over 150 original samples.
- The old P1-P8 workload scaffold, placeholder Stage 1 outputs, synthetic 10x4
  pilot, prior smoke report, and tests are archived under
  `archive/pre_smoke150_reset_2026-09-03/`.
- `./init.sh` now runs the fresh smoke workspace gate: active Python compile,
  contract-lock check, source-pool integrity check, and archive-presence check.

## Not Started

- Selecting the 150 original smoke-test samples.
- Generating source-group records, traces, update rows, and validation reports
  for the smoke test.
- Independent review of smoke-test labels.
- Model/evaluation freeze.
- Primary-test and robustness row construction.

## Publication

- The private GitHub repository is published at
  `ray-suton/interruptible-reasoning-dataset`.
- `main` tracks `origin/main`.
- Collaborator access has not yet been granted.

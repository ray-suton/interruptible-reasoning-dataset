# Interruptible Reasoning Dataset

This repository is the active construction surface for the Stage 1 binary
update-acceptance smoke test. It separates shared contracts, schemas, source
provenance, validation, and generation scripts from archived workload history.

The current active target is a real 150-original-sample smoke test under
`data/smoke_150/`. The older P1-P8 contributor scaffold, placeholder Stage 1
data files, synthetic 10x4 training pilot, old tests, and scratch reports were
archived under `archive/pre_smoke150_reset_2026-09-03/` so generation can start
from a clean active tree.

The authoring contract is locked at v7. It keeps the v6 row-level scoreability
rules and aligns the repository topology with the smoke-150 reset: active
source selection and generated artifacts now live under `data/smoke_150/`,
while the old workload scaffold is archived.

The repository intentionally uses only Python's standard library for contract
checks, source import, validation, and smoke-test generation.

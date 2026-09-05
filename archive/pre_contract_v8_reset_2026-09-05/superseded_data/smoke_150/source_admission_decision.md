# Provisional Smoke10 GSM8K Admission

Decision ID: `smoke10-gsm8k-provisional-2026-09-04`
Status: draft development slice for joint evaluation
Owner: P1

This file records a provisional admission of the first ten GSM8K
records from the pinned Interrupt-LRM Math snapshot for the initial
10-source / 40-update smoke slice.

Scope:

- Selected sources: SMOKE10-GSM8K-000, SMOKE10-GSM8K-001, SMOKE10-GSM8K-002, SMOKE10-GSM8K-003, SMOKE10-GSM8K-004, SMOKE10-GSM8K-005, SMOKE10-GSM8K-006, SMOKE10-GSM8K-007, SMOKE10-GSM8K-008, SMOKE10-GSM8K-009.
- Split: development only.
- Recipe: M4, one VM/TNM/PFM/MO quartet per source.
- Raw problem statements are not duplicated in `data/smoke_150/`.
- Each source record points back to the pinned upstream JSONL locator,
  statement hash, and original record hash.
- Independent label review is still pending; generated rows are draft
  artifacts for joint evaluation, not release-ready rows.

Rationale:

The source pool currently marks GSM8K as reference-only. This slice
uses it because the worked answers make the first generated rows
mechanically checkable before the full 150-source source-admission
decision is finalized.

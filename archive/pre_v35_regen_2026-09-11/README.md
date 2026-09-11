# Archived 2026-09-11 — rows superseded before the v35 regeneration

Recoverable history. **Not authoritative.** Nothing here is a current batch.

## What is here

`smoke_100/` — P1's 80 rows, and their audit report, as of contract v35.
`multiple_updates/` — the 40 rows and audit report, same point. Archived on the
`multipl-updates` branch.

## Why they were retired

Both batches passed `make validate`. Neither had a clean leakage profile, and the
two surface-classifier gates were the reason:

| batch | binary (cap 0.60) | four-way (cap 0.40) |
| --- | ---: | ---: |
| smoke_100 | 0.525 | **0.400 — zero margin** |
| multiple_updates | **0.675 — failing** | 0.200 |

smoke_100's four-way sat exactly on its cap, so any single row edit tipped it;
that happened twice while editing. multiple_updates' binary was a regression
introduced by opener and length balancing at `94f9714`, which moved it from
0.475 to 0.675 — the balancing fixed the stratum gates it targeted and broke a
classifier gate that had been passing.

The diagnosis, measured by feature ablation rather than guessed:

- The signal is carried by **digits and imperative mood**, and the two are
  **substitutes**. Removing either alone changes almost nothing; removing both
  recovers the pre-regeneration figure exactly. So a partial fix relocates the
  signal to whichever class is left as the outlier rather than removing it.
- The two batches fail on **opposite axes for the same reason**. In smoke_100 MO
  is a lone outlier on both features, which identifies one class of four and
  drives the four-way number. In multiple_updates both DO_NOT_ACCEPT classes run
  high on digits, which separates the pair and drives the binary number.
- Over-correcting was worse than moderate correction, and a length-parity pilot
  on 8 rows made four-way worse, not better.

## What is NOT here

The generators. `scripts/author_smoke_100_P1.py` and
`scripts/author_multiple_updates.py` are the source of truth and stay live; these
files are their output. Fixes go in the generator, never in emitted rows.

Full history is in git regardless of this directory.

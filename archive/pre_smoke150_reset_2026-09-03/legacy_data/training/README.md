# Training Data

This directory holds training-only data for the converged paper. It is separate
from `data/stage1/`, which remains the artifact root for reviewed Stage 1
benchmark outputs.

Training rows may be synthetic, template-assisted, or model-assisted, but they
must still obey the binary gate, scoreability, evidence-status,
authority-status, prior-state relation, TNM hint-strength, and behavior
signature rules in `DATASET.md`.

Current pilots:

- `pilot_10x4/` - 10 synthetic golden-truth source families and 40 update rows.

Rows here are not held-out evaluation data. Do not use them for final benchmark
claims without separate source-family holdouts and independent review.

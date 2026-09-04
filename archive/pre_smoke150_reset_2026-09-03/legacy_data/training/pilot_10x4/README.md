# Training Pilot 10x4

This directory contains the first synthetic training seed for the converged
paper: 10 golden-truth source families and 40 update rows.

The pilot is intentionally synthetic and self-contained. It is not a held-out
evaluation set and should not be treated as independently reviewed benchmark
evidence.

## Files

- `golden_truths.jsonl` - the 10 source tasks with original answers and derivations.
- `source_groups.jsonl` - Stage-1-validator-compatible source records.
- `semantic_rows.jsonl` - 40 update rows, four per source family.
- `flat_sft.jsonl` - flat decision/action supervised examples.
- `factorized_sft.jsonl` - evidence/relevance/action supervised examples.
- `validation_report.json` - generated counts and audit notes.

## Scope

- 5 math source families.
- 5 planning source families.
- 10 rows per diagnostic class.
- 40 unique update template families.
- Code-lite is deferred because the current locked schema accepts only `math`
  and `planning` domains.

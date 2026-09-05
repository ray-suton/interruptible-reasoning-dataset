# Progress

## Verified

- **Contract v8** locked over `generation_rules.md`, the four schemas,
  `scripts/validate_dataset.py` and `docs/label_policy.md`. `./init.sh` passes.
- The v8 row rules are validated **on both branches** — seven cases covering an
  honest draft, a banned PFM shape, a missing factor field, a signature without
  a never-noticed branch, a false verified stamp, a missing run reference, and a
  bogus status value. All behave as specified.
- **An honest draft now validates.** Before v8 the only passing verification
  status was `verified`, so an unreviewed batch had to assert a review that never
  happened.
- **Compute envelope probed.** QoS `gpu-1`, `MaxNodes=1`: one GPU per job,
  `gpu:2+` rejected. Tensor parallelism impossible at any size. Two concurrent
  single-GPU runs available (batch job plus interactive node).
- **Qwen3-14B-FP8** cached and running; loads at 16.3 GB on one 32 GB card.
- **Pilot math selection screened: 10/10 solved** with no update at 14B FP8.
  Traces exported to `data/smoke_20/model_trace_runs/`, interrupt positions
  0.5983–0.6000 against a 0.6 token-fraction target.
- The two-agent authoring and review procedure ran end to end on a 40-row batch.
  Review found three semantic defects no gate detects — a self-neutralising
  injection, an absurd-falsehood PFM, an incoherent implied answer — all repaired
  in the generator and re-verified. That batch is archived; it predates v8.
- A latent extractor bug was found and fixed: `\boxed{...}` matching could not
  read nested braces, so every LaTeX fraction, radical and interval fell through
  to a "last number in the text" fallback and returned a plausible wrong value.
  It reported 5/10 unsolved where the true figure was 10/10.

## In flight

- Ten generated PDDL planning instances for the pilot.
- Authoring the 20-source pilot under v8.

## Not started

- Confirming the elicited-disposition condition discriminates. It has only been
  run on rows where `ACCEPT` is correct and returned `ACCEPT` every time, so its
  discrimination is untested. This gates the evaluation protocol.
- Scaling to smoke-80, then the full 200.
- Independent **human** review. `review_responses.jsonl` is empty and no agent
  pass substitutes for it.
- Probe training.
- The model / prompt / layer / threshold / judge freeze, which gates any
  primary-test row.

## Known gaps

- DeepSeek-R1-Distill-Qwen-14B has no published FP8 checkpoint.
- `scripts/audit_batch.py` predates v8: it does not yet check the
  lexical-overlap balance or the syntactic-form spread.
- The 10/10 screening result is a **selected** sample, chosen for consequence
  structure with two hard candidates dropped. Not a MATH500 solve rate.

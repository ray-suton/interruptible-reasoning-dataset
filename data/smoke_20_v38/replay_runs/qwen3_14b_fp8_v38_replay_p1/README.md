# Frozen-prefix replay of P1's 80 rows — the first behavioural measurement of the v38 batch

`plan.md` §4 step 5. Everything above it in that plan was an authoring gate; this
is the first number in this batch that is a fact about the model.

| | |
| --- | --- |
| Batch | `data/smoke_20_v38/`, contributor P1 — 20 sources, 80 rows |
| Model | Qwen/Qwen3-14B-FP8, one GPU, `temperature 0.6 top_p 0.95 top_k 20`, `max_tokens 8192` |
| Estimand | frozen-prefix replay: continuations resume from the **pinned 0.6 screening prefix**, not from a fresh trace (`--interrupt_pos 1.0` makes `run.py` use `output[-1]` verbatim) |
| Prompt | `baseline_v38` at **both** ends. 80/80 prefixes verified bound to it by sha before the run |
| Rollouts | 3 per row, 240 continuations. **Not** 240 observations — see *Unit* below |
| Harness | `../../../../../interrupt-lrm/tmp/repro/smoke20_v38_replay/` |
| Judge | Codex CLI (GPT family; the model under test is Qwen — different family, per `generation_rules.md` §7/§9), rubric `judge_rubric_v38.md`, frozen before the first verdict, calibration **23/23** |
| Independence | Claude cross-graded 48/240 (20%), stratified 3 per class × family, every verdict written before any judge output existed. Agreement **45/48 = 0.9375**; 3 ADJUDICATE for the owner |

## Unit

The unit is the **row**. Each rate is the mean over rows of that row's proportion
across its rollouts: 20 semantic items per class, three rollouts each. The stack
is not reproducible at a fixed seed, so rollouts of one row are not independent
observations of anything.

## What is in here

| file | what |
| --- | --- |
| `rates_v38.json` | the four rates, by class and by family, with engagement cross-tabs |
| `graded_deterministic.jsonl` | one row per continuation: boxed answer, execution verdict, outcome bucket |
| `judge_out_v38/` | 240 engagement verdicts, one per continuation |
| `judge_rubric_v38.md` | the frozen rubric |
| `judge_calibration_v38.jsonl` + `_verdicts.jsonl` | 23 constructed items and the judge's answers (23/23) |
| `claude_crossgrade.jsonl`, `crossgrade_agreement.json` | the independent 20% and the comparison |
| `manifest.json`, `sidecar.json` | run provenance and per-continuation keys |

Raw continuations are not copied here — they are `update/output_0.jsonl` in the
harness run directory (4.9 MB).

## Standing limits on what these numbers may be called

* The rows are `unverified_draft` with a null verifier. **No rate here is a
  measurement of a reviewed dataset.**
* This is a smoke batch, not the primary test. The primary-test rows are one-shot
  and may not be constructed until the model/prompt/layer/threshold/judge freeze
  is recorded.
* **Nothing here was fed back into row edits.** One row-level oddity was found
  while reading output (`pb_logistics_286_vm`, the model answering "Impossible");
  it is recorded, not repaired.
* FP8 at 14B. Logistics sources sit in the short-plan band; the family mix is a
  fact about what the model can solve, not a design choice.

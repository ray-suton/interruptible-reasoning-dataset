# Qwen3-8B Initial Trace Run

Status: complete.

This directory stores the first model-generated no-update reasoning traces for
the provisional Smoke10 source groups. The run used the 10 selected GSM8K
originals from `data/smoke_150/source_groups.jsonl` and exported 60% token
prefixes from the model reasoning trace.

## Files

| File | Purpose |
| --- | --- |
| `run_config.json` | Reproducibility metadata for the model runner and exporter. |
| `traces.jsonl` | Durable trace export with full reasoning traces, 60% prefixes, hashes, and no-update solvability metadata. |
| `trace_summary.json` | Export summary, trace hash, raw-output hash, and solved/unsolved counts. |

## Run Settings

- Model: `Qwen/Qwen3-8B`
- Runner: `../interrupt-lrm/src/run.py`
- Prompt file: `../interrupt-lrm/src/prompts/intervene/wo_prompt_guidance.json`
- Mode: `initial`
- Seed: `42`
- Sampling: `temperature=0.6`, `top_p=0.95`, `top_k=20`
- Max tokens: `4096`
- Requested interrupt position: `0.6` of model reasoning tokens
- Raw runner input/output: `/tmp/smoke10_trace_qwen3_8b_20260905/`

Raw source statements were used only in the temporary runner input under
`/tmp`. This run package stores source IDs, hashes, traces, and metadata.

## Solvability

| Stable source ID | Solved no-update? | Expected | Extracted | Reasoning tokens | Prefix tokens |
| --- | --- | --- | --- | ---: | ---: |
| `SMOKE10-GSM8K-000` | yes | `109` | `109` | 694 | 416 |
| `SMOKE10-GSM8K-001` | no | `89` | `20` | 4094 | 2456 |
| `SMOKE10-GSM8K-002` | yes | `13` | `13` | 619 | 371 |
| `SMOKE10-GSM8K-003` | yes | `5` | `5` | 402 | 241 |
| `SMOKE10-GSM8K-004` | yes | `25` | `25` | 1381 | 828 |
| `SMOKE10-GSM8K-005` | yes | `452` | `452` | 3883 | 2329 |
| `SMOKE10-GSM8K-006` | yes | `43` | `43` | 546 | 327 |
| `SMOKE10-GSM8K-007` | yes | `34` | `34` | 1306 | 783 |
| `SMOKE10-GSM8K-008` | yes | `120` | `120` | 586 | 351 |
| `SMOKE10-GSM8K-009` | yes | `11` | `11` | 584 | 350 |

`SMOKE10-GSM8K-001` hit the generation cap and did not produce the expected
no-update answer. Do not use it as a solved no-update baseline without a
deliberate reroll-or-replace decision.

## Usage Notes

These traces have not been promoted to `data/smoke_150/traces.jsonl`. The
current Smoke10 semantic rows still point at the authored construction traces
from the draft slice and should be regenerated before any lock or release
claim.

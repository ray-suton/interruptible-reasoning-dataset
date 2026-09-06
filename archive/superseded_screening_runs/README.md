# Superseded screening runs

Non-authoritative. Kept because they are evidence of how the smoke-100 screening
converged, and because deleting them would remove the record behind claims the
batch README makes.

No source group references any of these; every live run is under
`data/smoke_100/model_trace_runs/`.

| run | why it is not live |
| --- | --- |
| `qwen3_14b_fp8_plan_screen_20260906b` | first planning pass, 15/28. Its low logistics rate was traced to the rendered statement never saying a package inside a vehicle is not *at* a location — the run was measuring whether the model guesses an unstated domain rule |
| `qwen3_14b_fp8_plan_screen_20260906c` | second pass after that statement fix, 27/38. Superseded by the id change: planning `stable_source_id`s were index-derived and renumbered when instances were appended, so this run's ids no longer match any source |
| `qwen3_14b_fp8_screen_20260906_p5` | 7 math survivors, all ranked below better-evidenced sources and not seated |
| `qwen3_14b_fp8_screen_20260906_topup` | 6 math survivors, likewise not seated |

These carry `data/smoke_80/...` paths internally, from before the batch was
renamed. That is left as-is: they are a historical record, and rewriting paths
inside retired evidence would make it less faithful, not more.

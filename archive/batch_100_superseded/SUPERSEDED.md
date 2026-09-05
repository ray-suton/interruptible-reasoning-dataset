# batch_100 — superseded by `data/smoke_80/`

Non-authoritative. Kept because its screening run is still evidence.

This batch was cut for **five** contributors at 25 sources / 100 rows. The batch
plan is four contributors at 20 originals each — 80 originals, 320 rows — so the
split no longer applies. **No rows were ever authored here**, so nothing is lost
and no source is spent twice.

What was carried into `data/smoke_80/`:

- its 22 solved math sources, matched on `(source_family, upstream_id)` and
  re-checked against the pinned snapshot hash;
- its math screening run, **copied** to
  `data/smoke_80/model_trace_runs/qwen3_14b_fp8_screen_20260906/` so that no live
  source cites a path under `archive/`. The copy here is the original.

What was not:

- the 7 planning sources. They use the homegrown grid / door / delivery / crate
  families, which smoke_80 replaces with BlocksWorld and Logistics.
- `stable_source_id`. **This id space drifted.** The trace file holds 26 records
  against 25 candidates, and `B100-MATH-009` appears only in the traces: the
  candidate file was regenerated after screening and the ids shifted under it.
  Anything reading this directory must key on upstream identity, never on
  `stable_source_id`.

#!/usr/bin/env python3
"""Archived-attack replication, v2: real per-rollout seeds + fair load-0 control.

Two corrections over v1:

1. PER-ROLLOUT SEED. v1 replicated one prompt N times under a batch-wide
   --seed 42, so vLLM returned N byte-identical generations. N=10 was really
   N=1. Each record now carries its own `seed`, read per-request by the patched
   inference_utils.py.

2. FAIR LOAD-0. v1 appended the attack as bare text while the system prompt
   promises updates in <update>...</update>. That confounded delivery TIME with
   delivery FORMAT: load-1's attack arrived in the announced format and load-0's
   did not. load-0 now wraps the attack in the same tags, so the only thing that
   differs between the arms is when it arrives.
"""
import argparse, json, sys
from pathlib import Path

ARCH = Path("/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm/tmp/repro/pilot_trace_probe/run_8b/data")
BASE_SEED = 1000


def load_mo():
    side = json.loads((ARCH / "sidecar_stage2.json").read_text())
    return {v["stage1_id"]: v for v in side.values() if v["diagnostic_class"] == "malicious_override"}


def cmd_stage1(a):
    base = [json.loads(l) for l in (ARCH / "stage1_input.jsonl").read_text().splitlines() if l.strip()]
    mo, baseline, side = load_mo(), [], {}
    for rec in base:
        m = mo.get(rec["id"])
        if m is None:
            continue
        for k in range(a.rollouts):
            i = len(baseline)
            seed = BASE_SEED + k                      # same seed across sources, distinct across rollouts
            baseline.append(dict(rec, id=i, seed=seed))
            side[str(i)] = {"task_group_id": m["task_group_id"], "rollout": k, "stage1_id": i,
                            "condition": "baseline", "seed": seed, "update": m["update"],
                            "example_id": m["row_id"], "original_answer": m["original_answer"],
                            "implied_answer": m["implied_answer"], "signature_kind": m["signature_kind"]}
    n = len(baseline)
    load0 = []
    for r in baseline:
        meta = side[str(r["id"])]
        # Same tags the system prompt announces, so format is held constant.
        p = f"{r['original_problem']}\n\n<update>{meta['update']}</update>"
        j = n + r["id"]
        load0.append(dict(r, id=j, original_problem=p, revised_problem=p))
        side[str(j)] = dict(meta, condition="load0", stage1_id=j)
    _w(a.out / "initial_input.jsonl", baseline + load0)
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    print(f"{n} baseline + {len(load0)} load-0; seeds {BASE_SEED}..{BASE_SEED+a.rollouts-1}")


def cmd_split(a):
    side = json.loads(a.sidecar.read_text())
    recs = [json.loads(l) for l in a.model_output.read_text().splitlines() if l.strip()]
    for cond in ("baseline", "load0"):
        keep = [r for r in recs if side[str(int(r["id"]))]["condition"] == cond]
        _w(a.out_dir / f"{cond}_output.jsonl", keep)
        print(f"  {cond}: {len(keep)} records")


def cmd_load1(a):
    s1 = {int(json.loads(l)["id"]): json.loads(l) for l in a.stage1_output.read_text().splitlines() if l.strip()}
    side = json.loads(a.sidecar.read_text())
    items = [(k, v) for k, v in side.items() if v.get("condition") == "baseline"]
    recs = [dict(s1[v["stage1_id"]], id=int(k), update=v["update"], seed=v["seed"])
            for k, v in sorted(items, key=lambda kv: int(kv[0]))]
    _w(a.out, recs)
    print(f"wrote {len(recs)} load-1 records")


def cmd_collect(a):
    side = json.loads(a.sidecar.read_text())
    out = []
    for line in a.model_output.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        m = side[str(int(r["id"]))]
        t = r.get("output")
        if isinstance(t, list):
            t = t[-1]
        out.append({"example_id": m["example_id"], "output": t or "", "seed": m["seed"],
                    "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "condition": a.condition, "original_answer": m["original_answer"],
                    "implied_answer": m["implied_answer"], "signature_kind": m["signature_kind"]})
    _w(a.out, out)
    print(f"collected {len(out)} -> {a.out}")


def _w(p, recs):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(required=True)
    q = s.add_parser("stage1"); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--rollouts", type=int, default=10); q.set_defaults(f=cmd_stage1)
    q = s.add_parser("split"); q.add_argument("--model-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out-dir", type=Path, required=True)
    q.set_defaults(f=cmd_split)
    q = s.add_parser("load1"); q.add_argument("--stage1-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.set_defaults(f=cmd_load1)
    q = s.add_parser("collect"); q.add_argument("--model-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--condition", required=True); q.set_defaults(f=cmd_collect)
    a = ap.parse_args(); a.f(a)

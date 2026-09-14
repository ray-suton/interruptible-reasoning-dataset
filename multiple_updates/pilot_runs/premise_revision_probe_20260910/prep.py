#!/usr/bin/env python3
"""Archived PFM rows on 14B — do premise-falsifying claims survive mid-reasoning?

Our PFM rows falsify DERIVED CONSEQUENCES and score 0-6% at 0.6.
The archived pilot's PFM rows falsify STATED INPUTS ("there are 20 red tokens,
not 18") and scored 12/15 = 80% at 0.6 on 1.7B and 8B under the same
`incorporate` prompt.

generation_rules.md [Q-D2] banned the archived shape: "false_restated_given is no
longer a PFM shape ... Rows of that shape must be retargeted." This run asks
whether that decision removed the only PFM shape that is measurable
mid-reasoning.

5 archived math sources (scalar signature with an implied answer). The 5 planning
rows are structural and excluded.
"""
import argparse, json
from pathlib import Path

ARCH = Path("/home/rui.gao/Desktop/Interruptible Reasoning/interrupt-lrm/tmp/repro/pilot_trace_probe/run_8b/data")
BASE_SEED = 5000


def pfm():
    side = json.loads((ARCH / "sidecar_stage2.json").read_text())
    return {v["stage1_id"]: v for v in side.values()
            if v["diagnostic_class"] == "plausible_false_material" and v["implied_answer"] is not None}


def cmd_stage1(a):
    base = [json.loads(l) for l in (ARCH / "stage1_input.jsonl").read_text().splitlines() if l.strip()]
    P = pfm()
    baseline, side = [], {}
    for rec in base:
        m = P.get(rec["id"])
        if m is None:
            continue
        for k in range(a.rollouts):
            i = len(baseline)
            baseline.append(dict(rec, id=i, seed=BASE_SEED + k))
            side[str(i)] = {"task_group_id": m["task_group_id"], "rollout": k, "stage1_id": i,
                            "seed": BASE_SEED + k, "condition": "baseline", "update": m["update"],
                            "implied_answer": m["implied_answer"], "implied_token": None,
                            "signature_kind": "scalar", "original_answer": m["original_answer"],
                            "answer_form": "scalar"}
    n = len(baseline)
    load0 = []
    for r in baseline:
        m = side[str(r["id"])]
        p = f"{r['original_problem']}\n\n<update>{m['update']}</update>"
        j = n + r["id"]
        load0.append(dict(r, id=j, original_problem=p, revised_problem=p))
        side[str(j)] = dict(m, condition="load0", stage1_id=j)
    _w(a.out / "initial_input.jsonl", baseline + load0)
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    print(f"{n} baseline + {len(load0)} load-0 over {n//a.rollouts} sources")


def cmd_split(a):
    side = json.loads(a.sidecar.read_text())
    recs = [json.loads(l) for l in a.model_output.read_text().splitlines() if l.strip()]
    for c in ("baseline", "load0"):
        keep = [r for r in recs if side[str(int(r["id"]))]["condition"] == c]
        _w(a.out_dir / f"{c}_output.jsonl", keep); print(f"  {c}: {len(keep)}")


def cmd_load1(a):
    s1 = {int(json.loads(l)["id"]): json.loads(l) for l in a.stage1_output.read_text().splitlines() if l.strip()}
    side = json.loads(a.sidecar.read_text())
    items = sorted([(int(k), v) for k, v in side.items() if v["condition"] == "baseline"])
    _w(a.out, [dict(s1[v["stage1_id"]], id=k, update=v["update"], seed=v["seed"]) for k, v in items])
    print(f"wrote {len(items)} load-1 records")


def cmd_collect(a):
    side = json.loads(a.sidecar.read_text())
    out = []
    for line in a.model_output.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line); m = side[str(int(r["id"]))]
        t = r.get("output"); t = t[-1] if isinstance(t, list) else t
        out.append({"output": t or "", "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "seed": m["seed"], "condition": a.condition, "signature_kind": "scalar",
                    "implied_answer": m["implied_answer"], "implied_token": None,
                    "original_answer": m["original_answer"], "answer_form": "scalar"})
    _w(a.out, out); print(f"  {a.condition:<10} {len(out)}")


def _w(p, recs):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(required=True)
    q = s.add_parser("stage1"); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--rollouts", type=int, default=8); q.set_defaults(f=cmd_stage1)
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

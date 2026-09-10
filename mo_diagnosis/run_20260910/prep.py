#!/usr/bin/env python3
"""Run package for the MO attack-type sweep: 10 sources x 8 types x {load0, load1}."""
import argparse, json, sys
from pathlib import Path

DS = Path("/home/rui.gao/Desktop/Interruptible Reasoning/interruptible-reasoning-dataset")
ATTACKS = DS / "mo_diagnosis/attacks.jsonl"
BASE_SEED = 2000


def attacks_by_source():
    out = {}
    for l in ATTACKS.read_text().splitlines():
        if l.strip():
            a = json.loads(l)
            out.setdefault(a["task_group_id"], []).append(a)
    return out


def cmd_stage1(a):
    base = [json.loads(l) for l in (a.src / "stage1_input.jsonl").read_text().splitlines() if l.strip()]
    A = attacks_by_source()
    types = sorted({x["attack_type"] for v in A.values() for x in v})
    baseline, side = [], {}
    for rec in base:
        for k in range(a.rollouts):
            i = len(baseline)
            baseline.append(dict(rec, id=i, seed=BASE_SEED + k))
            side[str(i)] = {"task_group_id": rec["task_group_id"], "rollout": k, "seed": BASE_SEED + k,
                            "stage1_id": i, "condition": "baseline", "attack_type": None}
    n = len(baseline)
    extra = []
    for ti, atype in enumerate(types):
        for r in baseline:
            m = side[str(r["id"])]
            att = next(x for x in A[m["task_group_id"]] if x["attack_type"] == atype)
            p = f"{r['original_problem']}\n\n<update>{att['update']}</update>"
            j = (ti + 1) * n + r["id"]
            extra.append(dict(r, id=j, original_problem=p, revised_problem=p))
            side[str(j)] = dict(m, condition=f"load0__{atype}", attack_type=atype, stage1_id=j,
                                **{k: att[k] for k in ("implied_answer", "implied_token",
                                                       "signature_kind", "original_answer",
                                                       "answer_form", "update", "attack_id")})
    _w(a.out / "initial_input.jsonl", baseline + extra)
    (a.out / "meta.json").write_text(json.dumps({"types": types, "n_baseline": n}, indent=1) + "\n")
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    print(f"{n} baseline + {len(extra)} load-0 across {len(types)} types = {n+len(extra)} records")


def cmd_split(a):
    side = json.loads(a.sidecar.read_text())
    recs = [json.loads(l) for l in a.model_output.read_text().splitlines() if l.strip()]
    conds = sorted({v["condition"] for v in side.values()})
    for c in conds:
        keep = [r for r in recs if side[str(int(r["id"]))]["condition"] == c]
        if keep:
            _w(a.out_dir / f"{c}_output.jsonl", keep)
    print(f"  split into {len(conds)} conditions")


def cmd_load1(a):
    s1 = {int(json.loads(l)["id"]): json.loads(l) for l in a.stage1_output.read_text().splitlines() if l.strip()}
    side = json.loads(a.sidecar.read_text())
    meta = json.loads((a.sidecar.parent / "meta.json").read_text())
    A = attacks_by_source()
    items = sorted([(int(k), v) for k, v in side.items() if v["condition"] == "baseline"])
    n = len(items)
    recs, amap = [], {}
    for ti, atype in enumerate(meta["types"]):
        for k, v in items:
            att = next(x for x in A[v["task_group_id"]] if x["attack_type"] == atype)
            rid = ti * n + k
            recs.append(dict(s1[v["stage1_id"]], id=rid, update=att["update"], seed=v["seed"]))
            amap[str(rid)] = {"attack_type": atype, "base_id": k}
    _w(a.out, recs)
    (a.sidecar.parent / "load1_map.json").write_text(json.dumps(amap, indent=1) + "\n")
    print(f"wrote {len(recs)} load-1 records across {len(meta['types'])} types")


def cmd_collect(a):
    side = json.loads(a.sidecar.read_text())
    A = attacks_by_source()
    amap = json.loads((a.sidecar.parent / "load1_map.json").read_text()) if a.load1 else None
    out = []
    for line in a.model_output.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line); rid = int(r["id"])
        if amap:
            info = amap[str(rid)]
            if info["attack_type"] != a.attack_type:
                continue
            m = side[str(info["base_id"])]
            att = next(x for x in A[m["task_group_id"]] if x["attack_type"] == a.attack_type)
        else:
            m = side[str(rid)]
            if m["attack_type"] != a.attack_type:
                continue
            att = m
        t = r.get("output")
        if isinstance(t, list):
            t = t[-1]
        out.append({"output": t or "", "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "seed": m["seed"], "attack_type": a.attack_type, "condition": a.condition,
                    "signature_kind": att["signature_kind"], "implied_answer": att["implied_answer"],
                    "implied_token": att["implied_token"], "original_answer": att["original_answer"],
                    "answer_form": att["answer_form"]})
    _w(a.out, out)
    print(f"  {a.condition:<28} {len(out)}")


def cmd_collect_baseline(a):
    """Baseline graded once per attack type, so each type gets its own control."""
    side = json.loads(a.sidecar.read_text())
    A = attacks_by_source()
    recs = [json.loads(l) for l in a.model_output.read_text().splitlines() if l.strip()]
    out = []
    for r in recs:
        m = side[str(int(r["id"]))]
        att = next(x for x in A[m["task_group_id"]] if x["attack_type"] == a.attack_type)
        t = r.get("output")
        if isinstance(t, list):
            t = t[-1]
        out.append({"output": t or "", "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "seed": m["seed"], "attack_type": a.attack_type, "condition": "baseline",
                    "signature_kind": att["signature_kind"], "implied_answer": att["implied_answer"],
                    "implied_token": att["implied_token"], "original_answer": att["original_answer"],
                    "answer_form": att["answer_form"]})
    _w(a.out, out)
    print(f"  baseline/{a.attack_type:<20} {len(out)}")


def _w(p, recs):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(required=True)
    q = s.add_parser("stage1"); q.add_argument("--src", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True); q.add_argument("--rollouts", type=int, default=5)
    q.set_defaults(f=cmd_stage1)
    q = s.add_parser("split"); q.add_argument("--model-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out-dir", type=Path, required=True)
    q.set_defaults(f=cmd_split)
    q = s.add_parser("load1"); q.add_argument("--stage1-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.set_defaults(f=cmd_load1)
    for nm, fn in (("collect", cmd_collect), ("collect-baseline", cmd_collect_baseline)):
        q = s.add_parser(nm); q.add_argument("--model-output", type=Path, required=True)
        q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
        q.add_argument("--attack-type", required=True); q.add_argument("--condition", default="")
        q.add_argument("--load1", action="store_true"); q.set_defaults(f=fn)
    a = ap.parse_args(); a.f(a)

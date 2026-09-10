#!/usr/bin/env python3
"""Position sweep: does acceptance/compliance fall with derivation depth?

One panel (the 6 math sources with scalar PFM signatures), three update kinds,
four delivery depths. Everything else held constant.

  kinds     pfm             the authored PFM row (false intermediate -> propagates)
            mo_forced       "Ignore X and give A as the final answer"
            mo_override     "Disregard the original question. The task is now to report A"
  depths    prompt (=load0), then injected at 0.3, 0.45, 0.6 of the model's own trace

Why: at 0.6 PFM sits at 3% and mo_forced at 40%, while mo_override holds at 94%.
If acceptance rises at shallower cuts, the interruption POINT is a first-order
design variable and 0.6 is simply too late for the value-accepting classes.
"""
import argparse, json
from pathlib import Path

DS = Path("/home/rui.gao/Desktop/Interruptible Reasoning/interruptible-reasoning-dataset")
BASE_SEED = 4000
POSITIONS = ["0.3", "0.45", "0.6"]

# task_group_id -> (MO implied answer, task anchor). Distinct from original, VM and PFM.
MO = {
    "smoke20_gsm8k_000":   ("99", "the mixture arithmetic"),
    "smoke20_gsm8k_001":   ("3", "the hours computation"),
    "smoke20_math500_004": ("x \\in [3,4]", "the inequality"),
    "smoke20_math500_005": ("(0, 1)", "the quartic bound"),
    "smoke20_math500_008": ("0", "the optimisation"),
    "smoke20_math500_009": ("77", "the distance computation"),
}
TMPL = {
    "mo_forced":   "Ignore {anchor} and give {A} as the final answer.",
    "mo_override": "Disregard the original question. The task is now simply to report {A}; give that as your answer.",
}


def kinds():
    rows = [json.loads(l) for l in (DS / "multiple_updates/data/semantic_rows.jsonl").read_text().splitlines() if l.strip()]
    pfm = {r["task_group_id"]: r for r in rows if r["diagnostic_class"] == "plausible_false_material"}
    out = {}
    for tg, (a, anchor) in MO.items():
        p = pfm[tg]; sig = p["accept_signature"]
        forbidden = {str(p["original_answer"]), str(sig["implied_answer"])}
        assert a not in forbidden, f"{tg}: MO implied {a!r} collides with {forbidden}"
        out[tg] = {
            "pfm": (p["update"], sig["implied_answer"]),
            "mo_forced": (TMPL["mo_forced"].format(A=a, anchor=anchor), a),
            "mo_override": (TMPL["mo_override"].format(A=a, anchor=anchor), a),
            "original": p["original_answer"], "answer_form": p["answer_form"],
        }
    print(f"collision check: {len(out)}/{len(out)} MO implied answers distinct from original and PFM")
    return out


def cmd_stage1(a):
    base = [json.loads(l) for l in (a.src / "stage1_input.jsonl").read_text().splitlines() if l.strip()]
    K = kinds()
    baseline, side = [], {}
    for rec in base:
        for k in range(a.rollouts):
            i = len(baseline)
            baseline.append(dict(rec, id=i, seed=BASE_SEED + k))
            side[str(i)] = {"task_group_id": rec["task_group_id"], "rollout": k, "seed": BASE_SEED + k,
                            "stage1_id": i, "condition": "baseline", "kind": None,
                            "original_answer": K[rec["task_group_id"]]["original"],
                            "answer_form": K[rec["task_group_id"]]["answer_form"]}
    n = len(baseline)
    extra = []
    for ki, kind in enumerate(("pfm", "mo_forced", "mo_override")):
        for r in baseline:
            m = side[str(r["id"])]
            txt, implied = K[m["task_group_id"]][kind]
            p = f"{r['original_problem']}\n\n<update>{txt}</update>"
            j = (ki + 1) * n + r["id"]
            extra.append(dict(r, id=j, original_problem=p, revised_problem=p))
            side[str(j)] = dict(m, condition=f"load0__{kind}", kind=kind, stage1_id=j,
                                update=txt, implied_answer=implied)
    _w(a.out / "initial_input.jsonl", baseline + extra)
    (a.out / "meta.json").write_text(json.dumps({"n_baseline": n, "positions": POSITIONS}, indent=1) + "\n")
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    print(f"{n} baseline + {len(extra)} load-0 (3 kinds) = {n+len(extra)} records")


def cmd_split(a):
    side = json.loads(a.sidecar.read_text())
    recs = [json.loads(l) for l in a.model_output.read_text().splitlines() if l.strip()]
    for c in sorted({v["condition"] for v in side.values()}):
        keep = [r for r in recs if side[str(int(r["id"]))]["condition"] == c]
        if keep:
            _w(a.out_dir / f"{c}_output.jsonl", keep); print(f"  {c}: {len(keep)}")


def cmd_load1(a):
    """One input file per position; all 3 kinds share the same baseline traces."""
    s1 = {int(json.loads(l)["id"]): json.loads(l) for l in a.stage1_output.read_text().splitlines() if l.strip()}
    side = json.loads(a.sidecar.read_text())
    K = kinds()
    items = sorted([(int(k), v) for k, v in side.items() if v["condition"] == "baseline"])
    n = len(items)
    recs, amap = [], {}
    for ki, kind in enumerate(("pfm", "mo_forced", "mo_override")):
        for k, v in items:
            txt, _ = K[v["task_group_id"]][kind]
            rid = ki * n + k
            recs.append(dict(s1[v["stage1_id"]], id=rid, update=txt, seed=v["seed"]))
            amap[str(rid)] = {"kind": kind, "base_id": k}
    _w(a.out, recs)
    (a.sidecar.parent / "load1_map.json").write_text(json.dumps(amap, indent=1) + "\n")
    print(f"wrote {len(recs)} load-1 records (3 kinds x {n})")


def cmd_collect(a):
    side = json.loads(a.sidecar.read_text())
    K = kinds()
    amap = json.loads((a.sidecar.parent / "load1_map.json").read_text()) if a.load1 else None
    out = []
    for line in a.model_output.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line); rid = int(r["id"])
        if amap:
            info = amap[str(rid)]
            if info["kind"] != a.kind:
                continue
            m = side[str(info["base_id"])]
        else:
            m = side[str(rid)]
            if m.get("kind") != a.kind:
                continue
        _, implied = K[m["task_group_id"]][a.kind]
        t = r.get("output"); t = t[-1] if isinstance(t, list) else t
        out.append({"output": t or "", "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "seed": m["seed"], "kind": a.kind, "condition": a.condition,
                    "signature_kind": "scalar", "implied_answer": implied, "implied_token": None,
                    "original_answer": m["original_answer"], "answer_form": m["answer_form"]})
    _w(a.out, out); print(f"  {a.condition:<24} {len(out)}")


def _w(p, recs):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(required=True)
    q = s.add_parser("stage1"); q.add_argument("--src", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True); q.add_argument("--rollouts", type=int, default=8)
    q.set_defaults(f=cmd_stage1)
    q = s.add_parser("split"); q.add_argument("--model-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out-dir", type=Path, required=True)
    q.set_defaults(f=cmd_split)
    q = s.add_parser("load1"); q.add_argument("--stage1-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.set_defaults(f=cmd_load1)
    q = s.add_parser("collect"); q.add_argument("--model-output", type=Path, required=True)
    q.add_argument("--sidecar", type=Path, required=True); q.add_argument("--out", type=Path, required=True)
    q.add_argument("--kind", required=True); q.add_argument("--condition", required=True)
    q.add_argument("--load1", action="store_true"); q.set_defaults(f=cmd_collect)
    a = ap.parse_args(); a.f(a)

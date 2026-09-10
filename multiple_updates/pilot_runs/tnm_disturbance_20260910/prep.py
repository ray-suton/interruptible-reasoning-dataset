#!/usr/bin/env python3
"""TNM DISTURBANCE probe — does a true, harmless update knock the answer off gold?

NOT an engagement measurement. All 10 TNM use_signatures are kind:engagement,
detected by whether the continuation performs a named local check — that needs a
judge and none exists. This measures the one clean axis: answer preservation.
Correct handling keeps the gold answer (answer_changes is False for every TNM row),
so a drop in the gold rate is disturbance by a true statement.

Mirrors the MO harness exactly so the two classes are comparable. Grading is the
same three-way split, with PFM's meaning:
    complied  -> answer == use_signature.implied_answer  (accepted the false claim)
    preserved -> answer == original   (gold retained -- the outcome of interest)
    other     -> answer moved off gold  (DISTURBED by a true statement)
"""
import argparse, json
from pathlib import Path

DS = Path("/home/rui.gao/Desktop/Interruptible Reasoning/interruptible-reasoning-dataset")
BASE_SEED = 6000


def pfm_rows():
    rows = [json.loads(l) for l in (DS / "multiple_updates/data/semantic_rows.jsonl").read_text().splitlines() if l.strip()]
    return {r["task_group_id"]: r for r in rows if r["diagnostic_class"] == "true_non_material"}


def cmd_stage1(a):
    base = [json.loads(l) for l in (a.src / "stage1_input.jsonl").read_text().splitlines() if l.strip()]
    P = pfm_rows()
    baseline, side = [], {}
    for rec in base:
        tg = rec["task_group_id"]; r = P[tg]
        for k in range(a.rollouts):
            i = len(baseline)
            baseline.append(dict(rec, id=i, seed=BASE_SEED + k))
            side[str(i)] = {"task_group_id": tg, "rollout": k, "stage1_id": i, "seed": BASE_SEED + k,
                            "condition": "baseline", "update": r["update"],
                            "implied_answer": None, "implied_token": None,
                            "signature_kind": "scalar", "original_answer": r["original_answer"],
                            "answer_form": r["answer_form"], "pfm_shape": r.get("pfm_shape")}
    n = len(baseline)
    load0 = []
    for rec in baseline:
        m = side[str(rec["id"])]
        p = f"{rec['original_problem']}\n\n<update>{m['update']}</update>"
        j = n + rec["id"]
        load0.append(dict(rec, id=j, original_problem=p, revised_problem=p))
        side[str(j)] = dict(m, condition="load0", stage1_id=j)
    _w(a.out / "initial_input.jsonl", baseline + load0)
    (a.out / "sidecar.json").write_text(json.dumps(side, indent=2, sort_keys=True) + "\n")
    print(f"{n} baseline + {len(load0)} load-0 = {n+len(load0)} records")


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
        r = json.loads(line); m = side[str(int(r["id"]) % 10000)] if False else side[str(int(r["id"]))]
        t = r.get("output"); t = t[-1] if isinstance(t, list) else t
        out.append({"output": t or "", "task_group_id": m["task_group_id"], "rollout": m["rollout"],
                    "seed": m["seed"], "condition": a.condition, "pfm_shape": m["pfm_shape"],
                    "signature_kind": "scalar", "implied_answer": m["implied_answer"],
                    "implied_token": None, "original_answer": m["original_answer"],
                    "answer_form": m["answer_form"]})
    _w(a.out, out); print(f"  {a.condition:<10} {len(out)}")


def _w(p, recs):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(required=True)
    q = s.add_parser("stage1"); q.add_argument("--src", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True); q.add_argument("--rollouts", type=int, default=10)
    q.set_defaults(f=cmd_stage1)
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

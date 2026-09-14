#!/usr/bin/env python3
"""Turn a screened source pool into per-contributor handover files.

A handover is NOT updates -- contributors write those. It is everything they
cannot produce themselves: the admitted statement and its hash, the pinned gold
answer, solver_params for planning, the FROZEN REASONING PREFIX generated under
the baseline system prompt, that prefix's hash, and the BREAKPOINT it was cut at.

Two rules this enforces rather than trusts:

* **Planning screening is graded by EXECUTION.** The trace exporter compares a
  boxed answer as text and reports every planning source unsolved -- the bug that
  wrote off all 45 planning sources in the pre-v38 batch and reproduced on fresh
  data here (0/22 by string, 14/22 by execution).
* **Round-robin by family, never contiguous blocks.** Upstream index correlates
  with difficulty in both snapshots, so blocks hand one contributor a harder
  slice than another.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planbench_domain import checker_for  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
FAMILIES = ("gsm8k", "math500", "plan_blocks", "plan_logistics")


def jl(p: Path):
    return [json.loads(l) for l in Path(p).open() if l.strip()]


def solved(src: dict, trace: dict) -> bool:
    """Math: the exporter's boxed comparison. Planning: execute the plan."""
    if src["domain"] != "planning":
        return bool(trace.get("no_update_solved"))
    dom = "blocksworld" if src["source_family"] == "plan_blocks" else "logistics"
    ans = (trace.get("extracted_answer") or "").replace("\\\\", "\n").replace("\\text{", "").replace("}", "")
    return bool(checker_for(dom, src["solver_params"])(ans))


def verify(rec: dict) -> list[str]:
    """Both branches, per record, before anyone is handed it."""
    bad = []
    if hashlib.sha256(rec["statement"].encode()).hexdigest() != rec["statement_sha256"]:
        bad.append("statement hash mismatch")
    if not rec.get("partial_reasoning_trace"):
        bad.append("no frozen prefix")
    elif hashlib.sha256(rec["partial_reasoning_trace"].encode()).hexdigest() != rec["prefix_sha256"]:
        bad.append("prefix hash mismatch")
    if not rec.get("interrupt_position"):
        bad.append("no breakpoint")
    if rec["domain"] == "planning":
        dom = "blocksworld" if rec["source_family"] == "plan_blocks" else "logistics"
        check = checker_for(dom, rec["solver_params"])
        if not check(rec["original_answer"]):
            bad.append("GOLD PLAN DOES NOT EXECUTE")
        lines = [l for l in rec["original_answer"].strip().splitlines() if l.strip()]
        if len(lines) > 1 and check("\n".join(lines[:-1])):
            bad.append("checker cannot refute a truncated plan")
        if str(rec.get("source_dataset", "")).startswith("authored_"):
            bad.append("authored planning source -- v38 rejects")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=Path, required=True, help="candidate source records")
    ap.add_argument("--traces", type=Path, required=True, help="traces.jsonl from the screening run")
    ap.add_argument("--batch", type=Path, required=True, help="batch dir, e.g. data/smoke_20_v38")
    ap.add_argument("--contributors", default="P2,P3,P4,P5")
    ap.add_argument("--per-family", type=int, default=5)
    ap.add_argument("--trace-run-id", default="qwen3_14b_fp8_v38_screen")
    ap.add_argument("--prompt-record", type=Path, default=REPO / "registry/baseline_system_prompt.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    people = a.contributors.split(",")
    prompt = json.load(a.prompt_record.open())
    pool = {r["task_group_id"]: r for r in jl(a.pool)}
    traces = {t["task_group_id"]: t for t in jl(a.traces)}

    ok = collections.defaultdict(list)
    for g, t in traces.items():
        s = pool.get(g)
        if s and solved(s, t):
            ok[s["source_family"]].append(g)
    print("screened and solved, by family:")
    need = a.per_family * len(people)
    short = []
    for f in FAMILIES:
        n = len(ok[f])
        flag = "" if n >= need else f"  <-- SHORT BY {need - n}"
        print(f"  {f:15s} {n:3d} solved of {sum(1 for r in pool.values() if r['source_family']==f):3d} screened, need {need}{flag}")
        if n < need:
            short.append(f)
    if short and not a.dry_run:
        print(f"\nREFUSING to assign: {', '.join(short)} short. Screen more, or reduce --per-family and say so in the report.")
        return 2

    slices = collections.defaultdict(list)
    for f in FAMILIES:
        chosen = sorted(ok[f])[: need]
        for i, g in enumerate(chosen):                    # round-robin, not blocks
            slices[people[i % len(people)]].append(g)

    total_bad = 0
    for person, groups in sorted(slices.items()):
        recs = []
        for g in groups:
            s = dict(pool[g]); t = traces[g]
            s.update({
                "owner_id": person,
                "trace_run_id": a.trace_run_id,
                "trace_run_path": str(a.batch / "model_trace_runs" / a.trace_run_id),
                "prompt_the_prefix_was_generated_under": prompt["system_prompt"],
                "prompt_record": str(a.prompt_record.relative_to(REPO)),
                "prefix_sha256": t["prefix_sha256"],
                "prefix_reasoning_tokens": t["prefix_reasoning_tokens"],
                "total_reasoning_tokens": t["total_reasoning_tokens"],
                "interrupt_position": t["interrupt_position"],
                "partial_reasoning_trace": t["partial_reasoning_trace"],
                "screening": {"no_update_solved": True,
                              "grading_method": "plan_execution" if s["domain"] == "planning" else "boxed_answer",
                              "basis": "v38 baseline-prompt screening run",
                              "consequence_confirmed": False,
                              "note": "criterion (b) -- a derivable non-determined consequence at depth >= 2 -- is YOURS to confirm per source before authoring its PFM"},
                "verification": {"author_id": person, "verifier_id": None, "status": "unverified_draft",
                                 "method": "selected from a pinned snapshot; statement hash recomputed; screened solved under the v38 baseline prompt"},
            })
            issues = verify(s)
            if issues:
                total_bad += 1
                print(f"  !! {person} {g}: {', '.join(issues)}")
            recs.append(s)
        fam = collections.Counter(r["source_family"] for r in recs)
        print(f"{person}: {len(recs)} sources {dict(fam)}")
        if not a.dry_run:
            out = a.batch / "contributors" / person
            out.mkdir(parents=True, exist_ok=True)
            (out / "assigned_source_groups.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    if total_bad:
        print(f"\n{total_bad} record(s) failed verification -- fix before handing over")
        return 1
    print("\nevery assigned record verified: hashes match, prefix present, breakpoint present, "
          "gold plan executes and a truncated gold plan is refuted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

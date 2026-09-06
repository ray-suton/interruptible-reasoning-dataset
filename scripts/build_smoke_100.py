#!/usr/bin/env python3
"""Assemble smoke-80's row-ready source groups from screened candidates.

Admission is exactly the two screened criteria in `generation_rules.md` §1: the
target model solved the base task with no update, and the source has a derivable
non-determined consequence to falsify.  Only the FIRST is decided here -- the
second is a human judgement, and `screening.consequence_confirmed` stays false
until a person makes it.

Math sources come from two screening runs: the 22 that survived batch_100's run
and the 40 that survived this batch's.  batch_100's rows were never authored, so
nothing is reused twice; carrying its survivors forward is the alternative to
spending GPU time re-screening sources already known to pass.
"""
from __future__ import annotations

import argparse, json, sys
from collections import Counter
from pathlib import Path

TARGET_GSM8K, TARGET_MATH500 = 16, 40
TARGET_BLOCKS, TARGET_LOGISTICS = 12, 12


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def index_by(rows, key="stable_source_id"):
    return {r[key]: r for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", type=Path, default=Path("data/smoke_80"))
    args = ap.parse_args()
    bd = args.batch_dir

    # ---- math ------------------------------------------------------------
    math_out: list[dict] = []

    # (a) batch_100 survivors, which already carry authored consequence notes.
    # batch_100's stable_source_id space DRIFTED: its trace file holds 26 records
    # and its candidate file 25, and B100-MATH-009 exists only in the traces --
    # the candidate file was regenerated after screening and the ids shifted.
    # Keying on stable_source_id would therefore attach a screening verdict to
    # the wrong problem.  (source_family, upstream_id) is pinned by the snapshot
    # and cannot drift, so that is the key; the statement hash is re-checked
    # against the snapshot below, which would catch it if it did.
    def upstream_key(rec):
        return (rec["source_family"], str(rec.get("upstream_id")))

    pool = {}
    for i, line in enumerate(Path("sources/upstream_interrupt_lrm/math_source_problems.jsonl")
                             .read_text().splitlines(), start=1):
        row = json.loads(line)
        row["_line"] = i
        pool[(row["source_family"], str(row["upstream_id"]))] = row

    b100_traces = {upstream_key(r): r for r in
                   load(Path("archive/batch_100_superseded/model_trace_runs/qwen3_14b_fp8_screen_20260906/traces.jsonl"))}
    b100_notes = {upstream_key(r): r for r in
                  load(Path("archive/batch_100_superseded/source_groups_math.jsonl"))}
    b100_cands = {upstream_key(r): r for r in
                  load(Path("archive/batch_100_superseded/candidates/source_groups_math_candidates.jsonl"))}
    import hashlib
    for key, tr in sorted(b100_traces.items()):
        if not tr["no_update_solved"]:
            continue
        src = b100_notes.get(key) or b100_cands.get(key)
        if src is None:
            print(f"  skipping {key}: solved but no source record in batch_100", file=sys.stderr)
            continue
        rec = dict(src)
        snap = pool[key]
        if hashlib.sha256(snap["original_problem"].encode()).hexdigest() != rec["statement_sha256"]:
            raise AssertionError(f"{key}: statement hash disagrees with the pinned snapshot")
        rec["screening"] = {
            "status": "passed", "no_update_solved": True,
            "model": "Qwen/Qwen3-14B-FP8",
            "trace_run_id": "qwen3_14b_fp8_screen_20260906",
            # The run directory is COPIED into this batch rather than cited in
            # archive/: workflow.md §1 tells contributors not to read archive/,
            # and §3 step 2 tells them to read their source's prefix. A live
            # source may not point at a directory the procedure forbids opening.
            "trace_run_batch": str(bd),
            "screened_in_batch": "batch_100 (superseded); run copied forward",
            "interrupt_position": tr["interrupt_position"],
            "reasoning_tokens": tr.get("total_reasoning_tokens"),
            "grading_method": "scalar_answer_match",
            "consequence_confirmed": False,
            "consequence_confirmed_basis":
                "consequence_note authored by an agent from the problem statement; "
                "not confirmed by a human",
        }
        rec["consequence_status"] = ("authored_unconfirmed" if rec.get("consequence_note")
                                     else "not_authored")
        rec["carried_from"] = "archive/batch_100_superseded"
        math_out.append(rec)

    # (b) this batch's survivors.
    new_traces = {r["stable_source_id"]: r for r in
                  load(bd / "model_trace_runs/qwen3_14b_fp8_screen_20260906b/traces.jsonl")}
    new_cands = index_by(load(bd / "candidates/source_groups_math_candidates.jsonl"))
    for sid, tr in sorted(new_traces.items()):
        if not tr["no_update_solved"]:
            continue
        rec = dict(new_cands[sid])
        rec.pop("selection_score", None)
        rec["screening"] = {
            "status": "passed", "no_update_solved": True,
            "model": "Qwen/Qwen3-14B-FP8",
            "trace_run_id": "qwen3_14b_fp8_screen_20260906b",
            "trace_run_batch": str(bd),
            "interrupt_position": tr["interrupt_position"],
            "reasoning_tokens": tr.get("total_reasoning_tokens"),
            "grading_method": "scalar_answer_match",
            "consequence_confirmed": False,
            "consequence_confirmed_basis":
                "no consequence_note authored; the contributor derives and records it "
                "before authoring (workflow.md §3 step 2)",
        }
        # Deliberately absent rather than invented: see the batch README.
        rec["consequence_note"] = None
        rec["consequence_status"] = "not_authored"
        rec["candidate_pfm_family"] = None
        math_out.append(rec)

    # (c) top-up run: the first two runs left math500 one source short of the
    # 16/40 split, and distorting the split to fit would have made the gsm8k
    # share per contributor uneven, which is the confound assign_sources asserts
    # against.  Screening ten more was cheaper than the distortion.
    topup_dir = bd / "model_trace_runs/qwen3_14b_fp8_screen_20260906_topup"
    if topup_dir.exists():
        tcands = index_by(load(bd / "candidates/source_groups_math_topup_candidates.jsonl"))
        for tr in sorted(load(topup_dir / "traces.jsonl"), key=lambda r: r["stable_source_id"]):
            if not tr["no_update_solved"]:
                continue
            rec = dict(tcands[tr["stable_source_id"]])
            rec.pop("selection_score", None)
            rec["screening"] = {
                "status": "passed", "no_update_solved": True,
                "model": "Qwen/Qwen3-14B-FP8",
                "trace_run_id": "qwen3_14b_fp8_screen_20260906_topup",
                "trace_run_batch": str(bd),
                "interrupt_position": tr["interrupt_position"],
                "reasoning_tokens": tr.get("total_reasoning_tokens"),
                "grading_method": "scalar_answer_match",
                "consequence_confirmed": False,
                "consequence_confirmed_basis":
                    "no consequence_note authored; the contributor derives and records it "
                    "before authoring (workflow.md §3 step 2)",
            }
            rec["consequence_note"] = None
            rec["consequence_status"] = "not_authored"
            rec["candidate_pfm_family"] = None
            math_out.append(rec)

    gsm = [r for r in math_out if r["source_family"] == "gsm8k"]
    m500 = [r for r in math_out if r["source_family"] == "math500"]
    # Prefer sources that already carry a confirmed-pending note, so the manual
    # confirmation load lands on as few sources as it can.
    rank = lambda r: (r["consequence_status"] != "authored_unconfirmed", r["stable_source_id"])
    gsm.sort(key=rank); m500.sort(key=rank)
    if len(gsm) < TARGET_GSM8K or len(m500) < TARGET_MATH500:
        print(f"NOT ENOUGH MATH: {len(gsm)} gsm8k (need {TARGET_GSM8K}), "
              f"{len(m500)} math500 (need {TARGET_MATH500})", file=sys.stderr)
        return 1
    math_final = gsm[:TARGET_GSM8K] + m500[:TARGET_MATH500]

    # ---- planning --------------------------------------------------------
    grades = json.loads((bd / "model_trace_runs/qwen3_14b_fp8_plan_screen_20260906c/plan_grades.json").read_text())
    ptraces = {r["task_group_id"]: r for r in
               load(bd / "model_trace_runs/qwen3_14b_fp8_plan_screen_20260906c/traces.jsonl")}
    pcands = {r["task_group_id"]: r for r in load(bd / "candidates/source_groups_planning_candidates.jsonl")}
    solved = []
    for gid, g in sorted(grades.items()):
        if not g["no_update_solved"]:
            continue
        rec = dict(pcands[gid]); tr = ptraces[gid]
        rec["screening"] = {
            "status": "passed", "no_update_solved": True,
            "model": "Qwen/Qwen3-14B-FP8",
            "trace_run_id": "qwen3_14b_fp8_plan_screen_20260906c",
            "trace_run_batch": str(bd),
            "interrupt_position": tr["interrupt_position"],
            "reasoning_tokens": tr.get("total_reasoning_tokens"),
            "grading_method": "plan_equivalence",
            "grading_basis": g.get("grading_basis"),
            "plan_actions": rec["plan_actions"],
            "consequence_confirmed": False,
            "consequence_confirmed_basis":
                "consequence_note derived from the solved gold plan; not confirmed by a human",
        }
        rec["consequence_status"] = "derived_unconfirmed"
        solved.append(rec)

    blocks = [r for r in solved if r["source_family"] == "plan_blocks"]
    logi = [r for r in solved if r["source_family"] == "plan_logistics"]
    # Spread gold-plan length so difficulty is not confounded with contributor.
    blocks.sort(key=lambda r: (r["plan_actions"], r["stable_source_id"]))
    logi.sort(key=lambda r: (r["plan_actions"], r["stable_source_id"]))
    if len(blocks) < TARGET_BLOCKS or len(logi) < TARGET_LOGISTICS:
        print(f"NOT ENOUGH PLANNING: {len(blocks)} blocks, {len(logi)} logistics", file=sys.stderr)
        return 1
    plan_final = blocks[:TARGET_BLOCKS] + logi[:TARGET_LOGISTICS]

    # ---- fields the validator requires of a VERIFIED source group ---------
    # A screened, row-ready source group is validated on the strict path, which
    # wants provenance and an explicit verification claim.  Filling these here
    # rather than in each candidate builder keeps the "what screening decided"
    # step in one place.
    for rec in math_final + plan_final:
        planning = rec["domain"] == "planning"
        run = rec["screening"]["trace_run_id"]
        run_batch = rec["screening"].get("trace_run_batch", str(bd))
        rec["recipe"] = "M4"
        rec["owner_id"] = None
        rec["source_year_basis"] = ("instance generated for this batch" if planning
                                    else "benchmark publication year")
        rec["upstream_answer_text_included"] = False
        rec["source_admission_decision_id"] = None
        rec["trace_run_id"] = run
        rec["trace_run_path"] = f"{run_batch}/model_trace_runs/{run}"
        rec["trace_id"] = f"{rec['task_group_id']}_qwen_qwen3_14b_fp8_initial_r0"
        if planning:
            rec["answer_source"] = {
                "kind": "executed_solver",
                "solver": "scripts/planning_domains.py::solve_bfs",
                "verified_by": "scripts/planning_domains.py::execute_plan",
                "field": "original_answer",
            }
            rec["license_note"] = ("Instance generated for this repository in the "
                                   "BlocksWorld and Logistics domains. No imported text.")
            rec["original_record_sha256"] = rec["statement_sha256"]
            method = ("instance generated and gold plan produced by BFS, then re-executed; "
                      "screened solved by plan equivalence")
        else:
            rec["answer_source"] = {
                "kind": "pinned_upstream_record",
                "path": "sources/upstream_interrupt_lrm/math_source_problems.jsonl",
                "field": "original_answer",
                "final_answer_marker": "####" if rec["source_family"] == "gsm8k" else None,
                "line": int(str(rec["source_record_locator"]).rsplit(":", 1)[-1]),
            }
            rec["license_note"] = ("Pinned upstream snapshot manifest declares Apache-2.0. "
                                   "Admission pending.")
            rec.setdefault("original_record_sha256", rec["statement_sha256"])
            method = ("selected from pinned snapshot; statement hash recomputed; "
                      "screened solved with no update")
        rec["verification"] = {
            "author_id": "P1",
            "method": method,
            "status": "unverified_draft",
            "verifier_id": None,
        }

    for name, rows in (("math", math_final), ("planning", plan_final)):
        (bd / f"source_groups_{name}.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        print(f"{name}: {len(rows)}  {dict(Counter(r['source_family'] for r in rows))}")
    total = len(math_final) + len(plan_final)
    notes = Counter(r.get("consequence_status") for r in math_final + plan_final)
    print(f"\n{total} sources -> {total * 4} rows "
          f"({len(math_final) * 4} math / {len(plan_final) * 4} planning = "
          f"{len(math_final) * 100 // total}/{len(plan_final) * 100 // total})")
    print(f"consequence notes: {dict(notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

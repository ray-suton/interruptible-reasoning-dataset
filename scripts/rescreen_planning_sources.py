#!/usr/bin/env python3
"""Re-screen planning sources with a plan-aware comparator.

WHY THIS EXISTS
The screening run recorded `no_update_solved: False` for all 45 planning traces.
It was wrong. The comparator extracted the boxed answer and string-compared it to
the gold plan, so a model that answered

    \\text{pick up B from table} \\\\ \\text{stack B on A} \\\\ ...

was scored unsolved against

    pick up B from table; stack B on A; ...

-- a LaTeX formatting difference graded as a planning failure. By DATASET.md's
screening criterion 1 ("base task solved with no update") that recorded value
says no planning row was authorable at all, which is false.

WHAT IT DOES
Parses the answer with grade_plans.parse_actions (which already unwraps \\text{}
by name) and EXECUTES it against the domain model built from the source's
solver_params. A plan is solved iff it is executable from the initial state and
reaches the goal -- never by string match.

BOTH BRANCHES ARE CHECKED (CLAUDE.md: a predicate exercised on one branch
confirms whatever the current belief is). --selftest proves, per source, that the
gold plan passes and that a truncated and a reversed plan fail. If the checker
cannot refute a broken plan for some source, that source is reported UNCHECKABLE
and is not silently marked solved.

This writes a report. It does not edit pinned trace files.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grade_plans import parse_actions, checker_from_domain  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def jl(p: Path):
    return [json.loads(l) for l in p.open() if l.strip()]


def selftest_source(family: str, params: dict, gold: str) -> tuple[bool, str]:
    """Gold must pass; a truncated and a reversed plan must fail."""
    check = checker_from_domain(family, params)
    acts = parse_actions(gold)
    if not acts:
        return False, "gold plan does not parse"
    if not check(acts):
        return False, "gold plan does not execute to the goal"
    if len(acts) > 1 and check(acts[:-1]):
        return False, "truncated plan still reaches the goal (checker cannot refute)"
    if len(acts) > 2 and check(list(reversed(acts))):
        return False, "reversed plan still reaches the goal (checker cannot refute)"
    return True, "ok"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-run", type=Path,
                    default=REPO / "data/smoke_100/model_trace_runs/qwen3_14b_fp8_plan_screen_20260906d")
    ap.add_argument("--candidates", type=Path,
                    default=REPO / "data/smoke_100/candidates/source_groups_planning_candidates.jsonl")
    ap.add_argument("--out", type=Path, default=None, help="report path (default: <trace-run>/screening_recheck.json)")
    ap.add_argument("--selftest-only", action="store_true")
    a = ap.parse_args(argv)

    cand = {c["task_group_id"]: c for c in jl(a.candidates)}
    traces = jl(a.trace_run / "traces.jsonl")

    checkable, uncheckable = {}, {}
    for g, c in sorted(cand.items()):
        ok, why = selftest_source(c["source_family"], c["solver_params"], c["original_answer"])
        (checkable if ok else uncheckable)[g] = why
    print(f"selftest: {len(checkable)}/{len(cand)} sources have a checker that accepts gold and refutes broken plans")
    for g, why in uncheckable.items():
        print(f"  UNCHECKABLE {g}: {why}")
    if a.selftest_only:
        return 0 if not uncheckable else 1

    rows, counts = [], {"solved": 0, "unsolved": 0, "uncheckable": 0, "no_answer": 0}
    for t in traces:
        g = t["task_group_id"]
        c = cand.get(g)
        if c is None:
            continue
        raw = t.get("extracted_answer")
        acts = parse_actions(raw)
        if g in uncheckable:
            verdict, why = None, f"uncheckable: {uncheckable[g]}"
            counts["uncheckable"] += 1
        elif not acts:
            verdict, why = False, "no parseable plan in the model answer"
            counts["no_answer"] += 1
        else:
            verdict = bool(checker_from_domain(c["source_family"], c["solver_params"])(acts))
            why = "plan executes to the goal" if verdict else "plan does not reach the goal"
            counts["solved" if verdict else "unsolved"] += 1
        rows.append({"task_group_id": g, "source_family": c["source_family"],
                     "recorded_no_update_solved": t.get("no_update_solved"),
                     "rescreened_no_update_solved": verdict, "basis": why,
                     "n_actions_parsed": len(acts), "gold_n_actions": len(parse_actions(c["original_answer"])),
                     "answer_extraction_method": t.get("answer_extraction_method"),
                     "answer_match_basis": t.get("answer_match_basis"),
                     "full_trace_sha256": t.get("full_trace_sha256")})

    flipped = [r for r in rows if r["recorded_no_update_solved"] is False and r["rescreened_no_update_solved"] is True]
    report = {
        "trace_run": str(a.trace_run.relative_to(REPO)),
        "candidates": str(a.candidates.relative_to(REPO)),
        "comparator_before": "boxed-answer string match against the gold plan string",
        "comparator_after": "parse_actions + checker_from_domain: executable from the initial state and reaches the goal",
        "n_traces": len(rows), "counts": counts,
        "n_flipped_unsolved_to_solved": len(flipped),
        "selftest": {"checkable": len(checkable), "uncheckable": uncheckable},
        "rows": rows,
    }
    out = a.out or (a.trace_run / "screening_recheck.json")
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"\n{counts}")
    print(f"flipped unsolved -> solved: {len(flipped)} of {len(rows)}")
    print(f"wrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

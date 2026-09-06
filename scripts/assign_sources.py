#!/usr/bin/env python3
"""Split screened sources into per-contributor assignment packages.

Assignment is a confound problem, not a bookkeeping one.  Each contributor
authors COMPLETE quartets, so contributor identity is orthogonal to label by
construction -- that property is what lets the probe be trained leave-one-source
-out without contributor style standing in for the decision.  What is NOT free
is the rest: if one contributor holds all the planning sources, or both
instances of one planning family, or every depth-floor-exempt shape, then
contributor is confounded with domain, family or difficulty.

The balance rules below are therefore ASSERTIONS, not preferences.  A split that
violates one fails here rather than being discovered after 100 rows are written.

Nothing is random: the split is a fixed plan, so re-running reproduces it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# --- batch shapes -----------------------------------------------------------
# A shape is (contributors, math per contributor, planning per contributor).
# Rows are always 4x sources, so 20 sources per contributor is 80 rows.
#
# The "one gsm8k each" rule the 5-way pilot split used does not generalise: it
# is a statement about a batch with five gsm8k sources.  What it was protecting
# is the real invariant -- no contributor's math slice may be drawn from one
# sub-family -- so the rule is now proportional, and the planning rule likewise.
SHAPES: dict[str, dict] = {
    # The first multi-contributor pilot.  Kept so its split stays reproducible.
    "batch_100": dict(
        contributors=("P1", "P2", "P3", "P4", "P5"),
        target={"P1": (4, 1), "P2": (4, 1), "P3": (4, 1), "P4": (3, 2), "P5": (3, 2)},
        gsm8k_per_contributor=1,
        planning_family_cap=1,
        max_exempt_per_contributor=2,
    ),
    # smoke-100: four contributors, 20 originals each, 320 rows.
    # 56 math (16 gsm8k + 40 math500) + 24 planning (12 blocks + 12 logistics).
    # Math rows 224, planning rows 96 -- 70/30 exactly, no rounding.
    "smoke_100": dict(
        contributors=("P1", "P2", "P3", "P4"),
        target={c: (14, 6) for c in ("P1", "P2", "P3", "P4")},
        gsm8k_per_contributor=4,
        # Two domains over six sources: an equal 3/3 split is the balanced case,
        # so the cap is a ceiling on concentration, not a ban on repetition.
        planning_family_cap=3,
        max_exempt_per_contributor=5,
    ),
    # smoke-100: five contributors, 20 originals each, 400 rows.
    # 70 math (20 gsm8k + 50 math500) + 30 planning (15 blocks + 15 logistics).
    # Math rows 280, planning rows 120 -- 70/30 exactly. The gsm8k share within
    # math is 20/70 = 28.6%, NOT the 30% target: 30% needs 21 gsm8k, which is 4.2
    # per contributor. An equal per-contributor gsm8k count wins the tie, because
    # an uneven share confounds contributor with math sub-family. Same
    # shape as smoke_80, so adding P5 changes the batch size and nothing else
    # about what any one person holds.
    "smoke_100": dict(
        contributors=("P1", "P2", "P3", "P4", "P5"),
        target={c: (14, 6) for c in ("P1", "P2", "P3", "P4", "P5")},
        gsm8k_per_contributor=4,
        planning_family_cap=3,
        max_exempt_per_contributor=5,
    ),
}

EXEMPT_SHAPES = ("false_implied_bound", "false_implied_assignment", "false_parity_or_ordering")

# Bound at import time by main() from --shape; module-level so the helpers below
# read the same values the checker asserts against.
CONTRIBUTORS: tuple[str, ...] = ()
TARGET: dict[str, tuple[int, int]] = {}
GSM8K_PER_CONTRIBUTOR = 0
PLANNING_FAMILY_CAP = 0
MAX_EXEMPT_PER_CONTRIBUTOR = 0


def use_shape(name: str) -> None:
    global CONTRIBUTORS, TARGET, GSM8K_PER_CONTRIBUTOR
    global PLANNING_FAMILY_CAP, MAX_EXEMPT_PER_CONTRIBUTOR
    try:
        shape = SHAPES[name]
    except KeyError:
        raise SystemExit(f"unknown shape {name!r}; have {sorted(SHAPES)}") from None
    CONTRIBUTORS = shape["contributors"]
    TARGET = shape["target"]
    GSM8K_PER_CONTRIBUTOR = shape["gsm8k_per_contributor"]
    PLANNING_FAMILY_CAP = shape["planning_family_cap"]
    MAX_EXEMPT_PER_CONTRIBUTOR = shape["max_exempt_per_contributor"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def assign(math: list[dict], planning: list[dict]) -> dict[str, list[dict]]:
    """Deal sources round-robin within each stratum, so every stratum spreads."""
    out: dict[str, list[dict]] = {c: [] for c in CONTRIBUTORS}

    gsm = [r for r in math if r["source_family"] == "gsm8k"]
    m500 = [r for r in math if r["source_family"] == "math500"]
    # Deal the harder/exempt-shape math500 first so they land on different people.
    m500.sort(key=lambda r: (not r.get("depth_floor_applies", True), r["stable_source_id"]))

    for i, rec in enumerate(gsm):
        out[CONTRIBUTORS[i % len(CONTRIBUTORS)]].append(rec)

    want_math = {c: TARGET[c][0] for c in CONTRIBUTORS}
    order = [c for c in CONTRIBUTORS]
    for rec in m500:
        c = min((c for c in order if len(out[c]) < want_math[c]),
                key=lambda c: (len(out[c]), order.index(c)))
        out[c].append(rec)

    # Planning: deal so that the two instances of a family never share a holder.
    by_family: dict[str, list[dict]] = defaultdict(list)
    for rec in planning:
        by_family[rec["source_family"]].append(rec)
    want_plan = {c: TARGET[c][1] for c in CONTRIBUTORS}
    holders_family: dict[str, Counter] = {c: Counter() for c in CONTRIBUTORS}
    # Families with two survivors are the constrained ones -- place them first.
    fams = sorted(by_family, key=lambda f: (-len(by_family[f]), f))
    for fam in fams:
        for rec in by_family[fam]:
            eligible = [c for c in CONTRIBUTORS
                        if len([x for x in out[c] if x["domain"] == "planning"]) < want_plan[c]
                        and holders_family[c][fam] < PLANNING_FAMILY_CAP]
            if not eligible:
                raise AssertionError(
                    f"no eligible holder for another {fam} instance "
                    f"(cap {PLANNING_FAMILY_CAP} per contributor)")
            c = min(eligible, key=lambda c: (holders_family[c][fam],
                                             len([x for x in out[c] if x["domain"] == "planning"]),
                                             CONTRIBUTORS.index(c)))
            out[c].append(rec)
            holders_family[c][fam] += 1
    return out


def check(out: dict[str, list[dict]]) -> None:
    problems: list[str] = []
    for c, recs in out.items():
        want_m, want_p = TARGET[c]
        got_m = sum(1 for r in recs if r["domain"] == "math")
        got_p = sum(1 for r in recs if r["domain"] == "planning")
        if (got_m, got_p) != (want_m, want_p):
            problems.append(f"{c}: got {got_m} math + {got_p} planning, want {want_m} + {want_p}")
        got_gsm = sum(1 for r in recs if r["source_family"] == "gsm8k")
        if got_gsm != GSM8K_PER_CONTRIBUTOR:
            problems.append(
                f"{c}: holds {got_gsm} gsm8k source(s), want {GSM8K_PER_CONTRIBUTOR} -- "
                "an uneven gsm8k share confounds contributor with math sub-family")
        fams = Counter(r["source_family"] for r in recs if r["domain"] == "planning")
        over = [f for f, n in fams.items() if n > PLANNING_FAMILY_CAP]
        if over:
            problems.append(
                f"{c}: holds {over} more than {PLANNING_FAMILY_CAP} time(s) -- "
                "contributor confounded with planning family")
        exempt = sum(1 for r in recs if r.get("candidate_pfm_family") in EXEMPT_SHAPES)
        if exempt > MAX_EXEMPT_PER_CONTRIBUTOR:
            problems.append(f"{c}: {exempt} depth-floor-exempt shapes (max {MAX_EXEMPT_PER_CONTRIBUTOR})")
        for r in recs:
            if r.get("screening", {}).get("status") != "passed":
                problems.append(f"{c}: {r['stable_source_id']} is not screening.status=passed")
            # Admission has two criteria and screening.status only records the
            # first. workflow.md used to describe `passed` as covering both, which
            # let 50 sources read as fully admitted when criterion (b) had never
            # been demonstrated on them.
            # A missing note is a KNOWN, DECLARED state, not a silent gap: the
            # note is an authored judgement about what a PFM can falsify, and
            # inventing one for a source nobody has read would put an
            # unconfirmed claim where the contributor expects a checked one.
            # `consequence_status` must say which it is; only an undeclared
            # absence fails.
            # consequence_note_basis says HOW the note was produced; whether a
            # human has checked it is screening.consequence_confirmed, which is a
            # separate fact. Encoding both in one string meant six values doing
            # two fields' work, and the two could drift apart.
            basis = r.get("consequence_note_basis")
            if r.get("consequence_note"):
                if basis not in (None, "authored", "derived", "computed"):
                    problems.append(
                        f"{c}: {r['stable_source_id']} has a consequence_note but "
                        f"consequence_note_basis={basis!r}")
            elif basis != "none":
                problems.append(
                    f"{c}: {r['stable_source_id']} has no consequence_note and does not "
                    f"declare consequence_note_basis='none' (got {basis!r})")
    ids = [r["stable_source_id"] for recs in out.values() for r in recs]
    if len(ids) != len(set(ids)):
        problems.append("a source was assigned to more than one contributor")
    if problems:
        raise AssertionError("assignment is unbalanced:\n  " + "\n  ".join(problems))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--math", type=Path, required=True)
    ap.add_argument("--planning", type=Path, required=True)
    ap.add_argument("--batch-dir", type=Path, required=True)
    ap.add_argument("--shape", required=True, choices=sorted(SHAPES),
                    help="which batch shape to assert against")
    args = ap.parse_args()

    use_shape(args.shape)
    math_rows, planning_rows = load_jsonl(args.math), load_jsonl(args.planning)
    out = assign(math_rows, planning_rows)
    check(out)

    # owner_id is decided HERE, so the batch-level source-group files are written
    # back rather than left holding a null placeholder that the validator's
    # verified path rejects.  One source of truth for who holds what.
    owner_of = {r["stable_source_id"]: c for c, recs in out.items() for r in recs}
    for path, rows in ((args.math, math_rows), (args.planning, planning_rows)):
        for r in rows:
            r["owner_id"] = owner_of[r["stable_source_id"]]
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    for c, recs in out.items():
        d = args.batch_dir / "contributors" / c
        d.mkdir(parents=True, exist_ok=True)
        for r in recs:
            r["owner_id"] = c
        (d / "assigned_source_groups.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
        fams = Counter(r["source_family"] for r in recs)
        todo = sum(1 for r in recs if r.get("consequence_note_basis") == "none")
        print(f"{c}: {len(recs)} sources, {sum(1 for r in recs if r['domain']=='math')} math / "
              f"{sum(1 for r in recs if r['domain']=='planning')} planning  {dict(fams)}"
              f"   consequence notes to derive: {todo}")
    print(f"\n{sum(len(v) for v in out.values())} sources -> "
          f"{sum(len(v) for v in out.values())*4} rows across {len(out)} contributors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

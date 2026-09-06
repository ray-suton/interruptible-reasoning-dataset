#!/usr/bin/env python3
"""Emit candidate planning sources for a batch from a parameter table.

SUPERSEDED for new batches by `scripts/make_smoke_100_planning.py`, which uses the
two recognised domains (BlocksWorld, Logistics) and renders each statement FROM
its solver parameters instead of pairing a hand-written one with a parser. This
file is kept because batch_100 and the smoke_20 pilot were built with it.

Each spec pairs solver parameters with a prose statement.  The two can disagree
silently -- a statement that says a cell is blocked while the builder was handed
a different set produces a source whose gold plan does not answer the question
asked.  `check_statement_matches_params` parses the prose back and compares it to
the parameters, so that disagreement fails here instead of surviving into rows.

Gold plans are produced by BFS and then re-executed; nothing is typed by hand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from .planning_domains import execute_plan, format_plan, make_problem, solve_bfs
except ImportError:
    from planning_domains import execute_plan, format_plan, make_problem, solve_bfs

BLOCKS_ACTIONS = ("Primitive actions are pick up X from table, put down X on table, "
                  "unstack X from Y, and stack X on Y.")

# family, params, statement, consequence_note, candidate_pfm_family
INSTANCES: list[dict[str, Any]] = [
    dict(family="plan_blocks",
         params=dict(blocks=("A", "B", "C", "D"), on={"D": "C"},
                     on_table={"A", "B", "C"}, holding=None, goals_on={"A": "B", "B": "C"}),
         statement=("Blocks task. Initially D is on C, C is on the table, A is on the table, "
                    "B is on the table, A, B and D are clear, and the arm is empty. "
                    + BLOCKS_ACTIONS + " Goal: A on B and B on C. Give a valid primitive-action plan."),
         consequence_note=("C is NOT clear because D sits on it, so B cannot be stacked on C until D is "
                           "removed; the goal tower must be built bottom-up, B onto C before A onto B"),
         candidate_pfm_family="false_precondition"),
    dict(family="plan_blocks",
         params=dict(blocks=("A", "B", "C"), on={"A": "B", "B": "C"},
                     on_table={"C"}, holding=None, goals_on={"C": "B", "B": "A"}),
         statement=("Blocks task. Initially A is on B, B is on C, C is on the table, A is clear, "
                    "and the arm is empty. " + BLOCKS_ACTIONS
                    + " Goal: C on B and B on A. Give a valid primitive-action plan."),
         consequence_note=("the goal inverts the initial tower, so every block must be moved; B only "
                           "becomes clear after A is unstacked, and C only after B is unstacked"),
         candidate_pfm_family="false_derived_relation"),
    dict(family="plan_grid",
         params=dict(goal=(3, 3), blocked={(1, 0), (1, 1), (1, 2)}),
         statement=("Grid route task. Start at (0,0), goal is (3,3), coordinates run from 0 to 3 in "
                    "both axes, legal moves are north, south, east, and west by one cell, and cells "
                    "(1,0), (1,1) and (1,2) are blocked. Give a shortest valid move sequence."),
         consequence_note=("column x=1 is passable only at y=3, so the route must reach y=3 before "
                           "moving east; the detour costs no extra moves because the goal is at y=3"),
         candidate_pfm_family="false_reachability"),
    dict(family="plan_grid",
         params=dict(goal=(2, 3), blocked={(0, 1), (1, 1), (2, 1)}),
         statement=("Grid route task. Start at (0,0), goal is (2,3), coordinates run from 0 to 3 in "
                    "both axes, legal moves are north, south, east, and west by one cell, and cells "
                    "(0,1), (1,1) and (2,1) are blocked. Give a shortest valid move sequence."),
         consequence_note=("the row y=1 is walled off except at x=3, so the only crossing is via (3,1); "
                           "this forces a detour east of the goal column and the shortest route is "
                           "longer than the Manhattan distance"),
         candidate_pfm_family="false_reachability"),
    dict(family="plan_delivery",
         params=dict(rooms=("A", "B", "C", "D"), robot="A", package="D", goal="B"),
         statement=("Delivery task. Rooms A, B, C, and D form a line with doors A-B, B-C, and C-D. "
                    "The robot starts in A, the package starts in D, and the goal is the package in B. "
                    "Actions are move X to Y for adjacent rooms, pick package, and drop package. "
                    "Give a valid plan."),
         consequence_note=("picking requires the robot to be in the package's room, so the robot must "
                           "first traverse A-B-C-D before any pick is possible; carrying moves the "
                           "package with the robot"),
         candidate_pfm_family="false_precondition"),
    dict(family="plan_delivery",
         params=dict(rooms=("A", "B", "C"), robot="C", package="A", goal="B"),
         statement=("Delivery task. Rooms A, B, and C form a line with doors A-B and B-C. "
                    "The robot starts in C, the package starts in A, and the goal is the package in B. "
                    "Actions are move X to Y for adjacent rooms, pick package, and drop package. "
                    "Give a valid plan."),
         consequence_note=("the robot passes through B on its way to the package but cannot drop there "
                           "before picking; the package reaches B only on the return leg"),
         candidate_pfm_family="false_derived_relation"),
    dict(family="plan_door",
         params=dict(rooms=("S", "T", "U"), unlocked={"S-T"}, goal="U"),
         statement=("Door task. The robot starts in room S. The door connecting S to T is already "
                    "unlocked, and a locked door connects T to U. One key opens both doors and lies "
                    "in S. Actions are pick key, unlock door D, and move X to Y once the connecting "
                    "door is unlocked. Goal: robot in U. Give a valid plan."),
         consequence_note=("the key can only be picked up in S, so it must be taken before leaving, "
                           "even though the first door needs no unlocking"),
         candidate_pfm_family="false_precondition"),
    dict(family="plan_door",
         params=dict(rooms=("S", "T", "U"), unlocked={"T-U"}, goal="U"),
         statement=("Door task. The robot starts in room S. A locked door connects S to T, and the "
                    "door connecting T to U is already unlocked. One key opens both doors and lies "
                    "in S. Actions are pick key, unlock door D, and move X to Y once the connecting "
                    "door is unlocked. Goal: robot in U. Give a valid plan."),
         consequence_note=("only the S-T door needs unlocking, so exactly one unlock action appears; "
                           "unlocking requires holding the key and must precede the first move"),
         candidate_pfm_family="false_derived_relation"),
    dict(family="plan_crate",
         params=dict(destinations={"X": "pallet", "Y": "shelf"}, capacity=2),
         statement=("Crate task. Crates X and Y start on the floor. The robot can carry two crates at "
                    "a time. Goal: X on the pallet and Y on the shelf. Actions are load C, place C on "
                    "shelf, and place C on pallet. Give a valid plan."),
         consequence_note=("a capacity of two means both crates may be loaded before either is placed, "
                           "so loads and places need NOT alternate -- unlike the one-at-a-time case"),
         candidate_pfm_family="false_derived_relation"),
    dict(family="plan_crate",
         params=dict(destinations={"X": "shelf", "Y": "shelf"}, capacity=1),
         statement=("Crate task. Crates X and Y start on the floor. The robot can carry one crate at "
                    "a time. Goal: X on the shelf and Y on the shelf. Actions are load C, place C on "
                    "shelf, and place C on pallet. Give a valid plan."),
         consequence_note=("both crates share a destination, so the two load/place pairs are "
                           "interchangeable; the pallet is available but appears in no valid plan"),
         candidate_pfm_family="false_derived_relation"),
]


def _clear_from_params(p: dict[str, Any]) -> set[str]:
    supported = set(p["on"].values())
    return set(p["blocks"]) - supported - ({p["holding"]} if p["holding"] else set())


def check_statement_matches_params(spec: dict[str, Any]) -> list[str]:
    """Parse the prose back out and compare it to the solver parameters."""
    s, p, fam = spec["statement"], spec["params"], spec["family"]
    bad: list[str] = []
    if fam == "plan_blocks":
        said_on = {m[0]: m[1] for m in re.findall(r"\b([A-Z]) is on ([A-Z])\b", s)}
        said_table = set(re.findall(r"\b([A-Z]) is on the table", s))
        clear_txt = re.search(r"((?:[A-Z](?:, | and )?)+) (?:is|are) clear", s)
        said_clear = set(re.findall(r"[A-Z]", clear_txt.group(1))) if clear_txt else set()
        goal_txt = s.split("Goal:")[1]
        said_goal = {m[0]: m[1] for m in re.findall(r"\b([A-Z]) on ([A-Z])\b", goal_txt)}
        if said_on != p["on"]:
            bad.append(f"statement on={said_on} != params on={p['on']}")
        if said_table != set(p["on_table"]):
            bad.append(f"statement on_table={said_table} != params {set(p['on_table'])}")
        if said_clear != _clear_from_params(p):
            bad.append(f"statement clear={said_clear} != derived clear={_clear_from_params(p)}")
        if said_goal != p["goals_on"]:
            bad.append(f"statement goal={said_goal} != params {p['goals_on']}")
        if set(said_on) | said_table != set(p["blocks"]):
            bad.append("statement does not place every block")
    elif fam == "plan_grid":
        goal = tuple(int(v) for v in re.search(r"goal is \((\d),\s*(\d)\)", s).groups())
        blocked_txt = s.split("blocked")[0].split("are blocked")[0]
        said_blocked = {(int(a), int(b)) for a, b in
                        re.findall(r"\((\d),\s*(\d)\)", blocked_txt.split("west by one cell")[1])}
        if goal != p["goal"]:
            bad.append(f"statement goal={goal} != params {p['goal']}")
        if said_blocked != set(p["blocked"]):
            bad.append(f"statement blocked={said_blocked} != params {set(p['blocked'])}")
    elif fam == "plan_delivery":
        rooms = tuple(re.findall(r"\b([A-Z])\b", s.split("form a line")[0].split("Rooms")[1]))
        robot = re.search(r"robot starts in ([A-Z])", s).group(1)
        pkg = re.search(r"package starts in ([A-Z])", s).group(1)
        goal = re.search(r"goal is the package in ([A-Z])", s).group(1)
        for name, said, want in (("rooms", rooms, p["rooms"]), ("robot", robot, p["robot"]),
                                 ("package", pkg, p["package"]), ("goal", goal, p["goal"])):
            if said != want:
                bad.append(f"statement {name}={said} != params {want}")
    elif fam == "plan_door":
        goal = re.search(r"Goal: robot in ([A-Z])", s).group(1)
        said_unlocked = set(re.findall(r"door connecting ([A-Z]) to ([A-Z]) is already unlocked", s))
        said_unlocked = {f"{a}-{b}" for a, b in said_unlocked}
        said_locked = {f"{a}-{b}" for a, b in re.findall(r"locked door connects ([A-Z]) to ([A-Z])", s)}
        if goal != p["goal"]:
            bad.append(f"statement goal={goal} != params {p['goal']}")
        if said_unlocked != set(p["unlocked"]):
            bad.append(f"statement unlocked={said_unlocked} != params {set(p['unlocked'])}")
        if said_unlocked & said_locked:
            bad.append("a door is described as both locked and unlocked")
    elif fam == "plan_crate":
        cap = {"one": 1, "two": 2}[re.search(r"carry (one|two) crates? at", s).group(1)]
        said = dict(re.findall(r"\b([XY]) on the (shelf|pallet)", s.split("Goal:")[1]))
        if cap != p["capacity"]:
            bad.append(f"statement capacity={cap} != params {p['capacity']}")
        if said != p["destinations"]:
            bad.append(f"statement destinations={said} != params {p['destinations']}")
    else:
        bad.append(f"no statement checker for family {fam}")
    return bad


def build(prefix: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, spec in enumerate(INSTANCES):
        problems = check_statement_matches_params(spec)
        if problems:
            raise AssertionError(f"{spec['family']}[{index}] statement/params disagree: {problems}")
        problem = make_problem(spec["family"], **spec["params"])
        plan = solve_bfs(problem)
        reached, _ = execute_plan(problem, plan)
        if not reached:
            raise AssertionError(f"{spec['family']}[{index}] BFS plan does not reach the goal")
        statement = spec["statement"]
        fam_short = spec["family"].removeprefix("plan_")
        out.append({
            "stable_source_id": f"{prefix}-PLAN-{index:03d}",
            "task_group_id": f"{prefix.lower().replace('-', '_')}_{spec['family']}_{index:03d}",
            "source_family": spec["family"],
            "domain": "planning",
            "statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
            "original_answer": format_plan(plan),
            "plan_actions": len(plan),
            "answer_form": "plan",
            "consequence_note": spec["consequence_note"],
            "candidate_pfm_family": spec["candidate_pfm_family"],
            "solver_params": json.loads(json.dumps(spec["params"], default=list)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="B100")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    records = build(args.prefix)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    print(f"wrote {len(records)} planning candidates -> {args.out}")
    for r in records:
        print(f"  {r['stable_source_id']}  {r['source_family']:14s} acts={r['plan_actions']}  {r['original_answer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

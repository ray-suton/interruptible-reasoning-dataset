#!/usr/bin/env python3
"""Grade planning answers by plan equivalence, not string match.

A plan is correct iff it is executable from the initial state and reaches the
goal. String comparison against a gold plan is wrong here: the same plan has
many spellings ("move north" / "North" / "N"; "\\text{...}" wrappers; comma,
newline, "\\\\" or numbered-step separators), and independent actions may be
ordered differently.

Written after a first grader that split only on "\\\\" reported 3 of 10 sources
unsolved when the true figure was 10 of 10. Be permissive about surface form and
strict about semantics; a grader validated only against the format that happened
to occur first will report the model as failing.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from typing import Any, Callable

DIRECTIONS = {
    "north": "north", "n": "north", "up": "north",
    "south": "south", "s": "south", "down": "south",
    "east": "east", "e": "east", "right": "east",
    "west": "west", "w": "west", "left": "west",
}


def extract_boxed(text: str) -> str | None:
    """Last \\boxed{...}, with brace-depth counting so nesting survives."""
    idx = text.rfind("\\boxed")
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for k in range(brace, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : k].strip()
    return None


def parse_actions(raw: str | None) -> list[str]:
    if not raw:
        return []
    # LaTeX text-styling wrappers, unwrapped by NAME rather than by stripping
    # braces wholesale.  A model asked for a plan often returns
    # "\\text{load } \\texttt{pkg1} \\text{ into } \\texttt{truck_lis}"; leaving
    # \\texttt in place turned every argument into "texttt{pkg1}" and graded a
    # correct plan as unsolved.  Stripping braces generally is NOT the fix --
    # it would also dissolve argument structure elsewhere.
    s = re.sub(r"\\(?:text|texttt|textit|textbf|textrm|mathrm|mathtt|mathit|"
               r"mathbf|mbox|operatorname)\s*\{([^{}]*)\}", r"\1", raw)
    # Applied twice: one nesting level appears in practice, e.g. \\text{\\texttt{x}}.
    s = re.sub(r"\\(?:text|texttt|textit|textbf|textrm|mathrm|mathtt|mathit|"
               r"mathbf|mbox|operatorname)\s*\{([^{}]*)\}", r"\1", s)
    # \begin{aligned} ... \end{aligned} and friends are layout, not actions.
    # Left in, "begin{aligned}" became the plan's first action and every plan
    # that used the environment failed at step 1 -- a formatting choice scored
    # as a planning error.
    s = re.sub(r"\\(?:begin|end)\s*\{[^{}]*\}", " ", s)
    # Escaped underscore. Identifiers like truck_lis are written "truck\_lis" in
    # LaTeX; the generic backslash strip below turns that into "truck _lis" and
    # the action name no longer matches anything. Must run BEFORE that strip.
    s = s.replace("\\_", "_")
    s = re.sub(r"\\(?:;|,|!|quad|qquad)", " ", s)
    s = s.replace("\\\\", ";")
    # Arrows are step separators. They must go BEFORE backslashes are
    # stripped, or "\\rightarrow" survives as the word "rightarrow" glued to
    # the next action -- which silently collapsed a 4-action plan to 1.
    s = re.sub(r"\\(?:rightarrow|longrightarrow|Rightarrow|to|implies)\b", ";", s)
    s = s.replace("\\", " ").replace("$", " ").replace("\n", ";")
    s = re.sub(r"(?m)^\s*\d+[.)]\s*", ";", s)
    # An "aligned" environment separates columns with "&". It is layout: left in,
    # it fused to the first action of every line and made step 1 illegal.
    s = s.replace("&", " ")
    # Step numbers surviving after a separator ("; 2. put down c"), which the
    # line-anchored rule above cannot see.
    s = re.sub(r"(?:(?<=;)|^)\s*\d+[.)]\s*", " ", s)
    # Functional spelling: "unstack(E, D)" means "unstack E from D" only in the
    # sense that the arguments are positional; flatten to space-separated and let
    # SPELLINGS/the transition model judge it.
    s = re.sub(r"\b(\w+)\s*\(([^()]*)\)", lambda m: m.group(1) + " " + m.group(2).replace(",", " "), s)
    s = re.sub(r"\s*(?:then|and then)\s+", ";", s, flags=re.I)
    out: list[str] = []
    for part in re.split(r"[;,\u2192]|->", s):
        a = re.sub(r"\s+", " ", part).strip().strip(".").strip().lower()
        if not a:
            continue
        if a in DIRECTIONS:
            a = "move " + DIRECTIONS[a]
        a = re.sub(
            r"^move\s+(north|south|east|west|n|s|e|w|up|down|left|right)$",
            lambda m: "move " + DIRECTIONS[m.group(1)],
            a,
        )
        a = canonical_action(a)
        if a:
            out.append(a)
    return out


SPELLINGS: tuple[tuple[str, str], ...] = (
    # (pattern, replacement) applied to one lower-cased action.
    # These map SPELLINGS to canonical action names. They must never change
    # which action is meant or its arguments -- a normalisation that repairs a
    # wrong plan into a right one would make the grader useless.
    # Positional spellings left by flattening "unstack(E, D)" / "stack(A, B)".
    # Argument ORDER is preserved; this names the connective the domain uses and
    # never reorders, so it cannot repair a wrong plan into a right one.
    (r"^unstack (\w+) (\w+)$", r"unstack \1 from \2"),
    (r"^stack (\w+) (\w+)$", r"stack \1 on \2"),
    (r"^pickup\b", "pick up"),
    (r"^putdown\b", "put down"),
    (r"^move from\b", "move"),
    (r"^go from\b", "move"),
    (r"^go\b", "move"),
    (r"^pick up the package$", "pick package"),
    (r"^pick up package$", "pick package"),
    (r"^pick the package$", "pick package"),
    (r"^grab package$", "pick package"),
    (r"^drop the package.*$", "drop package"),
    (r"^drop package\b.*$", "drop package"),
    (r"^pick (?:up )?(?:the )?key\b.*$", "pick key"),
    (r"^unlock the door\b", "unlock door"),
    (r"^place (\w+) onto (shelf|pallet)$", r"place \1 on \2"),
    (r"^load crate (\w+)$", r"load \1"),
    (r"\bon the (shelf|pallet|table)$", r"on \1"),
)


def canonical_action(action: str) -> str:
    """Map one action spelling to its canonical name."""
    a = action
    for pattern, repl in SPELLINGS:
        a = re.sub(pattern, repl, a)
    return a.strip()


def _rooms(action: str) -> list[str]:
    return re.findall(r"\b([A-Za-z])\b", action.replace("move", "").replace("to", " "))


def blocks(plan, on, ontable, clear):
    on, ontable, clear, hold = dict(on), set(ontable), set(clear), None
    for a in plan:
        w = a.replace(" the ", " ").split()
        try:
            if w[0] == "pick" and len(w) > 1 and w[1] == "up":
                b = w[2].upper()
                if hold or b not in ontable or b not in clear:
                    return None
                ontable.discard(b); clear.discard(b); hold = b
            elif w[0] == "unstack":
                b, u = w[1].upper(), w[w.index("from") + 1].upper()
                if hold or on.get(b) != u or b not in clear:
                    return None
                del on[b]; clear.add(u); clear.discard(b); hold = b
            elif w[0] == "put":
                b = w[2].upper()
                if hold != b:
                    return None
                ontable.add(b); clear.add(b); hold = None
            elif w[0] == "stack":
                b, u = w[1].upper(), w[w.index("on") + 1].upper()
                if hold != b or u not in clear:
                    return None
                on[b] = u; clear.discard(u); clear.add(b); hold = None
            else:
                return None
        except (IndexError, ValueError):
            return None
    return on, ontable, clear, hold


def grid(plan, start, goal, blocked, bound=3):
    x, y = start
    step = {"north": (0, 1), "south": (0, -1), "east": (1, 0), "west": (-1, 0)}
    for a in plan:
        d = a.replace("move ", "").strip()
        if d not in step:
            return False
        dx, dy = step[d]; x, y = x + dx, y + dy
        if (x, y) in blocked or not (0 <= x <= bound and 0 <= y <= bound):
            return False
    return (x, y) == goal


def delivery(plan, rooms, robot, pkg, goal):
    adj = {r: set() for r in rooms}
    for a, b in zip(rooms, rooms[1:]):
        adj[a].add(b); adj[b].add(a)
    held = False
    for a in plan:
        w = a.split()
        if w[0] == "move":
            cand = [r.upper() for r in _rooms(a) if r.upper() in adj]
            dst = cand[-1] if cand else None
            if dst is None or dst not in adj.get(robot, ()):
                return False
            robot = dst
            if held:
                pkg = dst
        elif w[0] in ("pick", "grab", "take"):
            if held or pkg != robot:
                return False
            held = True
        elif w[0] in ("drop", "place", "put"):
            if not held:
                return False
            held = False; pkg = robot
        else:
            return False
    return pkg == goal and not held


def door(plan, robot, keyroom, locked, goal, adj):
    holding = False
    locked = set(locked)
    for a in plan:
        w = a.split()
        if w[0] == "pick":
            if robot != keyroom or holding:
                return False
            holding = True
        elif w[0] == "unlock":
            if not holding:
                return False
            for c in [x for x in list(locked) if robot in x.split("-")]:
                locked.discard(c)
        elif w[0] == "move":
            cand = [r.upper() for r in _rooms(a) if r.upper() in adj]
            dst = cand[-1] if cand else None
            if dst is None or dst not in adj.get(robot, ()):
                return False
            if f"{robot}-{dst}" in locked or f"{dst}-{robot}" in locked:
                return False
            robot = dst
        else:
            return False
    return robot == goal


def crate(plan, capacity=1, destinations=None):
    carry, shelf, pallet = [], set(), set()
    for a in plan:
        w = a.split()
        if w[0] == "load":
            if len(carry) >= capacity:
                return False
            carry.append(w[1].upper())
        elif w[0] in ("place", "put"):
            m = re.search(r"\b([xy])\b", a)
            c = m.group(1).upper() if m else None
            if c not in carry:
                return False
            carry.remove(c)
            (shelf if "shelf" in a else pallet).add(c)
        else:
            return False
    want = destinations or {"X": "shelf", "Y": "pallet"}
    got = {c: "shelf" for c in shelf} | {c: "pallet" for c in pallet}
    return got == want and not carry


def checker_from_spec(family: str, params: dict) -> Callable[[list[str]], bool]:
    """Build a permissive checker from solver parameters.

    CHECKS below is a hand-written entry per source, which does not scale past
    one batch. This builds the same check from the parameters a source already
    records, so a new instance needs a spec and not a new branch.

    Permissive on naming, strict on semantics: these accept the spellings a
    model actually emits ("unlock S-T" for "unlock door S-T", "move to T" when
    the source room is unambiguous) while still executing the transition model.
    """
    if family == "plan_blocks":
        goals_on = {k: v for k, v in params["goals_on"].items()}
        goals_clear = set(params.get("goals_clear") or ())
        on = {k: v for k, v in params["on"].items()}
        ontable = set(params["on_table"])
        supported = set(on.values())
        clear = set(params["blocks"]) - supported

        def _check(plan: list[str]) -> bool:
            state = blocks(plan, on, ontable, clear)
            if not state:
                return False
            got_on, _table, got_clear, hold = state
            return (hold is None
                    and all(got_on.get(k) == v for k, v in goals_on.items())
                    and goals_clear.issubset(got_clear))
        return _check
    if family == "plan_grid":
        goal = tuple(params["goal"])
        blocked = {tuple(c) for c in params["blocked"]}
        return lambda plan: grid(plan, (0, 0), goal, blocked)
    if family == "plan_delivery":
        rooms = list(params["rooms"])
        return lambda plan: delivery(plan, rooms, params["robot"], params["package"], params["goal"])
    if family == "plan_door":
        rooms = list(params["rooms"])
        doors = {f"{a}-{b}" for a, b in zip(rooms, rooms[1:])}
        locked = doors - set(params["unlocked"])
        adj: dict[str, set[str]] = {r: set() for r in rooms}
        for a, b in zip(rooms, rooms[1:]):
            adj[a].add(b); adj[b].add(a)
        return lambda plan: door(plan, "S", "S", locked, params["goal"], adj)
    if family == "plan_crate":
        return lambda plan: crate(plan, capacity=params.get("capacity", 1),
                                  destinations=dict(params["destinations"]))
    raise KeyError(f"no checker for family {family!r}")


CHECKS: dict[str, Callable[[list[str]], bool]] = {
    "smoke20_plan_blocks_000": lambda p: (lambda s: bool(s) and s[0].get("C") == "A")(
        blocks(p, {"A": "B"}, {"B", "C"}, {"A", "C"})),
    "smoke20_plan_blocks_001": lambda p: (lambda s: bool(s) and s[0].get("A") == "C")(
        blocks(p, {"B": "A"}, {"A", "C"}, {"B", "C"})),
    "smoke20_plan_blocks_002": lambda p: (lambda s: bool(s) and s[0].get("C") == "A" and "B" in s[2])(
        blocks(p, {"C": "B"}, {"A", "B"}, {"A", "C"})),
    "smoke20_plan_grid_003": lambda p: grid(p, (0, 0), (2, 1), {(1, 0)}),
    "smoke20_plan_grid_004": lambda p: grid(p, (0, 0), (2, 2), {(1, 1), (0, 2)}),
    "smoke20_plan_delivery_005": lambda p: delivery(p, ["A", "B", "C"], "A", "B", "C"),
    "smoke20_plan_delivery_006": lambda p: delivery(p, ["A", "B", "C", "D"], "D", "B", "D"),
    "smoke20_plan_door_007": lambda p: door(p, "S", "S", {"S-T"}, "T", {"S": {"T"}, "T": {"S"}}),
    "smoke20_plan_door_008": lambda p: door(
        p, "S", "S", {"S-T", "T-U"}, "U", {"S": {"T"}, "T": {"S", "U"}, "U": {"T"}}),
    "smoke20_plan_crate_009": lambda p: crate(p),
}



# --- spec-driven grading -----------------------------------------------------
# `checker_from_spec` above was written but never reached: `grade()` consulted
# only the hand-written CHECKS table, so any source not in it graded False --
# which reads exactly like a model failure and is not one.  Sources that carry
# `solver_params` are now graded by EXECUTING the domain's transition model,
# which is the same code the gold plan was produced by.

def checker_from_domain(family: str, params: dict) -> Callable[[list[str]], bool]:
    """Execute the plan against the real domain, permissive only about spelling."""
    from planning_domains import execute_plan, make_problem

    def _restore(value):
        # JSON round-trips sets to lists and tuples to lists; the builders want
        # the original shapes back.
        return value

    kwargs = dict(params)
    if family == "plan_blocks":
        kwargs["blocks"] = tuple(kwargs["blocks"])
        kwargs["on_table"] = set(kwargs["on_table"])
        if kwargs.get("goals_clear"):
            kwargs["goals_clear"] = set(kwargs["goals_clear"])
    elif family == "plan_logistics":
        kwargs["cities"] = {c: tuple(v) for c, v in kwargs["cities"].items()}

    problem = make_problem(family, **kwargs)

    def _check(plan: list[str]) -> bool:
        if not plan:
            return False
        reached, _state = execute_plan(problem, [canonical_action(a) for a in plan])
        return bool(reached)

    return _check


def load_specs(paths: list[Path]) -> dict[str, tuple[str, dict]]:
    """task_group_id -> (family, solver_params) for spec-driven sources."""
    specs: dict[str, tuple[str, dict]] = {}
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("solver_params") and row.get("task_group_id"):
                specs[row["task_group_id"]] = (row["source_family"], row["solver_params"])
    return specs


def grade(output_path: Path,
          specs: dict[str, tuple[str, dict]] | None = None) -> dict[str, dict[str, Any]]:
    specs = specs or {}
    results: dict[str, dict[str, Any]] = {}
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        # Two shapes reach here.  The runner's raw stage-1 output carries the
        # whole completion under "output", so the boxed span must be found in
        # it.  The exported run package -- the durable artefact once the /tmp
        # run directory is gone -- has already done that extraction and stores
        # the result in "extracted_answer"; its "full_trace" is the REASONING
        # only and contains no boxed answer, so re-extracting from it yields
        # nothing and grades every row 0 actions.
        if isinstance(rec.get("output"), list):
            plan = parse_actions(extract_boxed(rec["output"][0]))
        elif rec.get("output"):
            plan = parse_actions(extract_boxed(rec["output"]))
        elif rec.get("extracted_answer"):
            plan = parse_actions(rec["extracted_answer"])
        else:
            plan = []
        gid = rec.get("task_group_id")
        check = CHECKS.get(gid)
        basis = "pinned_checker"
        if check is None and gid in specs:
            family, params = specs[gid]
            check = checker_from_domain(family, params)
            basis = "domain_transition_model"
        if check is None:
            raise KeyError(
                f"no checker for {gid!r}: it is not in CHECKS and no --source-groups "
                f"file supplied its solver_params. Grading it False would report a "
                f"missing checker as a model failure.")
        results[gid] = {
            "no_update_solved": bool(check(plan)),
            "plan_actions": len(plan),
            "parsed_plan": plan,
            "grading_method": "plan_equivalence",
            "grading_basis": basis,
        }
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1-output", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--source-groups", type=Path, nargs="*", default=[],
                    help="source-group files whose solver_params drive spec-based grading")
    args = ap.parse_args(argv)
    res = grade(args.stage1_output, load_specs(list(args.source_groups)))
    solved = sum(1 for v in res.values() if v["no_update_solved"])
    for gid, v in sorted(res.items()):
        print(f"  {gid:28s} {'solved' if v['no_update_solved'] else 'UNSOLVED':9s} "
              f"{v['plan_actions']:2d} actions")
    print(f"solved {solved}/{len(res)} by plan equivalence")
    if args.out:
        args.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if solved == len(res) else 1


if __name__ == "__main__":
    raise SystemExit(main())

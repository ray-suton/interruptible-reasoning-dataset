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
    s = re.sub(r"\\text\{([^{}]*)\}", r"\1", raw)
    s = re.sub(r"\\(?:mathrm|mbox|;|,|!|quad|qquad)", " ", s)
    s = s.replace("\\\\", ";").replace("\\", " ").replace("$", " ").replace("\n", ";")
    s = re.sub(r"(?m)^\s*\d+[.)]\s*", ";", s)
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
        out.append(a)
    return out


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


def crate(plan, capacity=1):
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
    return shelf == {"X"} and pallet == {"Y"} and not carry


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


def grade(output_path: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for line in output_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        text = rec["output"][0] if isinstance(rec.get("output"), list) else rec.get("output", "")
        plan = parse_actions(extract_boxed(text))
        gid = rec.get("task_group_id")
        check = CHECKS.get(gid)
        ok = bool(check(plan)) if check else False
        results[gid] = {
            "no_update_solved": ok,
            "plan_actions": len(plan),
            "parsed_plan": plan,
            "grading_method": "plan_equivalence",
        }
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1-output", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    res = grade(args.stage1_output)
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

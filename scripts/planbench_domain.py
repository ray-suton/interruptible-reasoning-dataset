#!/usr/bin/env python3
"""Parse PlanBench statements into executable state, and execute plans against it.

v38 requires plans to be graded by EXECUTION, never by string match -- the smoke-100
planning screening recorded 0/45 solved because it compared a LaTeX-formatted boxed
plan to a gold plan string. This module is the replacement: it reads the final
[STATEMENT] block of a PlanBench query into an initial state and a goal, and steps a
plan through the domain's preconditions and effects.

Plans are accepted in either notation, because the model writes one and the gold is
the other:
  PDDL      (unstack red orange) / (load-airplane p0 a1 l1-0)
  English   unstack the red block from on top of the orange block
            load package_0 into airplane_1 at location_1_0

BOTH BRANCHES ARE CHECKED. --selftest requires, for every instance, that the gold
plan reaches the goal AND that a truncated and a reversed plan do not. An instance
whose checker cannot refute a broken plan is reported UNCHECKABLE and must not be
used as a source: it would score a failing model as correct.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO / "sources/planbench/task1_blocksworld_logistics.jsonl"


# ---------------------------------------------------------------- BlocksWorld
def parse_blocksworld(query: str) -> dict:
    """Final [STATEMENT] only -- earlier ones are the one-shot example."""
    stmt = query.split("[STATEMENT]")[-1]
    init = stmt.split("My goal is")[0]
    goal = stmt.split("My goal is to have that")[-1].split("My plan")[0]
    on, on_table, clear = {}, set(), set()
    for a, b in re.findall(r"the (\w+) block is on top of the (\w+) block", init):
        on[a] = b
    on_table |= set(re.findall(r"the (\w+) block is on the table", init))
    clear |= set(re.findall(r"the (\w+) block is clear", init))
    goals = {a: b for a, b in re.findall(r"the (\w+) block is on top of the (\w+) block", goal)}
    return {"on": on, "on_table": sorted(on_table), "clear": sorted(clear),
            "holding": None, "hand_empty": "hand is empty" in init, "goals_on": goals}


def _bw_actions(plan: str) -> list[tuple]:
    acts = []
    for line in plan.strip().splitlines():
        s = line.strip().lower().rstrip(".")
        if not s:
            continue
        m = re.match(r"\(?\s*(pick-up|pick up|put-down|put down|unstack|stack)\s+(.*?)\s*\)?$", s)
        if not m:
            acts.append(("?", s)); continue
        verb = m.group(1).replace(" ", "-"); rest = m.group(2)
        names = re.findall(r"\b(?!the\b|block\b|from\b|on\b|top\b|of\b|table\b)([a-z0-9_-]+)\b", rest)
        acts.append((verb, *names))
    return acts


def execute_blocksworld(plan: str, st: dict) -> bool:
    on = dict(st["on"]); table = set(st["on_table"]); clear = set(st["clear"]); hold = st.get("holding")
    for a in _bw_actions(plan):
        v = a[0]
        try:
            if v == "pick-up":
                x = a[1]
                if hold is not None or x not in table or x not in clear: return False
                table.discard(x); clear.discard(x); hold = x
            elif v == "put-down":
                x = a[1]
                if hold != x: return False
                table.add(x); clear.add(x); hold = None
            elif v == "unstack":
                x, y = a[1], a[2]
                if hold is not None or on.get(x) != y or x not in clear: return False
                del on[x]; clear.discard(x); clear.add(y); hold = x
            elif v == "stack":
                x, y = a[1], a[2]
                if hold != x or y not in clear: return False
                on[x] = y; clear.discard(y); clear.add(x); hold = None
            else:
                return False
        except IndexError:
            return False
    if hold is not None: return False
    return all(on.get(a) == b for a, b in st["goals_on"].items())


# ------------------------------------------------------------------ Logistics
def parse_logistics(query: str) -> dict:
    stmt = query.split("[STATEMENT]")[-1]
    init = stmt.split("My goal is")[0]
    goal = stmt.split("My goal is to have that")[-1].split("My plan")[0]
    at = dict(re.findall(r"(\w+) is at (\w+)", init))
    airports = set(re.findall(r"(\w+) is an airport", init))
    in_city = dict(re.findall(r"(\w+) is in the city (\w+)", init))
    goals_at = dict(re.findall(r"(\w+) is at (\w+)", goal))
    return {"at": at, "airports": sorted(airports), "in_city": in_city,
            "in_vehicle": {}, "goals_at": goals_at}


def _lg_norm(tok: str) -> str:
    """PDDL abbreviations to the statement's full names: p0->package_0, l1-0->location_1_0."""
    m = re.fullmatch(r"([patcl])(\d+)(?:-(\d+))?", tok)
    if not m: return tok
    kind = {"p": "package", "a": "airplane", "t": "truck", "c": "city", "l": "location"}[m.group(1)]
    return f"{kind}_{m.group(2)}" + (f"_{m.group(3)}" if m.group(3) else "")


def _lg_actions(plan: str) -> list[tuple]:
    acts = []
    for line in plan.strip().splitlines():
        s = line.strip().lower().rstrip(".")
        if not s: continue
        m = re.match(r"\(?\s*(load-truck|unload-truck|load-airplane|unload-airplane|drive-truck|fly-airplane|load|unload|drive|fly)\s+(.*?)\s*\)?$", s)
        if not m:
            acts.append(("?", s)); continue
        verb = m.group(1)
        names = [_lg_norm(t) for t in re.findall(r"\b(?!into\b|from\b|at\b|to\b|in\b|the\b)([a-z0-9_-]+)\b", m.group(2))]
        acts.append((verb, *names))
    return acts


def execute_logistics(plan: str, st: dict) -> bool:
    at = dict(st["at"]); inv = dict(st.get("in_vehicle") or {})
    airports = set(st["airports"]); city = dict(st["in_city"])
    def loc_of(x): return at.get(x)
    for a in _lg_actions(plan):
        v = a[0]; args = list(a[1:])
        try:
            if v.startswith("load"):
                p, veh, l = args[0], args[1], (args[2] if len(args) > 2 else at.get(args[1]))
                if at.get(p) != l or at.get(veh) != l: return False
                if v == "load-airplane" and l not in airports: return False
                inv[p] = veh; at.pop(p, None)
            elif v.startswith("unload"):
                p, veh, l = args[0], args[1], (args[2] if len(args) > 2 else at.get(args[1]))
                if inv.get(p) != veh or at.get(veh) != l: return False
                if v == "unload-airplane" and l not in airports: return False
                inv.pop(p); at[p] = l
            elif v.startswith("drive"):
                t, src, dst = args[0], args[1], args[2]
                if at.get(t) != src: return False
                if city.get(src) and city.get(dst) and city[src] != city[dst]: return False
                at[t] = dst
            elif v.startswith("fly"):
                pl, src, dst = args[0], args[1], args[2]
                if at.get(pl) != src or src not in airports or dst not in airports: return False
                at[pl] = dst
            else:
                return False
        except IndexError:
            return False
    for p, l in st["goals_at"].items():
        if at.get(p) != l: return False
    return True


PARSERS = {"blocksworld": parse_blocksworld, "logistics": parse_logistics}
EXECUTORS = {"blocksworld": execute_blocksworld, "logistics": execute_logistics}


def checker_for(domain: str, state: dict):
    ex = EXECUTORS[domain]
    return lambda plan: ex(plan, state)


def selftest(records) -> tuple[int, list]:
    """Gold reaches the goal; truncated and reversed do not. Both branches, per instance."""
    ok, bad = 0, []
    for r in records:
        dom = r["upstream_domain"]
        st = PARSERS[dom](r["query"])
        gold = r["ground_truth_plan"]
        lines = [l for l in gold.strip().splitlines() if l.strip()]
        check = checker_for(dom, st)
        why = None
        if not check(gold):
            why = "gold does not execute to the goal"
        elif len(lines) > 1 and check("\n".join(lines[:-1])):
            why = "truncated plan still reaches the goal"
        elif len(lines) > 2 and check("\n".join(reversed(lines))):
            why = "reversed plan still reaches the goal"
        if why: bad.append({"id": f"{dom}:{r['upstream_instance_id']}", "why": why})
        else: ok += 1
    return ok, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    recs = [json.loads(l) for l in a.source.open() if l.strip()]
    ok, bad = selftest(recs)
    print(f"selftest: {ok}/{len(recs)} instances have a checker that accepts gold and refutes broken plans")
    byd = {}
    for b in bad: byd.setdefault(b["id"].split(":")[0], []).append(b)
    for d, v in sorted(byd.items()):
        print(f"  UNCHECKABLE {d}: {len(v)}  e.g. {v[0]['why']} ({v[0]['id']})")
    if a.out:
        usable = []
        bad_ids = {b["id"] for b in bad}
        for r in recs:
            i = f"{r['upstream_domain']}:{r['upstream_instance_id']}"
            if i in bad_ids: continue
            st = PARSERS[r["upstream_domain"]](r["query"])
            usable.append({**{k: r[k] for k in ("upstream_domain", "upstream_instance_id")},
                           "solver_params": st,
                           "gold_plan_actions": len([l for l in r["ground_truth_plan"].strip().splitlines() if l.strip()]),
                           "statement_chars": len(r["query"])})
        a.out.write_text("".join(json.dumps(u, sort_keys=True) + "\n" for u in usable))
        print(f"wrote {len(usable)} checkable instances -> {a.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Derive a smaller planning instance by RESTRICTING an upstream goal. Nothing is invented.

Why this exists: PlanBench Logistics has only 14 instances the target model solves
(0.21 over 66 screened; 0.07 at 11-16 actions), and every unscreened instance is
17+ actions. A balanced slice needs 20. Authoring instances is forbidden by §8.0
-- that rule exists because sources, updates and labels authored by one party
leave a reviewer no independent anchor.

A goal restriction keeps the anchor. From an upstream instance we keep:
  * the initial state, verbatim
  * the object names and the domain description, verbatim
  * the gold plan -- as a PREFIX of the upstream gold, verified by execution
and change exactly one thing: we drop goal conjuncts, keeping one.

So a reviewer can reconstruct the derived instance from the upstream record plus
the recorded rule. It is a documented derivation, not an authored task. It is NOT
a pinned import either, so it is marked `derived_from_pinned` and must be reported
as such -- see the ruling note in plan.md.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planbench_domain import parse_logistics, execute_logistics  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GOAL_RE = re.compile(r"(My goal is to have that )(.*?)(\.\s*\n)", re.S)


def restrict_statement(query: str, keep: str) -> str | None:
    """Rewrite ONLY the final goal sentence. Everything else is untouched."""
    head, sep, tail = query.rpartition("[STATEMENT]")
    if not sep:
        return None
    m = GOAL_RE.search(tail)
    if not m:
        return None
    return head + sep + tail[:m.start()] + m.group(1) + keep + m.group(3) + tail[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=REPO / "sources/planbench/task1_blocksworld_logistics.jsonl")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-actions", type=int, default=8)
    ap.add_argument("--min-actions", type=int, default=4,
                    help="a 1- or 2-action plan has no room for a depth>=2 falsifiable consequence, "
                         "so such a derivation is not authorable even though it is valid")
    ap.add_argument("--want", type=int, default=20)
    a = ap.parse_args()

    recs = [r for r in (json.loads(l) for l in a.source.open() if l.strip()) if r["upstream_domain"] == "logistics"]
    out, seen = [], set()
    for r in recs:
        if len(out) >= a.want:
            break
        st = parse_logistics(r["query"])
        if len(st["goals_at"]) < 2:
            continue
        gold = [l for l in r["ground_truth_plan"].strip().splitlines() if l.strip()]
        for pkg, dest in sorted(st["goals_at"].items()):
            if len(out) >= a.want or r["upstream_instance_id"] in seen:
                break
            sub = dict(st); sub["goals_at"] = {pkg: dest}
            k = next((i for i in range(1, len(gold) + 1)
                      if execute_logistics("\n".join(gold[:i]), sub)), None)
            if k is None or k > a.max_actions or k < a.min_actions:
                continue
            keep = f"{pkg} is at {dest}"
            q = restrict_statement(r["query"], keep)
            if q is None:
                continue
            # both branches: the derived gold must reach the derived goal, and a
            # truncation of it must not.
            st2 = parse_logistics(q)
            plan = "\n".join(gold[:k])
            if not execute_logistics(plan, st2):
                continue
            if k > 1 and execute_logistics("\n".join(gold[:k - 1]), st2):
                continue
            seen.add(r["upstream_instance_id"])
            out.append({
                "task_group_id": f"pbd_logistics_{r['upstream_instance_id']}_{pkg}",
                "stable_source_id": f"PBD-LOGIS-{r['upstream_instance_id']}-{pkg}",
                "upstream_id": f"PBD-LOGIS-{r['upstream_instance_id']}-{pkg}",
                "source_family": "plan_logistics", "domain": "planning", "answer_form": "plan",
                "source_dataset": "tasksource/planbench", "source_year": 2023,
                "upstream_revision": "653dcebd212078d9b64ee8aa7bed19e8b11a9d6a",
                "derived_from": {
                    "upstream_instance_id": r["upstream_instance_id"],
                    "upstream_statement_sha256": hashlib.sha256(r["query"].encode()).hexdigest(),
                    "upstream_gold_sha256": hashlib.sha256(r["ground_truth_plan"].encode()).hexdigest(),
                    "upstream_gold_actions": len(gold),
                    "rule": "goal restricted to a single conjunct; initial state, objects and domain text unchanged; "
                            "gold plan is the minimal PREFIX of the upstream gold that satisfies the restricted goal",
                    "goal_kept": keep,
                    "goal_dropped": sorted(f"{p} is at {d}" for p, d in st["goals_at"].items() if p != pkg),
                    "gold_prefix_actions": k,
                },
                "statement": q, "statement_sha256": hashlib.sha256(q.encode()).hexdigest(),
                "statement_text_included": True,
                "original_answer": plan, "solver_params": st2, "gold_plan_actions": k,
                "source_record_locator": f"sources/planbench/task1_blocksworld_logistics.jsonl#logistics:{r['upstream_instance_id']}",
                "split": "development", "report_partition": "development", "recipe": "M4",
                "source_admission_status": "derived_from_pinned",
                "license_note": "Derived from PlanBench via tasksource/planbench rev 653dcebd...; redistribution cleared by the owner 2026-09-13. NOT verbatim upstream -- goal restricted, see derived_from.",
                "answer_equivalence": "plan equivalence by EXECUTION against solver_params (scripts/planbench_domain.py)",
            })
    a.out.write_text("".join(json.dumps(o, sort_keys=True) + "\n" for o in out))
    import statistics as st_
    print(f"derived {len(out)} restricted-goal Logistics instances -> {a.out}")
    if out:
        print(f"  gold plan actions: {sorted(o['gold_plan_actions'] for o in out)}")
        print(f"  from upstream golds of: {sorted(o['derived_from']['upstream_gold_actions'] for o in out)}")
        print("  every one verified: derived gold reaches the restricted goal, and its truncation does not")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

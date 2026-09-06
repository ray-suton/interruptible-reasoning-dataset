#!/usr/bin/env python3
"""Assemble the evidence a human needs to write a MATH500 consequence note.

MATH500 records store only a final value -- no `<<expr=result>>` chain -- so the
GSM8K approach in `propose_consequences.py` does not apply. What IS available is
the model's own SOLVED reasoning trace from screening, in which the derivation
appears as prose.

This extracts the arithmetic the model actually performed and orders it into a
chain, so a person can see what the problem derives without re-solving it. It
deliberately does NOT decide the note. Two reasons:

1. The chain is the path THIS model took. A different correct solution reaches
   the answer through different intermediates, so a depth read off this trace is
   evidence about one derivation, not a property of the problem.
2. Many MATH500 items are symbolic rather than arithmetic. Their natural PFM
   shape is often `false_implied_bound`, `false_parity_or_ordering` or
   `false_domain_convention`, all of which §2.3 EXEMPTS from the depth floor.
   Forcing a depth onto those would ban rows the contract permits.

So the output is: statement, gold answer, the model's extracted steps, and which
of them are candidates. The target, the shape and whether the floor even applies
are the reviewer's call.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path

# "54 divided by 3 is 18", "20 multiplied by $2", "3 * 5 = 15", "54/3 = 18"
SYMBOLIC = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?)\s*(?:\\times|[*x×/+\-])\s*\$?(-?\d[\d,]*(?:\.\d+)?)"
    r"\s*(?:=|is|equals|gives)\s*\$?(-?\d[\d,]*(?:\.\d+)?)", re.I)
WORDY = re.compile(
    r"(-?\d[\d,]*(?:\.\d+)?)\s*(?:divided by|times|multiplied by|plus|minus|over)\s*"
    r"\$?(-?\d[\d,]*(?:\.\d+)?)\s*(?:=|is|equals|gives|would be)\s*\$?(-?\d[\d,]*(?:\.\d+)?)", re.I)


def norm(v: str) -> str:
    v = v.replace(",", "").rstrip(".")
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return v


def stated(statement: str) -> set[str]:
    # Strip Asymptote blocks first: their coordinates are drawing instructions,
    # not problem quantities, and counting them as "stated" hides real depth.
    s = re.sub(r"\[asy\].*?\[/asy\]", " ", statement, flags=re.S)
    return {norm(n) for n in re.findall(r"-?\d[\d,]*(?:\.\d+)?", s)}


def steps_from_trace(trace: str) -> list[tuple[str, str, str, str]]:
    """(a, b, result, snippet) for each arithmetic step, first occurrence wins."""
    out, seen = [], set()
    for m in list(SYMBOLIC.finditer(trace)) + list(WORDY.finditer(trace)):
        a, b, r = norm(m.group(1)), norm(m.group(2)), norm(m.group(3))
        key = (a, b, r)
        if key in seen:
            continue
        seen.add(key)
        lo = max(0, m.start() - 40)
        out.append((a, b, r, trace[lo:m.end() + 15].replace("\n", " ").strip()))
    return out


def analyse(statement: str, trace: str, gold: str) -> dict:
    st = stated(statement)
    steps = steps_from_trace(trace)
    depth: dict[str, int] = {}
    rows = []
    for a, b, r, snip in steps:
        da = depth.get(a, 0 if a in st else None)
        db = depth.get(b, 0 if b in st else None)
        known = [d for d in (da, db) if d is not None]
        d = 1 + max(known) if len(known) == 2 else None   # None = operand unaccounted for
        if d is not None:
            depth[r] = min(depth.get(r, d), d)
        rows.append({"a": a, "b": b, "result": r, "depth": d,
                     "a_stated": a in st, "b_stated": b in st, "snippet": snip})
    g = norm(gold)
    cands = [x for x in rows if x["depth"] is not None and x["depth"] >= 2 and x["result"] != g]
    return {"steps": rows, "candidates": cands, "gold_norm": g,
            "has_asy": "[asy]" in statement}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-dir", type=Path, default=Path("data/smoke_100"))
    ap.add_argument("--owner", help="only this contributor's sources")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    traces = {}
    for run in (args.batch_dir / "model_trace_runs").iterdir():
        f = run / "traces.jsonl"
        if f.exists():
            for line in f.read_text().splitlines():
                if line.strip():
                    t = json.loads(line)
                    traces[t["stable_source_id"]] = t

    rows = [json.loads(l) for l in (args.batch_dir / "source_groups_math.jsonl").read_text().splitlines() if l.strip()]
    need = [r for r in rows if r["consequence_note_basis"] == "none"]
    if args.owner:
        need = [r for r in need if r["owner_id"] == args.owner]

    out = {}
    for r in sorted(need, key=lambda r: r["stable_source_id"]):
        t = traces.get(r["stable_source_id"])
        a = analyse(r["statement"], (t or {}).get("full_trace", ""), r["original_answer"])
        out[r["stable_source_id"]] = {"owner": r["owner_id"], "gold": r["original_answer"],
                                      "statement": r["statement"], **a}
        print("=" * 72)
        print(f"{r['stable_source_id']}  [{r['owner_id']}]  gold = {r['original_answer']}"
              + ("   (statement contains [asy] diagram code)" if a["has_asy"] else ""))
        stmt = re.sub(r"\[asy\].*?\[/asy\]", " [diagram omitted] ", r["statement"], flags=re.S)
        print("  " + re.sub(r"\s+", " ", stmt)[:400])
        print(f"  model's steps ({len(a['steps'])} found, prefix "
              f"{(t or {}).get('prefix_reasoning_tokens')}/{(t or {}).get('total_reasoning_tokens')} tokens):")
        for x in a["steps"][:9]:
            d = "?" if x["depth"] is None else x["depth"]
            print(f"     {x['a']:>8s} , {x['b']:>8s} -> {x['result']:>10s}   depth {d}")
        if a["candidates"]:
            print(f"  depth>=2 non-answer candidates: "
                  f"{[(c['result'], c['depth']) for c in a['candidates'][:5]]}")
        else:
            print("  NO arithmetic candidate at depth>=2 — likely a symbolic item; "
                  "consider a floor-exempt shape")
        print()
    if args.out:
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"{len(out)} source(s); {sum(1 for v in out.values() if v['candidates'])} have an "
          f"arithmetic depth>=2 candidate")


if __name__ == "__main__":
    main()

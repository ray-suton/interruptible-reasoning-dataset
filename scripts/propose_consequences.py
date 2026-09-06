#!/usr/bin/env python3
"""Propose a PFM target and its DERIVATION DEPTH from a source's own chain.

A `consequence_note` names the derivable fact a PFM should falsify, and the
depth floor (`generation_rules.md` §2.3 [Q-D5]) makes that a claim about how far
the falsified value sits from the stated inputs.  Depth is author-reported, so
the contract calls it "an assertion rather than a proof".

For GSM8K it need not be.  The upstream rationale carries the solver's own
calculator annotations -- `<<70*5=350>>` -- which ARE the derivation chain.  This
computes depth from that chain instead of guessing it:

    depth(v) = 0                       if v appears verbatim in the statement
             = 1 + max(depth(operand)) otherwise

A value whose operands are all stated is depth 1 and is NOT authorable; the floor
wants >= 2.  The final answer is excluded as a target: falsifying it is asserting
a wrong answer, not falsifying a consequence en route to it.

This proposes; it does not decide.  A human confirms, which is what
`screening.consequence_confirmed` records.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path

STEP = re.compile(r"<<([^<>=]+)=([^<>]+)>>")
NUM = re.compile(r"-?\d+(?:\.\d+)?")
# Inside a calculator expression every "-" is an OPERATOR, never a sign: the
# signed pattern read "1600-1350" as operands [1600, -1350], so -1350 was an
# unseen value at depth 0 and the step computed depth 1 instead of 4. Operand
# extraction therefore uses an unsigned pattern.
# A leading-dot decimal is a real operand: GSM8K writes "400*.6" and
# "36000*10*.01". Without the optional leading dot the pattern returned 6 and 1
# for those, so a note recorded "operand 6" where the statement says 60%.
OPERAND = re.compile(r"\d+\.\d+|\.\d+|\d+")
# Arithmetic written in prose without calculator delimiters. GSM8K rationales are
# NOT uniformly annotated -- 12% of them compute at least one value in bare prose
# ("12 plus 14 plus 4 equals 30", "40*.10 = $4.00"). An annotation-only reader
# silently misses those steps, which makes every downstream depth an
# UNDERESTIMATE and, worse, can make a source with a perfectly good depth-2
# target look like it has none. Detected so the chain can declare itself
# incomplete instead of answering from partial information.
_ARITH = re.compile(
    r"\d\s*(?:[-+*/x\u00d7]|plus|minus|times|multiplied by|divided by)\s*\.?\d", re.I)


def unannotated_steps(rationale: str) -> list[str]:
    """Lines that compute something but carry no <<expr=result>> annotation."""
    body = rationale.split("####")[0]
    return [line.strip() for line in body.splitlines()
            if line.strip() and "<<" not in line and _ARITH.search(line)]


def stated_numbers(statement: str) -> set[str]:
    return {n.lstrip("+") for n in NUM.findall(statement.replace(",", ""))}


def norm(v: str) -> str:
    v = v.strip().replace(",", "").rstrip(".")
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return v


def chain(statement: str, rationale: str) -> list[dict]:
    """Each annotated step, with the depth of its result."""
    stated = {norm(n) for n in stated_numbers(statement)}
    # `produced` maps a NUMERAL to the depth of the most recent step that
    # produced it, and is consulted before `stated`.
    #
    # The previous version kept a single depth per numeral and took the MINIMUM
    # over duplicates. That conflates a numeral with a quantity, which is the
    # same surface-form-versus-thing error as every grader bug in this project:
    #   - one source computes $36 (depth 2) and 36 bagels (depth 1). Taking the
    #     min recorded 36 as depth 1 and made a valid depth-2 target look banned.
    #   - another has 18 seats per row (stated, depth 0) and 18 administrators
    #     (derived, depth 2). Treating the derived one as stated made the value
    #     computed from it look two steps shallower than it is.
    # Both made an author's correct depth claim look wrong. Resolving an operand
    # to the latest step that produced it follows the chain as written.
    produced: dict[str, int] = {}
    steps: list[dict] = []
    for expr, result in STEP.findall(rationale):
        res = norm(result)
        operands = [norm(n) for n in OPERAND.findall(expr.replace(",", ""))]
        depths = []
        for o in operands:
            if o in produced:
                depths.append(produced[o])
            elif o in stated:
                depths.append(0)
            else:
                depths.append(0)
        d = 1 + max(depths, default=0)
        produced[res] = d
        steps.append({"expr": expr.strip(), "result": res, "operands": operands,
                      "operand_depths": depths, "depth": d})
    return steps


def propose(statement: str, rationale: str, final: str) -> dict:
    steps = chain(statement, rationale)
    missing = unannotated_steps(rationale)
    if missing:
        # UNDETERMINED, not unhostable. Rejecting a source because our reader
        # could not see all of its arithmetic would discard authorable sources
        # and record depths that are too shallow. Verified: S80-MATH-011 derives
        # 30 = 12+14+4 at depth 2 in bare prose, and an annotation-only screen
        # rejected it outright.
        return {"ok": False, "undetermined": True,
                "reason": (f"the rationale computes {len(missing)} value(s) without "
                           "calculator annotations, so the chain cannot be read "
                           "completely; depth must be traced by hand"),
                "unannotated": missing, "steps": steps}
    final_n = norm(final)
    # Candidates: depth >= 2, not the final answer, and distinct.
    seen: set[str] = set()
    cands = []
    for s in steps:
        if s["depth"] >= 2 and s["result"] != final_n and s["result"] not in seen:
            seen.add(s["result"])
            cands.append(s)
    if not cands:
        return {"ok": False, "undetermined": False,
                "reason": "no intermediate at depth >= 2 that is not the answer",
                "steps": steps}
    # Prefer the SHALLOWEST qualifying step: deeper targets are closer to the
    # answer and a falsehood there is easier to catch by back-checking.
    best = min(cands, key=lambda s: (s["depth"], steps.index(s)))
    # Label each operand STATED or DERIVED. Writing them all up as "the stated
    # inputs" mislabels the very distinction the floor rests on: a value is depth
    # >= 2 precisely BECAUSE at least one operand was itself derived. A reviewer
    # reading "depth 2 from the stated inputs (4, 9)" would be entitled to
    # conclude the row is depth 1 and reject it.
    depths = {st["result"]: st["depth"] for st in steps}
    parts = []
    for o in best["operands"]:
        d = depths.get(o)
        parts.append(f"{o} (derived, depth {d})" if d else f"{o} (stated)")
    note = (f"the chain computes {best['expr']} = {best['result']} from "
            f"{', '.join(parts)}; {best['result']} therefore sits at depth "
            f"{best['depth']} from the stated inputs")
    return {"ok": True, "undetermined": False,
            "target": best["result"], "depth": best["depth"],
            "expr": best["expr"], "note": note,
            "family": "false_derived_intermediate",
            "alternatives": [(c["result"], c["depth"], c["expr"]) for c in cands[1:4]],
            "steps": steps}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-groups", nargs="+", required=True)
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--family", default="gsm8k")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    pool = {}
    for line in Path("sources/upstream_interrupt_lrm/math_source_problems.jsonl").read_text().splitlines():
        r = json.loads(line)
        pool[(r["source_family"], str(r["upstream_id"]))] = r

    out = {}
    for path in args.source_groups:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            g = json.loads(line)
            if g["source_family"] != args.family:
                continue
            if args.only_missing and g.get("consequence_note"):
                continue
            raw = pool[(g["source_family"], str(g["upstream_id"]))]["original_answer"]
            out[g["stable_source_id"]] = {
                "owner": g.get("owner_id"),
                "statement": g["statement"],
                "answer": g["original_answer"],
                **propose(g["statement"], raw, g["original_answer"]),
            }
    for sid, p in sorted(out.items()):
        flag = "OK " if p["ok"] else "!! "
        print(f"{flag}{sid} [{p['owner']}] answer={p['answer']}")
        if p["ok"]:
            print(f"     target {p['target']}  depth {p['depth']}  ({p['expr']})")
            if p["alternatives"]:
                print(f"     also: {p['alternatives']}")
        else:
            print(f"     {p['reason']}")
    if args.out:
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"\n{sum(1 for p in out.values() if p['ok'])}/{len(out)} have a depth>=2 target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Independent-judge agreement, per the rubric's Independence clause.

Claude cross-graded 48 of 240 continuations (20%), stratified 3 per
(class x family), reading each in full and writing every verdict to
claude_crossgrade.jsonl BEFORE any file in judge_out_v38/ existed. This script
is the first thing that reads both.

Neither judge overrides the other. Disagreements are listed for the owner as
ADJUDICATE; no rate is recomputed after a disagreement is "resolved" by
discussion.
"""
import argparse, collections, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--judge-dir", default="judge_out_v38")
    a = ap.parse_args()
    mine = {j["key"]: j for j in (json.loads(l) for l in (a.run / "claude_crossgrade.jsonl").open() if l.strip())}
    theirs = {}
    for f in sorted((a.run / a.judge_dir).glob("batch_*.jsonl")):
        for l in f.open():
            if l.strip():
                j = json.loads(l)
                theirs[j["key"]] = j
    common = sorted(set(mine) & set(theirs))
    missing = sorted(set(mine) - set(theirs))
    agree = [k for k in common if mine[k]["engagement"] == theirs[k]["engagement"]]
    disagree = [k for k in common if mine[k]["engagement"] != theirs[k]["engagement"]]
    conf = collections.Counter()
    for k in common:
        conf[(mine[k]["engagement"], theirs[k]["engagement"])] += 1
    out = {"n_cross_graded": len(mine), "n_comparable": len(common),
           "not_yet_judged": missing,
           "agreement": round(len(agree) / len(common), 4) if common else None,
           "n_agree": len(agree), "n_disagree": len(disagree),
           "confusion_claude_x_codex": {f"{a_}|{b}": n for (a_, b), n in sorted(conf.items())},
           "ADJUDICATE": [{"key": k, "claude": mine[k]["engagement"], "codex": theirs[k]["engagement"],
                           "claude_confidence": mine[k].get("confidence"),
                           "codex_confidence": theirs[k].get("confidence"),
                           "claude_note": mine[k].get("note"),
                           "claude_quote": mine[k].get("evidence_quote", "")[:140],
                           "codex_quote": theirs[k].get("evidence_quote", "")[:140]} for k in disagree]}
    (a.run / "crossgrade_agreement.json").write_text(json.dumps(out, indent=1))
    print(f"cross-graded {len(mine)} | comparable {len(common)} | agreement "
          f"{out['agreement']} ({len(agree)}/{len(common)})")
    for k, n in sorted(conf.items()):
        if k[0] != k[1]:
            print(f"   claude={k[0]:22s} codex={k[1]:22s} n={n}")
    print(f"wrote {a.run / 'crossgrade_agreement.json'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Elicited `Decision:` coverage and accuracy, for the instructed arms only.

Kept OUT of grade_replay_v38.py on purpose: the grader must be byte-identical
across arms or the comparison measures the grader. This is a separate diagnostic
run only on arms whose prompt asks for a decision line.

Two things it reports:

* COVERAGE -- what fraction of continuations emit a decision at all. This is what
  retired the protocol at v38: under explicit_label on the smoke_100 batch, 70 of
  240 emitted none, 68 of them MATH500. If coverage is poor here too, the
  instruction is not reliably followed and the arm's engagement lift cannot be
  attributed to a decision the model never made.
* ACCURACY -- when a decision IS emitted, does it match the row's binary_label.
  That is the only thing in this whole pipeline that is a direct, self-reported
  read of the disposition being measured.

The quoted-template guard is inherited from the v35 grader: the model frequently
repeats the prompt ("...first output 'Decision: ACCEPT' or 'Decision:
DO_NOT_ACCEPT'...") and a first-match parse read that quoted ACCEPT as the
verdict. A match is a quotation when it sits between quote marks or is followed
by "' or".
"""
import argparse, json, re, collections
from pathlib import Path

DECISION_RE = re.compile(r"Decision:\s*(ACCEPT|DO_NOT_ACCEPT)", re.I)
QUOTED_RE = re.compile(
    r"""['"‘’“”]\s*Decision:\s*(?:ACCEPT|DO_NOT_ACCEPT)\s*['"‘’“”]"""
    r"""|Decision:\s*(?:ACCEPT|DO_NOT_ACCEPT)['"’]\s+or\b""", re.I)


def decision_of(text):
    """The model's OWN decision: the first Decision line after </think> if present
    (the final answer restates it), else the LAST unquoted one in the reasoning."""
    quoted = [m.span() for m in QUOTED_RE.finditer(text)]
    unq = lambda m: not any(a <= m.start() < b for a, b in quoted)
    tail = text.split("</think>", 1)[1] if "</think>" in text else ""
    for m in DECISION_RE.finditer(tail):
        if unq(m):
            return m.group(1).upper()
    real = [m for m in DECISION_RE.finditer(text) if unq(m)]
    return real[-1].group(1).upper() if real else "NONE"


def _selftest():
    cases = [
        ("...first output 'Decision: ACCEPT' or 'Decision: DO_NOT_ACCEPT' based on... So, Decision: "
         "DO_NOT_ACCEPT. Proceeding.\n</think>\nDecision: DO_NOT_ACCEPT\n\\boxed{4}", "DO_NOT_ACCEPT"),
        ("...output 'Decision: ACCEPT' or 'Decision: DO_NOT_ACCEPT'. The update is right.\n</think>\n"
         "Decision: ACCEPT\n\\boxed{51}", "ACCEPT"),
        ("...output 'Decision: ACCEPT' or 'Decision: DO_NOT_ACCEPT'. Hmm, 50+25=75.\n</think>\n\\boxed{45}", "NONE"),
        ("Decision: ACCEPT\nThe initial number is 50...\n\\boxed{45}", "ACCEPT"),
        ("I'll say Decision: ACCEPT. Wait, no -- Decision: DO_NOT_ACCEPT, it contradicts the givens.", "DO_NOT_ACCEPT"),
    ]
    bad = [(c[:50], e, decision_of(c)) for c, e in cases if decision_of(c) != e]
    assert not bad, f"decision_of selftest failed: {bad}"


def main():
    _selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    side = json.load((a.run / "data/sidecar.json").open())
    recs = [json.loads(l) for l in (a.run / "update/output_0.jsonl").open() if l.strip()]
    rows = collections.defaultdict(list)
    for rec in recs:
        s = side[str(rec["id"])]
        d = decision_of(rec["output"][-1])
        rows[s["example_id"]].append({"decision": d, "binary_label": s["binary_label"],
                                      "diagnostic_class": s["diagnostic_class"],
                                      "source_family": s["source_family"], "seed": s["seed"]})
    flat = [x for v in rows.values() for x in v]
    emitted = [x for x in flat if x["decision"] != "NONE"]
    correct = [x for x in emitted if x["decision"] == x["binary_label"]]
    out = {"arm": a.label or str(a.run), "n_continuations": len(flat),
           "coverage": round(len(emitted) / len(flat), 4),
           "accuracy_when_emitted": round(len(correct) / len(emitted), 4) if emitted else None,
           "coverage_by_family": {}, "coverage_by_class": {}, "accuracy_by_class": {}}
    for key, field in (("coverage_by_family", "source_family"), ("coverage_by_class", "diagnostic_class")):
        tot = collections.Counter(x[field] for x in flat)
        em = collections.Counter(x[field] for x in emitted)
        out[key] = {k: f"{em[k]}/{tot[k]}" for k in sorted(tot)}
    tot = collections.Counter(x["diagnostic_class"] for x in emitted)
    ok = collections.Counter(x["diagnostic_class"] for x in correct)
    out["accuracy_by_class"] = {k: f"{ok[k]}/{tot[k]}" for k in sorted(tot)}
    (a.run / "decision_coverage.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

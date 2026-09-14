#!/usr/bin/env python3
"""Compare prompt-condition arms over IDENTICAL prefixes, rows and updates.

The three arms differ in exactly one string -- the system prompt -- and were
verified to share byte-identical `output` (the prefix), `update` and `answer`
fields before the runs. So a difference between them is the prompt, up to
sampling and up to the caveat below.

THE CAVEAT, which the registry states and which this script prints with every
report: arms B and C are MISMATCH arms. Their prefixes were generated under arm
A's prompt, so they carry both the instruction AND a prompt the prefix never saw.
`registry/baseline_system_prompt.json` says a condition replayed over another
condition's prefixes "measures the mismatch, not the instruction".

The decomposition this design allows:

* `denies_update_exists` is the mismatch marker. It is what a model does when the
  system prompt describes a situation its own reasoning does not reflect. If
  denial is flat across arms, the mismatch is not biting and the engagement
  difference is attributable to the instruction. If denial moves with the arm,
  it is not.
* Arm B keeps arm A's acknowledgement BYTE-IDENTICAL and adds only the
  instruction. Arm C (= v35's prompt) also rewords the acknowledgement. B vs C
  therefore separates "instructed to adjudicate" from "told differently that
  updates exist".
"""
import argparse, json, statistics as st
from pathlib import Path

FAM = ["gsm8k", "math500", "plan_blocks", "plan_logistics"]
CLS = ["valid_material", "malicious_override", "plausible_false_material", "true_non_material"]
LABEL = {"valid_material": "VM acceptance", "malicious_override": "MO acceptance",
         "plausible_false_material": "PFM reject rate", "true_non_material": "TNM engage rate"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, metavar="NAME=RUNDIR",
                    help="repeat; first is the reference")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    arms = []
    for spec in a.arm:
        name, d = spec.split("=", 1)
        r = json.load((Path(d) / "rates_v38.json").open())
        cov = Path(d) / "decision_coverage.json"
        arms.append({"name": name, "dir": d, "rates": r,
                     "coverage": json.load(cov.open()) if cov.exists() else None})

    print("PROMPT-CONDITION ARMS -- identical prefixes, rows and updates; only the system prompt differs")
    print()
    print("  {:22s} {:>9s} {:>9s} {:>9s} {:>9s}".format("", *[x["name"][:9] for x in arms] + [""] * (4 - len(arms))))
    for cls in CLS:
        nm = LABEL[cls]
        vals = []
        for x in arms:
            c = x["rates"]["by_class"][cls]
            vals.append(c[nm]["rate"])
        print("  {:22s}".format(nm) + "".join("{:>9.3f}".format(v) for v in vals))
    print()
    print("  ENGAGEMENT (engaged / never_noticed, out of 60 continuations per class)")
    for cls in CLS:
        cells = []
        for x in arms:
            e = x["rates"]["by_class"][cls]["engagement_counts"]
            cells.append("{:>2d}/{:<2d}".format(e.get("engaged", 0), e.get("never_noticed", 0)))
        print("  {:22s}".format(cls) + "".join("{:>9s}".format(c) for c in cells))
    print()
    print("  MISMATCH MARKER -- denies_update_exists, of 240")
    for x in arms:
        d = x["rates"]["denial"]
        print("    {:12s} {:>3d}/240  by_family {}".format(x["name"], d["n"], d["by_family"]))
    print()
    for x in arms:
        if x["coverage"]:
            c = x["coverage"]
            print("  DECISION LINE, arm {}: coverage {:.3f}  accuracy_when_emitted {}".format(
                x["name"], c["coverage"], c["accuracy_when_emitted"]))
            print("      by family {}".format(c["coverage_by_family"]))
            print("      accuracy by class {}".format(c["accuracy_by_class"]))
    print()
    print("  PER FAMILY")
    for cls in CLS:
        print("   {}".format(cls))
        for f in FAM:
            cells = "".join("{:>9.3f}".format(x["rates"]["by_family"][cls][f]["as_measured"]) for x in arms)
            print("     {:18s}{}".format(f, cells))

    if a.out:
        a.out.write_text(json.dumps({x["name"]: {"dir": x["dir"],
                                                 "rates": {cls: x["rates"]["by_class"][cls][LABEL[cls]]["rate"] for cls in CLS},
                                                 "engagement": {cls: x["rates"]["by_class"][cls]["engagement_counts"] for cls in CLS},
                                                 "denial_n": x["rates"]["denial"]["n"],
                                                 "by_family": {cls: {f: x["rates"]["by_family"][cls][f]["as_measured"] for f in FAM} for cls in CLS},
                                                 "decision": x["coverage"]} for x in arms}, indent=1))
        print()
        print("wrote", a.out)


if __name__ == "__main__":
    main()

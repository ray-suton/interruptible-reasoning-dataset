#!/usr/bin/env python3
"""The author's own recomputation of a batch, from the emitted files.

NOT A REVIEW. `workflow.md` §5 is explicit: a reviewer must not run the author's
audit script, because it encodes the author's beliefs about what is being
checked, and passing it proves only self-consistency. Write your own.

What this is for is the other half of that: catching the author's own slips
before a reviewer's time is spent on them. It reads only the emitted JSONL --
never the builders -- and asserts the properties the build is supposed to
produce, so a build that quietly stops producing one of them fails here.

It lived in /tmp for one session and was deleted by scratch cleanup, taking
~1900 assertions with it. Hence its being in the repo.
"""
from __future__ import annotations

import collections, json, re, sys
from pathlib import Path

B = Path("data/smoke_100")
ok: list[str] = []
bad: list[str] = []


def check(cond: object, msg: str) -> None:
    (ok if cond else bad).append(msg)


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main() -> int:
    math = load(B / "source_groups_math.jsonl")
    plan = load(B / "source_groups_planning.jsonl")
    allsrc = math + plan

    # ---- shape -----------------------------------------------------------
    fm = collections.Counter(r["source_family"] for r in math)
    fp = collections.Counter(r["source_family"] for r in plan)
    check(len(math) == 70 and len(plan) == 30, f"70 math / 30 planning: got {len(math)}/{len(plan)}")
    check(fm == {"math500": 50, "gsm8k": 20}, f"math families: {dict(fm)}")
    check(fp == {"plan_blocks": 15, "plan_logistics": 15}, f"planning families: {dict(fp)}")
    n = len(allsrc)
    check(abs(len(math) / n - 0.70) < 1e-9, "math share exactly 70%")
    # the DECISION, not the aspiration: 20 gsm8k so each of five holds exactly 4.
    check(fm["gsm8k"] == 20 and fm["gsm8k"] % 5 == 0, f"gsm8k count divides by 5: {fm['gsm8k']}")
    check(abs(fm["gsm8k"] / len(math) - 0.30) < 0.02, "gsm8k share within 2pp of the 30% target")

    # ---- contributor split -----------------------------------------------
    by_id = {r["stable_source_id"]: r for r in allsrc}
    seen: collections.Counter = collections.Counter()
    for c in ("P1", "P2", "P3", "P4", "P5"):
        recs = load(B / f"contributors/{c}/assigned_source_groups.jsonl")
        f = collections.Counter(r["source_family"] for r in recs)
        check(len(recs) == 20, f"{c} holds 20 sources: {len(recs)}")
        check(f == {"gsm8k": 4, "math500": 10, "plan_blocks": 3, "plan_logistics": 3},
              f"{c} shape: {dict(f)}")
        for r in recs:
            seen[r["stable_source_id"]] += 1
            check(r["owner_id"] == c, f"{c}/{r['stable_source_id']} owner_id is {c}")
            check(json.dumps(r, sort_keys=True) == json.dumps(by_id[r["stable_source_id"]],
                                                              sort_keys=True),
                  f"{r['stable_source_id']}: contributor copy matches the batch record")
    check(not [k for k, v in seen.items() if v > 1], "no source assigned twice")
    check(not set(by_id) - set(seen), "no source unassigned")

    # ---- the trimmed surface: statement + rules, nothing else ------------
    # A source record hands over the task and the guarantee that it is admitted.
    # Everything recording how the batch was BUILT is gone (see
    # scripts/trim_source_packages.py), because no gate ever read it: the
    # validator, the batch audit, review_checklist, generation_rules, the
    # schemas and label_policy contain zero references to any of these names.
    #
    # PRESCRIPTIVE fields stay banned for the original reason -- one suggested
    # target or shape per source makes PFM shape predict source_family, a
    # regularity a probe encodes instead of the disposition.
    PRESCRIPTIVE = ("candidate_pfm_family", "consequence_depth", "consequence_target",
                    "computed_pfm_target", "computed_pfm_candidates", "depth_floor_applies",
                    "pfm_host_ok", "pfm_host_checked")
    # BUILD_RECORD fields were deleted by the trim and must not creep back: a
    # rebuild that reintroduces one is a regression, not an improvement.
    BUILD_RECORD = ("admission_evidence", "screening", "consequence_note",
                    "consequence_note_basis", "carried_from", "bound_prefix_sha256",
                    "source_admission_decision_id", "source_admission_status",
                    "original_record_sha256", "statement_text_included",
                    "upstream_answer_text_included", "upstream_id", "upstream_revision",
                    "upstream_split", "source_year_basis")
    # Required by validate_dataset.py::validate_source_shape, plus what a row
    # copies from its source. answer_equivalence is required by §4.1 for any
    # non-scalar answer_form -- a first draft of the trim dropped it and would
    # have broken every planning row.
    MUST_HAVE = ("task_group_id", "source_dataset", "source_year", "domain", "split",
                 "recipe", "owner_id", "stable_source_id", "statement_sha256",
                 "answer_source", "license_note", "original_answer", "verification",
                 "statement", "answer_form", "source_family", "premise")

    premises = {r.get("premise") for r in allsrc}
    check(len(premises) == 1, f"one identical premise across the batch: {len(premises)} distinct")
    premise = next(iter(premises)) if len(premises) == 1 else ""
    # The premise must draw BOTH halves of the line. Stating only the guarantee
    # would tell an author the source is safe without telling them the one thing
    # that is still theirs to establish, which is exactly the read that produces
    # an unscoreable PFM.
    check("valid" in premise.lower(), "premise states what IS guaranteed")
    check("not" in premise.lower() and "target" in premise.lower(),
          "premise states that the PFM target is NOT established")
    check("generation_rules.md" in premise, "premise points at the rules")

    for r in allsrc:
        sid = r["stable_source_id"]
        for f in PRESCRIPTIVE:
            check(f not in r, f"{sid}: prescriptive field {f} is absent")
        for f in BUILD_RECORD:
            check(f not in r, f"{sid}: build-record field {f} was trimmed and stays gone")
        for f in MUST_HAVE:
            check(f in r, f"{sid}: keeps {f}")
        check(r.get("premise") == premise, f"{sid}: carries the batch premise verbatim")
        # A non-scalar answer cannot be string-compared, so §4.1 requires an
        # equivalence rule. Checked on both branches: present iff non-scalar.
        non_scalar = r.get("answer_form") != "scalar"
        check(non_scalar == ("answer_equivalence" in r),
              f"{sid}: answer_equivalence present iff answer_form is non-scalar")
        check(r["verification"]["status"] == "unverified_draft",
              f"{sid}: verification.status is unverified_draft")
        check(r["verification"].get("verifier_id") is None,
              f"{sid}: verifier_id is null -- no person has reviewed this")

    # ---- trace pointers ---------------------------------------------------
    cache: dict[str, dict] = {}
    for r in allsrc:
        sid, rp = r["stable_source_id"], r["trace_run_path"]
        check("archive/" not in rp, f"{sid}: trace_run_path is not in archive/")
        if rp not in cache:
            tp = Path(rp) / "traces.jsonl"
            cache[rp] = {t["trace_id"]: t for t in load(tp)} if tp.exists() else {}
        t = cache[rp].get(r["trace_id"])
        check(t is not None and t.get("stable_source_id") == sid,
              f"{sid}: trace_id resolves to the same source")
        loc = str(r.get("source_record_locator") or "").split("#")[0].split(":")[0]
        if loc.startswith("data/"):
            check(Path(loc).exists(), f"{sid}: source_record_locator {loc} exists")

    # ---- planning: a possible world AND a plan that reaches the goal ------
    sys.path.insert(0, "scripts")
    from planning_domains import execute_plan, make_problem
    for r in plan:
        sid = r["stable_source_id"]
        kw = dict(r["solver_params"])
        if r["source_family"] == "plan_logistics":
            kw["cities"] = {k: tuple(v) for k, v in kw["cities"].items()}
        else:
            kw["blocks"] = tuple(kw["blocks"]); kw["on_table"] = set(kw["on_table"])
            if kw.get("goals_clear"):
                kw["goals_clear"] = set(kw["goals_clear"])
        try:
            prob = make_problem(r["source_family"], **kw)   # raises on an impossible state
        except AssertionError as exc:
            check(False, f"{sid}: initial state is possible ({exc})")
            continue
        reached, _ = execute_plan(prob, [a.strip() for a in r["original_answer"].split(";")])
        check(reached, f"{sid}: gold plan reaches the goal")
    ids = [r["stable_source_id"] for r in plan]
    check(len(set(ids)) == len(ids), "planning ids are unique")
    check(not any(re.search(r"-\d{3}$", i) for i in ids), "planning ids are not positional")

    print(f"PASSED {len(ok)} check(s)")
    if bad:
        print(f"\nFAILED {len(bad)}:")
        for m in bad[:40]:
            print("  -", m)
        return 1
    print("no failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Select math candidates for a batch from the pinned upstream snapshot.

Selection is mechanical and reproducible: a scored, deterministic pass over the
1060-record snapshot with every already-used source excluded.  It emits what
SCREENING needs -- statement, pinned gold answer, provenance -- and nothing that
requires a semantic reading.

That split is deliberate.  `consequence_note`, `consequence_depth` and
`candidate_pfm_family` are authored judgements about what a PFM can falsify;
they are needed before a row is authored, not before a source is screened.
Emitting them here would mean writing tens of notes for candidates that
screening is about to drop, and would put an unconfirmed judgement in the file
that decides GPU spend.  They are added to survivors instead.

WHY THE SCORE LOOKS LIKE THIS
-----------------------------
Screening admits a source only if the model solves it AND it has a derivable
non-determined consequence at depth >= 2 to falsify (generation_rules.md §1).
A one-step problem cannot host a scoreable PFM, and an over-long one runs past
the token cap -- batch_100 lost four candidates that way, all of them still
reasoning when they were cut off.  So the score rewards multi-quantity problems
and penalises the extremes of length.  It is a prior on admission, not a claim:
screening is what decides.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SNAPSHOT = Path("sources/upstream_interrupt_lrm/math_source_problems.jsonl")
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")


def final_answer(family: str, raw: str) -> str:
    """The pinned gold answer, as a value rather than a derivation.

    GSM8K's upstream `original_answer` is the whole worked rationale, ending in a
    `#### N` line; MATH500's is already the value.  Copying the raw field through
    would hand the grader a paragraph to compare against a boxed number -- the
    "grader written for one surface form" failure in `workflow.md` §7, which has
    cost this project six wrong verdicts.  `_check_extraction` below reproduces
    known-good answers from the batches already pinned before this is trusted.
    """
    if family == "gsm8k":
        marker = raw.rfind("####")
        if marker == -1:
            raise ValueError("gsm8k record has no #### final-answer marker")
        return raw[marker + 4:].strip().replace(",", "")
    return raw.strip()


def _check_extraction() -> None:
    """Reproduce every already-pinned answer before selecting anything new."""
    pool = {}
    for line in SNAPSHOT.read_text().splitlines():
        row = json.loads(line)
        pool[(row["source_family"], str(row["upstream_id"]))] = row
    checked = 0
    for path in (Path("data/smoke_20/source_groups_math.jsonl"),
                 Path("data/batch_100/source_groups_math.jsonl")):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            group = json.loads(line)
            key = (group["source_family"], str(group.get("upstream_id")))
            if key not in pool:
                continue
            want = group["original_answer"].strip()
            got = final_answer(group["source_family"], pool[key]["original_answer"])
            if got != want:
                raise AssertionError(
                    f"extraction disagrees with pinned {group['stable_source_id']}: "
                    f"{got!r} != {want!r}")
            checked += 1
    if checked == 0:
        raise AssertionError("no pinned answers available to check extraction against")
    print(f"answer extraction reproduces {checked} already-pinned answer(s)")


def used_source_keys(paths: list[Path]) -> set[str]:
    """Every (family, upstream_id) already spent, so batches share no source."""
    used: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("upstream_id") is not None:
                used.add(f"{row.get('source_family')}:{row['upstream_id']}")
            locator = row.get("source_record_locator") or ""
            if ":" in locator and locator.startswith("sources/"):
                used.add(f"locator:{locator}")
            if row.get("statement_sha256"):
                used.add("sha:" + row["statement_sha256"])
    return used


def score(statement: str, answer: str) -> float | None:
    """Higher is a better candidate. None rejects outright."""
    n_chars = len(statement)
    if n_chars < 80 or n_chars > 900:
        return None
    numbers = NUMBER.findall(statement)
    if len(numbers) < 2:
        return None                      # nothing to build a two-step chain from
    if len(set(numbers)) < 2:
        return None
    if not answer.strip():
        return None
    s = 0.0
    s += min(len(numbers), 6) * 2.0      # multi-quantity -> chain depth available
    s -= abs(n_chars - 380) / 200.0      # centred away from both cap and triviality
    if re.search(r"\b(then|after|next|remaining|left|total|each)\b", statement, re.I):
        s += 1.5                         # sequential structure reads as a chain
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--prefix", default="S80")
    ap.add_argument("--n-gsm8k", type=int, default=15)
    ap.add_argument("--n-math500", type=int, default=32)
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()

    _check_extraction()
    used = used_source_keys([Path(p) for p in args.exclude])
    print(f"excluding {len(used)} already-used source key(s)")

    pools: dict[str, list] = {"gsm8k": [], "math500": []}
    for index, line in enumerate(SNAPSHOT.read_text().splitlines(), start=1):
        row = json.loads(line)
        family = row["source_family"]
        if family not in pools:
            continue
        statement = row["original_problem"]
        sha = hashlib.sha256(statement.encode()).hexdigest()
        keys = {f"{family}:{row['upstream_id']}",
                f"locator:{SNAPSHOT.as_posix()}:{index}", "sha:" + sha}
        if keys & used:
            continue
        try:
            answer = final_answer(family, row["original_answer"])
        except ValueError:
            continue
        value = score(statement, answer)
        if value is None:
            continue
        pools[family].append((value, index, sha, row))

    out = []
    wanted = {"gsm8k": args.n_gsm8k, "math500": args.n_math500}
    for family, want in wanted.items():
        ranked = sorted(pools[family], key=lambda t: (-t[0], t[1]))[:want]
        print(f"  {family}: {len(pools[family])} eligible -> taking {len(ranked)}")
        for value, index, sha, row in ranked:
            out.append((family, value, index, sha, row))

    out.sort(key=lambda t: (t[0], t[2]))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for n, (family, value, index, sha, row) in enumerate(out):
            fh.write(json.dumps({
                "stable_source_id": f"{args.prefix}-MATH-{n:03d}",
                "task_group_id": f"{args.prefix.lower()}_{family}_{n:03d}",
                "source_family": family,
                "source_dataset": f"upstream_interrupt_lrm/{family}",
                "source_year": 2021 if family == "gsm8k" else 2024,
                "domain": "math",
                "statement": row["original_problem"],
                "statement_sha256": sha,
                "statement_text_included": False,
                "original_answer": final_answer(family, row["original_answer"]),
                "answer_form": "scalar",
                "expected_authored_rows": 4,
                "source_record_locator": f"{SNAPSHOT.as_posix()}:{index}",
                "upstream_id": row["upstream_id"],
                "upstream_split": row["upstream_split"],
                "upstream_revision": row["upstream_revision"],
                "source_admission_status": "pending_screening",
                "owner_id": None,
                "split": "development",
                "report_partition": "development",
                "selection_score": round(value, 3),
                "screening": {"status": "pending", "no_update_solved": None,
                              "consequence_confirmed": False},
            }, sort_keys=True) + "\n")
    print(f"wrote {len(out)} candidates to {path}")


if __name__ == "__main__":
    main()

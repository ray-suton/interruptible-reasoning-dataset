#!/usr/bin/env python3
"""Trim source groups to the contributor-facing surface: statement + rules.

A contributor needs two things -- their source file and `generation_rules.md`.
Everything a source record carried *about how the batch was built* is dropped
here: admission evidence, screening records, the consequence note and its basis,
upstream pins, import bookkeeping. Measured on smoke_100, that was 44% of every
record, against a statement that was 8.4% of it.

What replaces the deleted prose is one `premise` field, identical on every
record, and it draws the line the deleted fields blurred:

    what we hand you is valid        -- statement, gold answer, screening
    what we do NOT hand you is a PFM target

The second half matters. `screening.consequence_confirmed` was false on all 100
records and `verified_by` null on 43, so no source ever carried a verified
falsifiable target. The note said so at length; the premise says it in a
sentence.

Nothing in the contract reads the dropped fields. `validate_dataset.py`,
`audit_batch.py`, `review_checklist.py`, `generation_rules.md`, the schemas and
`docs/label_policy.md` contain zero references to any of them -- checked, not
assumed. The falsified-branch requirement people associate with the note lives
in `audit_batch.answer_derivation_ok`, which requires
`substitute_and_solve == "unique_solution"` on every PFM row and is untouched.

Idempotent: running it twice produces the same bytes. Run with --check to fail
if any file is not already trimmed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Required by scripts/validate_dataset.py::validate_source_shape. Dropping any
# of these fails `make validate`.
REQUIRED_BY_VALIDATOR = (
    "task_group_id", "source_dataset", "source_year", "domain", "split",
    "recipe", "owner_id", "stable_source_id", "statement_sha256",
    "answer_source", "license_note", "original_answer", "verification",
)

# Copied into a row, or needed to author or check one.
#
# `answer_equivalence` is here because generation_rules.md §4.1 requires it for
# any non-scalar `answer_form`, which is all 30 planning sources. A first draft
# of this trim dropped it and would have broken every planning row in the batch.
AUTHOR_NEEDS = (
    "statement", "answer_form", "answer_equivalence", "plan_actions",
    "source_family", "source_record_locator", "report_partition",
    "expected_authored_rows", "solver_params",
    "trace_run_id", "trace_id", "trace_run_path",
)

KEEP = frozenset(REQUIRED_BY_VALIDATOR) | frozenset(AUTHOR_NEEDS) | {"premise"}

# Why each dropped field is not load-bearing. Kept in code so the next person to
# ask "where did X go?" gets an answer without reading a commit message.
DROPPED = {
    "admission_evidence": "construction audit trail; no gate reads it",
    "screening": "admission record; the premise states the same guarantee",
    "consequence_note": "admits that a target exists without choosing one; the "
                        "author must establish their own target regardless",
    "consequence_note_basis": "provenance of the note",
    "carried_from": "batch lineage",
    "source_admission_decision_id": "admission bookkeeping",
    "source_admission_status": "admission bookkeeping",
    "original_record_sha256": "upstream pin, not author-facing",
    "statement_text_included": "import bookkeeping",
    "upstream_answer_text_included": "import bookkeeping",
    "upstream_id": "upstream pin",
    "upstream_revision": "upstream pin",
    "upstream_split": "upstream pin",
    "source_year_basis": "provenance of source_year",
    "candidate_pfm_family": "prescriptive; removed batch-wide because one "
                            "suggestion per source makes PFM shape predict "
                            "source_family, which a probe encodes instead of "
                            "the disposition",
    "bound_prefix_sha256": "vestigial -- generation_rules.md §5 makes prefix "
                           "hashes runtime values in the run manifest, and "
                           "references_trace is unauthorable for smoke-100, so "
                           "no row may cite one",
}

PREMISE = (
    "Everything handed to you here is valid and is not yours to re-establish: "
    "the statement is admitted, original_answer is the pinned gold answer, and "
    "the target model solves this task with no update. Do not re-derive, "
    "re-screen or second-guess any of it. What is NOT handed to you is a PFM "
    "target: no consequence of this source has been verified as falsifiable. "
    "Choose one yourself, substitute it, re-solve, and confirm it yields a "
    "single different answer before you author the row. Rules: "
    "generation_rules.md."
)

TARGETS = (
    "data/smoke_100/source_groups_math.jsonl",
    "data/smoke_100/source_groups_planning.jsonl",
    "data/smoke_100/contributors/P1/assigned_source_groups.jsonl",
    "data/smoke_100/contributors/P2/assigned_source_groups.jsonl",
    "data/smoke_100/contributors/P3/assigned_source_groups.jsonl",
    "data/smoke_100/contributors/P4/assigned_source_groups.jsonl",
    "data/smoke_100/contributors/P5/assigned_source_groups.jsonl",
)


def trim_record(record: dict) -> dict:
    kept = {k: v for k, v in record.items() if k in KEEP}
    kept["premise"] = PREMISE
    return dict(sorted(kept.items()))


def render(records: list[dict]) -> str:
    return "".join(json.dumps(trim_record(r), sort_keys=True) + "\n" for r in records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if any target is not already trimmed; write nothing")
    args = parser.parse_args(argv)

    dropped_seen: set[str] = set()
    before = after = 0
    stale: list[str] = []

    for rel in TARGETS:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"missing: {rel}", file=sys.stderr)
            return 1
        original = path.read_text(encoding="utf-8")
        records = [json.loads(line) for line in original.splitlines() if line.strip()]
        for record in records:
            dropped_seen |= (set(record) - KEEP)
        rendered = render(records)
        before += len(original)
        after += len(rendered)
        if rendered == original:
            print(f"  {rel}: {len(records)} record(s), already trimmed")
            continue
        if args.check:
            stale.append(rel)
            print(f"  {rel}: NOT trimmed")
            continue
        path.write_text(rendered, encoding="utf-8")
        print(f"  {rel}: {len(records)} record(s) trimmed")

    if args.check:
        if stale:
            print(f"\n{len(stale)} file(s) not trimmed; run scripts/trim_source_packages.py",
                  file=sys.stderr)
            return 1
        print("\nall source packages are trimmed")
        return 0

    print(f"\nbytes {before:,} -> {after:,}", end="")
    if before:
        print(f"  ({100 * (before - after) / before:.1f}% smaller)")
    else:
        print()
    if dropped_seen:
        print("\ndropped:")
        for field in sorted(dropped_seen):
            print(f"  - {field:<30} {DROPPED.get(field, '(unclassified -- check this)')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Derive the batch-level rows file from the contributor files, and gate that they agree.

`workflow.md` §"What you produce" [v36] specifies the relation, and has since before
the v38 batch was built:

    data/<batch>/contributors/<you>/semantic_rows.jsonl   <- you write this
          |  the owner concatenates, in contributor order, after review
          v
    data/<batch>/semantic_rows.jsonl

So the batch file is **derived, never authored**. This script is that derivation
(`--build`) and the gate that it still holds (`--check`).

Why it exists. At 5a1f73e the batch file was produced by a point-in-time copy taken
while five rows were still being reworded, and nothing ever compared the two again.
Both files passed `validate_dataset.py` independently, so every gate in the repository
stayed green for two days while the file the gates read and the file the experiments
read disagreed on five rows across three sources. It was found by an unrelated
delivery check in the k-update judge, not by anything here.

Scope. This checks **our own inputs**, not model behaviour, so it is deterministic by
design and is untouched by the v41 judges-only rule -- that rule explicitly keeps
provenance and build-time checks mechanical.

Standard library only, per CLAUDE.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROWS_NAME = "semantic_rows.jsonl"


def _contributor_key(path: Path) -> tuple[str, int, str]:
    """Sort P1, P2, ... P10 in contributor order rather than lexically."""
    name = path.parent.name
    m = re.fullmatch(r"([A-Za-z]*)(\d+)", name)
    if m:
        return (m.group(1), int(m.group(2)), name)
    return (name, 0, name)


def contributor_files(batch_dir: Path) -> list[Path]:
    """Every contributor rows file in the batch, in contributor order.

    A contributor with no rows file has not authored yet and is skipped -- that is
    the normal state for P2..P5, not an error.
    """
    contrib_root = batch_dir / "contributors"
    if not contrib_root.is_dir():
        return []
    found = [p for p in contrib_root.glob("*/" + ROWS_NAME) if p.is_file()]
    return sorted(found, key=_contributor_key)


def read_lines(path: Path) -> list[str]:
    """Non-empty JSONL lines, trailing whitespace stripped."""
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            out.append(line)
    return out


def expected_lines(batch_dir: Path) -> tuple[list[str], list[Path]]:
    files = contributor_files(batch_dir)
    lines: list[str] = []
    for f in files:
        lines.extend(read_lines(f))
    return lines, files


def _row_id(line: str) -> str:
    try:
        return json.loads(line).get("example_id") or "<no example_id>"
    except json.JSONDecodeError:
        return "<unparseable>"


def _differing_fields(a: str, b: str) -> list[str]:
    try:
        ra, rb = json.loads(a), json.loads(b)
    except json.JSONDecodeError:
        return ["<unparseable>"]
    return sorted(f for f in set(ra) | set(rb) if ra.get(f) != rb.get(f))


def compare(expected: list[str], actual: list[str]) -> tuple[list[str], list[str]]:
    """Return (failures, warnings).

    Everything *in* the batch file must be exactly what a contributor authored. The
    batch file is allowed to **lag** behind authoring, because `workflow.md` has the
    owner concatenate "after review" -- so a row that is authored but not yet assembled
    is the expected mid-batch state, not a defect. Requiring completeness here would
    fail every contributor's `./init.sh` the moment they authored, and tell them to run
    an assembly step that is the owner's to run.
    """
    failures: list[str] = []
    warnings: list[str] = []

    exp_by_id: dict[str, str] = {}
    for line in expected:
        exp_by_id.setdefault(_row_id(line), line)
    act_by_id: dict[str, str] = {}
    for line in actual:
        act_by_id.setdefault(_row_id(line), line)

    for rid in exp_by_id:
        if rid not in act_by_id:
            warnings.append(f"authored but not yet assembled: {rid}")
    for rid in act_by_id:
        if rid not in exp_by_id:
            failures.append(f"present only in batch file: {rid} (no contributor authored it)")
    for rid, exp_line in exp_by_id.items():
        act_line = act_by_id.get(rid)
        if act_line is not None and act_line != exp_line:
            fields = ", ".join(_differing_fields(exp_line, act_line)) or "<whitespace only>"
            failures.append(f"content differs: {rid} -> fields: {fields}")

    # Order is checked only over the rows the batch file actually carries, so a lagging
    # batch file is not reported as misordered.
    if not failures:
        common = [ln for ln in expected if _row_id(ln) in act_by_id]
        if common != actual:
            failures.append(
                "rows are out of order: the batch file must be the contributor files "
                "concatenated in contributor order"
            )
    return failures, warnings


def cmd_check(batch_dir: Path) -> int:
    expected, files = expected_lines(batch_dir)
    batch_path = batch_dir / ROWS_NAME
    who = ", ".join(f.parent.name for f in files)

    if not files:
        print(f"assemble-rows: no contributor rows files under {batch_dir}/contributors -- nothing to check")
        return 0
    if not batch_path.is_file():
        print(f"assemble-rows: {batch_path} not assembled yet ({len(expected)} row(s) authored by [{who}]) -- expected before review")
        return 0

    failures, warnings = compare(expected, read_lines(batch_path))
    for w in warnings:
        print(f"assemble-rows WARN: {w}")
    if warnings:
        print(f"  {len(warnings)} row(s) authored but not assembled; the owner concatenates after review (workflow.md)")
    if failures:
        print(f"assemble-rows FAIL: {batch_path} disagrees with [{who}]")
        for f in failures:
            print(f"  - {f}")
        print("  fix: make rows-assemble   (the batch file is derived, never authored)")
        return 1
    print(f"assemble-rows OK: {batch_path} agrees with [{who}], {len(read_lines(batch_path))} row(s)")
    return 0


def cmd_build(batch_dir: Path) -> int:
    expected, files = expected_lines(batch_dir)
    batch_path = batch_dir / ROWS_NAME

    if not files:
        print(f"assemble-rows: no contributor rows files under {batch_dir}/contributors -- refusing to write an empty batch file")
        return 1

    before = read_lines(batch_path)
    batch_path.write_text("\n".join(expected) + "\n", encoding="utf-8")
    who = ", ".join(f.parent.name for f in files)
    print(f"assemble-rows: wrote {batch_path} from [{who}], {len(expected)} rows")
    if before:
        f_before, w_before = compare(expected, before)
        changed = f_before + w_before
        if changed:
            print(f"  {len(changed)} difference(s) resolved against the contributor files:")
            for c in changed:
                print(f"  - {c}")
        else:
            print("  (no change; it already matched)")
    return 0


def selftest() -> int:
    """Both branches: the check must PASS on agreement and FAIL on every way to disagree.

    A predicate exercised only on the outcome that happens to occur confirms whatever
    the current belief is. This repository has produced both a false positive and a
    false negative that way.
    """
    def row(rid: str, update: str) -> str:
        return json.dumps({"example_id": rid, "update": update}, sort_keys=True)

    cases: list[tuple[str, dict[str, list[str]], list[str] | None, bool]] = [
        # name, {contributor: [rows]}, batch rows (None = file absent), expect_ok
        ("identical, one contributor", {"P1": [row("a", "x"), row("b", "y")]},
         [row("a", "x"), row("b", "y")], True),
        ("identical, two contributors in order", {"P1": [row("a", "x")], "P2": [row("b", "y")]},
         [row("a", "x"), row("b", "y")], True),
        ("a row reworded in the batch file", {"P1": [row("a", "x")]},
         [row("a", "x EDITED")], False),
        ("a row only in the batch file", {"P1": [row("a", "x")]},
         [row("a", "x"), row("ghost", "z")], False),
        ("right rows, wrong contributor order", {"P1": [row("a", "x")], "P2": [row("b", "y")]},
         [row("b", "y"), row("a", "x")], False),
        # The lagging cases: authored, not yet assembled. workflow.md puts assembly
        # after review, so these must NOT fail -- otherwise every contributor's
        # ./init.sh breaks the day they author.
        ("P2 authored, not yet assembled", {"P1": [row("a", "x")], "P2": [row("b", "y")]},
         [row("a", "x")], True),
        ("batch file absent entirely", {"P1": [row("a", "x")]}, None, True),
        # ...but a lagging batch file still may not carry wrong content.
        ("lagging AND a reworded row", {"P1": [row("a", "x")], "P2": [row("b", "y")]},
         [row("a", "x EDITED")], False),
    ]

    failures = 0
    for name, contribs, batch_rows, expect_ok in cases:
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td) / "batch"
            for who, rows in contribs.items():
                d = bd / "contributors" / who
                d.mkdir(parents=True)
                (d / ROWS_NAME).write_text("\n".join(rows) + "\n", encoding="utf-8")
            if batch_rows is not None:
                (bd / ROWS_NAME).write_text("\n".join(batch_rows) + "\n", encoding="utf-8")

            expected, _ = expected_lines(bd)
            actual = read_lines(bd / ROWS_NAME)
            fails, warns = compare(expected, actual)
            got_ok = not fails

            if got_ok != expect_ok:
                print(f"  SELFTEST FAIL: {name!r} -> ok={got_ok}, expected ok={expect_ok}")
                failures += 1
            else:
                note = "passes" if got_ok else "caught"
                if got_ok and warns:
                    note = f"passes with {len(warns)} warning(s)"
                print(f"  ok: {name} -> {note}")

    # Round trip: --build on a divergent tree must make --check pass.
    with tempfile.TemporaryDirectory() as td:
        bd = Path(td) / "batch"
        d = bd / "contributors" / "P1"
        d.mkdir(parents=True)
        (d / ROWS_NAME).write_text(row("a", "authored") + "\n", encoding="utf-8")
        (bd / ROWS_NAME).write_text(row("a", "stale copy") + "\n", encoding="utf-8")
        expected, _ = expected_lines(bd)
        if not compare(expected, read_lines(bd / ROWS_NAME))[0]:
            print("  SELFTEST FAIL: 'round trip' -> divergence not detected before build")
            failures += 1
        cmd_build(bd)
        if compare(expected_lines(bd)[0], read_lines(bd / ROWS_NAME))[0]:
            print("  SELFTEST FAIL: 'round trip' -> still divergent after build")
            failures += 1
        else:
            print("  ok: round trip -> build resolves the divergence")

    if failures:
        print(f"assemble-rows selftest: {failures} FAILURE(S)")
        return 1
    print("assemble-rows selftest: all cases behaved as specified")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-dir", type=Path, default=Path("data/smoke_20_v38"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="fail if the batch file is not the concatenation (default)")
    g.add_argument("--build", action="store_true", help="write the batch file from the contributor files")
    g.add_argument("--selftest", action="store_true", help="validate the check on both branches, no data needed")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.build:
        return cmd_build(args.batch_dir)
    return cmd_check(args.batch_dir)


if __name__ == "__main__":
    sys.exit(main())

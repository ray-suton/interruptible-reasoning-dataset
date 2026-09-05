#!/usr/bin/env python3
"""Assert every source group's trace pointer actually resolves.

`trace_id` and `trace_run_path` are built by PATTERN in `build_smoke_80.py`.
A pattern that is never checked against what the exporter wrote is the shape of
every grading bug in this project: it looks right and is only wrong later.
Contributors follow this pointer to read their prefix and to bind
`bound_prefix_sha256`, so a stale one is not cosmetic.
"""
from __future__ import annotations
import json, sys
from pathlib import Path


def main(argv: list[str]) -> int:
    problems: list[str] = []
    checked = 0
    cache: dict[str, dict[str, dict]] = {}
    for arg in argv:
        for line in Path(arg).read_text().splitlines():
            if not line.strip():
                continue
            g = json.loads(line)
            run_path = g.get("trace_run_path")
            if not run_path:
                problems.append(f"{g['stable_source_id']}: no trace_run_path")
                continue
            if "archive/" in run_path:
                problems.append(
                    f"{g['stable_source_id']}: trace_run_path points into archive/, "
                    "which workflow.md §1 tells contributors not to read")
            traces = Path(run_path) / "traces.jsonl"
            if run_path not in cache:
                if not traces.exists():
                    problems.append(f"{g['stable_source_id']}: {traces} does not exist")
                    cache[run_path] = {}
                    continue
                cache[run_path] = {
                    r["trace_id"]: r
                    for r in (json.loads(l) for l in traces.read_text().splitlines() if l.strip())
                }
            by_id = cache[run_path]
            rec = by_id.get(g.get("trace_id"))
            if rec is None:
                problems.append(
                    f"{g['stable_source_id']}: trace_id {g.get('trace_id')!r} not in {traces}")
                continue
            if rec.get("stable_source_id") != g["stable_source_id"]:
                problems.append(
                    f"{g['stable_source_id']}: trace_id resolves to "
                    f"{rec.get('stable_source_id')!r}")
            if not rec.get("prefix_valid", True):
                problems.append(f"{g['stable_source_id']}: trace records prefix_valid=false")
            checked += 1
    if problems:
        print(f"{len(problems)} problem(s):", file=sys.stderr)
        for p in problems[:25]:
            print("  " + p, file=sys.stderr)
        return 1
    print(f"all {checked} source group trace pointers resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

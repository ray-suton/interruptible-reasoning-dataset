#!/usr/bin/env python3
"""Assert every source group's trace pointer actually resolves.

`trace_id` and `trace_run_path` are built by PATTERN in `build_smoke_100.py`.
A pattern that is never checked against what the exporter wrote is the shape of
every grading bug in this project: it looks right and is only wrong later.
Contributors follow this pointer to read their prefix and to bind
`bound_prefix_sha256`, so a stale one is not cosmetic.
"""
from __future__ import annotations
import json, re, sys
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
            # Any recorded path must exist. A batch rename left every planning
            # source pointing at data/smoke_80/... for one build; nothing failed,
            # because only trace_run_path was being checked.
            for field in ("source_record_locator",):
                val = str(g.get(field) or "")
                bare = val.split("#")[0].split(":")[0]
                if bare.startswith("data/") and not Path(bare).exists():
                    problems.append(
                        f"{g['stable_source_id']}: {field} points at {bare}, which does not exist")
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
    # The run PACKAGES must not carry dead paths either. Only the source groups
    # were being checked, so a batch rename left `traces_path` in every
    # trace_summary.json and `source_record_locator` in every exported trace
    # pointing at a directory that no longer existed -- and nothing failed.
    for run_path in sorted(cache):
        run_dir = Path(run_path)
        for name in ("trace_summary.json", "traces.jsonl", "plan_grades.json"):
            f = run_dir / name
            if not f.exists():
                continue
            # A key whose name marks it historical is exempt: a provenance record
            # is allowed -- and required -- to name a path that has since moved.
            # Only paths presented as CURRENT must resolve.
            HISTORICAL = ("_original", "_note", "_was", "path_note")
            text = f.read_text()
            if name.endswith(".json"):
                try:
                    doc = json.loads(text)
                except json.JSONDecodeError:
                    doc = None
                if isinstance(doc, dict):
                    text = json.dumps({k: v for k, v in doc.items()
                                       if not any(k.endswith(h) for h in HISTORICAL)})
            for token in set(re.findall(r"data/[A-Za-z0-9_./-]+", text)):
                base = token.split("#")[0].rstrip('.,"')
                if base.startswith("data/") and not Path(base).exists():
                    problems.append(f"{run_dir.name}/{name}: references {base}, "
                                    "which does not exist")
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

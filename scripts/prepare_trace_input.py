#!/usr/bin/env python3
"""Prepare temporary model-run inputs for the Smoke10 selected originals.

This script writes raw prompt text only to the requested output directory. Use a
temporary run directory when source text should not be duplicated into the repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_GROUPS = ROOT / "data/smoke_20/source_groups_math.jsonl"
DEFAULT_SOURCE_POOL = ROOT / "sources/upstream_interrupt_lrm/math_source_problems.jsonl"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_source_pool(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    records = {}
    for line_no, record in enumerate(load_jsonl(path), start=1):
        key = (str(record.get("source_family")), str(record.get("upstream_id")))
        record = dict(record)
        record["_source_line"] = line_no
        records[key] = record
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-groups", type=Path, default=DEFAULT_SOURCE_GROUPS)
    parser.add_argument("--source-pool", type=Path, default=DEFAULT_SOURCE_POOL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_groups = load_jsonl(args.source_groups)
    if args.limit:
        source_groups = source_groups[: args.limit]
    source_pool = load_source_pool(args.source_pool)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    stage1_records: list[dict[str, Any]] = []
    sidecar: dict[str, dict[str, Any]] = {}
    for index, group in enumerate(source_groups):
        # Authored sources (e.g. the planning instances) carry their statement
        # inline and have no pool record to look up. Pinned sources are still
        # resolved through the pool with a hash check.
        if group.get("statement_text_included") and group.get("statement"):
            source = {"_source_line": 0}
            problem = group["statement"]
        else:
            key = (str(group["source_family"]), str(group["upstream_id"]))
            source = source_pool.get(key)
            if source is None:
                raise ValueError(f"missing source pool record for {key[0]}:{key[1]}")
            problem = source["original_problem"]
        if sha256_text(problem) != group["statement_sha256"]:
            raise ValueError(f"statement hash mismatch for {group['task_group_id']}")

        stage1_records.append(
            {
                "id": index,
                "source": group["source_family"],
                "stable_source_id": group["stable_source_id"],
                "task_group_id": group["task_group_id"],
                "original_problem": problem,
                "revised_problem": problem,
                "update": "",
                "answer": group["original_answer"],
            }
        )
        sidecar[str(index)] = {
            "task_group_id": group["task_group_id"],
            "stable_source_id": group["stable_source_id"],
            "source_family": group["source_family"],
            "upstream_id": group.get("upstream_id"),
            "upstream_revision": group.get("upstream_revision"),
            "source_dataset": group["source_dataset"],
            "source_year": group["source_year"],
            "split": group["split"],
            "report_partition": group["report_partition"],
            "original_answer": group["original_answer"],
            "source_record_locator": group["source_record_locator"],
            "statement_sha256": group["statement_sha256"],
            "original_record_sha256": group.get("original_record_sha256"),
            "source_line": source["_source_line"],
        }

    stage1_path = args.output_dir / "stage1_input.jsonl"
    sidecar_path = args.output_dir / "sidecar_stage1.json"
    provenance_path = args.output_dir / "input_provenance.json"

    with stage1_path.open("w", encoding="utf-8") as handle:
        for record in stage1_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    provenance = {
        "source_groups": str(args.source_groups.relative_to(ROOT) if args.source_groups.is_relative_to(ROOT) else args.source_groups),
        "source_groups_sha256": sha256_text(args.source_groups.read_text(encoding="utf-8")),
        "source_pool": str(args.source_pool.relative_to(ROOT) if args.source_pool.is_relative_to(ROOT) else args.source_pool),
        "source_pool_sha256": sha256_text(args.source_pool.read_text(encoding="utf-8")),
        "record_count": len(stage1_records),
        "raw_problem_text_written_to": str(stage1_path),
    }
    provenance_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(stage1_records)} stage-1 input record(s) to {stage1_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

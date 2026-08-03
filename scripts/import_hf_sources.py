#!/usr/bin/env python3
"""Import a revision-pinned Hugging Face source snapshot.

The default import extracts only original source problems and answers from the
Interrupt-LRM Math configuration. Revised problems and upstream update text are
intentionally excluded from the Stage 1 source snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = "dynamic-lm/update-interrupt-benchmark"
DEFAULT_REVISION = "6ac4ea4baadeccafbb452c1649c90e24ffac4cfc"
DEFAULT_CONFIG = "Math"
DEFAULT_SPLIT = "test"
DEFAULT_OUTPUT_ROOT = ROOT / "sources" / "upstream_interrupt_lrm"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit(
            "The optional Hugging Face import requires the `datasets` package. "
            "Run this script in the existing interrupt-lrm environment."
        ) from exc

    dataset = load_dataset(
        args.dataset_id,
        args.config,
        split=args.split,
        revision=args.revision,
    )

    required = {"id", "source", "original_problem", "original_answer"}
    missing = required.difference(dataset.column_names)
    if missing:
        raise SystemExit(f"upstream schema is missing required columns: {sorted(missing)}")

    records: list[dict[str, Any]] = []
    stage1_aime_links: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    family_positions: Counter[str] = Counter()
    for upstream_index, row in enumerate(dataset):
        source_family = str(row["source"])
        upstream_id = str(row["id"])
        source_key = f"{source_family}:{upstream_id}"
        if source_key in seen_ids:
            raise SystemExit(f"duplicate upstream source key: {source_key}")
        seen_ids.add(source_key)
        original = {
            "source_family": source_family,
            "upstream_id": upstream_id,
            "original_problem": str(row["original_problem"]),
            "original_answer": str(row["original_answer"]),
        }
        record = {
                "upstream_dataset": args.dataset_id,
                "upstream_revision": args.revision,
                "upstream_config": args.config,
                "upstream_split": args.split,
                "upstream_index": upstream_index,
                **original,
                "original_record_sha256": sha256_text(canonical_json(original)),
                "stage1_status": (
                    "candidate_aime_development_source"
                    if source_family in {"aime2024", "aime2025"}
                    else "reference_only"
                ),
            }
        records.append(record)
        family_position = family_positions[source_family]
        family_positions[source_family] += 1
        if source_family in {"aime2024", "aime2025"}:
            year = int(source_family[-4:])
            part = "I" if family_position < 15 else "II"
            problem_number = family_position % 15 + 1
            stable_source_id = f"A{year % 100:02d}-{part}-{problem_number:02d}"
            stage1_aime_links.append(
                {
                    "stable_source_id": stable_source_id,
                    "task_group_id": stable_source_id.lower().replace("-", "_"),
                    "upstream_dataset": args.dataset_id,
                    "upstream_revision": args.revision,
                    "upstream_config": args.config,
                    "upstream_split": args.split,
                    "upstream_id": upstream_id,
                    "upstream_index": upstream_index,
                    "source_family": source_family,
                    "original_record_sha256": record["original_record_sha256"],
                }
            )

    args.output_root.mkdir(parents=True, exist_ok=True)
    output_path = args.output_root / "math_source_problems.jsonl"
    serialized = "".join(canonical_json(record) + "\n" for record in records)
    output_path.write_text(serialized, encoding="utf-8")
    links_path = args.output_root / "stage1_aime_links.jsonl"
    serialized_links = "".join(canonical_json(record) + "\n" for record in stage1_aime_links)
    links_path.write_text(serialized_links, encoding="utf-8")

    manifest = {
        "dataset_id": args.dataset_id,
        "revision": args.revision,
        "config": args.config,
        "split": args.split,
        "license_declared_by_dataset_card": "apache-2.0",
        "source_url": f"https://huggingface.co/datasets/{args.dataset_id}/tree/{args.revision}",
        "selection": "original_problem and original_answer only; revised_problem and update excluded",
        "record_count": len(records),
        "source_family_counts": dict(sorted(Counter(record["source_family"] for record in records).items())),
        "output": output_path.name,
        "output_sha256": sha256_text(serialized),
        "stage1_aime_link_count": len(stage1_aime_links),
        "stage1_aime_links": links_path.name,
        "stage1_aime_links_sha256": sha256_text(serialized_links),
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

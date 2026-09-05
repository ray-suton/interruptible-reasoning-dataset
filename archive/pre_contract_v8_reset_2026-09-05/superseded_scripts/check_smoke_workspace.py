#!/usr/bin/env python3
"""Check that the active repo is ready for the 150-original smoke test.

This is a workspace-shape check, not a row-label validator. It keeps the active
surface focused on the next generation pass and verifies that legacy workload
assets were archived instead of deleted.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SMOKE_TARGET_SIZE = 150
ARCHIVE_ROOT = Path("archive/pre_smoke150_reset_2026-09-03")
SOURCE_POOL = Path("sources/upstream_interrupt_lrm/math_source_problems.jsonl")
SOURCE_LINKS = Path("sources/upstream_interrupt_lrm/stage1_aime_links.jsonl")
SOURCE_MANIFEST = Path("sources/upstream_interrupt_lrm/manifest.json")

REQUIRED_ACTIVE_FILES = (
    "DATASET.md",
    "update_rules.md",
    "docs/concepts.md",
    "docs/source_import_policy.md",
    "docs/original/README.md",
    "docs/original/STAGE1_PLAN.md",
    "docs/original/label_policy.md",
    "registry/contract_lock.json",
    "schema/dataset_row.schema.json",
    "schema/source_group.schema.json",
    "schema/source_registry.schema.json",
    "schema/review_response.schema.json",
    "scripts/contract_lock.py",
    "scripts/import_hf_sources.py",
    "scripts/validate_dataset.py",
    "sources/README.md",
    str(SOURCE_MANIFEST),
    str(SOURCE_POOL),
    str(SOURCE_LINKS),
    "data/smoke_150/README.md",
)

REQUIRED_ARCHIVE_PATHS = (
    ARCHIVE_ROOT / "MANIFEST.md",
    ARCHIVE_ROOT / "legacy_workload" / "contributors",
    ARCHIVE_ROOT / "legacy_registry" / "source_registry.jsonl",
    ARCHIVE_ROOT / "legacy_data" / "stage1",
    ARCHIVE_ROOT / "legacy_data" / "training",
    ARCHIVE_ROOT / "legacy_tests" / "tests",
    ARCHIVE_ROOT / "legacy_scripts" / "generate_scaffold.py",
    ARCHIVE_ROOT / "legacy_scripts" / "generate_training_pilot_10x4.py",
)

MUST_NOT_BE_ACTIVE = (
    "contributors",
    "adjudication",
    "reviews",
    "manifests",
    "tests",
    "data/stage1",
    "data/training",
    "registry/source_registry.jsonl",
    "registry/manifest.json",
    "registry/recipes.json",
    "scripts/generate_scaffold.py",
    "scripts/generate_training_pilot_10x4.py",
    "scripts/__pycache__",
)

REQUIRED_SOURCE_FIELDS = (
    "source_family",
    "upstream_id",
    "upstream_revision",
    "original_problem",
    "original_answer",
    "original_record_sha256",
    "stage1_status",
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{path}: cannot read JSON: {exc}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON: {exc.msg}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path}: expected a JSON object")
        return {}
    return value


def load_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"{path}: cannot read JSONL: {exc}")
        return rows
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path}:{line_no}: expected a JSON object")
            continue
        rows.append(value)
    return rows


def check_required_paths(errors: list[str]) -> None:
    for rel in REQUIRED_ACTIVE_FILES:
        if not (ROOT / rel).is_file():
            errors.append(f"missing active file: {rel}")
    if not (ROOT / "data/smoke_150").is_dir():
        errors.append("missing active directory: data/smoke_150")
    for rel in REQUIRED_ARCHIVE_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing archived path: {rel}")
    for rel in MUST_NOT_BE_ACTIVE:
        if (ROOT / rel).exists():
            errors.append(f"legacy path still active; archive it: {rel}")


def check_source_pool(errors: list[str]) -> dict[str, Any]:
    manifest = load_json(ROOT / SOURCE_MANIFEST, errors)
    rows = load_jsonl(ROOT / SOURCE_POOL, errors)
    links = load_jsonl(ROOT / SOURCE_LINKS, errors)

    if len(rows) < SMOKE_TARGET_SIZE:
        errors.append(
            f"{SOURCE_POOL}: need at least {SMOKE_TARGET_SIZE} original records; found {len(rows)}"
        )

    seen_keys: set[tuple[str, str]] = set()
    seen_digests: set[str] = set()
    for index, row in enumerate(rows, start=1):
        label = f"{SOURCE_POOL}:{index}"
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in row:
                errors.append(f"{label}: missing {field!r}")
        if not row.get("original_problem"):
            errors.append(f"{label}: original_problem is empty")
        if not row.get("original_answer"):
            errors.append(f"{label}: original_answer is empty")
        digest = row.get("original_record_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{label}: original_record_sha256 must be 64 hex characters")
        elif digest in seen_digests:
            errors.append(f"{label}: duplicate original_record_sha256 {digest}")
        else:
            seen_digests.add(digest)
        key = (str(row.get("source_family")), str(row.get("upstream_id")))
        if key in seen_keys:
            errors.append(f"{label}: duplicate source key {key[0]}:{key[1]}")
        else:
            seen_keys.add(key)

    if manifest:
        expected_count = manifest.get("record_count")
        if expected_count != len(rows):
            errors.append(
                f"{SOURCE_MANIFEST}: record_count {expected_count!r} does not match {len(rows)} source rows"
            )
        expected_link_count = manifest.get("stage1_aime_link_count")
        if expected_link_count != len(links):
            errors.append(
                f"{SOURCE_MANIFEST}: stage1_aime_link_count {expected_link_count!r} "
                f"does not match {len(links)} link rows"
            )
        output_sha = manifest.get("output_sha256")
        current_output_sha = sha256_text((ROOT / SOURCE_POOL).read_text(encoding="utf-8"))
        if output_sha != current_output_sha:
            errors.append(f"{SOURCE_MANIFEST}: output_sha256 does not match {SOURCE_POOL}")
        links_sha = manifest.get("stage1_aime_links_sha256")
        current_links_sha = sha256_text((ROOT / SOURCE_LINKS).read_text(encoding="utf-8"))
        if links_sha != current_links_sha:
            errors.append(f"{SOURCE_MANIFEST}: stage1_aime_links_sha256 does not match {SOURCE_LINKS}")

    family_counts = Counter(str(row.get("source_family")) for row in rows)
    status_counts = Counter(str(row.get("stage1_status")) for row in rows)
    return {
        "source_records": len(rows),
        "source_family_counts": dict(sorted(family_counts.items())),
        "stage1_status_counts": dict(sorted(status_counts.items())),
        "aime_link_records": len(links),
    }


def main() -> int:
    errors: list[str] = []
    check_required_paths(errors)
    summary = check_source_pool(errors)
    summary.update(
        {
            "active_root": "data/smoke_150",
            "archive_root": str(ARCHIVE_ROOT),
            "target_original_samples": SMOKE_TARGET_SIZE,
        }
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate Stage 1 interruptible-reasoning dataset JSONL packages.

The validator intentionally uses only the Python standard library. The JSON
Schema files in ../schema document the release shape; this script implements
the same core field checks plus dataset-level invariants that JSON Schema
cannot express.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CLASSES = {
    "valid_material",
    "true_non_material",
    "plausible_false_material",
    "malicious_override",
}
LABEL_FOR_CLASS = {
    "valid_material": "ACCEPT",
    "true_non_material": "ACCEPT",
    "plausible_false_material": "DO_NOT_ACCEPT",
    "malicious_override": "DO_NOT_ACCEPT",
}
EXPECTED_TRACE_FIELDS = (
    "full_trace_sha256",
    "prefix_sha256",
    "partial_reasoning_trace",
    "interrupt_position",
    "no_update_solved",
    "prefix_valid",
)
PEOPLE = {f"P{i}" for i in range(1, 9)}
SPLITS = {"development", "primary_test"}
REPORT_PARTITIONS = {"development", "primary", "primary_test", "robustness", "primary_plus_robustness"}


@dataclass(frozen=True)
class Issue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ValidationErrorCollector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def add(self, path: str, message: str) -> None:
        self.issues.append(Issue(path, message))

    def require(self, condition: bool, path: str, message: str) -> None:
        if not condition:
            self.add(path, message)


def load_jsonl(paths: Iterable[Path], errors: ValidationErrorCollector) -> list[tuple[dict[str, Any], str]]:
    records: list[tuple[dict[str, Any], str]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.add(str(path), f"cannot read file: {exc}")
            continue
        for line_no, line in enumerate(lines, start=1):
            label = f"{path}:{line_no}"
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.add(label, f"invalid JSON: {exc.msg}")
                continue
            if not isinstance(value, dict):
                errors.add(label, "record must be a JSON object")
                continue
            records.append((value, label))
    return records


def require_fields(record: dict[str, Any], path: str, fields: Iterable[str], errors: ValidationErrorCollector) -> None:
    for field in fields:
        errors.require(field in record, path, f"missing required field {field!r}")


def require_type(record: dict[str, Any], path: str, field: str, typ: type, errors: ValidationErrorCollector) -> None:
    if field in record and not isinstance(record[field], typ):
        errors.add(path, f"field {field!r} must be {typ.__name__}")


def require_source_year(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    if "source_year" not in record:
        return
    value = record["source_year"]
    if value is None and record.get("domain") == "planning":
        return
    if not isinstance(value, int):
        errors.add(path, "source_year must be an integer, except planning records may use null")


def validate_registry_shape(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    require_fields(
        record,
        path,
        (
            "task_group_id",
            "stable_source_id",
            "source_dataset",
            "source_year",
            "domain",
            "split",
            "report_partition",
            "recipe",
            "owner_id",
            "reviewer_id",
            "import_status",
            "provenance_status",
            "license_status",
            "source_hash_status",
            "problem_text_redistribution",
            "statement_text_included",
            "expected_authored_rows",
            "expected_primary_rows",
            "expected_robustness_rows",
        ),
        errors,
    )
    for field in (
        "task_group_id",
        "stable_source_id",
        "source_dataset",
        "domain",
        "split",
        "report_partition",
        "recipe",
        "owner_id",
        "reviewer_id",
        "import_status",
        "provenance_status",
        "license_status",
        "source_hash_status",
        "problem_text_redistribution",
    ):
        require_type(record, path, field, str, errors)
    for field in ("expected_authored_rows", "expected_primary_rows", "expected_robustness_rows"):
        require_type(record, path, field, int, errors)
        if isinstance(record.get(field), int) and record[field] < 0:
            errors.add(path, f"{field} must be non-negative")
    require_type(record, path, "statement_text_included", bool, errors)
    require_source_year(record, path, errors)
    if record.get("domain") not in {"math", "planning"}:
        errors.add(path, "domain must be 'math' or 'planning'")
    if record.get("split") not in SPLITS:
        errors.add(path, "split must be development or primary_test")
    if record.get("report_partition") not in REPORT_PARTITIONS:
        errors.add(path, "report_partition must be development, primary, primary_test, robustness, or primary_plus_robustness")
    if record.get("recipe") not in {"D8", "M4", "T8"}:
        errors.add(path, "recipe must be D8, M4, or T8")
    if record.get("owner_id") not in PEOPLE:
        errors.add(path, "owner_id must be P1..P8")
    if record.get("reviewer_id") not in PEOPLE:
        errors.add(path, "reviewer_id must be P1..P8")
    if record.get("owner_id") == record.get("reviewer_id"):
        errors.add(path, "reviewer_id must differ from owner_id")
    if record.get("report_partition") in {"robustness", "primary_plus_robustness"} and record.get("split") != "primary_test":
        errors.add(path, "robustness report partitions must use split primary_test")
    if record.get("domain") == "math" and record.get("source_year") is None:
        errors.add(path, "math records must have a concrete source_year")


def validate_source_shape(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    require_fields(
        record,
        path,
        (
            "task_group_id",
            "source_dataset",
            "source_year",
            "domain",
            "split",
            "recipe",
            "owner_id",
            "stable_source_id",
            "statement_sha256",
            "answer_source",
            "license_note",
            "original_answer",
            "verification",
        ),
        errors,
    )
    for field in ("task_group_id", "source_dataset", "domain", "split", "recipe", "owner_id", "stable_source_id"):
        require_type(record, path, field, str, errors)
    require_source_year(record, path, errors)
    require_type(record, path, "verification", dict, errors)
    if record.get("domain") not in {"math", "planning"}:
        errors.add(path, "domain must be 'math' or 'planning'")
    if record.get("split") not in SPLITS:
        errors.add(path, "split must be development or primary_test")
    if record.get("domain") == "math" and record.get("source_year") is None:
        errors.add(path, "math records must have a concrete source_year")
    if record.get("recipe") not in {"D8", "M4", "T8"}:
        errors.add(path, "recipe must be D8, M4, or T8")
    if record.get("owner_id") not in PEOPLE:
        errors.add(path, "owner_id must be P1..P8")
    if not has_sha256(record.get("statement_sha256")):
        errors.add(path, "statement_sha256 must be 64 lowercase hex characters")
    verification = record.get("verification")
    if isinstance(verification, dict) and verification.get("status") != "verified":
        errors.add(path, "source verification.status must be 'verified'")


def validate_row_shape(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    require_fields(
        record,
        path,
        (
            "example_id",
            "task_group_id",
            "source_dataset",
            "source_year",
            "domain",
            "split",
            "authority_policy",
            "original_answer",
            "trace",
            "update",
            "update_variant_id",
            "update_template_family",
            "diagnostic_class",
            "binary_label",
            "answer_changes",
            "post_update_answer",
            "annotation_rationale",
            "verification",
        ),
        errors,
    )
    for field in (
        "example_id",
        "task_group_id",
        "source_dataset",
        "domain",
        "split",
        "authority_policy",
        "original_answer",
        "update",
        "update_variant_id",
        "update_template_family",
        "diagnostic_class",
        "binary_label",
        "post_update_answer",
        "annotation_rationale",
    ):
        require_type(record, path, field, str, errors)
    require_source_year(record, path, errors)
    require_type(record, path, "answer_changes", bool, errors)
    require_type(record, path, "trace", dict, errors)
    require_type(record, path, "verification", dict, errors)
    if record.get("authority_policy") != "stage1_original_problem_authoritative":
        errors.add(path, "authority_policy must be stage1_original_problem_authoritative")
    if record.get("diagnostic_class") not in CLASSES:
        errors.add(path, "diagnostic_class must be one of the four Stage 1 classes")
    if record.get("binary_label") not in {"ACCEPT", "DO_NOT_ACCEPT"}:
        errors.add(path, "binary_label must be ACCEPT or DO_NOT_ACCEPT")
    if record.get("split") not in SPLITS:
        errors.add(path, "split must be development or primary_test")
    if "report_partition" in record and record.get("report_partition") not in REPORT_PARTITIONS:
        errors.add(path, "report_partition must be development, primary, primary_test, robustness, or primary_plus_robustness")
    if record.get("report_partition") in {"robustness", "primary_plus_robustness"} and record.get("split") != "primary_test":
        errors.add(path, "robustness report partitions must use split primary_test")
    if record.get("domain") == "math" and record.get("source_year") is None:
        errors.add(path, "math records must have a concrete source_year")
    trace = record.get("trace")
    if isinstance(trace, dict):
        require_fields(trace, f"{path}.trace", ("full_trace", *EXPECTED_TRACE_FIELDS), errors)
        if "interrupt_position" in trace and not isinstance(trace["interrupt_position"], (int, float)):
            errors.add(path, "trace.interrupt_position must be numeric")
        for field in ("full_trace_sha256", "prefix_sha256"):
            if field in trace and not has_sha256(trace[field]):
                errors.add(path, f"trace.{field} must be 64 lowercase hex characters")
        for field in ("no_update_solved", "prefix_valid"):
            if field in trace and not isinstance(trace[field], bool):
                errors.add(path, f"trace.{field} must be boolean")
    verification = record.get("verification")
    if isinstance(verification, dict):
        require_fields(verification, f"{path}.verification", ("author_id", "verifier_id", "method", "status"), errors)
        if verification.get("author_id") not in PEOPLE:
            errors.add(path, "verification.author_id must be P1..P8")
        if verification.get("verifier_id") not in PEOPLE:
            errors.add(path, "verification.verifier_id must be P1..P8")
        if verification.get("status") != "verified":
            errors.add(path, "verification.status must be 'verified'")


def validate_review_shape(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    require_fields(record, path, ("review_id", "example_id", "author_id", "reviewer_id", "status", "response"), errors)
    for field in ("review_id", "example_id", "author_id", "reviewer_id", "status", "response"):
        require_type(record, path, field, str, errors)
    if record.get("author_id") not in PEOPLE:
        errors.add(path, "author_id must be P1..P8")
    if record.get("reviewer_id") not in PEOPLE:
        errors.add(path, "reviewer_id must be P1..P8")
    if record.get("status") not in {"PASS", "FIX", "ADJUDICATE"}:
        errors.add(path, "status must be PASS, FIX, or ADJUDICATE")


def has_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def trace_key(row: dict[str, Any]) -> tuple[Any, ...]:
    trace = row.get("trace", {})
    if not isinstance(trace, dict):
        return ()
    return tuple(trace.get(field) for field in EXPECTED_TRACE_FIELDS)


def validate_dataset(
    registry: list[tuple[dict[str, Any], str]],
    assigned: list[tuple[dict[str, Any], str]],
    sources: list[tuple[dict[str, Any], str]],
    rows: list[tuple[dict[str, Any], str]],
    reviews: list[tuple[dict[str, Any], str]],
    complete_recipe_counts: bool,
) -> list[Issue]:
    errors = ValidationErrorCollector()
    registry_by_group: dict[str, tuple[dict[str, Any], str]] = {}
    source_by_group: dict[str, tuple[dict[str, Any], str]] = {}
    example_ids: dict[str, str] = {}
    rows_by_group: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)

    for record, path in registry:
        validate_registry_shape(record, path, errors)
        group_id = record.get("task_group_id")
        stable_id = record.get("stable_source_id")
        if isinstance(group_id, str):
            if group_id in registry_by_group:
                errors.add(path, f"duplicate registry task_group_id also seen at {registry_by_group[group_id][1]}")
            registry_by_group[group_id] = (record, path)
        if isinstance(stable_id, str):
            duplicates = [
                prior_path
                for prior, prior_path in registry_by_group.values()
                if prior is not record and prior.get("stable_source_id") == stable_id
            ]
            if duplicates:
                errors.add(path, f"duplicate stable_source_id also seen at {duplicates[0]}")

    for record, path in assigned:
        validate_registry_shape(record, path, errors)
        group_id = record.get("task_group_id")
        if isinstance(group_id, str):
            registry_entry = registry_by_group.get(group_id)
            if registry and registry_entry is None:
                errors.add(path, "assigned source group is not present in source registry")
            elif registry_entry is not None:
                registry_record, _registry_path = registry_entry
                for field in (
                    "stable_source_id",
                    "source_dataset",
                    "source_year",
                    "domain",
                    "split",
                    "report_partition",
                    "recipe",
                    "owner_id",
                    "reviewer_id",
                ):
                    if record.get(field) != registry_record.get(field):
                        errors.add(path, f"assigned source group {field} does not match source registry")

    for record, path in sources:
        validate_source_shape(record, path, errors)
        group_id = record.get("task_group_id")
        if isinstance(group_id, str):
            if group_id in source_by_group:
                errors.add(path, f"duplicate task_group_id also seen at {source_by_group[group_id][1]}")
            source_by_group[group_id] = (record, path)
            registry_entry = registry_by_group.get(group_id)
            if registry and registry_entry is None:
                errors.add(path, "verified source group is not present in source registry")
            elif registry_entry is not None:
                registry_record, _registry_path = registry_entry
                for field in ("stable_source_id", "source_dataset", "source_year", "domain", "split", "recipe", "owner_id"):
                    if field in record and record.get(field) != registry_record.get(field):
                        errors.add(path, f"verified source group {field} does not match source registry")

    for record, path in rows:
        validate_row_shape(record, path, errors)
        example_id = record.get("example_id")
        if isinstance(example_id, str):
            if example_id in example_ids:
                errors.add(path, f"duplicate example_id also seen at {example_ids[example_id]}")
            example_ids[example_id] = path
        group_id = record.get("task_group_id")
        if isinstance(group_id, str):
            rows_by_group[group_id].append((record, path))
        validate_row_semantics(record, path, errors)

    for record, path in reviews:
        validate_review_shape(record, path, errors)
        if record.get("author_id") == record.get("reviewer_id"):
            errors.add(path, "reviewer_id must differ from author_id")
        example_id = record.get("example_id")
        if isinstance(example_id, str) and example_ids and example_id not in example_ids:
            errors.add(path, "review response references unknown example_id")

    validate_group_consistency(source_by_group, rows_by_group, errors)
    validate_template_leakage(rows_by_group, errors)
    if complete_recipe_counts:
        validate_complete_recipe_counts(source_by_group, rows_by_group, errors)
    return errors.issues


def validate_row_semantics(record: dict[str, Any], path: str, errors: ValidationErrorCollector) -> None:
    diagnostic_class = record.get("diagnostic_class")
    expected_label = LABEL_FOR_CLASS.get(diagnostic_class)
    if expected_label and record.get("binary_label") != expected_label:
        errors.add(path, f"{diagnostic_class} must have binary_label {expected_label}")

    original = record.get("original_answer")
    post_update = record.get("post_update_answer")
    answer_changes = record.get("answer_changes")
    if diagnostic_class == "valid_material":
        if answer_changes is not True:
            errors.add(path, "valid_material rows must set answer_changes=true")
    elif diagnostic_class in {"true_non_material", "plausible_false_material", "malicious_override"}:
        if answer_changes is not False:
            errors.add(path, f"{diagnostic_class} rows must set answer_changes=false")
        if isinstance(original, str) and isinstance(post_update, str) and post_update != original:
            errors.add(path, f"{diagnostic_class} rows must preserve original_answer in post_update_answer")

    verification = record.get("verification")
    if isinstance(verification, dict) and verification.get("author_id") == verification.get("verifier_id"):
        errors.add(path, "verification.verifier_id must differ from author_id")


def validate_group_consistency(
    source_by_group: dict[str, tuple[dict[str, Any], str]],
    rows_by_group: dict[str, list[tuple[dict[str, Any], str]]],
    errors: ValidationErrorCollector,
) -> None:
    for group_id, grouped_rows in rows_by_group.items():
        source_entry = source_by_group.get(group_id)
        if source_entry is None:
            for _, path in grouped_rows:
                errors.add(path, "row references unknown task_group_id")
            continue
        source, _source_path = source_entry
        trace_seen: tuple[Any, ...] | None = None
        split_seen: str | None = None
        variant_keys: set[tuple[Any, Any]] = set()
        for row, path in grouped_rows:
            for field in ("source_dataset", "source_year", "domain", "split", "original_answer"):
                if field in row and field in source and row[field] != source[field]:
                    errors.add(path, f"row {field} does not match source group")
            author_id = row.get("verification", {}).get("author_id") if isinstance(row.get("verification"), dict) else None
            if author_id != source.get("owner_id"):
                errors.add(path, "verification.author_id must match source group owner_id")
            current_trace = trace_key(row)
            if trace_seen is None:
                trace_seen = current_trace
            elif current_trace != trace_seen:
                errors.add(path, "all rows in a task_group_id must share the same trace prefix metadata")
            current_split = row.get("split")
            if split_seen is None and isinstance(current_split, str):
                split_seen = current_split
            elif current_split != split_seen:
                errors.add(path, "all rows in a task_group_id must stay in one split")
            variant_key = (row.get("diagnostic_class"), row.get("update_variant_id"))
            if variant_key in variant_keys:
                errors.add(path, "duplicate diagnostic_class/update_variant_id within task_group_id")
            variant_keys.add(variant_key)


def validate_template_leakage(
    rows_by_group: dict[str, list[tuple[dict[str, Any], str]]],
    errors: ValidationErrorCollector,
) -> None:
    development_families: dict[str, str] = {}
    test_families: dict[str, str] = {}
    exact_updates: dict[tuple[str, str], str] = {}

    for grouped_rows in rows_by_group.values():
        for row, path in grouped_rows:
            family = row.get("update_template_family")
            split = row.get("split")
            update = row.get("update")
            if isinstance(family, str):
                if split == "development":
                    development_families.setdefault(family, path)
                elif split == "primary_test":
                    test_families.setdefault(family, path)
            if isinstance(update, str) and isinstance(split, str):
                key = (split, update.strip())
                prior = exact_updates.get(key)
                if prior is not None:
                    errors.add(path, f"duplicate exact update text within {split} also seen at {prior}")
                exact_updates[key] = path

    leaked = set(development_families).intersection(test_families)
    for family in sorted(leaked):
        errors.add(test_families[family], f"template family {family!r} appears in both development and primary_test")


def validate_complete_recipe_counts(
    source_by_group: dict[str, tuple[dict[str, Any], str]],
    rows_by_group: dict[str, list[tuple[dict[str, Any], str]]],
    errors: ValidationErrorCollector,
) -> None:
    for group_id, (source, source_path) in source_by_group.items():
        recipe = source.get("recipe")
        grouped_rows = rows_by_group.get(group_id, [])
        counts = Counter((row.get("diagnostic_class"), row.get("update_variant_id")) for row, _ in grouped_rows)
        if recipe == "D8":
            expected = {(diagnostic_class, variant) for diagnostic_class in CLASSES for variant in ("a", "b")}
        elif recipe == "M4":
            expected = {(diagnostic_class, "primary") for diagnostic_class in CLASSES}
        elif recipe == "T8":
            expected = {(diagnostic_class, variant) for diagnostic_class in CLASSES for variant in ("primary", "paraphrase")}
        else:
            continue
        actual = set(counts)
        missing = expected - actual
        extra = actual - expected
        if missing:
            errors.add(source_path, f"{recipe} group {group_id} is missing rows: {format_pairs(missing)}")
        if extra:
            errors.add(source_path, f"{recipe} group {group_id} has unexpected rows: {format_pairs(extra)}")
        duplicated = [pair for pair, count in counts.items() if count > 1]
        if duplicated:
            errors.add(source_path, f"{recipe} group {group_id} has duplicate recipe rows: {format_pairs(duplicated)}")
        if len(grouped_rows) != len(expected):
            errors.add(source_path, f"{recipe} group {group_id} has {len(grouped_rows)} rows, expected {len(expected)}")


def format_pairs(pairs: Iterable[tuple[Any, Any]]) -> str:
    return ", ".join(f"{diagnostic_class}/{variant}" for diagnostic_class, variant in sorted(pairs))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-registry", nargs="*", type=Path, default=[], help="pending source_registry.jsonl files")
    parser.add_argument("--assigned-source-groups", nargs="*", type=Path, default=[], help="pending contributor assigned_source_groups.jsonl files")
    parser.add_argument("--source-groups", nargs="*", type=Path, default=[], help="verified source_groups.jsonl files")
    parser.add_argument("--rows", nargs="*", type=Path, default=[], help="authored_rows.jsonl files")
    parser.add_argument("--review-responses", nargs="*", type=Path, default=[], help="review_responses.jsonl files")
    parser.add_argument(
        "--complete-recipe-counts",
        action="store_true",
        help="require every source group to contain the exact D8/M4/T8 row set",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    load_errors = ValidationErrorCollector()
    registry = load_jsonl(args.source_registry, load_errors)
    assigned = load_jsonl(args.assigned_source_groups, load_errors)
    sources = load_jsonl(args.source_groups, load_errors)
    rows = load_jsonl(args.rows, load_errors)
    reviews = load_jsonl(args.review_responses, load_errors)
    if load_errors.issues:
        for issue in load_errors.issues:
            print(issue, file=sys.stderr)
        return 1

    issues = validate_dataset(registry, assigned, sources, rows, reviews, args.complete_recipe_counts)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    print(
        f"validated {len(registry)} pending registry source(s), {len(assigned)} assigned source(s), "
        f"{len(sources)} verified source group(s), {len(rows)} row(s), {len(reviews)} review response(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

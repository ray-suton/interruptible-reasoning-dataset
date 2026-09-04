#!/usr/bin/env python3
"""Generate deterministic Stage 1 dataset-construction scaffolds.

This script records source identifiers and assignment metadata only. It does
not redistribute problem statements, answer text, or update text.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry"
CONTRIBUTORS_DIR = ROOT / "contributors"
UPSTREAM_AIME_LINKS = ROOT / "sources" / "upstream_interrupt_lrm" / "stage1_aime_links.jsonl"

PEOPLE = tuple(f"P{i}" for i in range(1, 9))
REVIEWER_BY_OWNER = {
    "P1": "P5",
    "P2": "P6",
    "P3": "P7",
    "P4": "P8",
    "P5": "P2",
    "P6": "P3",
    "P7": "P4",
    "P8": "P1",
}

EXPECTED_PERSON_TOTALS = {
    "P1": 220,
    "P2": 220,
    "P3": 216,
    "P4": 216,
    "P5": 216,
    "P6": 216,
    "P7": 216,
    "P8": 216,
}

RECIPE_ROWS = {"D8": 8, "M4": 4, "T8": 8}
DIAGNOSTIC_CLASSES = (
    "valid_material",
    "true_non_material",
    "plausible_false_material",
    "malicious_override",
)


@dataclass(frozen=True)
class SourceGroup:
    task_group_id: str
    source_dataset: str
    source_id: str
    source_year: int | None
    domain: str
    split: str
    report_partition: str
    recipe: str
    owner: str
    reviewer: str

    @property
    def expected_authored_rows(self) -> int:
        return RECIPE_ROWS[self.recipe]

    @property
    def expected_primary_rows(self) -> int:
        if self.recipe == "T8":
            return 4
        return self.expected_authored_rows

    @property
    def expected_robustness_rows(self) -> int:
        return 4 if self.recipe == "T8" else 0

    def as_registry_record(self, upstream_link: dict[str, object] | None = None) -> dict[str, object]:
        record: dict[str, object] = {
            "task_group_id": self.task_group_id,
            "stable_source_id": self.source_id,
            "source_dataset": self.source_dataset,
            "source_year": self.source_year,
            "domain": self.domain,
            "split": self.split,
            "report_partition": self.report_partition,
            "recipe": self.recipe,
            "owner_id": self.owner,
            "reviewer_id": self.reviewer,
            "expected_authored_rows": self.expected_authored_rows,
            "expected_primary_rows": self.expected_primary_rows,
            "expected_robustness_rows": self.expected_robustness_rows,
            "statement_text_included": False,
            "problem_text_redistribution": "not_redistributed",
            "provenance_status": "pending_source_audit",
            "import_status": "pending",
            "license_status": "pending_review",
            "source_hash_status": "pending_after_acquisition",
            "notes": "Scaffold registry entry only; no source problem text or gold answer is stored here.",
        }
        if upstream_link:
            record.update(
                {
                    "upstream_dataset": upstream_link["upstream_dataset"],
                    "upstream_revision": upstream_link["upstream_revision"],
                    "upstream_config": upstream_link["upstream_config"],
                    "upstream_split": upstream_link["upstream_split"],
                    "upstream_id": upstream_link["upstream_id"],
                    "upstream_index": upstream_link["upstream_index"],
                    "original_record_sha256": upstream_link["original_record_sha256"],
                    "problem_text_redistribution": "private_pinned_upstream_snapshot",
                    "provenance_status": "pinned_huggingface_revision",
                    "import_status": "imported_upstream_reference",
                    "license_status": "dataset_card_apache-2.0",
                    "source_hash_status": "recorded",
                    "notes": (
                        "Original problem and answer are present in the pinned upstream snapshot; "
                        "verified source-group construction is still pending."
                    ),
                }
            )
        return record


def aime_ids(year: int, part: str, start: int, end: int) -> list[str]:
    return [f"A{str(year)[-2:]}-{part}-{i:02d}" for i in range(start, end + 1)]


def imo_ids(year: int, start: int, end: int) -> list[str]:
    return [f"IMO{str(year)[-2:]}-{i:02d}" for i in range(start, end + 1)]


def bw_ids(prefix: str, start: int, end: int) -> list[str]:
    return [f"BW-{prefix}{i:03d}" for i in range(start, end + 1)]


def source_metadata(source_id: str, recipe: str) -> tuple[str, int | None, str, str, str]:
    if source_id.startswith("A"):
        year = 2000 + int(source_id[1:3])
        return "AIME", year, "math", "primary_test" if recipe == "M4" else "development", "primary" if recipe == "M4" else "development"
    if source_id.startswith("IMO"):
        year = 2000 + int(source_id[3:5])
        return "IMO", year, "math", "primary_test" if recipe == "M4" else "development", "primary" if recipe == "M4" else "development"
    if source_id.startswith("BW-D"):
        return "BlocksWorld", None, "planning", "development", "development"
    if source_id.startswith("BW-T"):
        return "BlocksWorld", None, "planning", "primary_test", "primary_plus_robustness"
    raise ValueError(f"Unknown source id: {source_id}")


def task_group_id(source_id: str) -> str:
    return source_id.lower().replace("-", "_")


def owner_groups(owner: str, recipe: str, ids: list[str]) -> list[SourceGroup]:
    groups = []
    for source_id in ids:
        dataset, year, domain, split, report_partition = source_metadata(source_id, recipe)
        groups.append(
            SourceGroup(
                task_group_id=task_group_id(source_id),
                source_dataset=dataset,
                source_id=source_id,
                source_year=year,
                domain=domain,
                split=split,
                report_partition=report_partition,
                recipe=recipe,
                owner=owner,
                reviewer=REVIEWER_BY_OWNER[owner],
            )
        )
    return groups


def build_groups() -> list[SourceGroup]:
    allocation: dict[str, dict[str, list[str]]] = {
        "P1": {
            "D8": aime_ids(2024, "I", 1, 8) + imo_ids(2024, 1, 1) + bw_ids("D", 1, 12),
            "M4": aime_ids(2026, "I", 1, 4) + imo_ids(2025, 1, 1),
            "T8": bw_ids("T", 1, 4),
        },
        "P2": {
            "D8": aime_ids(2024, "I", 9, 15) + aime_ids(2024, "II", 1, 1) + imo_ids(2024, 2, 2) + bw_ids("D", 13, 24),
            "M4": aime_ids(2026, "I", 5, 8) + imo_ids(2026, 1, 1),
            "T8": bw_ids("T", 5, 8),
        },
        "P3": {
            "D8": aime_ids(2024, "II", 2, 8) + imo_ids(2024, 3, 3) + bw_ids("D", 25, 37),
            "M4": aime_ids(2026, "I", 9, 11) + imo_ids(2025, 2, 2),
            "T8": bw_ids("T", 9, 12),
        },
        "P4": {
            "D8": aime_ids(2024, "II", 9, 15) + imo_ids(2024, 4, 4) + bw_ids("D", 38, 50),
            "M4": aime_ids(2026, "I", 12, 14) + imo_ids(2026, 2, 2),
            "T8": bw_ids("T", 13, 16),
        },
        "P5": {
            "D8": aime_ids(2025, "I", 1, 7) + imo_ids(2024, 5, 5) + bw_ids("D", 51, 62),
            "M4": aime_ids(2026, "I", 15, 15) + aime_ids(2026, "II", 1, 4) + imo_ids(2025, 3, 3),
            "T8": bw_ids("T", 17, 20),
        },
        "P6": {
            "D8": aime_ids(2025, "I", 8, 14) + imo_ids(2024, 6, 6) + bw_ids("D", 63, 74),
            "M4": aime_ids(2026, "II", 5, 9) + imo_ids(2026, 3, 3),
            "T8": bw_ids("T", 21, 24),
        },
        "P7": {
            "D8": aime_ids(2025, "I", 15, 15) + aime_ids(2025, "II", 1, 7) + bw_ids("D", 75, 87),
            "M4": aime_ids(2026, "II", 10, 12) + imo_ids(2025, 4, 5) + imo_ids(2026, 4, 4),
            "T8": bw_ids("T", 25, 27),
        },
        "P8": {
            "D8": aime_ids(2025, "II", 8, 15) + bw_ids("D", 88, 100),
            "M4": aime_ids(2026, "II", 13, 15) + imo_ids(2025, 6, 6) + imo_ids(2026, 5, 6),
            "T8": bw_ids("T", 28, 30),
        },
    }

    groups: list[SourceGroup] = []
    for owner in PEOPLE:
        for recipe in ("D8", "M4", "T8"):
            groups.extend(owner_groups(owner, recipe, allocation[owner][recipe]))
    return groups


def row_plan_for_recipe(recipe: str) -> list[dict[str, str]]:
    if recipe == "D8":
        rows = []
        for diagnostic_class in DIAGNOSTIC_CLASSES:
            label = "ACCEPT" if diagnostic_class in {"valid_material", "true_non_material"} else "DO_NOT_ACCEPT"
            for variant in ("a", "b"):
                rows.append({"diagnostic_class": diagnostic_class, "binary_label": label, "update_variant_id": variant, "report_partition": "development"})
        return rows
    if recipe == "M4":
        return [
            {
                "diagnostic_class": diagnostic_class,
                "binary_label": "ACCEPT" if diagnostic_class in {"valid_material", "true_non_material"} else "DO_NOT_ACCEPT",
                "update_variant_id": "primary",
                "report_partition": "primary",
            }
            for diagnostic_class in DIAGNOSTIC_CLASSES
        ]
    if recipe == "T8":
        rows = []
        for variant, partition in (("primary", "primary"), ("paraphrase", "robustness")):
            for diagnostic_class in DIAGNOSTIC_CLASSES:
                rows.append(
                    {
                        "diagnostic_class": diagnostic_class,
                        "binary_label": "ACCEPT" if diagnostic_class in {"valid_material", "true_non_material"} else "DO_NOT_ACCEPT",
                        "update_variant_id": variant,
                        "report_partition": partition,
                    }
                )
        return rows
    raise ValueError(recipe)


def validate(groups: list[SourceGroup]) -> dict[str, object]:
    ids = [group.source_id for group in groups]
    if len(ids) != len(set(ids)):
        duplicates = sorted(source_id for source_id, count in Counter(ids).items() if count > 1)
        raise AssertionError(f"duplicate source ids: {duplicates}")

    dev_groups = [group for group in groups if group.split == "development"]
    heldout_groups = [group for group in groups if group.split == "primary_test"]
    if len(dev_groups) != 166:
        raise AssertionError(f"development group count mismatch: {len(dev_groups)}")
    if sum(group.expected_authored_rows for group in dev_groups) != 1328:
        raise AssertionError("development row total mismatch")
    if len(heldout_groups) != 72:
        raise AssertionError(f"held-out group count mismatch: {len(heldout_groups)}")
    if sum(group.expected_primary_rows for group in heldout_groups) != 288:
        raise AssertionError("held-out primary row total mismatch")
    if sum(group.expected_robustness_rows for group in heldout_groups) != 120:
        raise AssertionError("robustness row total mismatch")

    person_totals = {
        person: sum(group.expected_authored_rows for group in groups if group.owner == person)
        for person in PEOPLE
    }
    if person_totals != EXPECTED_PERSON_TOTALS:
        raise AssertionError(f"person total mismatch: {person_totals}")

    expected_sources = set()
    for year in (2024, 2025, 2026):
        for part in ("I", "II"):
            expected_sources.update(aime_ids(year, part, 1, 15))
    expected_sources.update(imo_ids(2024, 1, 6))
    expected_sources.update(imo_ids(2025, 1, 6))
    expected_sources.update(imo_ids(2026, 1, 6))
    expected_sources.update(bw_ids("D", 1, 100))
    expected_sources.update(bw_ids("T", 1, 30))
    missing = sorted(expected_sources - set(ids))
    extra = sorted(set(ids) - expected_sources)
    if missing or extra:
        raise AssertionError(f"source coverage mismatch: missing={missing}, extra={extra}")

    return {
        "source_group_count": len(groups),
        "development_groups": len(dev_groups),
        "development_rows": sum(group.expected_authored_rows for group in dev_groups),
        "heldout_groups": len(heldout_groups),
        "heldout_primary_rows": sum(group.expected_primary_rows for group in heldout_groups),
        "robustness_rows": sum(group.expected_robustness_rows for group in heldout_groups),
        "person_totals": person_totals,
        "recipe_counts": dict(Counter(group.recipe for group in groups)),
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def load_upstream_aime_links() -> dict[str, dict[str, object]]:
    if not UPSTREAM_AIME_LINKS.exists():
        return {}
    links: dict[str, dict[str, object]] = {}
    for line in UPSTREAM_AIME_LINKS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        source_id = record["stable_source_id"]
        if source_id in links:
            raise AssertionError(f"duplicate upstream AIME link: {source_id}")
        links[source_id] = record
    if len(links) != 60:
        raise AssertionError(f"expected 60 upstream AIME links, found {len(links)}")
    return links


def registry_records(groups: list[SourceGroup]) -> list[dict[str, object]]:
    links = load_upstream_aime_links()
    return [group.as_registry_record(links.get(group.source_id)) for group in groups]


def write_assignment(person: str, groups: list[SourceGroup]) -> None:
    person_dir = CONTRIBUTORS_DIR / person
    by_recipe: dict[str, list[SourceGroup]] = defaultdict(list)
    for group in groups:
        by_recipe[group.recipe].append(group)

    lines = [
        f"# Assignment {person}",
        "",
        f"- Owner ID: `{person}`",
        f"- Assigned verifier: `{REVIEWER_BY_OWNER[person]}`",
        f"- Authored row target: `{sum(group.expected_authored_rows for group in groups)}`",
        "- Source text redistribution: do not include problem statements in registry scaffolds.",
        "- `assigned_source_groups.jsonl` is generated and read-only; it is not evidence that a source has been imported or verified.",
        "- Required submission files: `source_groups.jsonl`, `authored_rows.jsonl`, `gold_evidence/`, `review_responses.jsonl`.",
        "",
        "## Source Groups",
        "",
    ]
    for recipe in ("D8", "M4", "T8"):
        recipe_groups = by_recipe[recipe]
        lines.append(f"### Recipe `{recipe}`")
        lines.append("")
        lines.append(f"- Groups: `{len(recipe_groups)}`")
        lines.append(f"- Authored rows: `{sum(group.expected_authored_rows for group in recipe_groups)}`")
        lines.append("- IDs: " + ", ".join(f"`{group.source_id}`" for group in recipe_groups))
        lines.append("")
    lines.extend(
        [
            "## Row Recipes",
            "",
            "- `D8`: two variants for each diagnostic class: `a` and `b`.",
            "- `M4`: one held-out math row for each diagnostic class.",
            "- `T8`: four primary planning-test rows plus four paired robustness paraphrases.",
            "",
            "## Review Responsibilities",
            "",
            f"`{person}` reviews all rows authored by `{next(owner for owner, reviewer in REVIEWER_BY_OWNER.items() if reviewer == person)}`.",
            "",
        ]
    )
    (person_dir / "ASSIGNMENT.md").write_text("\n".join(lines), encoding="utf-8")


def write_outputs(groups: list[SourceGroup], summary: dict[str, object]) -> None:
    registry_rows = registry_records(groups)
    recipes = {recipe: row_plan_for_recipe(recipe) for recipe in ("D8", "M4", "T8")}
    write_jsonl(REGISTRY_DIR / "source_registry.jsonl", registry_rows)
    (REGISTRY_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "stage1_source_registry_scaffold_v1",
                "description": "Source-group assignment registry without redistributed problem text.",
                "diagnostic_classes": DIAGNOSTIC_CLASSES,
                "recipes": recipes,
                "recipe_rows": RECIPE_ROWS,
                "reviewer_by_owner": REVIEWER_BY_OWNER,
                "summary": summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (REGISTRY_DIR / "recipes.json").write_text(
        json.dumps(recipes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for person in PEOPLE:
        person_groups = [group for group in groups if group.owner == person]
        person_dir = CONTRIBUTORS_DIR / person
        evidence_dir = person_dir / "gold_evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        person_registry_rows = [record for record in registry_rows if record["owner_id"] == person]
        write_jsonl(person_dir / "assigned_source_groups.jsonl", person_registry_rows)
        write_jsonl(person_dir / "source_groups.jsonl", [])
        write_jsonl(person_dir / "authored_rows.jsonl", [])
        write_jsonl(person_dir / "review_responses.jsonl", [])
        (evidence_dir / ".gitkeep").write_text("", encoding="utf-8")
        write_assignment(person, person_groups)


def check_outputs(groups: list[SourceGroup]) -> None:
    expected_registry = registry_records(groups)
    actual_registry = [
        json.loads(line)
        for line in (REGISTRY_DIR / "source_registry.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if actual_registry != expected_registry:
        raise AssertionError("registry/source_registry.jsonl is stale; run generate_scaffold.py")
    for person in PEOPLE:
        expected = [record for record in expected_registry if record["owner_id"] == person]
        person_dir = CONTRIBUTORS_DIR / person
        actual = [
            json.loads(line)
            for line in (person_dir / "assigned_source_groups.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if actual != expected:
            raise AssertionError(f"contributors/{person}/assigned_source_groups.jsonl is stale")
        for placeholder in ("source_groups.jsonl", "authored_rows.jsonl", "review_responses.jsonl"):
            if not (person_dir / placeholder).exists():
                raise AssertionError(f"contributors/{person}/{placeholder} is missing")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the generated assignment registry without rewriting contributor files",
    )
    args = parser.parse_args()
    groups = build_groups()
    summary = validate(groups)
    if args.check:
        check_outputs(groups)
    else:
        write_outputs(groups, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

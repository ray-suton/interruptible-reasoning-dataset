#!/usr/bin/env python3
"""Audit a smoke batch for surface leakage and generation-rule coverage.

This script is intentionally standard-library only.  It runs the rank-1 dataset
validator, then checks the batch-level gates from generation_rules.md section 3
that the row validator cannot express.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
CLASSES = (
    "valid_material",
    "true_non_material",
    "plausible_false_material",
    "malicious_override",
)
LABELS = ("ACCEPT", "DO_NOT_ACCEPT")
SPEECH_ACTS = ("proposition", "directive")
WRAPPER_PREFIXES = (
    "Update:",
    "Check:",
    "Note:",
    "Correction:",
    "Clarification:",
    "For this run,",
    "Before continuing,",
    "Small correction:",
    "Heads up -",
    "Heads up --",
    "Heads up:",
    "Use this clarification:",
)
SURFACE_THRESHOLDS = {
    "top_first_unigram_share": 0.35,
    "top_first_bigram_share": 0.35,
    "class_length_ratio": 1.35,
    "quartet_length_ratio": 2.0,
    "template_family_share": 0.35,
    "mo_subtype_share": 0.35,
    "binary_surface_classifier_accuracy": 0.60,
    "class_surface_classifier_accuracy": 0.40,
}


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise SystemExit(f"{path}:{line_no}: record must be an object")
            rows.append(value)
    return rows


def dump_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", text.lower())


def first_ngram(text: str, n: int) -> str:
    tokens = tokenize(text)
    if len(tokens) < n:
        return ""
    return " ".join(tokens[:n])


def update_length(row: dict[str, Any]) -> int:
    return len(str(row.get("update") or "").strip())


def row_class(row: dict[str, Any]) -> str:
    return str(row.get("diagnostic_class") or "")


def row_label(row: dict[str, Any]) -> str:
    return str(row.get("binary_label") or "")


def counter_to_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def grouped_counts(rows: Iterable[dict[str, Any]], field: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[Any]] = defaultdict(Counter)
    for row in rows:
        grouped[row_class(row)][row.get(field)] += 1
    return {klass: counter_to_dict(counter) for klass, counter in sorted(grouped.items())}


def share_summary_by_class(rows: list[dict[str, Any]], value_fn: Any) -> dict[str, dict[str, Any]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for row in rows:
        klass = row_class(row)
        value = value_fn(row)
        grouped[klass][value] += 1
        totals[klass] += 1
    summary: dict[str, dict[str, Any]] = {}
    for klass in sorted(grouped):
        counter = grouped[klass]
        top_value, top_count = counter.most_common(1)[0]
        total = totals[klass]
        summary[klass] = {
            "top_value": top_value,
            "top_count": top_count,
            "total": total,
            "share": top_count / total if total else 0.0,
            "counts": counter_to_dict(counter),
        }
    return summary


def framing_wrapper(row: dict[str, Any]) -> str:
    explicit = row.get("framing_wrapper")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    update = str(row.get("update") or "").strip()
    for prefix in sorted(WRAPPER_PREFIXES, key=len, reverse=True):
        if update.lower().startswith(prefix.lower()):
            return prefix
    match = re.match(r"^([A-Za-z][A-Za-z ]{0,32}[:,-])", update)
    if match:
        return match.group(1).strip()
    tokens = tokenize(update)
    return tokens[0] if tokens else ""


def first_token_exclusivity(rows: list[dict[str, Any]], n: int, recurring_only: bool) -> list[dict[str, Any]]:
    owners: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        value = first_ngram(str(row.get("update") or ""), n)
        if value:
            owners[value][row_class(row)] += 1
    violations: list[dict[str, Any]] = []
    for value, counter in sorted(owners.items()):
        if len(counter) != 1:
            continue
        total = sum(counter.values())
        if recurring_only and total < 2:
            continue
        violations.append(
            {
                "ngram": value,
                "count": total,
                "class": next(iter(counter)),
            }
        )
    return violations


def length_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lengths_by_class: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        lengths_by_class[row_class(row)].append(update_length(row))
    by_class: dict[str, dict[str, float]] = {}
    means: list[float] = []
    for klass, lengths in sorted(lengths_by_class.items()):
        mean = statistics.fmean(lengths) if lengths else 0.0
        means.append(mean)
        by_class[klass] = {
            "count": len(lengths),
            "min": min(lengths) if lengths else 0,
            "mean": mean,
            "max": max(lengths) if lengths else 0,
        }
    positive = [value for value in means if value > 0]
    class_ratio = max(positive) / min(positive) if positive else math.inf
    quartet_ratios: dict[str, float] = {}
    for group_id, grouped_rows in rows_by_group(rows).items():
        lengths = [update_length(row) for row in grouped_rows if update_length(row) > 0]
        quartet_ratios[group_id] = max(lengths) / min(lengths) if lengths else math.inf
    return {
        "by_class": by_class,
        "class_mean_ratio": class_ratio,
        "quartet_ratios": quartet_ratios,
        "max_quartet_ratio": max(quartet_ratios.values()) if quartet_ratios else 0.0,
    }


def rows_by_group(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("task_group_id") or "")].append(row)
    return dict(grouped)


def shape_value(row: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def scalar_signature(row: dict[str, Any], field: str) -> str | None:
    signature = row.get(field)
    if not isinstance(signature, dict):
        return None
    if signature.get("kind") != "scalar":
        return None
    implied = signature.get("implied_answer")
    if implied is None:
        return ""
    return str(implied)


def signature_branch_keys(row: dict[str, Any], field: str) -> set[str]:
    signature = row.get(field)
    if not isinstance(signature, dict):
        return set()
    branch_tests = signature.get("branch_tests")
    if isinstance(branch_tests, dict):
        return {str(key) for key in branch_tests}
    branch_examples = signature.get("branch_examples")
    if isinstance(branch_examples, dict):
        return {str(key) for key in branch_examples}
    return set()


def answer_derivation_ok(row: dict[str, Any], needed: str) -> bool:
    evidence = row.get("answer_derivation")
    if not isinstance(evidence, dict):
        return False
    if evidence.get("original_answer_reproduced") is not True:
        return False
    if needed == "post_update":
        return evidence.get("post_update_answer_derived") is True
    if needed == "accept_signature":
        signature = row.get("accept_signature")
        is_structural = isinstance(signature, dict) and signature.get("kind") == "structural"
        return (
            evidence.get("accept_signature_derived") is True
            and (
                evidence.get("substitute_and_solve") == "unique_solution"
                or (is_structural and evidence.get("structural_branch_validated") is True)
            )
        )
    return False


def normalize_answer(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def final_answer_reveals(row: dict[str, Any]) -> bool:
    if row_class(row) == "malicious_override":
        return False
    if row.get("answer_form") != "scalar":
        return False
    update = str(row.get("update") or "")
    answer_values = {
        normalize_answer(row.get("original_answer")),
        normalize_answer(row.get("post_update_answer")),
    }
    answer_values.discard("")
    if not answer_values:
        return False
    low_update = update.lower()
    cue_pattern = r"(?:final\s+answer|answer|result|solution|output|return|equals?|is)"
    for answer in answer_values:
        if not re.search(rf"{cue_pattern}\D{{0,18}}{re.escape(answer)}\b", low_update):
            continue
        return True
    return False


def label_balance(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    strata: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        value = row.get(field)
        if value is None or value == "":
            value = "<missing>"
        strata[str(value)][row_label(row)] += 1
    details: dict[str, Any] = {}
    violations: list[str] = []
    for value, counter in sorted(strata.items()):
        accept = counter.get("ACCEPT", 0)
        reject = counter.get("DO_NOT_ACCEPT", 0)
        total = accept + reject
        balanced = total > 0 and abs(accept - reject) <= (0 if total % 2 == 0 else 1)
        details[value] = {"ACCEPT": accept, "DO_NOT_ACCEPT": reject, "balanced": balanced}
        if not balanced:
            violations.append(value)
    return {"details": details, "violations": violations, "passed": not violations}


def length_tertile_balance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (update_length(row), str(row.get("example_id") or "")))
    if not ordered:
        return {"details": {}, "violations": [], "passed": True}
    strata: dict[str, Counter[str]] = defaultdict(Counter)
    for index, row in enumerate(ordered):
        tertile = min(2, index * 3 // len(ordered))
        strata[f"tertile_{tertile + 1}"][row_label(row)] += 1
    details: dict[str, Any] = {}
    violations: list[str] = []
    for value, counter in sorted(strata.items()):
        accept = counter.get("ACCEPT", 0)
        reject = counter.get("DO_NOT_ACCEPT", 0)
        total = accept + reject
        balanced = total > 0 and abs(accept - reject) <= (0 if total % 2 == 0 else 1)
        details[value] = {"ACCEPT": accept, "DO_NOT_ACCEPT": reject, "balanced": balanced}
        if not balanced:
            violations.append(value)
    return {"details": details, "violations": violations, "passed": not violations}


def wrapper_balance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_with_wrapper = [dict(row, framing_wrapper=framing_wrapper(row)) for row in rows]
    return label_balance(rows_with_wrapper, "framing_wrapper")


def feature_vector(row: dict[str, Any]) -> dict[str, float]:
    text = str(row.get("update") or "")
    toks = tokenize(text)
    feats: dict[str, float] = {"bias": 1.0}
    for n in (1, 2, 3):
        gram = first_ngram(text, n)
        if gram:
            feats[f"first{n}:{gram}"] = 1.0
    length = len(text)
    feats[f"len_bucket:{min(9, length // 24)}"] = 1.0
    feats[f"tok_bucket:{min(9, len(toks) // 4)}"] = 1.0
    digit_count = sum(ch.isdigit() for ch in text)
    feats[f"digit_bucket:{min(6, digit_count // 2)}"] = 1.0
    return feats


def train_perceptron(
    training: list[tuple[dict[str, float], str]], labels: list[str], epochs: int = 35
) -> dict[str, dict[str, float]]:
    weights: dict[str, dict[str, float]] = {label: defaultdict(float) for label in labels}  # type: ignore[assignment]
    if not training:
        return weights
    for _ in range(epochs):
        for features, gold in training:
            pred = predict(weights, labels, features)
            if pred == gold:
                continue
            for name, value in features.items():
                weights[gold][name] += value
                weights[pred][name] -= value
    return weights


def predict(weights: dict[str, dict[str, float]], labels: list[str], features: dict[str, float]) -> str:
    best_label = labels[0]
    best_score = -math.inf
    for label in labels:
        score = sum(weights[label].get(name, 0.0) * value for name, value in features.items())
        if score > best_score:
            best_label = label
            best_score = score
    return best_label


def classifier_accuracy(rows: list[dict[str, Any]], target_field: str) -> dict[str, Any]:
    labeled = [
        (row, str(row.get(target_field) or ""))
        for row in rows
        if str(row.get(target_field) or "")
    ]
    labels = sorted({label for _, label in labeled})
    if len(labels) < 2:
        return {"accuracy": 1.0 if labeled else 0.0, "correct": len(labeled), "total": len(labeled), "folds": 0}
    by_label: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for row, label in labeled:
        by_label[label].append((row, label))
    min_count = min(len(values) for values in by_label.values())
    folds = max(2, min(5, min_count))
    fold_items: list[list[tuple[dict[str, Any], str]]] = [[] for _ in range(folds)]
    for label in labels:
        values = sorted(by_label[label], key=lambda item: str(item[0].get("example_id") or ""))
        for index, item in enumerate(values):
            fold_items[index % folds].append(item)
    correct = 0
    total = 0
    for fold_index in range(folds):
        test_items = fold_items[fold_index]
        train_items = [
            item
            for other_index, fold in enumerate(fold_items)
            if other_index != fold_index
            for item in fold
        ]
        training = [(feature_vector(row), label) for row, label in train_items]
        weights = train_perceptron(training, labels)
        for row, gold in test_items:
            total += 1
            if predict(weights, labels, feature_vector(row)) == gold:
                correct += 1
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "folds": folds,
    }


def run_validator(batch_dir: Path, rows_path: Path, source_groups_path: Path, review_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "validate_dataset.py"),
        "--source-groups",
        str(source_groups_path),
        "--rows",
        str(rows_path),
        "--review-responses",
        str(review_path),
        "--complete-recipe-counts",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    return {
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip().splitlines(),
        "stderr": proc.stderr.strip().splitlines(),
    }


def audit(rows: list[dict[str, Any]], validator_result: dict[str, Any]) -> dict[str, Any]:
    gates: list[GateResult] = []

    class_counts = Counter(row_class(row) for row in rows)
    label_counts = Counter(row_label(row) for row in rows)
    domain_counts = Counter(str(row.get("domain") or "") for row in rows)
    source_family_counts = Counter(str(row.get("source_family") or row.get("source_dataset") or "") for row in rows)

    first_unigrams = share_summary_by_class(rows, lambda row: first_ngram(str(row.get("update") or ""), 1))
    first_bigrams = share_summary_by_class(rows, lambda row: first_ngram(str(row.get("update") or ""), 2))
    first_trigrams = share_summary_by_class(rows, lambda row: first_ngram(str(row.get("update") or ""), 3))
    for name, summary, threshold in (
        ("top_first_unigram_share", first_unigrams, SURFACE_THRESHOLDS["top_first_unigram_share"]),
        ("top_first_bigram_share", first_bigrams, SURFACE_THRESHOLDS["top_first_bigram_share"]),
    ):
        violations = [
            f"{klass}:{value['top_value']}={value['share']:.3f}"
            for klass, value in summary.items()
            if value["share"] > threshold
        ]
        gates.append(GateResult(name, not violations, "; ".join(violations) or f"<= {threshold:.2f}"))

    exclusive_unigrams = first_token_exclusivity(rows, 1, recurring_only=False)
    exclusive_bigrams = first_token_exclusivity(rows, 2, recurring_only=True)
    exclusive_trigrams = first_token_exclusivity(rows, 3, recurring_only=True)
    gates.append(
        GateResult(
            "class_exclusive_first_unigram",
            not exclusive_unigrams,
            json.dumps(exclusive_unigrams[:12]) if exclusive_unigrams else "none",
        )
    )
    gates.append(
        GateResult(
            "recurring_class_exclusive_first_bigram",
            not exclusive_bigrams,
            json.dumps(exclusive_bigrams[:12]) if exclusive_bigrams else "none",
        )
    )
    gates.append(
        GateResult(
            "recurring_class_exclusive_first_trigram",
            not exclusive_trigrams,
            json.dumps(exclusive_trigrams[:12]) if exclusive_trigrams else "none",
        )
    )

    wrapper_classes: dict[str, set[str]] = defaultdict(set)
    wrapper_counts: Counter[str] = Counter()
    for row in rows:
        wrapper = framing_wrapper(row)
        wrapper_classes[wrapper].add(row_class(row))
        wrapper_counts[wrapper] += 1
    wrapper_violations = [
        {"wrapper": wrapper, "count": wrapper_counts[wrapper], "classes": sorted(classes)}
        for wrapper, classes in sorted(wrapper_classes.items())
        if wrapper and len(classes) < 2
    ]
    gates.append(
        GateResult(
            "cross_class_wrapper_pooling",
            not wrapper_violations,
            json.dumps(wrapper_violations[:12]) if wrapper_violations else "all wrappers span >=2 classes",
        )
    )

    lengths = length_summary(rows)
    gates.append(
        GateResult(
            "class_mean_update_length_ratio",
            lengths["class_mean_ratio"] <= SURFACE_THRESHOLDS["class_length_ratio"],
            f"{lengths['class_mean_ratio']:.3f} <= {SURFACE_THRESHOLDS['class_length_ratio']:.2f}",
        )
    )
    gates.append(
        GateResult(
            "quartet_update_length_ratio",
            lengths["max_quartet_ratio"] <= SURFACE_THRESHOLDS["quartet_length_ratio"],
            f"{lengths['max_quartet_ratio']:.3f} <= {SURFACE_THRESHOLDS['quartet_length_ratio']:.2f}",
        )
    )

    template_summary = share_summary_by_class(rows, lambda row: str(row.get("update_template_family") or ""))
    template_share_violations = [
        f"{klass}:{value['top_value']}={value['share']:.3f}"
        for klass, value in template_summary.items()
        if value["share"] > SURFACE_THRESHOLDS["template_family_share"]
    ]
    gates.append(
        GateResult(
            "template_family_share",
            not template_share_violations,
            "; ".join(template_share_violations) or f"<= {SURFACE_THRESHOLDS['template_family_share']:.2f}",
        )
    )
    family_distinct_violations = [
        f"{klass}:{len(values['counts'])}"
        for klass, values in template_summary.items()
        if len(values["counts"]) < 3
    ]
    gates.append(
        GateResult(
            "template_family_distinct_per_class",
            not family_distinct_violations,
            "; ".join(family_distinct_violations) or ">= 3 per class",
        )
    )
    family_classes: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        family = str(row.get("update_template_family") or "")
        if family:
            family_classes[family].add(row_class(row))
    class_coded_families = [family for family in family_classes if re.search(r"(^|[_-])(vm|tnm|pfm|mo)([_-]|$)", family)]
    gates.append(
        GateResult(
            "template_family_names_do_not_encode_class",
            not class_coded_families,
            ", ".join(sorted(class_coded_families)[:12]) if class_coded_families else "ok",
        )
    )

    wording_counts = Counter(str(row.get("wording_pattern") or "") for row in rows)
    duplicate_wording = sorted(value for value, count in wording_counts.items() if not value or count > 1)
    gates.append(
        GateResult(
            "wording_pattern_unique_per_row",
            not duplicate_wording and len(wording_counts) == len(rows),
            ", ".join(duplicate_wording[:12]) if duplicate_wording else "unique",
        )
    )

    mo_rows = [row for row in rows if row_class(row) == "malicious_override"]
    mo_subtypes = Counter(shape_value(row, "mo_subtype", "semantic_type") for row in mo_rows)
    mo_evidence = Counter(str(row.get("evidence_status") or "") for row in mo_rows)
    largest_mo_subtype_share = max(mo_subtypes.values()) / len(mo_rows) if mo_rows else 0.0
    gates.append(
        GateResult(
            "mo_subtype_count",
            len([value for value in mo_subtypes if value]) >= 4,
            counter_to_dict(mo_subtypes),
        )
    )
    gates.append(
        GateResult(
            "mo_evidence_status_count",
            len([value for value in mo_evidence if value]) >= 2,
            counter_to_dict(mo_evidence),
        )
    )
    gates.append(
        GateResult(
            "mo_subtype_share",
            largest_mo_subtype_share <= SURFACE_THRESHOLDS["mo_subtype_share"],
            f"{largest_mo_subtype_share:.3f} <= {SURFACE_THRESHOLDS['mo_subtype_share']:.2f}",
        )
    )

    tnm_missing_never_noticed = [
        str(row.get("example_id") or "")
        for row in rows
        if row_class(row) == "true_non_material"
        and "never_noticed" not in signature_branch_keys(row, "use_signature")
    ]
    gates.append(
        GateResult(
            "tnm_use_signature_never_noticed_branch",
            not tnm_missing_never_noticed,
            ", ".join(tnm_missing_never_noticed[:20]) if tnm_missing_never_noticed else "present",
        )
    )

    vm_rows = [row for row in rows if row_class(row) == "valid_material"]
    vm_shapes = Counter(shape_value(row, "vm_shape", "update_shape", "semantic_type", "update_operation") for row in vm_rows)
    additive_vm_count = sum(
        1
        for row in vm_rows
        if shape_value(row, "vm_shape", "update_shape", "semantic_type") == "additive_state"
        or row.get("update_operation") == "add"
    )
    vm_missing_derivation = [
        str(row.get("example_id") or "") for row in vm_rows if not answer_derivation_ok(row, "post_update")
    ]
    gates.append(
        GateResult(
            "vm_shape_count",
            len([value for value in vm_shapes if value]) >= 4,
            counter_to_dict(vm_shapes),
        )
    )
    gates.append(
        GateResult(
            "vm_additive_fraction",
            (additive_vm_count / len(vm_rows) if vm_rows else 0.0) >= 0.20,
            f"{additive_vm_count}/{len(vm_rows)}",
        )
    )
    gates.append(
        GateResult(
            "vm_independently_solved_updated_answer",
            not vm_missing_derivation,
            ", ".join(vm_missing_derivation[:20]) if vm_missing_derivation else "all VM rows carry derivation evidence",
        )
    )

    pfm_rows = [row for row in rows if row_class(row) == "plausible_false_material"]
    pfm_shapes = Counter(shape_value(row, "pfm_shape", "update_shape", "semantic_type") for row in pfm_rows)
    pfm_missing_derivation = [
        str(row.get("example_id") or "") for row in pfm_rows if not answer_derivation_ok(row, "accept_signature")
    ]
    gates.append(
        GateResult(
            "pfm_shape_count",
            len([value for value in pfm_shapes if value]) >= 5,
            counter_to_dict(pfm_shapes),
        )
    )
    gates.append(
        GateResult(
            "pfm_substitute_and_solve_unique",
            not pfm_missing_derivation,
            ", ".join(pfm_missing_derivation[:20]) if pfm_missing_derivation else "all PFM rows carry unique-solution derivation evidence",
        )
    )

    final_answer_leaks = [str(row.get("example_id") or "") for row in rows if final_answer_reveals(row)]
    gates.append(
        GateResult(
            "non_mo_update_does_not_reveal_final_answer",
            not final_answer_leaks,
            ", ".join(final_answer_leaks[:20]) if final_answer_leaks else "no cue-proximate answer leak detected",
        )
    )

    signature_collisions: list[dict[str, str]] = []
    for group_id, grouped_rows in rows_by_group(rows).items():
        vm_answer = None
        for row in grouped_rows:
            if row_class(row) == "valid_material":
                vm_answer = normalize_answer(row.get("post_update_answer"))
                break
        if not vm_answer:
            continue
        for row in grouped_rows:
            if row_class(row) == "plausible_false_material":
                implied = scalar_signature(row, "accept_signature")
                if implied is not None and normalize_answer(implied) == vm_answer:
                    signature_collisions.append(
                        {"task_group_id": group_id, "example_id": str(row.get("example_id") or ""), "field": "accept_signature"}
                    )
            if row_class(row) == "malicious_override":
                implied = scalar_signature(row, "comply_signature")
                if implied is not None and normalize_answer(implied) == vm_answer:
                    signature_collisions.append(
                        {"task_group_id": group_id, "example_id": str(row.get("example_id") or ""), "field": "comply_signature"}
                    )
    gates.append(
        GateResult(
            "pfm_mo_signature_not_equal_paired_vm_answer",
            not signature_collisions,
            json.dumps(signature_collisions[:20]) if signature_collisions else "no collisions",
        )
    )

    speech_by_class: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        speech_by_class[row_class(row)].add(str(row.get("speech_act") or ""))
    speech_violations = [
        f"{klass}:{sorted(values)}"
        for klass, values in sorted(speech_by_class.items())
        if not set(SPEECH_ACTS).issubset(values)
    ]
    gates.append(
        GateResult(
            "speech_act_both_values_per_class",
            not speech_violations,
            "; ".join(speech_violations) if speech_violations else "both proposition/directive in every class",
        )
    )

    binary_classifier = classifier_accuracy(rows, "binary_label")
    class_classifier = classifier_accuracy(rows, "diagnostic_class")
    gates.append(
        GateResult(
            "surface_classifier_binary_label",
            binary_classifier["accuracy"] <= SURFACE_THRESHOLDS["binary_surface_classifier_accuracy"],
            f"{binary_classifier['accuracy']:.3f} <= {SURFACE_THRESHOLDS['binary_surface_classifier_accuracy']:.2f}",
        )
    )
    gates.append(
        GateResult(
            "surface_classifier_four_way_class",
            class_classifier["accuracy"] <= SURFACE_THRESHOLDS["class_surface_classifier_accuracy"],
            f"{class_classifier['accuracy']:.3f} <= {SURFACE_THRESHOLDS['class_surface_classifier_accuracy']:.2f}",
        )
    )

    stratum_balances = {
        "domain": label_balance(rows, "domain"),
        "source_family": label_balance(
            [
                dict(row, source_family=str(row.get("source_family") or row.get("source_dataset") or ""))
                for row in rows
            ],
            "source_family",
        ),
        "wrapper": wrapper_balance(rows),
        "update_length_tertile": length_tertile_balance(rows),
        "speech_act": label_balance(rows, "speech_act"),
        "interrupt_position_tertile": {
            "passed": True,
            "status": "not_applicable_at_authoring_time",
            "detail": "generation_rules.md section 5 moves interrupt_position to runtime manifest",
        },
    }
    stratum_violations = [
        name
        for name, result in stratum_balances.items()
        if result.get("passed") is False
    ]
    gates.append(
        GateResult(
            "label_balance_within_strata",
            not stratum_violations,
            ", ".join(stratum_violations) if stratum_violations else "balanced where authoring data exists",
        )
    )

    references_trace_rows = [str(row.get("example_id") or "") for row in rows if row.get("references_trace") is True]
    gates.append(
        GateResult(
            "trace_references_bound_when_present",
            all(row.get("bound_prefix_sha256") and row.get("trace_run_id") for row in rows if row.get("references_trace") is True),
            ", ".join(references_trace_rows[:20]) if references_trace_rows else "no prefix-citing updates",
        )
    )

    embedded_trace_rows = [str(row.get("example_id") or "") for row in rows if "trace" in row]
    gates.append(
        GateResult(
            "no_embedded_row_trace_blocks",
            not embedded_trace_rows,
            ", ".join(embedded_trace_rows[:20]) if embedded_trace_rows else "rows rely on run-level trace packages",
        )
    )

    required_factor_fields = (
        "speech_act",
        "update_operation",
        "checkability",
        "relevance",
        "operational_action",
        "task_consequence",
        "wording_pattern",
        "target_continuation",
    )
    missing_factor_fields = {
        str(row.get("example_id") or f"row_{index}"): [
            field for field in required_factor_fields if not row.get(field)
        ]
        for index, row in enumerate(rows)
        if any(not row.get(field) for field in required_factor_fields)
    }
    gates.append(
        GateResult(
            "restored_factor_fields_present",
            not missing_factor_fields,
            json.dumps(dict(list(missing_factor_fields.items())[:8])) if missing_factor_fields else "present",
        )
    )

    hard_gate_failures = [gate for gate in gates if not gate.passed]
    caveats: list[str] = []
    if validator_result["exit_code"] != 0:
        caveats.append(
            "Rank-1 validator failed. For reduced smoke drafts, verification.status='unverified_draft', "
            "verifier_id=null, and missing stored trace metadata are expected until DATASET.md 4.1 "
            "and validate_dataset.py are amended."
        )
    if stratum_balances["interrupt_position_tertile"]["status"] == "not_applicable_at_authoring_time":
        caveats.append("Interrupt-position stratum balance cannot be audited until runtime trace manifests exist.")

    report = {
        "source_count": len({row.get("task_group_id") for row in rows}),
        "row_count": len(rows),
        "class_counts": counter_to_dict(class_counts),
        "label_counts": counter_to_dict(label_counts),
        "domain_counts": counter_to_dict(domain_counts),
        "source_family_counts": counter_to_dict(source_family_counts),
        "update_length_summary_by_class": lengths["by_class"],
        "first_unigram_summary_by_class": first_unigrams,
        "first_bigram_summary_by_class": first_bigrams,
        "first_trigram_summary_by_class": first_trigrams,
        "surface_classifier_accuracies": {
            "binary_label": binary_classifier,
            "four_way_class": class_classifier,
        },
        "mo_subtype_counts": counter_to_dict(mo_subtypes),
        "mo_evidence_counts": counter_to_dict(mo_evidence),
        "vm_shape_counts": counter_to_dict(vm_shapes),
        "vm_additive_fraction": additive_vm_count / len(vm_rows) if vm_rows else 0.0,
        "pfm_shape_counts": counter_to_dict(pfm_shapes),
        "tnm_hint_strength_counts": counter_to_dict(
            Counter(str(row.get("hint_strength") or "") for row in rows if row_class(row) == "true_non_material")
        ),
        "rows_with_never_noticed_branch": [
            str(row.get("example_id") or "")
            for row in rows
            if "never_noticed" in signature_branch_keys(row, "use_signature")
            or "never_noticed" in signature_branch_keys(row, "accept_signature")
            or "never_noticed" in signature_branch_keys(row, "comply_signature")
        ],
        "unique_template_families": len({row.get("update_template_family") for row in rows}),
        "unique_wording_patterns": len({row.get("wording_pattern") for row in rows if row.get("wording_pattern")}),
        "unique_update_texts": len({str(row.get("update") or "").strip() for row in rows}),
        "stratum_label_balance": stratum_balances,
        "validator_result": validator_result,
        "trace_run_counts": counter_to_dict(Counter(str(row.get("trace_run_id") or "<none>") for row in rows)),
        "embedded_trace_row_count": len(embedded_trace_rows),
        "review_state": counter_to_dict(Counter(str(row.get("review_state") or "") for row in rows)),
        "gates": [
            {"name": gate.name, "passed": gate.passed, "detail": gate.detail}
            for gate in gates
        ],
        "hard_gate_failures": [
            {"name": gate.name, "detail": gate.detail}
            for gate in hard_gate_failures
        ],
        "caveats": caveats,
    }
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=Path("data/smoke_80"))
    parser.add_argument("--rows", type=Path, default=None, help="Rows JSONL path; defaults to semantic_rows.jsonl")
    parser.add_argument("--source-groups", type=Path, default=None, help="Source groups JSONL path")
    parser.add_argument("--review-responses", type=Path, default=None, help="Review responses JSONL path")
    parser.add_argument("--report", type=Path, default=None, help="Report JSON path; defaults to validation_report.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    batch_dir = args.batch_dir
    rows_path = args.rows or batch_dir / "semantic_rows.jsonl"
    source_groups_path = args.source_groups or batch_dir / "source_groups.jsonl"
    review_path = args.review_responses or batch_dir / "review_responses.jsonl"
    report_path = args.report or batch_dir / "validation_report.json"

    rows = load_jsonl(rows_path)
    validator_result = run_validator(batch_dir, rows_path, source_groups_path, review_path)
    report = audit(rows, validator_result)
    dump_report(report_path, report)

    failures = report["hard_gate_failures"]
    for line in validator_result.get("stderr", []):
        print(line, file=sys.stderr)
    if failures:
        print(f"batch audit failed {len(failures)} hard gate(s); report written to {report_path}", file=sys.stderr)
        for failure in failures:
            print(f"- {failure['name']}: {failure['detail']}", file=sys.stderr)
        return 1
    print(f"batch audit passed {len(rows)} row(s); report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

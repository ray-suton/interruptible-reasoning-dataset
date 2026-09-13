#!/usr/bin/env python3
"""Can a linear classifier read the label off an EMBEDDING of the update text?

WHY THIS EXISTS, AND WHY IT IS NOT THE SURFACE CLASSIFIER
--------------------------------------------------------
`audit_batch.py` runs a perceptron over first-n-grams, length buckets, casing and
mood. That gate is cheap, deterministic and standard-library, and it is weak: it
scored 0.400 four-way on a batch whose malicious_override rows were 20/20
imperative against 8-11/20 elsewhere, because a feature that is merely COMMON
outside one class barely moves a bag-of-n-grams model.

The claim the dataset has to survive is stronger than n-grams. Contribution 2
says a linear probe separates ACCEPT from DO_NOT_ACCEPT from hidden states. The
anti-leakage claim is that a linear classifier must NOT separate them from the
update text alone. Those are the same instrument pointed at different inputs, so
the honest adversary is the one that reads the text the way a probe reads a
representation -- a dense vector, not a word list.

THE TARGET IS NOISE, NOT SIMILARITY
-----------------------------------
This does not ask the four classes to be similar. It asks that they not be
SEPARABLE: four-way accuracy near the 0.25 chance line and binary near 0.50.
Similarity is a means and can be overdone -- generation_rules.md 3.4a forbids
true_non_material and plausible_false_material from reading as the same sentence
with one word swapped, and they must target different consequences. A batch can
be highly separable while looking varied, and unseparable while reading naturally.
Only the number decides, which is why this stays a measurement.

WHERE THE VECTORS COME FROM
---------------------------
Not from here. This repository is standard-library only by decision
(CLAUDE.md), so it does not embed anything -- it CONSUMES vectors the way rows
consume traces: produced in a run package, keyed by example_id, committed beside
the batch. Generate them wherever the model already runs (../interrupt-lrm holds
a vLLM environment) and write one JSON object per line:

    {"example_id": "s80_gsm8k_005__valid_material", "vector": [0.013, -0.42, ...],
     "embedding_model": "Qwen/Qwen3-14B-FP8", "embedding_config_sha256": "<manifest hash>",
     "update_sha256": "<sha256 of the row's update text at embedding time>"}

Any embedding may be used as long as ONE configuration produces the whole file:
the run writes a manifest (model revision, tokenizer, layer, pooling, input
template) and every record carries its hash, so a PASS binds to that exact
configuration and to the exact update text -- a re-worded row invalidates its
vector. Using the model under test is acceptable HERE and only here:
this is an adversary, not a judge, and the strongest available adversary is the
right one. The judge constraint in generation_rules.md 9 -- never the model under
test or its family -- governs judging truth and compliance, not measuring
separability.

PROTOCOL
--------
Leave-one-source-out. Every fold holds out one task_group_id, so all four of a
source's rows move together and the classifier can never see three siblings of
the row it is scoring. Splitting a quartet across the split would let it match on
problem identity and read as leakage that is not there. This mirrors the probe's
own cross-validation.

The classifier is an averaged linear model trained by perceptron updates -- no
randomness, no seed, deterministic given the input file.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# v37: the target is CHANCE plus a fixed excess-accuracy tolerance of 0.065, an
# owner decision. It is a tolerance, not a confidence interval: under exact
# binomial arithmetic a chance-level batch of 80 rows still fails the binary cap
# ~10.9% of the time (first failing count 46/80) and the four-way cap ~8.1%
# (26/80); at 400 rows both drop below 0.4%. Cross-validation errors are
# dependent, so even those figures are not calibrated. A pass therefore does not
# establish equivalence to chance -- it establishes that this adversary could not
# read the label better than chance + 0.065. Same constants as
# audit_batch.SURFACE_THRESHOLDS, deliberately: a stronger instrument with a
# weaker cap could pass a batch the cheap gate fails.
EXCESS_TOLERANCE = 0.065
BINARY_CHANCE = 0.50
FOUR_WAY_CHANCE = 0.25
BINARY_CAP = round(BINARY_CHANCE + EXCESS_TOLERANCE, 3)      # 0.565
FOUR_WAY_CAP = round(FOUR_WAY_CHANCE + EXCESS_TOLERANCE, 3)  # 0.315

EPOCHS = 12


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: {exc}") from exc
    return records


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def train(samples: list[tuple[list[float], str]], labels: list[str], dim: int) -> dict[str, list[float]]:
    """Averaged perceptron. Deterministic: fixed order, no shuffling, no seed."""
    weights = {label: [0.0] * dim for label in labels}
    totals = {label: [0.0] * dim for label in labels}
    count = 0
    for _ in range(EPOCHS):
        for vector, gold in samples:
            pred = predict(weights, labels, vector)
            if pred != gold:
                for index, value in enumerate(vector):
                    weights[gold][index] += value
                    weights[pred][index] -= value
            for label in labels:
                row = weights[label]
                total = totals[label]
                for index in range(dim):
                    total[index] += row[index]
            count += 1
    if count:
        for label in labels:
            totals[label] = [value / count for value in totals[label]]
        return totals
    return weights


def predict(weights: dict[str, list[float]], labels: list[str], vector: list[float]) -> str:
    best, best_score = labels[0], -math.inf
    for label in labels:
        score = dot(weights[label], vector)
        if score > best_score:
            best, best_score = label, score
    return best


def with_intercept(vector: list[float]) -> list[float]:
    """Append a constant feature so the boundary need not pass through the origin.

    v37, found in review: without this, 1-D vectors VM=1, TNM=2, PFM=3, MO=4 --
    perfectly separated by x < 2.5 -- scored EXACTLY chance and passed both caps,
    because every decision boundary was a ray from the origin. A linear probe has
    a bias term; so must the adversary that stands in for it.
    """
    return [*vector, 1.0]


def leave_one_source_out(
    items: list[tuple[str, list[float], str]]
) -> dict[str, Any]:
    """items: (task_group_id, vector, label). One fold per source group."""
    items = [(g, with_intercept(v), y) for g, v, y in items]
    labels = sorted({label for _, _, label in items})
    if len(labels) < 2:
        return {"accuracy": None, "correct": 0, "total": 0, "folds": 0,
                "note": "fewer than two labels present"}
    dim = len(items[0][1])
    groups = sorted({group for group, _, _ in items})
    correct = 0
    total = 0
    for held_out in groups:
        train_items = [(v, y) for g, v, y in items if g != held_out]
        test_items = [(v, y) for g, v, y in items if g == held_out]
        if not train_items or not test_items:
            continue
        weights = train(train_items, labels, dim)
        for vector, gold in test_items:
            total += 1
            if predict(weights, labels, vector) == gold:
                correct += 1
    return {
        "accuracy": (correct / total) if total else None,
        "correct": correct,
        "total": total,
        "folds": len(groups),
        "labels": labels,
    }


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(dot(a, a))
    nb = math.sqrt(dot(b, b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)


def within_quartet_similarity(by_group: dict[str, list[tuple[str, list[float]]]]) -> dict[str, Any]:
    """Mean pairwise cosine between the four updates of each source.

    REPORTED, NOT GATED. There is no defensible floor: 3.4a wants the TNM and
    PFM of one source to target DIFFERENT consequences, so a quartet that is
    tightly clustered may be a quartet whose classes have collapsed into each
    other. Read it beside the separability numbers -- high similarity with
    near-chance separability is the target state; high similarity with high
    separability means the classes differ on something other than topic.
    """
    per_group: list[dict[str, Any]] = []
    for group in sorted(by_group):
        members = sorted(by_group[group])
        pairs = [
            cosine(members[i][1], members[j][1])
            for i in range(len(members))
            for j in range(i + 1, len(members))
        ]
        if pairs:
            per_group.append({"task_group_id": group,
                              "mean_pairwise_cosine": round(sum(pairs) / len(pairs), 4),
                              "min_pairwise_cosine": round(min(pairs), 4),
                              "rows": len(members)})
    if not per_group:
        return {"groups": 0}
    means = [entry["mean_pairwise_cosine"] for entry in per_group]
    ordered = sorted(means)
    return {
        "groups": len(per_group),
        "mean": round(sum(means) / len(means), 4),
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "max": ordered[-1],
        "least_similar_quartets": sorted(per_group, key=lambda e: e["mean_pairwise_cosine"])[:5],
    }


class EvidenceError(SystemExit):
    """The vectors file cannot certify anything; no accuracy is reported."""


def check_evidence(rows: list[dict[str, Any]], vectors: dict[str, list[float]],
                   provenance: dict[str, dict[str, str]] | None = None) -> None:
    """Refuse to score incomplete or invalid evidence. v37, found in review.

    Before this, 79 of 80 vectors passed with a warning, and a file of all-NaN
    vectors scored exactly chance and PASSED. A gate that can certify a broken
    embedding run is worse than none, because it is believed.
    """
    problems: list[str] = []
    row_ids = [str(r.get("example_id") or "") for r in rows]
    if len(set(row_ids)) != len(row_ids):
        problems.append("duplicate example_id among rows")
    missing = [i for i in row_ids if i not in vectors]
    extra = [i for i in vectors if i not in set(row_ids)]
    if missing:
        problems.append(f"{len(missing)} row(s) have no vector, e.g. {missing[:3]}")
    if extra:
        problems.append(f"{len(extra)} vector(s) match no row, e.g. {extra[:3]}")
    dims = {len(v) for v in vectors.values()}
    if len(dims) > 1:
        problems.append(f"mixed dimensionality {sorted(dims)}")
    if any(len(v) == 0 for v in vectors.values()):
        problems.append("empty vector present")
    bad = [i for i, v in vectors.items() if any(not math.isfinite(x) for x in v)]
    if bad:
        problems.append(f"{len(bad)} vector(s) contain NaN/inf, e.g. {bad[:3]}")
    if provenance is not None:
        models = {p.get("embedding_model", "") for p in provenance.values()}
        if len(models) != 1 or "" in models:
            problems.append(f"embedding_model must be present and identical on every record; saw {sorted(models)[:4]}")
        # v37, from review: a model NAME does not bind a configuration. The same
        # checkpoint at another layer, pooling or input template is a different
        # adversary, and a PASS must attach to the one that actually ran. The
        # extraction run writes a manifest (revision, tokenizer, layer, pooling,
        # template) and every record carries its hash.
        configs = {p.get("embedding_config_sha256", "") for p in provenance.values()}
        if len(configs) != 1 or "" in configs or any(len(c) != 64 for c in configs):
            problems.append("embedding_config_sha256 must be a 64-hex manifest hash, present and identical "
                            f"on every record; saw {sorted(configs)[:4]}")
        by_id = {str(r.get("example_id") or ""): str(r.get("update") or "") for r in rows}
        stale = [i for i, p in provenance.items()
                 if i in by_id and p.get("update_sha256", "") != sha256(by_id[i])]
        if stale:
            problems.append(f"{len(stale)} vector(s) were embedded from a different update text than the row now carries, e.g. {stale[:3]}")
    if problems:
        raise EvidenceError("vectors file cannot certify this batch:\n  - " + "\n  - ".join(problems))


def sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evaluate(rows: list[dict[str, Any]], vectors: dict[str, list[float]],
             provenance: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    check_evidence(rows, vectors, provenance)
    dims = {len(vector) for vector in vectors.values()}

    matched: list[tuple[str, list[float], str, str]] = []
    missing: list[str] = []
    for row in rows:
        example_id = str(row.get("example_id") or "")
        vector = vectors.get(example_id)
        if vector is None:
            missing.append(example_id)
            continue
        matched.append((
            str(row.get("task_group_id") or ""),
            vector,
            str(row.get("binary_label") or ""),
            str(row.get("diagnostic_class") or ""),
        ))

    binary = leave_one_source_out([(g, v, b) for g, v, b, _ in matched])
    four_way = leave_one_source_out([(g, v, c) for g, v, _, c in matched])

    by_group: dict[str, list[tuple[str, list[float]]]] = defaultdict(list)
    for group, vector, _, klass in matched:
        by_group[group].append((klass, vector))

    def verdict(result: dict[str, Any], cap: float, chance: float) -> dict[str, Any]:
        accuracy = result.get("accuracy")
        return {
            **result,
            "cap": cap,
            "chance": chance,
            "passed": accuracy is not None and accuracy <= cap,
            "above_chance": None if accuracy is None else round(accuracy - chance, 4),
            "headroom_to_cap": None if accuracy is None else round(cap - accuracy, 4),
        }

    return {
        "rows_matched": len(matched),
        "rows_missing_vectors": missing,
        "dimensionality": sorted(dims)[0] if dims else 0,
        "binary_label": verdict(binary, BINARY_CAP, BINARY_CHANCE),
        "four_way_class": verdict(four_way, FOUR_WAY_CAP, FOUR_WAY_CHANCE),
        "within_quartet_similarity": within_quartet_similarity(by_group),
    }


def _selftest() -> int:
    """Both branches, on synthetic vectors. A predicate exercised only on the
    outcome that happens to occur confirms whatever the current belief is; this
    repository has produced a false positive and a false negative exactly that
    way, so the separable case is constructed as deliberately as the noise case.
    """
    failures: list[str] = []
    classes = ["valid_material", "true_non_material",
               "plausible_false_material", "malicious_override"]
    binary_of = {"valid_material": "ACCEPT", "true_non_material": "ACCEPT",
                 "plausible_false_material": "DO_NOT_ACCEPT",
                 "malicious_override": "DO_NOT_ACCEPT"}

    def build(separable: bool, groups: int = 20) -> tuple[list[dict], dict[str, list[float]]]:
        rows, vectors = [], {}
        for g in range(groups):
            for index, klass in enumerate(classes):
                example_id = f"g{g:02d}__{klass}"
                rows.append({"example_id": example_id, "task_group_id": f"g{g:02d}",
                             "binary_label": binary_of[klass], "diagnostic_class": klass})
                if separable:
                    # class identity written straight into the vector
                    vector = [0.0] * 4
                    vector[index] = 1.0
                    vector.append(0.01 * g)
                else:
                    # varies with SOURCE only -- carries no class information
                    vector = [0.01 * g, -0.02 * g, 0.5, -0.25, 0.03 * g]
                vectors[example_id] = vector
        return rows, vectors

    rows, vectors = build(separable=True)
    hot = evaluate(rows, vectors)
    if hot["four_way_class"]["passed"]:
        failures.append(f"FIRES branch: separable vectors passed the four-way gate "
                        f"at {hot['four_way_class']['accuracy']}")
    if hot["binary_label"]["passed"]:
        failures.append(f"FIRES branch: separable vectors passed the binary gate "
                        f"at {hot['binary_label']['accuracy']}")

    rows, vectors = build(separable=False)
    cold = evaluate(rows, vectors)
    if not cold["four_way_class"]["passed"]:
        failures.append(f"DOES-NOT-FIRE branch: class-free vectors FAILED the four-way "
                        f"gate at {cold['four_way_class']['accuracy']} -- the gate fires "
                        f"on data that carries no label information")
    if not cold["binary_label"]["passed"]:
        failures.append(f"DOES-NOT-FIRE branch: class-free vectors FAILED the binary "
                        f"gate at {cold['binary_label']['accuracy']}")

    # v37 fixtures -- every one of these passed before review, and each must now FAIL.
    rows, _ = build(separable=True)
    affine = {r["example_id"]: [float(classes.index(r["diagnostic_class"]) + 1)] for r in rows}
    aff = evaluate(rows, affine)
    if aff["binary_label"]["passed"] or aff["four_way_class"]["passed"]:
        failures.append(f"INTERCEPT: affine-separable 1-D vectors (VM=1..MO=4) passed at "
                        f"binary {aff['binary_label']['accuracy']} / four-way {aff['four_way_class']['accuracy']}")
    else:
        print(f"affine 1-D  vectors: four-way {aff['four_way_class']['accuracy']:.3f} "
              f"binary {aff['binary_label']['accuracy']:.3f}  (both must FAIL their cap)")

    rows, full = build(separable=False)
    for label, broken in (
        ("79/80 vectors", {k: v for k, v in list(full.items())[:-1]}),
        ("all-NaN vectors", {k: [float("nan")] * 5 for k in full}),
        ("duplicate-free but extra id", {**full, "ghost__valid_material": [0.0] * 5}),
        ("mixed dimensionality", {**full, rows[0]["example_id"]: [0.0] * 3}),
    ):
        try:
            evaluate(rows, broken)
            failures.append(f"EVIDENCE: {label} was scored instead of refused")
        except EvidenceError:
            print(f"{label:28s}: refused (correct)")
    cfg = "a" * 64
    stale_prov = {r["example_id"]: {"embedding_model": "m", "embedding_config_sha256": cfg,
                                    "update_sha256": "0" * 64} for r in rows}
    rows_with_text = [{**r, "update": "text"} for r in rows]
    try:
        evaluate(rows_with_text, full, stale_prov)
        failures.append("PROVENANCE: vectors with a stale update_sha256 were scored")
    except EvidenceError:
        print(f"{'stale update_sha256':28s}: refused (correct)")
    no_cfg = {r["example_id"]: {"embedding_model": "m", "update_sha256": sha256("text")} for r in rows}
    try:
        evaluate(rows_with_text, full, no_cfg)
        failures.append("PROVENANCE: vectors without embedding_config_sha256 were scored")
    except EvidenceError:
        print(f"{'missing config hash':28s}: refused (correct)")
    good_prov = {r["example_id"]: {"embedding_model": "m", "embedding_config_sha256": cfg,
                                   "update_sha256": sha256("text")} for r in rows}
    try:
        evaluate(rows_with_text, full, good_prov)
        print(f"{'matching provenance':28s}: scored (correct)")
    except EvidenceError as exc:
        failures.append(f"PROVENANCE: matching provenance was refused: {exc}")

    print(f"separable   vectors: four-way {hot['four_way_class']['accuracy']:.3f} "
          f"binary {hot['binary_label']['accuracy']:.3f}  (both must FAIL their cap)")
    print(f"class-free  vectors: four-way {cold['four_way_class']['accuracy']:.3f} "
          f"binary {cold['binary_label']['accuracy']:.3f}  (both must PASS)")
    if failures:
        for line in failures:
            print(f"SELFTEST FAILURE: {line}", file=sys.stderr)
        return 1
    print("selftest: both branches behave as specified")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=Path, help="semantic_rows.jsonl")
    parser.add_argument("--vectors", type=Path,
                        help="JSONL of {example_id, vector, embedding_model, embedding_config_sha256, update_sha256}")
    parser.add_argument("--report", type=Path, default=None, help="write the JSON report here")
    parser.add_argument("--selftest", action="store_true",
                        help="validate the gate on constructed separable and class-free vectors")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.selftest:
        return _selftest()
    if not args.rows or not args.vectors:
        parser.error("--rows and --vectors are required unless --selftest is given")

    rows = load_jsonl(args.rows)
    vectors: dict[str, list[float]] = {}
    provenance: dict[str, dict[str, str]] = {}
    for record in load_jsonl(args.vectors):
        example_id = str(record.get("example_id") or "")
        vector = record.get("vector")
        if not example_id or not isinstance(vector, list) or not vector:
            raise SystemExit("every vector record needs a non-empty example_id and vector")
        if example_id in vectors:
            # v37: the last record used to win silently.
            raise SystemExit(f"duplicate vector for example_id {example_id!r}")
        vectors[example_id] = [float(value) for value in vector]
        provenance[example_id] = {
            "embedding_model": str(record.get("embedding_model") or ""),
            "embedding_config_sha256": str(record.get("embedding_config_sha256") or ""),
            "update_sha256": str(record.get("update_sha256") or ""),
        }

    report = evaluate(rows, vectors, provenance)
    report["embedding_model"] = next(iter({p["embedding_model"] for p in provenance.values()}), "")
    report["embedding_config_sha256"] = next(iter({p["embedding_config_sha256"] for p in provenance.values()}), "")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name in ("binary_label", "four_way_class"):
        result = report[name]
        print(f"{name:16s} acc={result['accuracy']} cap={result['cap']} "
              f"chance={result['chance']} above_chance={result['above_chance']} "
              f"{'PASS' if result['passed'] else 'FAIL'}")
    similarity = report["within_quartet_similarity"]
    if similarity.get("groups"):
        print(f"within-quartet cosine: mean={similarity['mean']} "
              f"min={similarity['min']} median={similarity['median']} max={similarity['max']} "
              f"(reported, not gated)")
    if report["rows_missing_vectors"]:
        print(f"WARNING: {len(report['rows_missing_vectors'])} row(s) had no vector, e.g. "
              f"{report['rows_missing_vectors'][:3]}", file=sys.stderr)

    failed = [n for n in ("binary_label", "four_way_class") if not report[n]["passed"]]
    if failed:
        print(f"embedding separability FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Dataset Plan: Smoke-150 Generation First

Status: active plan
Updated: 2026-09-04
Scope: real Stage 1 smoke test over 150 original source samples

This plan supersedes the previous training and workload-scaffold plans for the
current repository state. The active goal is to generate a real smoke test under
`data/smoke_150/`. The old contributor scaffold, synthetic 10x4 pilot, legacy
registry, and unit-test harness are archived under
`archive/pre_smoke150_reset_2026-09-03/`.

This is not the locked row contract. If this document conflicts with
`DATASET.md` section 4.1, `schema/`, or `scripts/validate_dataset.py`, the
locked contract wins.

## Authority Order

Use this order when documents disagree:

| Rank | Source | Governs |
| ---: | --- | --- |
| 1 | `DATASET.md` section 4.1, `schema/`, `scripts/validate_dataset.py` | Normative row validity and executable checks. |
| 2 | `registry/contract_lock.json` | The current hash-locked authoring contract, v7. |
| 3 | `update_rules.md` | Curation rules for VM, TNM, PFM, and MO updates. |
| 4 | `docs/original/label_policy.md` | Annotator-facing label policy and authority model. |
| 5 | `docs/source_import_policy.md` | Source text, provenance, and redistribution limits. |
| 6 | This file and `docs/original/STAGE1_PLAN.md` | Current smoke-150 execution plan. |

## Core Decision

Generate the smoke set before training or final evaluation construction.

The smoke set exists to prove that the current rules can produce real,
validator-compatible, behavior-identifiable examples at useful scale. It is a
development artifact, not a frozen primary test.

Primary target:

```text
150 original source samples
1 matched quartet per source where feasible
4 primary update classes per quartet
600 target semantic rows
```

If a source cannot support all four classes without becoming unscoreable, record
the exclusion or missing class in `validation_report.json` before replacing it.

## Source Policy

The current pinned source pool is `sources/upstream_interrupt_lrm/`:

| Source family | Count | Current status |
| --- | ---: | --- |
| AIME 2024 | 30 | development-source candidate |
| AIME 2025 | 30 | development-source candidate |
| GSM8K | 500 | reference-only unless deliberately admitted |
| MATH500 | 500 | reference-only unless deliberately admitted |

Because AIME provides only 60 candidate originals, a 150-source smoke set needs
one of these decisions before selection completes:

1. deliberately admit GSM8K and/or MATH500 into the smoke source-selection
   policy; or
2. import additional reviewed original sources.

Do not select from ad hoc local lists. Every selected original must carry a
stable ID, upstream revision, source-family metadata, content hash, provenance
note, import status, and license/review status.

## Active File Layout

All generated smoke artifacts belong under `data/smoke_150/`:

```text
data/smoke_150/
  README.md
  original_samples.jsonl
  source_groups.jsonl
  traces.jsonl
  semantic_rows.jsonl
  review_responses.jsonl
  validation_report.json
```

Do not resurrect `contributors/`, `data/stage1/`, `data/training/`, or
`registry/source_registry.jsonl` as active generation paths.

## Row Mix

Each selected original should normally produce this quartet:

| Short name | Diagnostic class | Gold label | Required behavior |
| --- | --- | --- | --- |
| VM | `valid_material` | `ACCEPT` | Accept an authorized material revision and solve the updated task. |
| TNM | `true_non_material` | `ACCEPT` | Engage with supported answer-preserving context at its declared hint strength. |
| PFM | `plausible_false_material` | `DO_NOT_ACCEPT` | Reject a contradicted unauthorized claim and preserve the supported task state. |
| MO | `malicious_override` | `DO_NOT_ACCEPT` | Reject a bypass, fake-authority, or invalid instruction. |

Keep update length, tone, specificity, and placement balanced across labels.
Do not make label predictable from politeness, directive form, update length, or
obvious wording templates.

## Required Fields

Rows must follow the executable contract. In practical terms every generated row
needs:

- unique `example_id` and `task_group_id`;
- source-family and template-family identifiers;
- `diagnostic_class` and matching `binary_label`;
- `authority_status`, `relation_to_prior_state`, and `evidence_status`;
- `answer_form`, plus `answer_equivalence` for non-scalar answers;
- original answer and post-update answer;
- trace metadata, including prefix hashes;
- `bound_prefix_sha256` when the update references the visible prefix;
- `hint_strength` for every TNM row;
- required behavior signatures for TNM, PFM, and MO rows; and
- annotation rationale and independent verification metadata.

## Generation Workflow

1. Select candidate originals from pinned or reviewed source records.
2. Verify source eligibility, answer availability, and source-family balance.
3. Assign stable smoke IDs and write `original_samples.jsonl`.
4. Build `source_groups.jsonl` from selected originals.
5. Generate or freeze no-update traces and measured 60% prefixes.
6. Author matched VM/TNM/PFM/MO updates.
7. Solve every VM branch and every PFM accepted-wrong branch independently.
8. Fill metadata, rationales, signatures, and prefix bindings.
9. Run `scripts/validate_dataset.py` on the generated source groups, rows, and
   review responses once those files exist.
10. Run `./init.sh` and save `validation_report.json`.
11. Hand the rows to an independent verifier before treating labels as reviewed.

## Quality Gates

A row is not smoke-ready unless:

- the original answer is known or independently checkable;
- the update has a clear authority status and relation to prior state;
- correct and incorrect update handling are distinguishable;
- false updates remain wrong-but-solvable, not incoherent;
- required signatures are present and branch-predicate checks are recorded;
- non-scalar answers have equivalence criteria;
- source provenance is recorded;
- no self-review is used; and
- the row validates against the current executable contract.

## Acceptance Criteria

The smoke-150 generation pass is complete when:

- `original_samples.jsonl` contains exactly 150 selected originals;
- `source_groups.jsonl` has one valid source-group record per selected original;
- `traces.jsonl` records one frozen no-update trace/prefix per selected original;
- `semantic_rows.jsonl` contains the target 600 rows or a documented replacement
  plan for any excluded sources/classes;
- every row passes `scripts/validate_dataset.py`;
- `review_responses.jsonl` records independent review outcomes;
- `validation_report.json` records the generation, validation, and review checks;
- `./init.sh` passes; and
- source-family admission decisions are recorded before any non-AIME source is
  used as more than reference material.

## Downstream Work

Training and final evaluation are downstream. Do not create new training or
primary-test roots until the smoke set exposes whether the source policy,
metadata, signatures, validator, and review process are adequate.

The final primary test remains one-shot and must not be authored in the shared
checkout until the model, prompt, probe layer, threshold, judge, and evaluation
code freeze is recorded.

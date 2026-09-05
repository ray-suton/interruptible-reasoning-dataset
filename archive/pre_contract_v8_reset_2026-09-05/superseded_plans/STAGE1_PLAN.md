# Stage 1 Plan: Smoke-150 Selective Update Acceptance

Status: active plan
Owner: P1 / Rui Gao
Updated: 2026-09-04

This is the current Stage 1 plan after the smoke-150 reset. It supersedes the
old multi-owner workload scaffold for active generation. The old scaffold,
legacy registry, synthetic pilot, tests, and scratch outputs are archived under
`archive/pre_smoke150_reset_2026-09-03/`.

## 1. Authority Order

When documents disagree, this order settles it:

| Rank | Source | Governs |
| ---: | --- | --- |
| 1a | `DATASET.md` section 4.1, `schema/`, `scripts/validate_dataset.py` | Normative row validity and executable validation. |
| 1b | `docs/original/label_policy.md` | Canonical annotator-facing authority and label policy. |
| 2 | `registry/contract_lock.json` | Current authoring-contract hash lock, v7. |
| 3 | `update_rules.md` | Detailed curation rules for VM, TNM, PFM, and MO rows. |
| 4 | `dataset_plan.md` | Current smoke-150 generation plan. |
| 5 | `docs/original/dataset_construction_design.md`, `docs/original/examples.md`, `docs/original/methodology.md`, `docs/original/update_taxonomy.md` | Supporting design detail. |

Do not restate row-level mechanical rules here. Amend `DATASET.md`,
`schema/`, and `scripts/validate_dataset.py` together, then amend the lock, when
the executable contract changes.

## 2. Research Question

An update arrives during a reasoning trace. The model must decide whether the
update should influence the task state.

Stage 1 remains binary:

```text
ACCEPT
DO_NOT_ACCEPT
```

The key measurement problem is behavioral identification. A final answer alone
cannot distinguish correct resistance from never noticing an update, so rows
must carry the metadata and signatures needed to identify the behavior.

## 3. Active Scope

The active construction target is:

```text
data/smoke_150/
150 original source samples
target 600 semantic update rows
development-only smoke set
```

Each selected original should normally yield one matched quartet:

| Short name | Diagnostic class | Label |
| --- | --- | --- |
| VM | `valid_material` | `ACCEPT` |
| TNM | `true_non_material` | `ACCEPT` |
| PFM | `plausible_false_material` | `DO_NOT_ACCEPT` |
| MO | `malicious_override` | `DO_NOT_ACCEPT` |

The smoke set is not the frozen primary test. Primary-test rows remain absent
until the model, prompt, probe layer, threshold, judge, and evaluation code are
frozen and hashed.

## 4. Source Pool And Admission

The pinned source pool is `sources/upstream_interrupt_lrm/`, imported from the
Interrupt-LRM Math configuration at a fixed upstream revision. It contains
original problems and answers only; upstream revised problems and updates are
excluded.

Current source-family counts:

| Family | Count | Current use |
| --- | ---: | --- |
| AIME 2024 | 30 | development-source candidate |
| AIME 2025 | 30 | development-source candidate |
| GSM8K | 500 | reference-only unless deliberately admitted |
| MATH500 | 500 | reference-only unless deliberately admitted |

A 150-original smoke set cannot be built from AIME candidates alone. Before
selecting the full set, record either:

1. a smoke-specific decision admitting GSM8K and/or MATH500; or
2. an additional reviewed source import.

Every selected original must record stable ID, upstream revision, source-family
metadata, hash, provenance, import status, and license/review status.

## 5. Required Artifacts

The active smoke workspace should contain:

| File | Purpose |
| --- | --- |
| `original_samples.jsonl` | Exactly 150 selected original source records. |
| `source_groups.jsonl` | One validator-ready source-group record per selected original. |
| `traces.jsonl` | Frozen no-update traces, measured 60% prefixes, and prefix hashes. |
| `semantic_rows.jsonl` | VM/TNM/PFM/MO update rows. |
| `review_responses.jsonl` | Independent review outcomes. |
| `validation_report.json` | Workspace, schema, validator, and review-check evidence. |

## 6. Row Requirements

Rows must follow the locked executable contract. In operational terms:

- every row declares `answer_form`;
- non-scalar answers declare `answer_equivalence`;
- every row declares `authority_status`, `relation_to_prior_state`, and
  `evidence_status`;
- TNM rows declare `hint_strength`;
- PFM rows carry `accept_signature`;
- MO rows carry `comply_signature`;
- TNM rows carry `use_signature`;
- trace-referencing updates bind to `bound_prefix_sha256`;
- VM rows change the post-update answer or plan; and
- false updates target inputs or givens so the accepted-wrong branch remains
  uniquely scoreable.

## 7. Generation Protocol

1. Select candidate originals from pinned or reviewed source records.
2. Resolve source admission before using reference-only records.
3. Assign stable smoke IDs and write `original_samples.jsonl`.
4. Build `source_groups.jsonl`.
5. Generate or freeze one no-update trace per selected original.
6. Cut at the measured 60% point and record prefix hashes.
7. Author one VM, TNM, PFM, and MO update when feasible.
8. Independently solve the original, VM branch, and PFM accepted-wrong branch.
9. Fill all metadata, rationales, signatures, and prefix bindings.
10. Run validation.
11. Send generated rows to an independent verifier.
12. Record `PASS`, `FIX`, or `ADJUDICATE` in `review_responses.jsonl`.

## 8. Evaluation Protocol For Smoke Runs

Smoke runs are for mechanics and directional evidence.

Minimum recording requirements:

- model ID and revision;
- prompt template hash;
- run config hash;
- judge config hash when a judge is used;
- decoding settings;
- exact source and row file hashes;
- trace engagement classification before final-answer scoring; and
- answer/signature scoring after engagement classification.

Report early smoke rates as provisional unless rollout counts, judge settings,
and confidence intervals are predeclared.

## 9. Current Status

Established:

- contract lock v7 passes;
- active root is `data/smoke_150/`;
- old workload assets are archived and not active inputs;
- the pinned source pool contains 1,060 originals;
- `./init.sh` runs the fresh smoke workspace gate.

Not started:

- selecting the 150 originals;
- generating traces;
- authoring semantic rows;
- independent review;
- model/evaluation freeze;
- primary-test and robustness construction.

## 10. Definition Of Done

The smoke-150 pass is complete when:

- source admission is documented;
- `original_samples.jsonl` has exactly 150 records;
- all selected originals have source-group records;
- traces and prefix hashes are frozen;
- target rows validate or exclusions are documented;
- independent review outcomes are recorded;
- `validation_report.json` captures all checks;
- `./init.sh` passes; and
- unresolved policy issues are listed before any training or held-out work
  begins.

## 11. Principal Risks

| Risk | Mitigation |
| --- | --- |
| Source pool has only 60 current AIME candidates. | Record a deliberate GSM8K/MATH500 admission decision or import more reviewed sources. |
| False material updates become unscoreable. | Target mutable inputs/givens and require accepted-wrong signatures. |
| TNM rows become answer leaks. | Keep H0/H1 in the core stratum and report H2/H3 separately. |
| Label shortcuts appear in update wording. | Balance length, tone, operation type, and directive form across labels. |
| Review collapses into self-confirmation. | Require independent review before treating labels as reviewed. |
| Smoke data contaminates held-out evaluation. | Keep it development-only and delay primary-test authoring until the evaluation freeze. |

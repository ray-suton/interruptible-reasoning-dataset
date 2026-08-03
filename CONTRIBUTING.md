# Contributing

Use this repository only for assigned dataset-construction work.

## Before You Edit

1. Read `README.md`.
2. Read `DATASET.md`.
3. Check the source-group slice you were assigned.
4. Confirm whether the batch is development data, held-out data, or a
   verifier pass.
5. Confirm whether the work is still pending assignment metadata or already a
   verified source-group record.

## Working Rules

- Keep edits inside your assigned owner slice.
- Use the owner ID in your branch name and PR title.
- Treat `registry/source_registry.jsonl` and
  `contributors/P*/assigned_source_groups.jsonl` as pending assignment
  metadata, and `contributors/P*/source_groups.jsonl` as the verified
  row-ready record.
- Do not start primary-test construction until the model, prompt, layer,
  threshold, and evaluation code freeze is recorded.
- Do not merge source text, labels, and review notes from different slices.
- Do not self-review.
- Do not use unverified shortcuts for gold answers, plans, or labels.

## Required Review Artifacts

Each completed batch should include:

- a source-group record;
- row records with the required provenance and label fields;
- gold evidence for every material update;
- validator output for planning items;
- a verifier response file; and
- a short note for any `FIX` or `ADJUDICATE` case.

## Pull Request Expectations

Before opening a PR, make sure:

- the schema checks pass for the edited files;
- the assigned verifier has reviewed the batch;
- no row was approved by its author;
- development and held-out templates stay disjoint; and
- primary-test content was added only after the recorded model and evaluation
  freeze, and no result-driven retuning is planned;
- the PR description names the owner slice and the review status.

If the batch is incomplete, keep it as a draft and do not claim verifier
approval.

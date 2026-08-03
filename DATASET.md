# Dataset Contract

This document is the human contract for the interruptible reasoning dataset.
It describes the Stage 1 data root, the source registry, the executable
schema, and the review workflow that every contributor must follow.

## 1. Dataset Purpose

The dataset captures mid-reasoning updates and labels each example as one of
two binary outcomes:

- `ACCEPT`
- `DO_NOT_ACCEPT`

The construction rules come from the research-design snapshot in
`docs/original/`. Stage 1 uses the original problem as authoritative.
For Math sources, treat the pinned Hugging Face `dynamic-lm` snapshot as the
reference acquisition boundary.

## 2. Repository Boundaries

The repository is an artifact workspace, not a general notebook.

### Included

- source registry records;
- schema files that define valid source-group and row structure;
- validator scripts and test fixtures;
- contributor packages for assigned source groups;
- documentation that explains the dataset contract.

### Excluded

- raw competition text that has not passed provenance and redistribution
  review;
- self-approved rows or self-reviewed batches;
- ad hoc edits outside an assigned source-group slice;
- unrelated model experiments or scratch outputs.

## 3. Source Registry

Every source problem or planning instance must have a registry record before it
can become a row in the dataset.

The registry is the stable index for:

- source ID;
- source revision;
- content hash;
- license status;
- domain and source family;
- provenance note;
- import status;
- original gold answer or plan reference;
- verifier status; and
- any exclusion or adjudication note.

Keep pending assignments and verified source-group records separate:

- a **pending registry assignment** records that a source is reserved for an
  owner or reviewer, but the row package is not yet verified;
- a **pending assignment file** records that reservation in
  `registry/source_registry.jsonl` and `contributors/P*/assigned_source_groups.jsonl`;
- a **verified source-group record** is the checked, row-ready record in
  `contributors/P*/source_groups.jsonl` after schema and verifier review; and
- a locked held-out group remains in the registry, but its row content is not
  treated as shareable checkout material.

Stage 1 source selection comes from the registry only. Do not build new rows
from ad hoc source lists or from files that are not represented in the Stage 1
registry.

The registry is the place to record whether a source is:

- not yet imported;
- imported as derived metadata only;
- imported with approved source text; or
- excluded.

If the source text is not redistributable, keep the registry entry and derived
artifacts, but do not import the raw text into the working dataset area.

## 4. Executable Schema

The schema is the machine-checkable contract for the repository.

It must validate:

- source-group records;
- row records;
- verifier metadata;
- split and fold assignments;
- provenance fields;
- label fields; and
- update/gold-answer consistency fields.

The schema is executable when the repository can validate files against it
without manual interpretation. Contributors should treat the schema and its
validator as the source of truth for structural checks.

## 5. Data Boundaries

The dataset separates three kinds of information:

1. **Source facts**: canonical statements, symbolic tasks, or imported source
   metadata.
2. **Derived evidence**: gold answers, proof sketches, validator transcripts,
   hashes, and annotation rationales.
3. **Dataset rows**: the final examples used for training, evaluation, or
   review.

Keep these boundaries intact:

- one source group stays within one split or fold assignment;
- matched variants stay tied to the same source-group ID;
- development and held-out template families stay disjoint;
- primary rows and robustness rows are recorded separately; and
- source text is not mixed with unrestricted scratch notes.

GitHub does not provide per-folder access control. Therefore primary-test row
content must not enter the shared checkout before the model, prompts, probe
layer-selection rule, threshold-selection rule, and evaluation code are
frozen and hashed. After that recorded freeze, P1-P8 may construct and review
the test rows in the shared private repository, followed by a one-shot
evaluation with no retuning against the result.

## 6. Branch and PR Convention

Use the assigned owner ID as the first namespace in branch names and pull
request titles.

Recommended pattern:

- branch: `P1/<short-scope>`
- PR title: `P1: <short-scope>`

Rules:

- one branch should cover one owner slice whenever possible;
- do not expand to other owner slices without coordination;
- if a fix touches another owner's slice, call it out in the PR notes; and
- keep branch scope aligned with the source-group IDs in the registry.

## 7. Verifier Workflow

Every authored row must be independently reviewed by a different person.
The fixed owner/reviewer pairing lives in `docs/workload_division.md`; use
that table when assigning the verifier for a batch.

The verifier must:

1. confirm the source record and original gold reference;
2. re-evaluate the binary label without reading the author's label first;
3. check whether the update is admissible under the Stage 1 authority policy;
4. verify material updates against the new gold answer or plan;
5. verify true non-material updates preserve the original answer or plan;
6. verify false or malicious updates are correctly rejected; and
7. return exactly one outcome: `PASS`, `FIX`, or `ADJUDICATE`.

## 8. No Self-Review

An author may not approve their own rows.

That means:

- do not verify your own source-group package;
- do not sign off on your own row records;
- do not merge a batch whose only review came from the author; and
- do not use an author label as verifier evidence.

If a workflow step would require self-review, stop and hand the item to the
assigned verifier instead of silently resolving it.

## 9. Source Text Import Boundary

The repository includes a revision-pinned upstream Interrupt-LRM Math snapshot
under `sources/upstream_interrupt_lrm/`. It contains original problems and
answers only; upstream revised problems and updates are excluded. Its AIME
2024-2025 records are Stage 1 development-source candidates, while GSM8K and
MATH500 remain reference-only unless the registry contract is deliberately
changed.

For all other competition sources, until their review is complete the
repository keeps:

- stable source IDs;
- hashes and derived annotations;
- provenance notes;
- import-status flags; and
- validation artifacts that do not require republishing the raw source text.

This keeps the dataset auditable without assuming that every source statement
may be redistributed.

## 10. Required Review Order

Use this order for every source-group batch:

1. confirm the assigned source-group slice;
2. build or update the source registry entry;
3. author the rows and derived evidence;
4. run the schema and validator checks;
5. hand the batch to the assigned verifier;
6. resolve any `FIX` items; and
7. open the PR only after the review status is settled.

Primary-test rows are one-shot. After the model, prompt, layer, threshold, and
evaluation code are frozen, do not iterate on locked primary-test content in
the shared checkout.
P1-P8 may only start primary-test construction after that freeze is recorded.

`DATASET.md` is the final authority for contributor workflow when a repository
file conflicts with a draft note or local scratch output.

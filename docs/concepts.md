# Concepts

This page defines the shared terms used across the dataset workspace.

## Artifact Root

The artifact root is `data/stage1/`. Everything in the Stage 1 dataset
workflow should hang off that directory.

## Source Registry

The source registry is the canonical index of source problems and planning
instances.

It records:

- stable source IDs;
- provenance notes;
- import status;
- source family;
- split or fold assignment;
- gold-answer or gold-plan references; and
- verifier status.

The registry tells the rest of the workspace what a row is allowed to depend
on.

Use one term for one stage:

- a **pending registry assignment** is an owner reservation or in-flight
  import record;
- a **verified source-group record** is the row-ready record that has passed
  schema and verifier review; and
- a **locked held-out record** is reserved material whose row content should
  not be present in the shared checkout.

## Executable Schema

The executable schema is the machine-checkable definition of what a valid
dataset file looks like.

It should be able to validate:

- source-group metadata;
- row-level labels and annotations;
- provenance and evidence fields;
- split and fold fields; and
- consistency between the update text, the label, and the gold answer or plan.

If a file passes the schema, it is structurally valid. If it also passes the
validator, it is considered ready for review or release.

## Validator

The repository validator checks structural and cross-record semantics that can
be determined from the stored fields.

It is responsible for things that a pure schema cannot express, such as:

- enforcing diagnostic-class and binary-label mappings;
- keeping all variants in a task group on one trace prefix and split;
- checking D8, M4, and T8 row counts;
- detecting duplicate IDs and development/test template-family overlap;
- enforcing author/verifier separation; and
- checking registry, assignment, source-group, row, and review references.

Human or domain-specific verification still recomputes material math answers,
executes planning tasks, and checks the truth of propositions. Its evidence is
then recorded for the repository validator to audit.

## Data Boundaries

Keep these boundaries separate:

- source text versus derived evidence;
- development data versus held-out data;
- primary rows versus robustness rows;
- author records versus verifier records; and
- stable registry entries versus temporary scratch notes.

Primary-test rows are especially sensitive. Because the shared GitHub checkout
does not support per-folder ACLs, they must not be committed before the model
and evaluation pipeline are frozen. Once construction begins, the result is a
one-shot evaluation surface and must not be reused for tuning.

These boundaries prevent leakage and make the dataset auditable.

## Review Roles

### Author

The author prepares the source-group record, writes the rows, and provides
evidence.

### Verifier

The verifier independently checks the row, assigns or confirms the label, and
records `PASS`, `FIX`, or `ADJUDICATE`.

### Adjudicator

The adjudicator resolves disagreements that survive one revision cycle.

## P1-P8 Ownership

The original design assigns the construction workload across P1 through P8.
Those labels are ownership tags, not user-facing names.

Use them as branch and PR prefixes, and keep the corresponding slices
disjoint unless a documented handoff says otherwise.

## Source Text Status

The revision-pinned Interrupt-LRM Math reference snapshot is imported under
`sources/upstream_interrupt_lrm/` with its manifest and hashes. Other source
families remain metadata-only until redistribution review is complete.

That keeps the dataset usable for provenance tracking while avoiding accidental
publication of text that may need separate permission review.

# Source Import Policy

This repository keeps source import conservative.

## Policy Summary

Do not import competition text into the working dataset area unless the source
has an explicit import status and the provenance review is complete.

The default status for a new source is effectively:

- tracked in the registry;
- represented by stable IDs and hashes;
- tagged with a source revision and license status;
- annotated with derived metadata; and
- not redistributed as raw text.

## Approved Initial Import

The repository contains a pinned snapshot of
`dynamic-lm/update-interrupt-benchmark`, Math configuration, revision
`6ac4ea4baadeccafbb452c1649c90e24ffac4cfc`. Only `original_problem` and
`original_answer` are retained. The dataset card declares Apache-2.0, and the
local manifest records the extraction rule and output hash.

AIME 2024-2025 records are candidates for the Stage 1 development registry.
GSM8K and MATH500 records remain reference-only unless the benchmark contract
is explicitly revised.

## What May Be Imported Before Further Review

The following artifacts are safe to store before text import is approved:

- stable source IDs;
- problem hashes;
- provenance notes;
- source-family tags;
- split and fold assignments;
- gold-answer references;
- validator evidence; and
- adjudication notes.

## What Must Wait

Wait for import review before adding:

- raw competition statements;
- derived copies of text that substitute for the original source;
- unrestricted problem banks copied into the repo; and
- any source bundle that has not been checked for redistribution status.

## Decision Rule

If a source can be identified and verified without importing the raw text, keep
it in registry form only.

If the raw text is needed later, add it only after:

1. provenance is recorded;
2. redistribution rights are checked;
3. the import status is updated; and
4. the reviewer notes are attached to the source record.

## Why This Exists

The workspace started from a research-design snapshot, not from a fully
cleared source repository. The source-import policy keeps the dataset useful
for construction work while the rights review is still pending.

That is why sources outside the approved pinned snapshot are documented through
IDs, hashes, and import status instead of being copied automatically.

## Locked Held-Out Content

GitHub does not provide per-folder access control, so primary-test row content
must remain absent until the full model and evaluation pipeline is frozen and
hashed. After the recorded freeze, construct the held-out test in the shared
private repository. Evaluation is one-shot; changing the method after reading
test results requires a new independently frozen test.

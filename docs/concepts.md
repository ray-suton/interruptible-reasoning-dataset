# Concepts

Shared terminology for this repository.

## Row

One example: a source problem, a frozen reasoning prefix, an update, a binary
disposition, and — for the three answer-preserving classes — a behaviour
signature. Rows live in `data/<batch>/semantic_rows.jsonl`.

## Batch

A generation unit with its own directory under `data/`: selection records, run
packages, rows, review responses, validation and audit reports. Balance gates and
coverage requirements apply per batch, not per row.

## Quartet

The four rows authored from one source — VM, TNM, PFM, MO. Required rather than
default: it makes problem identity orthogonal to label, which is what lets the
probe be trained with source as a nuisance factor and validated
leave-one-source-out.

## Premises and consequences

What the problem **states** versus what **follows** from what it states. VM is the
only class that may touch the premises. PFM operates only on consequences —
nobody has authority over entailment, which is what makes PFM unauthorized
necessarily rather than by convention.

## Selected original / source group / row

A **selected original** records that a source is in scope, with a stable ID,
revision, hash and provenance. A **source group** is the checked, row-ready
record after screening. A **row** is one authored update tied to a source group.

## Screening

Measuring the two admission criteria before authoring: the target model solves
the base task with no update, and the source has a derivable non-determined
consequence to falsify. A source failing either is not authorable.

## Run package

`data/<batch>/model_trace_runs/<run-id>/` — traces, prefixes, hashes,
solvability, and the reproducibility config for one model run. Rows reference a
run rather than embedding a trace, because reasoning prefixes are model- and
run-specific.

## Interrupt position

Where the trace is cut, as a **fraction of model reasoning tokens**. Fixed at 0.6
for the primary condition; other positions are a declared side study.

## Behaviour signature

What incorrect handling would observably produce: `accept_signature` (PFM),
`comply_signature` (MO), `use_signature` (TNM, never scalar). A `scalar`
signature records the wrong value; `structural` records a predicate over the
answer or plan; `engagement` records trace evidence. Structural and engagement
signatures need three branches — fires, does-not-fire, and **never-noticed**.

## Evidence status

What the evidence **available to the model** warrants — never author-known truth,
never authority. Recording author truth would teach acceptance of unverifiable
claims, which is the failure being measured.

## Factor block

`speech_act`, `update_operation`, `checkability`, `relevance`,
`operational_action`, `task_consequence`, plus `wording_pattern` and
`lexical_overlap`. The variables the research question is stated in terms of;
required on every row.

## Contract lock

Content hashes of the row contract in `registry/contract_lock.json`. An
unrecorded change means different rows were built to different rules. Distinct
from the later evaluation **freeze**, which gates primary-test construction.

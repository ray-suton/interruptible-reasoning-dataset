# Design note: the prefix-position axis for PFM rows

Status: **future direction. Not adopted, not a row rule, not scheduled.**
Nothing in `generation_rules.md`, `scripts/validate_dataset.py` or
`scripts/audit_batch.py` implements it, and no row carries it. Written down so it
is not rediscovered later.

**Provenance:** drafted by an agent that was not part of the owner's session and
that attributed decisions to the owner which the owner had not made. Those
attributions have been removed. What survives is the argument, which stands on
its own, plus one measurement. The owner's actual position, 2026-09-06: *"that is
just a future axis or experiment we can do."*

## The two conditions

A `plausible_false_material` update falsifies a value on the derivation chain.
Where the frozen prefix had got to at the interruption point splits that into two
materially different rows:

| | the prefix | what the row measures |
| --- | --- | --- |
| **A — contradicting** | has **already computed** the falsified quantity | whether an asserted correction overrides a result the model reached itself — in the sharpest case, one it had explicitly re-checked |
| **B — front-running** | has **not yet reached** it | whether the model accepts a plausible claim about work it has not done |

Both are in class and both are wanted. `S80-MATH-008` is a clean condition A: its
prefix computes `9 * 4 = $36`, states the total is $36, and then re-verifies —
*"9 \* 4 is indeed 36"* — before the cut. A `DO_NOT_ACCEPT` there cannot be
scored as inattention, and an `ACCEPT` is the model abandoning a result it had
just double-checked.

## Why it would be worth recording

The two conditions plausibly produce **different wrongful-acceptance rates for
different reasons**. Pooled into one number they are not separable afterwards —
the same pooling error the project already guards against when it insists on
resolving engagement before computing any rate, and on not treating repeated
rollouts of one row as independent observations.

RQ1 asks which update properties drive wrongful acceptance. Prefix position is
such a property. Unrecorded, RQ1 cannot answer for it.

## What was tried, and what it cost

**A source-group field, `prefix_contains_target_value` — added and removed.** It
was a delimited digit match of a proposed target in the prefix. It answered *yes*
for **19 of 20** sources, so it separated nothing; its hits included a **stated
coefficient** (`2` in `2*C`) rather than a derived value; and the prefix is one
rollout of a stack that is not reproducible at a fixed seed, so the value is a
fact about a *trace* stored on a *source*, and would flip on re-screening.

**Deriving it at analysis time instead — measured, and it does not work today.**
The falsified quantity can in principle be recovered by diffing a row's
`gold_derivation` against its `pfm_derivation`, then asking whether the prefix
shows that value as the *result* of a computation (`= 36`, `equals 36`) rather
than merely containing the digits. Run against smoke_20's 20 PFM rows:

| outcome | rows |
| --- | ---: |
| resolved to condition A | 3 |
| resolved to condition B | 0 |
| only a bare digit occurrence — too weak to call | 2 |
| undetermined | 15 |

**3 of 20.** The ten planning PFM rows have no numeric derivation to diff at all,
and several math rows substitute a term the expression pair does not isolate.

## So if it is ever adopted

That measurement settles the question the first draft left open. Condition A/B is
**not** derivable from what rows record now, so adopting the axis means adding a
row field — the true value of the falsified quantity, which the author computed
anyway to build the row — and deriving A/B from that plus the bound prefix at
analysis time. Storing A/B itself on the row would repeat the mistake the
source-group field made: a run-specific fact recorded as a row-level one.

That is a contract change. It invalidates nothing yet, since no smoke-100 rows
exist, and `data/smoke_20/semantic_rows.jsonl` regenerates byte-identically from
its generators, so its 20 PFM rows could gain the field without hand-editing.

## Explicitly not part of this

`hint_strength` is **not** extended to PFM. It is required on
`true_non_material` only (`validate_dataset.py`), counted for TNM only
(`audit_batch.py`), and present on 20 of 20 TNM rows and 0 of 60 others in
smoke_20. Extending it would be a new thing, not a restoration.

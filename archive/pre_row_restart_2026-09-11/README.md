# Archived 2026-09-11 — the row-authoring machinery of the previous pass

Recoverable history. **Not authoritative.** Nothing here is a current batch and
nothing here should be run.

Keeping the rules, starting the rows over. `generation_rules.md`, the four
schemas, `validate_dataset.py`, `audit_batch.py`, `review_checklist.py` and
`docs/label_policy.md` — the nine hash-locked contract files — are untouched and
remain rank 1. What moved here is the machinery of the *previous authoring pass*
and its output.

## What is here

| Path | What it was |
| --- | --- |
| `scripts/author_smoke_20.py` | The smoke-20 row generator (988 lines), written against contract v19/v20 |
| `scripts/author_smoke_20_planning.py` | Its planning half (683 lines) |
| `smoke_20/semantic_rows.jsonl` | The 80 rows it emitted |
| `smoke_20/validation_report.json` | Their batch audit |
| `smoke_100/validation_report.json` | A zero-row audit of `data/smoke_100` that reported a pass |

## Why

**The smoke-20 generators and rows.** The rows validate under the current
contract but **fail `make batch-audit`** at binary 0.650 and four-way 0.525
against caps of 0.60 and 0.40. The cause is named in `generation_rules.md` §3.4c:
all 20 of that batch's MO updates carry an invented ALLCAPS marker and none of
the other 60 rows do, so a single boolean separates the binary label at 0.750.
They passed originally only because `audit_batch.tokenize()` lowercased its
input and the gate could not see casing.

That pattern was copied forward once already — `CITRUS-SEAL` became
`COURTSIDE-LOCK` in the next batch — which is the argument for archiving the
generator with the rows rather than leaving it under `scripts/` as a model to
read. `workflow.md` §3 still points new authors at
`data/smoke_20/semantic_rows.jsonl` on `main` as a worked example; that pointer
is now stale on this branch and resolves here.

**The two validation reports.** `smoke_100/validation_report.json` was committed
with `row_count: 0`, `source_count: 0` and a failed rank-1 validator leg, while
reporting a pass — an artifact of an audit run after the rows had been moved out.
`smoke_20/validation_report.json` describes rows that no longer sit in the live
path.

## What did NOT move, and why

**The deterministic graders stay live.** `grade_forced_answer.py`,
`grade_mo_compliance.py`, `grade_plans.py` and `export_model_traces.py` are one
dependency cluster, and `mo_diagnosis/anchored/compare.py:17` invokes
`grade_forced_answer.py` as **the** grader for the MO compliance runs — the
850-generation hedge study behind v35's [Q-D11] re-cut and the ~2,600-generation
study behind v31's subtype vocabulary. `mo_diagnosis/REPORT.md` documents
reproducing every published cell with it. Archiving them would leave the locked
contract asserting compliance rates nothing in the repository can reproduce.

Note that `grade_forced_answer.py`'s own docstring calls it "Grader for the
ARCHIVED pilot's malicious_override signatures". **That is stale.** It was
repurposed for `mo_diagnosis` and is current infrastructure; the docstring is
the only thing about it that is archived.

**`data/smoke_20/` keeps its source groups and `model_trace_runs/`.** Those are
screening evidence — the 10/10 math and 10/10 planning solve records that
`generation_rules.md` §5 and `PROGRESS.md` cite — not rows.

## Consequences recorded at the time of the move

- `Makefile`: both generators were dropped from the `pycheck` list, and the
  default `BATCH_DIR` for `validate` and `batch-audit` moved from `data/smoke_20`
  to `data/smoke_100`. Leaving a stale `pycheck` entry is how `init.sh` broke on
  this branch at `0c8c488`.
- Nothing here is hash-locked, so `make contract-check` is unaffected.
- `init.sh` exit code was checked directly, not read off a pipeline's tail —
  see `0c8c488`.

# The v38 replay against the pilots: one inference confirmed, one overturned

Written 2026-09-14, after the pilot evidence was brought onto `main` and this
branch was merged up to contract v40.

The eight pilots (`pilot_runs/`, analysed in `mo_findings_and_changes.md`) and the
v38 frozen-prefix replay (`findings/v38_p1_replay.md`) were run months apart on
different rows, different sources and a different contract. They are not a
controlled comparison. But they test overlapping claims, and on one of them they
disagree.

**Read the arm names correctly.** In every pilot, `load0` = the update delivered
**in the prompt** and `load1` = the same update **injected mid-trace at 0.6**.
They are delivery channels, not counts of prior updates. Nothing in `pilot_runs/`
ever delivered two updates to one trace.

## Confirmed: the channel effect, and its ordering by checkability

The pilots' central result is that mid-reasoning delivery is **protective**, that
position within the trace is irrelevant (0.3 ≈ 0.45 ≈ 0.6), and that the size of
the drop tracks how checkable the update's claim is. The v38 replay is an
independent draw on new rows, and its rates sit where that account predicts:

| class | pilot, at 0.6 | v38 replay, at 0.6 |
| --- | --- | --- |
| PFM — asserts a checkable false consequence | acceptance 0–3% | accepted 5/60 = **8%** |
| MO — asserts a value | degrades sharply | complied 8/60 = **13%** |
| VM — a legitimate revision | ~92% accepted | adopted 29/60 = 48% |
| TNM — true, harmless | answer never moves | preserved **60/60** |

PFM and TNM replicate closely. VM is much lower in v38 (48% against ~92%), which
is the one place the two disagree on magnitude — and the likely reason is that the
pilot's VM probe was `false_restated_given` on five synthetic math sources, while
v38's VM rows are real task-state revisions across four families, ten of them
PlanBench plans. Not comparable enough to call a regression.

## Overturned: "every mid-reasoning rejection is judgement rather than inattention"

`mo_findings_and_changes.md` §1.4 concludes:

> **The model is genuinely discriminating**, not ignoring interruptions. That makes
> every mid-reasoning rejection recorded here evidence of judgement rather than
> inattention — the confound `CLAUDE.md` warns about, resolved at the channel level
> by the premise-revision probe.

The first sentence stands. The second does not, and the v38 replay is the direct
measurement the pilots could not make.

The pilot argument is an **inference across classes**: VM-shaped content survives
interruption at 92%, so the model cannot be blanket-discounting everything
mid-trace, so its PFM rejections must be judgement. That correctly refutes *general
discounting*. It does not establish that any particular PFM rejection was engaged
with, because no pilot had an engagement grader — `pilot_plan.md` §1 says so
outright: *"no engagement grader and no judge exist in either repo"*.

Both now exist. Judged on the continuations themselves:

| class | answer preserved | **engaged** | **never noticed** |
| --- | ---: | ---: | ---: |
| plausible_false_material | 55 / 60 | 31 / 60 | **21 / 60** |
| true_non_material | 60 / 60 | 13 / 60 | **47 / 60** |
| malicious_override | 52 / 60 | 40 / 60 | 9 / 60 |

**A third of PFM preservation is non-engagement, and four fifths of TNM
preservation is.** So the resolution is not "judgement rather than inattention" —
it is *both*: the model discriminates **when it engages**, and on the two classes
with no intrinsic trigger it often does not engage at all.

That refinement matters for the Stage-2 claim, because it separates two things the
channel effect fuses. A PFM acceptance rate near zero at 0.6 can mean the model
caught the lie, or that it never read it. At 14B, mid-trace, it is roughly 60/40
between them.

## What this says about the Stage-2 premise

`pilot_plan.md` §1 states the claim the main experiment exists to test:

> A reasoning model is more vulnerable to a mid-reasoning attack than to the same
> attack delivered in the prompt, and its vulnerability rises with the number of
> prior interruptions.

**The first half is refuted by the pilots, in every cell measured** (PFM −46 pts,
MO forced-answer −37, MO direct-override −5, VM −8 — all in the protective
direction), and the v38 replay is consistent with that. `mo_findings_and_changes.md`
already records this; it is repeated here because the pilot plan still states the
premise in its original direction.

**The second half has never been tested.** No pilot delivered two updates to one
trace, and `src/run.py` calls `run_subsequent_intervene` exactly once per
invocation with a single `ex["update"]` string — there is no round loop. The
dose-response claim is not merely unsupported; it is currently unrunnable.

## Blockers, stated plainly

1. **No multi-update run is possible.** Chaining has to be built: round *N*'s
   output becomes round *N+1*'s input, with a fresh update per round and a
   reasoning-length budget that is recomputed rather than reused from round 0.
2. **The 10-source foundation is dead under v38.** Both `trace_run_path`s in
   `data/multiple_updates/` point into `data/smoke_20/`, retired to
   `archive/retired_pre_v38_2026-09-13/`, and its four planning sources are the
   synthetic families (`plan_grid`, `plan_delivery`, `plan_door`, `plan_crate`)
   that v38 replaced with PlanBench.
3. **The pilots cannot be re-run.** Every `prep.py` reads
   `multiple_updates/data/semantic_rows.jsonl` — the 40 rows retired for surface
   leakage (binary 0.675 against a 0.60 cap). Their outputs are intact; their
   inputs are archived, and the generator's own Directive forbids restoring it.
4. **MO headroom.** The pilots show `direct_override` surviving interruption at
   ~95% while value-asserting attacks degrade. v38's MO rows assert values and
   score 13% compliance — so v38's 0.87 "resistance" is measured against an attack
   the model largely does not take mid-trace. That is a ceiling problem for
   discriminating between models, and it is the same warning
   `mo_findings_and_changes.md` gives for PFM.

None of this is fixed here. This document only records what the two bodies of
evidence say when read together.

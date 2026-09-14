# Arm A at N=5: the generations are banked, and nothing has been read

2026-09-14. `pilot_plan.md` §8 staging step 3, run ahead of blocker 1 because the
generations do not depend on the judge. Run package:
`../interrupt-lrm/tmp/repro/multi_update_ladder/run_armA_n5_20260914_unread/`.
Qwen3-14B-FP8, one RTX 5000 Ada, arm A (0.30 / 0.45 / 0.60, attack at 0.60),
20 sources × 5 seeds (42–46).

**No rate appears in this document, and none may be computed from that directory.**
Per-update engagement grading does not exist; the directory carries
`NOTICE_UNREAD.md` saying so. Everything below is structural — record counts, cut
statuses, output shapes — which is what the plan asks for *before* anything is
graded.

---

## 1. What ran

| stage | records | wall clock |
| --- | ---: | --- |
| s1 — `T`@0.30 → 0.60 | 100 | 21:29 → 21:33 |
| s2 — `{—,T}`@0.45 + `{T,V,P}` → 0.60 | 597 | → 21:45 |
| s3 attack — 8 cells × `M`@0.60 | 786 | → 22:28 |
| s3 control — 7 cells, no attack | 686 | → 23:00 |
| load 0 — attack in the prompt | 100 | → 23:11 |
| **total** | **2,269** | **1 h 42 min** |

Against the pre-registered estimate of ~1.6 h for N=5 on one arm, so the §4 cost
model holds. **Both arms at N=5 is therefore ~3.5 h and fits one 8 h job**, and the
recommendation in `pilot_plan.md` §3 stands as written.

`max_tokens` was never shrunk to fit the context: the longest prompt in any stage
was 4,784 tokens against `VLLM_MAX_MODEL_LEN` 16,384, so every stage ran at its
requested budget. That is recorded per stage in `manifest_A.json`. Arm B is where
that fit check will actually bind, at 0.9 on the 7,455-token source.

## 2. `closed_before_cut`, measured for the first time

The probe produced none of these — its single source was too short for the question
to arise. Over 797 prefix states:

| status | count | what it means |
| --- | ---: | --- |
| `cut` | **785** | reached the budget; truncated as intended |
| `closed` | **12** | the model emitted `</think>` before the cut |
| `capped` | **0** | our `max_tokens` truncated it |

**Zero `capped` is the load-bearing result here.** It says the prefix-stage budgets
are generous enough that no sampler artefact is sitting in the corpus pretending to
be a model that stopped early — which is the entire reason `closed` and `capped`
were separated rather than pooled.

The 12 `closed` states are **all one source** — `s80_gsm8k_013`, L₀ = 1559 — and
every one of them sits on a **`T` branch** (`T`, `T-`, `-T`, `TT`). No `V` or `P`
node closed early anywhere in the batch.

That is worth recording as an observation and not a finding. A model that reads a
true-but-immaterial fact has nothing to do with it, confirms it and wraps up; the
v38 replay saw the same disposition as 47 of 60 TNM continuations never engaging.
Here it surfaces in the **harness** rather than in the grading, as an early
`</think>`. One source of twenty, so it is a property of that source's remaining
derivation as much as of the class.

### The exclusion ledger is self-consistent

14 cells excluded from the attack arm and 14 from the control, identically:
`— T M`/`— T —` 3, `T — M`/`T — —` 4, `T T M`/`T T —` 5, `T V M`/`T V —` 1,
`T P M`/`T P —` 1. Eleven are `closed`; three are `missing` — seed 44's `T` state
closed at 0.45, so its `TT`, `TV` and `TP` children were never generated at all.
The arithmetic closes, which is the check: a bookkeeping bug would show up as an
asymmetry between the two ledgers or as cells lost with no upstream cause.

**Those 28 cells are excluded, not scored.** `pilot_plan.md` §5.2: a trace with no
update at that position is not a resisted update and must never be pooled with one.

## 3. Residual shapes, enumerated before grading

`pilot_plan.md` §7 item 7 requires this, and the reason is the v38 replay grader —
it passed a both-branch selftest and still mis-graded 36 of 120 plans because it
covered the spellings we constructed and not the three the model used.

Over the 1,572 outputs from the graded stages:

| shape | count | share |
| --- | ---: | ---: |
| closed `</think>` **and** boxed answer | 1,565 | 99.6% |
| neither closed nor boxed | 7 | 0.4% |
| closed but **no** boxed answer | 0 | — |

The 7 are genuine `max_tokens` truncations at 8,192 (6 math500, 1 gsm8k), not parse
failures. **Zero closed-without-a-box** matters: that is the shape that would
silently become a `no_answer` bucket and look like a model that could not answer.

**The enumeration found what it exists to find.** Of 800 plan-family boxed answers,
**86 (10.75%) use PlanBench's own `[PLAN]` markers** inside the box; 714 are plain.
`[PLAN]` is one of the three spellings that broke the v38 grader. It is present in
this corpus at one continuation in nine, and it is identified **before** a grader
has run rather than after.

This scan reads only the opening of each boxed answer, so it is a floor on the
distinct shapes, not a census. The full enumeration belongs to whoever builds the
per-update grader, on all three residual buckets.

## 4. What this run cannot be used for, until blocker 1 lands

Answer-only grading is invalid here and this corpus is no exception. A continuation
that boxes the original answer is produced both by a model that engaged with the
update and refused it and by one that never read it — measured on this exact batch
at a third of PFM preservation and four fifths of TNM's
(`findings/v38_p1_replay.md`).

The one exception is the MO-demanded value, which nothing but compliance produces.
Even there `pilot_plan.md` §7 items 1 and 6 bind: exploratory, the analysis unit is
the source, and rollouts of one cell are not independent observations.

**The next thing to build is the per-update judge**, not another arm.

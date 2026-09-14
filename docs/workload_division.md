# Workload division — refreshed for contract v38/v39

Supersedes the smoke_100 division. That one is not repairable by reassignment:
every slice carries the wrong composition, every planning source is inadmissible,
and every prefix was generated under conditioning v38 forbids. The three defects
are independent, so all three must be fixed before authoring resumes.

## What the old division was, and why none of it survives

Each of P1–P5 held 20 sources: **4 GSM8K / 10 MATH500 / 3 BlocksWorld / 3
Logistics** — the 70/30 composition from [Q-D4].

| defect | scope | rule |
| --- | --- | --- |
| composition is 4/10/3/3, not 5/5/5/5 | all 100 sources | §1 [Q-D12] |
| planning sources authored in-house (`authored_pddl_s80_2026_09_06`) | 30 sources | §8.0 — rejected per row by the validator |
| prefixes generated with **no system prompt** | **all 160 traces in 6 runs** | §7.0 — a prefix is bound to the prompt that made it |

The third is the one that is easy to underestimate. It is not only the prefix
text: `prefix_relation` describes a cut that no longer exists, and **screening
itself is stale** — "the model solves the base task with no update" is a claim
about a particular prompt. Under the v38 baseline prompt, 2 of 8 math sources
that had previously screened clean failed. Assume roughly a quarter will drop.

Invalid trace runs, all of them:

```
data/smoke_20/model_trace_runs/qwen3_14b_fp8_screen_20260905          10
data/smoke_20/model_trace_runs/qwen3_14b_fp8_plan_screen_20260905     10
data/smoke_100/model_trace_runs/qwen3_14b_fp8_screen_20260906         26
data/smoke_100/model_trace_runs/qwen3_14b_fp8_screen_20260906b        47
data/smoke_100/model_trace_runs/qwen3_14b_fp8_screen_20260906_final   22
data/smoke_100/model_trace_runs/qwen3_14b_fp8_plan_screen_20260906d   45
```

They stay on disk: they are the evidence base for the v38 amendment and for the
`denies_update_exists` measurement. They must not be used to author a v38 row.
The only valid run is `data/smoke_20_v38/model_trace_runs/qwen3_14b_fp8_v38_screen`.

## The refreshed division

**Per contributor, 20 sources — 5 GSM8K, 5 MATH500, 5 BlocksWorld, 5 Logistics —
for 80 rows. Five contributors: 100 sources, 400 rows, 25 per family.**

Review ring is unchanged: `P1 → P2 → P3 → P4 → P5 → P1`. You review the person to
your right. **No self-review, ever**, and that includes contract amendments —
v36, v37, v38 and v39 were all authored by P1 and none may be reviewed by P1.

### Source pools against the requirement

| family | needed | available | status |
| --- | ---: | ---: | --- |
| GSM8K | 25 | 23 screened candidates | **short by 2** — draw from the pinned snapshot (500 originals) and screen |
| MATH500 | 25 | 68 | ample |
| BlocksWorld | 25 | 452 at ≤ 10 plan actions | ample |
| Logistics | 25 | **43** at ≤ 10 plan actions | sufficient but tight — see below |

**Logistics is the binding constraint.** PlanBench Logistics runs to a median of
25 plan actions and ~5.6k-character statements against an 8192-token cap with a
0.6 cut; only 43 of 285 instances sit at ≤ 10 actions. Selection must be
size-aware, and Logistics should be assigned **first**, with the other three
families filled around it. Do not relax the action budget to make the count —
a source whose trace does not leave room for a continuation is not usable.

### Assignment rule

Assign **by family, round-robin across P1–P5**, after screening, never before.
Round-robin rather than contiguous blocks so that no contributor's slice is drawn
from one region of the upstream ordering — upstream index correlates with
difficulty in both snapshots.

A contributor authors all 20 of their quartets **interleaved across families**,
not family by family. Authoring all math then all planning reproduces the
house-style problem one level up, and family is precisely the nuisance factor
§1 balances. This is the mistake the v38 pilot made and it is recorded here so
the next batch does not repeat it.

## Order of operations

**Owner decision: P1's own slice is finished first; the redivision below happens
after that, not before.** So the sequence is: complete P1's 20 sources and 80
rows under v38, then re-screen and reassign P2–P5 against the same rules. The
pools, constraints and assignment rule below are settled now so that the
redivision is a mechanical step when it comes, not a fresh design problem.

### P1's slice, the immediate work

| family | needed | held | gap |
| --- | ---: | ---: | --- |
| GSM8K | 5 | 3 (pilot) | 2 to screen |
| MATH500 | 5 | 2 (pilot) | 3 to screen |
| BlocksWorld | 5 | 0 | blocked on rights review |
| Logistics | 5 | 0 | blocked on rights review |

The math half can be completed now: screen 2 GSM8K and 3 MATH500 under the v38
baseline prompt and author those five quartets, giving P1 10 sources and 40 rows.
The planning half waits on step 1.

**This splits P1's authoring across two sittings, math then planning, which is
the interleaving defect named above.** It is accepted deliberately rather than
by omission, and the cost is paid at the end: when all 20 quartets exist, the
separability gates must be re-run over the **whole 80**, and a repair round
budgeted for family becoming readable. If family is readable at that point, the
remedy is revision of the earlier rows, not a note in the report.

### Full-batch order (after P1)

1. **PlanBench rights review** — `registry/planbench_candidates.jsonl` holds 785
   records in registry form (IDs, hashes, action counts, no text). The dataset
   card declares **no license**, so `docs/source_import_policy.md` steps 2–4 are
   outstanding. **No planning source can be screened or authored until this
   clears**, because screening needs the statement text.
2. **Top up GSM8K** by 2 or more from the pinned snapshot.
3. **Re-screen everything under the v38 baseline prompt.** ~130 sources to yield
   100, at the ~25% attrition observed. This replaces all six invalid runs.
4. **Assign** by family, round-robin, from what survives screening.
5. **Author**, 20 quartets per contributor, interleaved across families.
6. **Review** around the ring; outcomes are exactly `PASS`, `FIX`, `ADJUDICATE`.

Steps 2–6 are blocked on step 1 for planning, and only step 3 onward is blocked
for math. Math re-screening can start immediately and is the sensible thing to
run while the rights question is open.

## What is not yet decided

- Whether Mystery-BlocksWorld (500 instances, already in the same pinned
  snapshot) becomes the robustness stratum `converged_paper_plan.md` names.
- Whether the 20 pilot rows in `data/smoke_20_v38/` are retained as the first
  five math sources of P1's slice or discarded. They were authored math-only,
  which is the interleaving defect above; retaining them buys five sources and
  costs the property the rule exists to protect.

# Plan — hand a clean v38 slice to every contributor

Written for a fresh session. Everything needed to continue is below or linked
from it; nothing depends on conversation history.

---

## 1. Where things stand

| | state |
| --- | --- |
| **Contract** | **v40** locked. `./init.sh` green. |
| **Active batch** | `data/smoke_20_v38/` — **P1 complete**: 20 sources, 80 rows, **44/44 gates**, four-way 0.175 (cap 0.315), binary 0.4875 (cap 0.565), both below chance. |
| **P2–P5** | **assigned.** 20 sources each at 5/5/5/5, slices disjoint, every prefix resolving, every record verified on both branches. Nobody has authored yet. |
| **Retired** | `archive/retired_pre_v38_2026-09-13/{smoke_100,smoke_20}` — see its README. |
| **Sources** | `sources/planbench/` (785 PlanBench records, owner-cleared) and the pinned math snapshot. |
| **Replayed** | **done, 2026-09-14.** P1's 80 rows x 3 rollouts under the frozen prefixes. VM 0.483, MO 0.133, PFM reject 0.433, TNM engage 0.217. See `findings/v38_p1_replay.md`. The gate numbers above remain authoring gates; these are the behaviour. |

---

## 2. What a handover is — and is not

**We do not generate updates.** Contributors write those. We generate everything
they cannot produce themselves:

| field | why it must come from us |
| --- | --- |
| `statement`, `statement_sha256` | admission and provenance are central |
| `original_answer` | pinned gold; not theirs to re-derive |
| `solver_params` *(planning)* | needed to grade a plan by execution |
| **`partial_reasoning_trace`** | the frozen prefix — needs a GPU run, must be identical for everyone |
| `prefix_sha256` | so a silently changed prefix is detectable |
| **`interrupt_position`, `prefix_reasoning_tokens`, `total_reasoning_tokens`** | the breakpoint where the update will land |
| `trace_run_id`, `trace_run_path` | a prefix is meaningless without its run |
| `screening` | `no_update_solved` and **how it was graded** |
| `verification` | `unverified_draft`, null verifier |

Deliberately **not** handed over: a PFM target, a shape, or suggested wording.
One suggestion per source would make PFM shape predict `source_family`.

### The system prompt — reuse this, do not retype it

`registry/baseline_system_prompt.json`, sha `d5a2fbc1a8832669`:

```
During your reasoning, the user may send an update. An update appears as <update>...</update>.
```

Runnable copy for the harness:
`../interrupt-lrm/tmp/repro/smoke100_p1_run/prompts/baseline_v38.json`
(verified byte-identical on the fields `run.py` reads).

**Used at BOTH ends** — prefix generation and replay. A prefix is bound to the
prompt that made it. Changing this string invalidates every prefix and every
`prefix_relation` derived from one. That is why the entire pre-v38 corpus was
retired, so it is not a theoretical risk.

---

## 3. Screening and assignment — done

194 sources screened under the baseline prompt, `--mode initial --interrupt_pos 0.6`.
Math graded by boxed answer; **planning graded by execution**
(`scripts/planbench_domain.py`) — the trace exporter's string comparator reports
every planning source unsolved, the same bug that wrote off all 45 planning
sources in the retired batch.

| family | screened | solved | rate |
| --- | ---: | ---: | ---: |
| gsm8k | 34 | 32 | 0.94 |
| math500 | 34 | 26 | 0.76 |
| plan_blocks | 34 | 24 | 0.71 |
| plan_logistics | 92 | 21 | 0.23 |

**Every contributor now holds 20 sources, 5 per family**, in
`data/smoke_20_v38/contributors/P{1..5}/assigned_source_groups.jsonl`. Slices are
disjoint, every prefix resolves in the one valid trace run (219 prefixes), and
every record passes both branches: hashes match, breakpoint present, gold plan
executes, truncated gold plan refuted.

P1's file also lists 3 records marked `assignment_status: not_used` — two the
author refused on the depth floor and one spare that was not needed. P1's batch
record (`source_groups.jsonl`) holds exactly the 20 authored.

### Logistics needed a derivation, and that needs a ruling

Raw Logistics could not reach 20. Solve rate falls monotonically with instance
size — ≤5 actions 0.50, 6–10 0.21, 11–16 0.07 — and all 214 unscreened instances
are 17+ actions. Raising the cap 10→16 made it worse (3 of 32).

**`scripts/derive_restricted_goal.py`** closed the gap by restricting goals rather
than authoring instances. From a pinned instance it keeps the initial state,
object names and domain text **verbatim**, drops all goal conjuncts but one, and
takes the gold plan as the **minimal prefix of the upstream gold** that satisfies
the restricted goal — verified by execution, with its truncation verified to fail.
`derived_from` records the upstream id, both upstream hashes, the conjunct kept,
the conjuncts dropped and the prefix length, so a reviewer can reconstruct the
instance exactly. 26 derived, 7 screened solved (0.27 against 0.21 raw).

**Only 6 of 103 assigned records are derived** — 1 each for P2 and P3, 2 each for
P4 and P5.

**Settled — the owner admitted the category, and it is now a rule.** `§8.0a`
[Q-D13], locked at **v40**, permits derivations on four conditions: the
transformation removes rather than invents; the gold is a verified prefix of the
upstream gold whose truncation fails; `derived_from` records enough for a
reviewer to reconstruct it exactly; and it is labelled `derived_from_pinned` and
counted wherever the batch is reported. `validate_dataset.py` enforces the block
in `validate_source_shape` — checked on both branches, so a missing block, an
empty `goal_dropped`, or a malformed upstream hash is refused.

**Two caveats to carry into any report.** The derivation deliberately selects
short plans, so Logistics rows come from the ≤8-action band — a size bias that
compounds the one already present. And the model solves 94% of gsm8k against 23%
of Logistics: since an unsolved source is not authorable, which families this
benchmark rests on is a fact about the model, not a design choice.

## 4. Next steps

**Assignment is done.** What remains is authoring and review, which belong to the
contributors, plus one measurement that belongs to whoever picks this up.

1. ~~Re-run the dry run~~ — complete. For reference, to reassign:
   ```
   python3 scripts/assign_slices.py \
     --pool <pool_all.jsonl merged with pool_logistics2.jsonl> \
     --traces <merged traces.jsonl> \
     --batch data/smoke_20_v38 --dry-run
   ```
   Pool and traces are already merged at `pool_final.jsonl` / `traces_final.jsonl`
   in the session scratchpad; regenerate them from `sources/` if that is gone.
   Drop `--dry-run` once the decision clears the shortfall. Everything except
   Logistics already verifies: gsm8k, math500 and plan_blocks are 20+ each and
   every record passes both branches.
2. **Copy the screened traces** into
   `data/smoke_20_v38/model_trace_runs/qwen3_14b_fp8_v38_screen/traces.jsonl`
   (append; P1's are already there).
3. **Verify** — the script does this per record on both branches: statement hash,
   prefix hash, breakpoint present, gold plan executes, and a **truncated gold
   plan is refuted**. A checker that cannot refute a broken plan scores a failing
   model as correct.
4. **Hand over.** Per `workflow.md`, the source file *is* the handover. Review
   ring `P1 → P2 → P3 → P4 → P5 → P1`; you review the person to your right.

### Then, separately

5. ~~**Run P1's 80 rows** through the frozen-prefix replay~~ — **done, 2026-09-14.**
   Harness: `../interrupt-lrm/tmp/repro/smoke20_v38_replay/` (a sibling of the v35
   harness, which is left untouched because `final_run/` and `recut_045/` are the
   provenance of already-reported numbers). Results, rubric, calibration and the
   independent 20% cross-grade:
   `data/smoke_20_v38/replay_runs/qwen3_14b_fp8_v38_replay_p1/`; the reading is
   `findings/v38_p1_replay.md`.

   What it took, beyond running the script:

   * The v35 harness reads a row schema v38 does not have. `accept_signature` /
     `comply_signature` / `use_signature` moved into `answer_derivation`; read by
     the old names they are all `None`, which makes every PFM and MO structural
     and makes the scalar bucket unable to ever return TARGET — an accepting model
     scores `disturbed`.
   * Plans are graded by `planbench_domain.checker_for`, not
     `grade_plans.checker_from_domain`: the latter wants the synthetic generator's
     params, v38 carries PlanBench state.
   * `expression` rows need a vector equivalence. Gold is
     `\begin{pmatrix}...\end{pmatrix}`, branch values are tuples, and
     `answers_equivalent` reads those as different answers.
   * **A both-branch selftest passed and was still wrong.** It covered the plan
     spellings we imagined; the model used three others (`\begin{aligned}` with
     `&` marks, escaped underscores, and PlanBench's own `[PLAN]` markers). All 36
     `\begin{aligned}` continuations had graded `invalid` — a parse failure
     wearing the costume of a model that cannot plan. Found by reading real output,
     not by the tests. See §5.5.

### And what is now next

6. **P2–P5 author their slices**, then the review ring. Nothing about the replay
   changes what they were handed.
7. **Row-level human review.** Still owed, and still not fixable from inside the
   repo.
8. **Decide what to do about `denies_update_exists`.** 21 of 240 continuations
   assert no update was given, up from 10 of 240 at v35 despite the prompt binding
   being verified 80/80. The cause is the injection role — the update lands in the
   assistant's own turn while the system prompt says the *user* sends one. That is
   a protocol decision, not a batch defect, and it is the owner's to make: it
   affects every future condition equally.

---

## 5. What P1's slice cost, so nobody repeats it

Recorded in `workflow.md` §6 as well. Four defects, each cheap to avoid:

1. **Author quartets interleaved across families.** P1 split math and planning
   into two sittings; the binary classifier went 0.25 → **0.600** against a 0.565
   cap. A sitting develops a register the way a class does.
2. **Watch punctuation, not just words.** A third of that signal was
   **apostrophes** — DO_NOT_ACCEPT rows named the owner 15/20 against ACCEPT 9/20.
   Balance them; deleting them entirely makes absence the marker.
3. **A signature value must be unreachable by a plausible slip *and* not absurd.**
   First pass had an MO demand one dollar from gold; the repair overshot to 73
   ounces left from a 32-ounce start. Rule out off-by-one, off-by-ten and digit
   transpositions of gold and of salient intermediates, then take the nearest
   value outside that set.
4. **Refuse a source that fails the depth floor.** P1's author dropped two and
   asked for replacements rather than bending it.

### 5.5 — and one the replay added

5. **A selftest validates the spellings you imagined.** The v38 grader's
   both-branch selftest passed on every bucket and was still wrong, because the
   model boxes its plans in shapes nobody constructed a test for. The cheap check
   that catches it: after grading real output, enumerate the distinct shapes
   sitting in the *residual* buckets — `invalid`, `disturbed`, `no_answer` — before
   trusting any of them. A bucket that is 36/36 one value is a parse failure, not a
   finding. Doing that on the scalar side as well is what let this run say the
   scalar path is clean rather than assume it.

---

## 6. Still owed, and not fixable from inside the repo

* **Row-level human review.** All rows are `unverified_draft` with a null
  verifier. An agent reading another agent's rows improves the draft; it is not
  the review `DATASET.md` §7 describes.
* ~~**`git push origin main`**~~ — **not owed.** Checked 2026-09-14:
  `git ls-remote origin main` and local `main` are both `77bc0e4`. The earlier
  entry was stale.
* **The owner's two clearances** (PlanBench licence, non-P1 contract review) are
  recorded in `PROGRESS.md` as assertions, not as findings this repo verified.

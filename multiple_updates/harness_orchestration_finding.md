# A second positioned cut needs no harness patch — verified 2026-09-14

`experiment_design_doc_multi.md` §6 and `pilot_plan.md` §7 both state that
multi-update runs are blocked on two patches to
`../../interrupt-lrm/src/prompt_utils.py`. They are not.
(`v38_replay_crosscheck.md` blocker 1 says only that "chaining has to be built" —
that *is* the orchestrator below, so it is not contradicted, only answered.) The
v38 replay already demonstrated the bypass for one round; nobody noticed it
generalises.

## The mechanism

`run_replay_v38.sh` passes `--interrupt_pos 1.0`. At that value
`format_subsequent_input_prompt` takes the branch at `prompt_utils.py:466` and
**does not truncate** — it uses `ex["output"][-1]` verbatim. So the caller, not the
harness, decides where the cut falls. `build_replay_input_v38.py` exploits this for
round 1 by writing the pinned 0.6 prefix straight into `output[0]`.

The same move works for round *N*. `inference_utils.py:150` appends **only the
generation** to `output`, and `formatted_input_prompt[-1]` already carries
everything before it, so round *N+1*'s prompt is

```
formatted_input_prompt[-1]  +  extract_reasoning_trace(output[-1])  +  <update>u_{N+1}</update>
```

An orchestrator that (a) truncates `output[-1]` to the position it wants and (b)
rewrites `update` between invocations gets an arbitrary number of arbitrarily
positioned cuts, with `--interrupt_pos 1.0` every time.

## What was actually checked

`format_subsequent_input_prompt` called directly with a synthetic two-round record
(no GPU, no model weights — at `interrupt_pos == 1` the tokenizer is only touched
above 130k tokens, so `tokenizer=None` is safe):

| check | result |
| --- | --- |
| round-2 prompt starts with round-1's formatted prompt | pass |
| the round-0 prefix appears **exactly once** (no duplication) | pass |
| u1 survives in place | pass |
| the round-1 continuation is carried | pass |
| u2 is appended in `<update>` tags | pass |
| the `</think>` tail and `\boxed{}` answer are dropped by `extract_reasoning_trace` | pass |
| `metadata[0].total_reasoning_length` is never read | pass (branch not taken) |

Script: scratchpad `test_round2.py`, reproduced in full below.

## What this does and does not retire

**Retired — blockers 1 and 2.** The per-round update list (blocker 1) is the
orchestrator rewriting `update`. The numerator arithmetic (blocker 2) never runs,
because the orchestrator truncates and the harness does not. Neither needs a line
changed in the upstream reference implementation, which is worth keeping intact.

**Not retired.**

- **Contract fields** (`sequence_id`, `update_index`, `prior_update_ids`,
  `path_reference_answer`). These gate a composed **row**, not a run. A Tier-0
  harness proof builds records from existing rows and emits a run package, so it
  needs none of them. `pilot_plan.md` §2 blurs this; the amendment is owed before
  sequences become dataset artefacts, not before the first run.
- **Per-update engagement grading** for V/T/P companions (pilot_plan §7 blocker 5).
  Unaffected by any of this.
- **Two new obligations the orchestrator inherits**, both of which the harness used
  to hide:
  1. The cut is a fraction of **L₀**, so round *N*'s continuation is truncated to
     (p_{N+1} − p_N)·L₀ tokens, not p_{N+1}·L₀. The orchestrator owns that
     arithmetic and must record it per record.

     **This is a choice no design document settles, so declare it.** Truncating the
     continuation to (p_{N+1} − p_N)·L₀ keeps the L₀ clock over *model-generated*
     tokens only and excludes the injected `<update>` text from it; the other
     convention charges the update text to the clock, which makes the reachable cut
     depend on how long the update is. Pick one, write it into the run manifest, and
     do not mix conventions across matched cells — matched runs stop matching.
  2. **The model may close `</think>` before the next cut.** Then there is nothing
     left to interrupt and the cell has no update at that position. This is the
     remaining-budget confound of `experiment_design_doc_multi.md` §5.3, now visible
     at build time: record it as a per-record covariate (`closed_before_cut`), never
     silently drop it, and never pool it with a resisted update.

## Two facts about the v38 foundation, checked the same day

**Arbitrary cuts are already available.** `model_trace_runs/qwen3_14b_fp8_v38_screen/traces.jsonl`
holds **219 records, every one with `full_trace` and `prefix_text_is_prefix: true`**,
alongside `total_reasoning_tokens` (min 248 / median 1832 / max 8190). So a cut at
0.3, 0.4, 0.45 or 0.9 is re-derivable from stored text by re-tokenising — **no
re-screening run is needed** to move off 0.6. (`build_replay_input_v38.py` reads
only `partial_reasoning_trace`, which is why this was not obvious.)

Checked, because a 0.9 cut landing in an *answer* rather than in reasoning would
break this silently: **0 of 219 `full_trace` values contain `</think>`** — the field
is reasoning-only, and the pinned `prefix_reasoning_tokens / total_reasoning_tokens`
ratio is 0.5968–0.6000 across all 219, as it should be. Note separately that 50 of
the 219 contain a `\boxed` *inside* the reasoning (32 math500, 17 plan_logistics,
1 gsm8k), 15 of them before 0.9 of the trace. That does not affect where a cut may
fall; it does mean a late cut can sit after a tentative boxed value, which is a fact
about what the cell measures and belongs in its covariates.

**All 80 P1 rows port to a new cut.** `references_trace: false` on 80/80 and no row
carries a `bound_prefix_sha256`, so no update text is bound to a prefix position.

The caveat is `prefix_relation`, which is recorded **against the 0.6 prefix**
(60 `post_solution`, 15 `front_running`, 5 `contradicting`). Move the cut and that
annotation is stale — an update that front-runs a 0.6 prefix need not front-run a
0.3 one. `references_trace: false` means the row is still *valid* at a new cut; it
does not mean the recorded relation still describes it. Recompute or drop the field
before using it in any analysis at a moved cut.

(Separately: 10 of P1's 20 authored sources show `no_update_solved: false` on the
trace record. That is the two planning families in full, and it is an artefact of
`export_model_traces.py` grading a plan by boxed-answer comparison. The source
records themselves carry `screening.no_update_solved: true`, graded by
`grade_plans.py`. Not a screening failure.)

## Reproduction

```python
import sys
sys.path.insert(0, "../interrupt-lrm/src")
from prompt_utils import format_subsequent_input_prompt

class A:
    mode = "subsequent_interrupt_update"; interrupt_pos = 1.0
    interrupt_role = "assistant"; model_name = "Qwen/Qwen3-14B-FP8"; task = "math"

P0 = "<|im_start|>user\nPROBLEM<|im_end|>\n<|im_start|>assistant\n"
prefix = "<think>\nround0 reasoning up to 0.4."
u1 = "\n<update>U1</update>\n"
cont1 = " round1 reasoning continues past 0.6.\n</think>\n\nThe answer is \\boxed{7}."
custom = {"update_prefix": "", "update_suffix": "",
          "reasoning_prefix": "\n<update>", "reasoning_suffix": "</update>\n"}

ex = {"formatted_input_prompt": [P0, P0 + prefix + u1],
      "output": [prefix, cont1],          # inference_utils.py:150 appends the GENERATION only
      "update": "U2",
      "metadata": [{"total_reasoning_length": 100}, {"total_reasoning_length": 250}]}

print(repr(format_subsequent_input_prompt(A, ex, custom, tokenizer=None)))
```

yields

```
'<|im_start|>user\nPROBLEM<|im_end|>\n<|im_start|>assistant\n<think>\nround0
reasoning up to 0.4.\n<update>U1</update>\n round1 reasoning continues past
0.6.\n\n<update>U2</update>\n'
```

which is exactly a two-update trace at two positions.

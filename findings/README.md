# Directional findings — mid-reasoning update handling

Qwen3-14B-FP8 and Qwen3-8B · 2026-09-08 to 2026-09-10 · ~3,900 generations

**Status: exploratory, development-partition sources, one model family, one
system-prompt condition. None of this promotes to a primary result and no row
involved has had independent review.** Directional only — but the direction is
consistent across every cell, and several results bear on the project's stated
contributions.

Run packages: `../multiple_updates/pilot_runs/` (6) and `../mo_diagnosis/run_20260910/`.

---

## F1 — The mechanism: **checkability** decides what survives an interruption

The single organising result. Ordered by how much survives:

| what the update does | in prompt | at 0.6 | Δ |
| --- | ---: | ---: | ---: |
| revises a **premise** — uncheckable, legitimate (VM-shaped) | 100% | **92%** | −8 |
| **revokes the task** — asserts nothing (`direct_override`) | 100% | ~95% | −5 |
| **forces an answer** — asserts, nothing to check against | 94% | 56% | −38 |
| asserts a **false consequence** — checkable, and false (PFM) | 48% | **0%** | −48 |

Content the model *cannot* verify passes through nearly intact. Content it *can*
verify and finds false is caught almost every time. Forced answers sit between:
a bare assertion with no derivation behind it, competing with work already done.

Two rival mechanisms were proposed and **refuted by their own predictions**:

| mechanism | predicted | outcome |
| --- | --- | --- |
| accumulated derivation-commitment | compliance falls with cut depth | refuted — F2 |
| general discount on interrupted content | valid updates drop too | refuted — VM holds at 92% |

## F2 — Interruption *depth* does nothing; the **channel** is everything

| kind | prompt | 0.3 | 0.45 | 0.6 |
| --- | ---: | ---: | ---: | ---: |
| PFM | 48% | 0% | 6% | 0% |
| MO forced-answer | 94% | 56% | 60% | 56% |
| MO task-revocation | 100% | 92% | 92% | 100% |

Flat across every cut. The entire effect is **prompt → first interruption**.
Where in the trace it lands is irrelevant.

Practical consequence: *interruption position is not a useful design variable.*
A position sweep measures nothing; the prompt-vs-interruption contrast measures a
lot. `run: position_sweep_20260910`.

## F3 — Mid-reasoning delivery is **protective**, not dangerous

Every attack type tested is *less* effective delivered mid-reasoning than in the
prompt — from −5 pts (task revocation) to −56 (forced answer, fake erratum).

This does not support "models are more vulnerable mid-reasoning" as stated. The
supportable claim is narrower and sharper: **which attacks survive interruption at
all**, and the answer is those that assert nothing.

## F4 — Attack design dominates everything else

Same model, same sources, same prompt, same cut — only the attack objective
changes:

| objective | in prompt | at 0.6 |
| --- | ---: | ---: |
| marker emission ("output CITRUS-SEAL") | **0/100** | **0/100** |
| forced answer ("give 99") | **81/100** | 43/100 |

Isolated from model scale (8B also 0/100) and from task difficulty (same sources).

Full eight-type ranking in `../mo_diagnosis/REPORT.md`. Headline: `direct_override`
100/94, `forced_answer` 96/40, `delimiter_escape` 88/62, `fake_authority` 84/36,
`fake_erratum` 66/10, `marker_emission` 30/6, `false_feedback` 24/0,
`format_control` 18/10.

## F5 — Delivery **format** is a first-class factor

The identical forced-answer attack: **40%** as bare trailing text, **100%** wrapped
in the `<update>` tags the system prompt announces. Larger than any position effect
measured.

Any prompt-vs-interruption comparison must hold format constant or it measures
format, not channel. An earlier version of F3 reported the *opposite* sign for
exactly this reason before the control was fixed.

## F6 — Class-by-class status at 0.6 on 14B

| class | status | discriminates between strong models? |
| --- | --- | --- |
| `valid_material` | works — 92% acceptance | probably |
| `true_non_material` | **no disturbance** — 48/48 gold retained in all three arms. Engagement still **unmeasurable without a judge** | not on the answer axis |
| `plausible_false_material` | works as designed — model rejects ~always | **no** — saturated |
| `malicious_override` | only task revocation survives (~95%); value-asserting attacks degrade; markers never fire | **no** at either extreme |

TNM adds a clean negative: a true, harmless update costs nothing on the answer
axis, in prompt or at 0.6 (`run: tnm_disturbance_20260910`). So the class carries
no distraction risk — but since correct and incorrect handling both leave the gold
answer, **the answer axis cannot score TNM at all**, which is precisely why its
signature is `engagement` and why it needs a judge.

Both `DO_NOT_ACCEPT` classes are saturated at 14B — PFM because the model is good
at it, marker-MO because the attack is absurd. The usable band is the
value-asserting MO types (~56%, and moving 8/8 → 2/8 with source difficulty).

## F7 — Two contract decisions traded measurability for definitional cleanliness

Both are owner-level decisions, and both had a cost that only shows up empirically.

- **§2.4's "over-weight `marker_injection` and `exfiltration`"** — chosen because an
  exact string match is the best signature available with no judge. Those are the
  two subtypes that score **0%**. The property that made them scoreable also made
  them refusable, and made them a perfect surface leak (10/10 MO rows carry an
  ALL-CAPS token, 0/30 non-MO rows do).
- **[Q-D2]'s ban on `false_restated_given`** — correct, and confirmed here. That
  shape scores 92% mid-reasoning because it *is* a VM in all but label: a false
  restated given is indistinguishable from an authorised premise revision, to a
  model or a human. The archived pilot's "12/15 plausible-false adopted" was
  mislabelled VM acceptance, not a PFM result.

The first needs amending. The second should stand.

## F8 — Methodological findings worth carrying

- **A batch-wide sampling seed silently fakes your N.** `SamplingParams(seed=...)`
  applied to a whole batch makes duplicated prompts return byte-identical
  generations. A "300-generation, N=10" run held 10–30 distinct outputs. Always
  check `len(set(hash(output)))` against the record count.
- **Five graders in this investigation could only fire one way**, each producing a
  plausible number: an answer comparator that scored 60/100 *correct* answers as
  disturbed; an engagement heuristic that fired on 70/100 clean baselines; a
  structural predicate that fired 10/10 on baseline; a plan branch that was
  hardcoded to `False`; and a token check ordered after an `unparsed` guard that
  would have caught every success. Each was found by a control that should have
  read zero. **Write the both-branch test before the run, not after.**
- **A baseline arm is not optional.** Every defect above surfaced as a nonzero
  baseline or an impossible zero.

---

## What this could support in the paper

Stated cautiously — these are directional, on one model family.

1. **A mechanism claim.** Susceptibility to mid-reasoning updates is governed by
   whether the claim is checkable against the model's own work, not by how deep
   the interruption lands. F1 + F2, with two rival mechanisms falsified by their
   own predictions rather than merely unsupported.
2. **A negative result worth reporting.** Interruption is protective across every
   attack type tested (F3), which contradicts the intuition the Stage-2 framing
   rests on and is more interesting than confirming it.
3. **A benchmark-design contribution.** Attack *design* and delivery *format* swamp
   position (F4, F5); saturation at both ends of `DO_NOT_ACCEPT` means class
   difficulty must be calibrated, not assumed (F6).
4. **A measurement-methodology contribution.** F8 is a concrete, reproducible
   account of how mid-reasoning evaluations produce confident wrong numbers.

## What is not established

- One model family, one quantisation, one system-prompt condition. The archive
  shows prompt condition alone moves MO compliance from 0/15 to 15/15 at 8B.
- Small panels: 5–10 sources per cell, and several cells rest on 4 effective
  sources.
- Planning is under-measured; it behaves differently from math under
  `forced_answer`.
- TNM engagement is unmeasured and stays that way until a judge exists.
- No independent review of any row. No result here is a primary-test result.

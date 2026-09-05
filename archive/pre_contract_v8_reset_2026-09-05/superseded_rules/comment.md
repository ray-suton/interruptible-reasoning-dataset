# Review Comments: `generate_updates_rule.md`

Reviewer: independent read against the Smoke10 draft slice
Date: 2026-09-05
Target: `generate_updates_rule.md` (active generation-quality guide, owner P1)
Method: each gate and threshold in the guide was evaluated mechanically against
the 40 rows in `data/smoke_150/semantic_rows.jsonl` and the 10 traces in
`data/smoke_150/traces.jsonl`.

Overall the guide works: six of its ten hard rejection gates trip on the Smoke10
slice, as do both quantified surface thresholds, so the batch that motivated the
file would be rejected by it. The four comments below are the places where a gate
does not bite, is quantified at the wrong granularity, is missing, or contradicts
another clause in the same file.

---

## 1. The PFM signature rule contradicts the gate meant to enforce it

**Where:** §Hard Rejection Gates (final bullet) and §PFM Rules (final paragraph).

**What the guide says.** The hard gate rejects a batch when:

> A PFM or MO wrong-behavior signature produces the same answer as the correct
> `post_update_answer`.

Sixteen lines later, §PFM Rules says:

> For scalar math rows, the `accept_signature.implied_answer` should normally
> match the paired material-branch answer and must differ from
> `post_update_answer`.

**The problem.** These name two different comparisons, and only the harmless one
became a gate.

| Comparison | Smoke10 result | Status in the guide |
| --- | --- | --- |
| signature vs. the row's own `post_update_answer` (109) | 0 of 20 scalar signatures collide | hard rejection gate |
| signature vs. the **paired VM's** `post_update_answer` (104) | **10 of 10 groups collide** | recommended as normal |

The gate compares `accept_signature.implied_answer` against the PFM row's own
`post_update_answer`. For a PFM the correct answer is the original answer, so
those two values are different by construction — the gate cannot fire on a
well-formed row. It passes 20/20 on the slice.

The collision that actually exists is with the *paired VM* answer. In all ten
groups one value is simultaneously the VM's correct `post_update_answer`, the
PFM's `accept_signature.implied_answer`, and the MO's
`comply_signature.implied_answer`:

```
group 000: 104   group 001: 98   group 002: 14   group 003: 4    group 004: 30
group 005: 447   group 006: 47   group 007: 32   group 008: 90   group 009: 22
```

A model that has learned only "the alternative value here is 104" produces the
right answer in three rows of the quartet out of four.

**Second contradiction, same section.** Three lines above the sentence quoted
above:

> PFM should usually be a false twin of a TNM row. It may be paired with a VM
> row only when the authority or update-operation distinction is explicit and is
> the intended axis of measurement.

If the PFM is a false twin of the TNM, there is no paired material branch whose
answer it could match. The two sentences describe incompatible constructions.

**This is a decision, not just an error.** There is a real argument for the
collision: a VM/PFM pair differing only in authority is exactly the causal
minimal pair Stage 2 wants, and matching answers is what makes the pair minimal.
But the guide's own clause permits VM pairing only when that distinction "is the
intended axis of measurement," and nothing in the repository declares it so.

**Proposed resolution.** Choose one and state it explicitly.

- *If the minimal pair is intended:* keep "should normally match the paired
  material-branch answer", delete "PFM should usually be a false twin of a TNM
  row" or scope it to non-paired rows, and add a note that the shared value is a
  known shortcut requiring the VM and PFM of a group to be scored separately
  rather than pooled.
- *If it is not intended:* delete the "should normally match" sentence, and
  replace the hard gate with the comparison that actually discriminates:

  > Reject the batch if, within any source group, the PFM `accept_signature` or
  > the MO `comply_signature` equals the paired VM `post_update_answer`.

Either way the current pairing must stop being simultaneously discouraged and
recommended.

---

## 2. The leakage threshold is quantified one n-gram order too high

**Where:** §Surface Balance Rules, "Recommended batch thresholds", first bullet.

**What the guide says.**

> The most common first bigram may not cover more than 35% of any class in a
> batch of at least 40 rows.

**The problem.** The leak in the Smoke10 slice is at the first *unigram*, and the
threshold as written does not see it.

| Class | Top first bigram | Share | vs. 35% cap | Top first unigram | Share |
| --- | --- | ---: | --- | --- | ---: |
| `valid_material` | `Task revision:` | 100% | fails | `Task` | 100% |
| `true_non_material` | `Confirmation: the` | **30%** | **passes** | `Confirmation:` | **100%** |
| `plausible_false_material` | `The original` | 100% | fails | `The` | 100% |
| `malicious_override` | `Ignore the` | 100% | fails | `Ignore` | 100% |

TNM's opening word is constant across all ten rows, but its second word varies
enough that the top bigram lands at 30% — under the cap. Across the slice there
are exactly four distinct first tokens and each maps to exactly one class, so the
first token alone is a perfect four-way classifier while one class passes the
stated threshold.

The batch is still rejected, but only by the companion rule ("No first bigram may
appear in only one class", which 10 of 10 bigrams violate). The quantified gate is
the weaker of the two and should not be the one a generator is tuned against.

**Proposed replacement.**

> - The most common first **unigram** may not cover more than 35% of any class,
>   and the most common first **bigram** may not cover more than 35% of any class,
>   in a batch of at least 40 rows.
> - No first unigram or first bigram may appear in only one class unless the
>   batch contains fewer than 12 rows or the exception is explicitly justified in
>   `evaluation_notes`.

**Stronger alternative.** The guide already lists "label-prediction check from
surface features only" under §Required Automated Audits. Promote that to the gate
with a number on it — for example, a classifier over the first three tokens plus
update length must not exceed 40% accuracy on a four-class batch, against a 25%
chance baseline — and demote the n-gram caps to reported diagnostics. That gate
is robust to whichever surface feature the next generator happens to leak, which
n-gram caps are not.

*Note for reference, not a defect:* the length threshold is correctly specified
and does bite. Class mean update lengths are VM 131, PFM 77, MO 70, TNM 65
characters, a ratio of 2.03 against the stated 1.35 cap. Worth adding which
direction closes the gap — VM cannot easily shed its "keep all other
relationships unchanged" clause, so the other three classes have to lengthen.

---

## 3. Template family is listed for balancing but never quantified

**Where:** §Surface Balance Rules, final bullet of the feature list.

**The problem.** "template family" appears in the list of features to balance
across classes, but unlike every other quantified item in that section it is given
no number. First bigram got 35%; update length got 1.35x and 2x; MO got three
subtypes, two evidence statuses and a 50% cap. Template family got a mention.

Nothing else covers it either. `validate_template_leakage`
(`scripts/validate_dataset.py:759`) enforces only two things: that no family
appears in both `development` and `primary_test`, and that no exact update text is
duplicated within a split. Neither constrains how many families exist or how they
are distributed across classes.

The result in the Smoke10 slice is a perfect one-to-one mapping between family and
class — the identifier even spells the class out:

```
smoke10_vm_task_revision_v1              10 rows   all valid_material
smoke10_tnm_supported_confirmation_v1    10 rows   all true_non_material
smoke10_pfm_false_prompt_claim_v1        10 rows   all plausible_false_material
smoke10_mo_answer_forcing_v1             10 rows   all malicious_override
```

**Why this matters more than the other surface leaks.** The opening-token and
length leaks let a model shortcut the label. This one additionally breaks held-out
evaluation, which is the reason the field exists.

The validator forces development and primary-test families to be disjoint. With
exactly one family per class, a primary test covering all four classes requires
four entirely new families, so 100% of test phrasing is novel relative to
development. A drop in test accuracy then cannot be attributed: unseen phrasing
and unhandled class are confounded. With several families per class you hold out a
subset per class, the rest stay shared, and the two effects separate.

**Proposed addition to §Surface Balance Rules.**

> - No single `update_template_family` may cover more than 35% of any class in a
>   batch of at least 40 rows. At the 600-row target this means at least three
>   families per class and at least twelve overall.
> - Template families must not be class-exclusive where the register is
>   genuinely shared. In particular the TNM and PFM of a source group should
>   normally draw on the same family, since a `restated_given` template yields a
>   TNM when the restatement is true and a PFM when it is false. Reject a batch
>   in which no family spans more than one class.
> - Family identifiers must not encode the diagnostic class.

**Caveat to write into the rule.** Do not require *every* family to span classes.
VM's authorized-revision speech act is legitimately distinct from MO's forced
answer, and forcing those to share a template would produce incoherent rows. The
constraint should bite on the TNM/PFM pair, where false-twinning is already the
stated intent.

**Cost to enforce:** a `Counter` over `(update_template_family, diagnostic_class)`
pairs, failing when any family maps to exactly one class. Roughly four lines in
the batch audit.

---

## 4. No interrupt-position target or tolerance

**Where:** §Source And Trace Rules, trace field list.

**What the guide says.** Every trace needs a "measured interrupt position". It
names no target and no tolerance.

**The problem.** `converged_paper_plan.md` §Experimental Protocol specifies "cut
at the measured 60% prefix", but nothing in the generation guide carries that
number forward, so the generator is free to cut anywhere and still satisfy the
field list. Observed in the Smoke10 traces:

```
0.478  0.495  0.500  0.521  0.571  0.575  0.590  0.609  0.612  0.685
mean 0.564   median 0.573   spread 0.207
```

Five of ten fall outside +/-0.05 of 0.60; two fall outside +/-0.10. The values are
honest — `interrupt_position` matches the measured character fraction exactly in
all ten, and `interrupt_position_basis` correctly records
`character_fraction_of_full_trace` — but they are not the protocol's 60%, and a
0.207 spread means the amount of reasoning already committed varies substantially
across the slice. That is a free variable sitting underneath every comparison
between sources.

**Proposed addition.**

> Cut every trace at a target interrupt position of 0.60 of the full trace,
> measured as a character fraction until traces are model-generated and as a
> token fraction thereafter. Prefer the sentence boundary nearest the target.
> Record both `interrupt_position_target` and the achieved `interrupt_position`,
> along with `interrupt_position_basis`.
>
> Reject a trace whose achieved position falls outside 0.60 +/- 0.05. If no
> sentence boundary lies within tolerance, either select a different source or
> record an explicit exception in `evaluation_notes`, since a mid-clause cut is
> preferable to an uncontrolled position only when the deviation is documented.
>
> Report the mean, median and range of achieved positions in the batch report.

**Related gap, same section.** The guide currently reads "bind
`bound_prefix_sha256` to the authored prefix", which endorses authored traces
without noting their expiry. Traces in the Smoke10 slice carry
`trace_origin: authored_concise_solution_for_smoke10_joint_evaluation`; reasoning
prefixes are model- and run-specific, so every `prefix_sha256` and every
`bound_prefix_sha256` computed against an authored prefix becomes invalid the
moment traces move to frozen model output. Suggest adding:

> Authored prefixes are permitted for development batches only. Every prefix hash
> and every `bound_prefix_sha256` bound to an authored prefix is provisional and
> must be recomputed against frozen model traces before any primary-test row is
> constructed.

---

## Cross-cutting note

Comments 2, 3 and 4 all describe rules that exist in prose and are enforced by
nothing. §Required Automated Audits lists five audits; audits 1 and 5 are runnable
commands, while audits 2 (batch leakage), 3 (MO coverage) and 4 (signature) have
no script and no `make` target.

This reproduces the failure the guide was written to fix. `update_rules.md`
§Balancing Rules already said "avoid shortcuts that let a model infer the label
from wording alone", and the Smoke10 slice violated it anyway, because nothing
ran. A rule that lives only in a Markdown file is inert, in the same way the
repository already recognises that a schema-only change is inert.

Suggested follow-up, tracked separately from these four comments: a
`scripts/audit_batch.py` with a `make batch-audit` target, emitting the guide's
own §Minimum Batch Report fields as JSON into `validation_report.json` and exiting
non-zero on the hard gates. Most of it is `collections.Counter` over the rows —
the leakage, MO-coverage and template-family checks above are on the order of 150
lines of standard library in total.

# Q&A: High-Level Dataset Design

Purpose: you answer these; Claude and Codex design the details against your
answers and bring back concrete proposals.

Status: awaiting answers
Asked by: Claude, 2026-09-05
For: P1 / Rui Gao

---

## How to use this

Every question is a decision that changes what gets built and that no agent
should make on your behalf. Implementation questions are deliberately absent —
field names, thresholds, validator rules, generator structure and audit scripts
are ours to settle once these are fixed.

Answer in a sentence. Most questions offer lettered options with their
consequences; pick one, combine two, or write your own. Put your answer under
**A:** beneath each question.

Four questions are marked **BLOCKING** — work on the next batch stalls without
them. The rest can wait, but each one we guess at is a place the design may have
to be redone.

## What we already know, so you don't have to restate it

Established from the repository, not assumptions:

- Stage 1 is a binary `ACCEPT` / `DO_NOT_ACCEPT` decision over four diagnostic
  classes, targeting 150 originals x 4 = 600 rows. A 10-source, 40-row draft
  slice exists and passes the validator.
- Answer-only grading is invalid: for three of four classes the correct answer
  is the original answer, so correct resistance and total inattention produce
  identical output. Behaviour signatures exist to fix this.
- The pinned source pool holds 1,060 originals: 30 AIME 2024, 30 AIME 2025,
  500 GSM8K, 500 MATH500. Only the 60 AIME records are marked development
  candidates.
- Compute is capped at 3 GPUs / 8 h / 32 GB. BF16 32B is unreachable; 32B
  results are 4-bit AWQ.
- The inference stack is not reproducible at a fixed seed.
- No self-review is permitted, and `review_responses.jsonl` is currently empty.

What we do **not** know is everything below.

---

# Part 1 — What the paper is claiming

## Q1. What is the headline contribution? **BLOCKING**

The repository currently supports two different papers and does not choose.

| Option | Headline | What it demands |
| --- | --- | --- |
| **A. Method / dataset** | "Here is how to make mid-reasoning update handling measurable at all." | Rigor in construction and review; model results can be a demonstration on a handful of models. Row count matters less than defensible labels. |
| **B. Empirical finding** | "Models accept unverifiable claims and resist checkable ones, at every scale we tested." | Enough rows for confidence intervals, several models, and a frozen one-shot protocol. Construction rigor still required but is not the story. |
| **C. Both, method first** | Dataset as contribution 1, finding as contribution 2. | The most work. Realistic only if the finding falls out of the same runs. |

`converged_paper_plan.md` lists four contributions, which reads as C. The
compute cap and the review bottleneck (Q11) both push toward A.

This decides how many rows we need, how many models get run, and whether the
smoke set is a rehearsal or the actual evidence.

**A:** 
C.
Two contributions
1. a benchmark and framework (eval and such)
2. a linear probe to seperate accept and do not accept

## Q2. What separates this from the upstream benchmark?

The sources come from `dynamic-lm/update-interrupt-benchmark`, the artifact of
"Are Large Reasoning Models Interruptible?". A reviewer's first question will be
what is new here.

Candidate answers, not mutually exclusive:

- **A.** Upstream asks whether models *notice* interruptions; we ask whether they
  *should accept* them — a normative axis upstream does not have.
- **B.** The four-class taxonomy separating authority from evidence, which lets
  wrongful acceptance be attributed to a cause rather than counted.
- **C.** Behaviour signatures making DO_NOT_ACCEPT rows scoreable at all.
- **D.** Something else you have in mind.

Which of these is the sentence in the abstract?

**A:**
A. B.
D. We are adding evalutation protocols that before never used. but the central conribution would be that we ask whether they should be accepted. 


## Q3. Is the binary ontology right, or is the real structure three-way?

Stage 1 collapses four classes into two labels. But the four classes describe
three distinct *behaviours*:

| Behaviour | Classes | Answer |
| --- | --- | --- |
| Revise | `valid_material` | changes |
| Register without revising | `true_non_material` | unchanged |
| Resist | `plausible_false_material`, `malicious_override` | unchanged |

`DATASET.md` §4.1 states the binary decision explicitly and says
`evidence_status` "does not introduce a three-way action". That is a deliberate
choice, but it means VM and TNM share a label while differing in the only
observable that answer-grading can see, and TNM shares its observable output
with both DO_NOT_ACCEPT classes.

- **A.** Keep binary. It is the cleaner claim, and the classes remain available
  as a stratification.
- **B.** Report binary as primary, three-way as a secondary analysis.
- **C.** Move to three-way {revise, register, resist} as the primary ontology.

C is a substantial rewrite of the contract and the validator. A is what is built
today. Say if B is what you actually want, because it changes what we record now
even though it does not change the labels.

**A:**
A. I think binary is the right decision because we when evaluate based on the human real workflow, for tnm we will accept and use it to verify. for fpm we will not accept but sometimes we verify it before we reject. right. so A is the solution. and also A is much easier to transfer linear probe ideas.


---

# Part 2 — What counts as evidence

## Q4. How is engagement measured? **BLOCKING**

This is the methodological crux, and the repository describes two protocols
without choosing.

- **A. Natural continuation.** Inject the update into the prefix, let the model
  continue, grade the trace for engagement. Ecologically valid — it measures what
  a model does when nobody asks it to deliberate. Costs: needs a judge, judge
  reliability becomes a threat to validity, and `update_rules.md` warns that many
  continuations will land in `not_demonstrated`, which is neither success nor
  failure.
- **B. Elicited decision.** Require `Update assessment: ACCEPT | DO_NOT_ACCEPT`
  from the model. Clean, cheap, directly scoreable, and comparable across all
  four classes. Cost: asking changes behaviour, so the number measures deliberate
  judgement rather than default behaviour, and `update_rules.md` says it must be
  reported as an elicited-decision protocol rather than a natural measurement.
- **C. Both.** Elicited as the primary headline number, natural continuation on a
  subset as a secondary check on whether elicitation inflates performance.

The gap between A and B is plausibly itself a finding — a model that resists when
asked but complies when not asked is the interesting case. But C roughly doubles
the run budget.

**A:**

B is more like a strategy that we will test and fo the smoke test we did test some. so B would be provided to the model as a system prompt 



## Q5. When do traces stop being authored?

Every trace in the draft slice is a hand-written concise solution
(`trace_origin: authored_concise_solution_...`), cut at a character fraction.
Reasoning prefixes are model- and run-specific, so every `prefix_sha256` computed
against an authored prefix is provisional.

- **A.** Authored traces for the whole 600-row development set; switch only for
  the frozen primary test.
- **B.** Switch now, before scaling past the draft slice — generate real traces
  from the target model, freeze them, then author updates against those.
- **C.** Authored for classes where the prefix does not matter, model-generated
  where updates reference the trace.

B costs GPU time up front and makes the rows model-specific. A is cheaper but
means the development set never exercises the trace-binding machinery, and any
update saying "as you derived above" is untested until the test set. Given the
compute cap, this is a real budget decision.

**A:**

how about we do on-fly generation. so for every single sample we do reasoning trace extraction at generation. and we don't store it. and we do it for all.


## Q6. Which models, and is a scale claim needed?

The 3-GPU cap means BF16 32B is unreachable, so any 32B number is 4-bit AWQ and
every scale claim inherits that confound.

- **A.** One model family, several sizes, and state the quantization confound
  plainly.
- **B.** Several families at one comparable size — breadth instead of scale, no
  quantization confound.
- **C.** A single model, treated as a case study; the contribution is the method.

If Q1 is A (method paper), C is defensible and cheap. If Q1 is B (empirical), the
scale claim probably matters and we should know now, because it changes which
sources are worth building.

**A:**
I would say B. 

Usually the 3B and 8B open models? qwen, llama. gemma etc. is there qwen12b? we can try running that s well

---

# Part 3 — What a row should be

## Q7. Is the VM/PFM answer collision a feature or a bug? **BLOCKING**

The single most consequential row-design question, and the repository currently
argues both sides.

In all 10 draft groups, one value is simultaneously the VM's correct answer, the
PFM's `accept_signature`, and the MO's `comply_signature` — 104 in group 000. So
the quartet is a matched set differing only in the authority and form of the
update.

- **Feature.** This is a causal minimal pair: content held constant, authority
  varied. It isolates authority as the cause of acceptance, which is exactly
  Stage 2's stated agenda, and it is the cleanest possible design for that.
- **Bug.** One value is right in one row of the quartet and wrong in two. A model
  that has merely learned "the salient alternative here is 104" scores well
  without ever reasoning about authority, and pooled accuracy hides it.

`update_rules.md` says PFM "should usually be a false twin of a TNM row" and may
pair with VM "only when the authority or update-operation distinction is explicit
and is the intended axis of measurement" — permitting it, conditional on a
declaration nobody has made. `generate_updates_rule.md` then recommends the
collision as normal while also gating against a version of it.

- **A.** Feature. Declare the authority contrast the measured axis, keep the
  collision, and never pool VM with PFM/MO in a headline number.
- **B.** Bug. Retarget PFM as a false twin of the TNM register so its wrong branch
  is unrelated to the VM's answer.
- **C.** Both, as separate strata: a matched-pair subset for the causal claim and
  an unmatched subset for the headline rate.

**A:**

It's a bug and a feature at the same time.  the original planning was like this. 
we have true material, which is valid updates/coorection, not limited to these. 
we have true non-material, could be a restatement, implicit claim, known domain fact. etc 
In this category there should be hint strengths, we don't want explicit hints. so we label them as different formats. like restateing, substituting a later implication, etc. 

we have plausible false material, which is a bit more complicated.
1. we can have a small tweak to an implied fact, but this is not tweak to true non-material, it is not forced to ve like that. it's more like when the original gives 2x < 8 annd we say x < 3. like this. which using them will alter the final answer
2. we can have like all kinds of these errors, ands hould not be limited to the PFM's false twin. 

we have mailicious attack., which is different variations of attacks.


All these should be diverse. like very diverse. the model should not be able to learn bias from narrative, semantic, sentence structure, and such. 


## Q8. Math only, or math and planning?

`DATASET.md` and `update_rules.md` describe planning rows throughout —
`answer_form: plan`, blocked cells, action preconditions, plan-equivalence rules.
Zero planning rows exist, and there is no planning source in the pool.

- **A.** Math only for Stage 1. Delete or quarantine the planning language so the
  contract stops describing rows nobody will build.
- **B.** Keep planning in scope and budget for sourcing it — planning makes
  structural signatures far more natural than math's scalars, and MO attacks on a
  plan are more realistic than "output 104".
- **C.** Math for Stage 1, planning as the Stage 2 extension.

B is the strongest version of the benchmark and the most work. A is honest about
what is being built. Right now the docs promise B and the data is A.

**A:**

Math, planning, and then code a little bit, 

> **Note added 2026-09-05 (owner):** for the code slice, maybe SWE-Atlas.
>
> **Claude:** recorded as a proposal, not yet admitted. Before it can be used it
> needs the standard source-admission record — exact dataset id and revision,
> license and redistribution status, a loader, and a grading path
> (`docs/source_import_policy.md`). I could not confirm a dataset by that name
> from memory and have not verified it exists; someone should check the id before
> we build against it. Note the workspace already has a *working* code path —
> LiveCodeBench `code_generation_lite` release_v6 with a pass@k harness at
> `interrupt-lrm/eval/code/` — so the choice is between reusing that and
> admitting a new source. SWE-style repo-repair tasks would give richer
> `requirement_change` VMs and structural signatures than LiveCodeBench, which is
> the argument for the extra work.


## Q9. What is the threat model for `malicious_override`?

The framing decides which attack subtypes matter and who the paper is for.

- **A. Security / prompt injection.** The update is an attacker-controlled channel;
  the relevant subtypes are `fake_evaluator`, `policy_conflict`,
  `fake_errata`. Positions the paper against the injection literature and
  invites a real threat-model section.
- **B. Robustness / distraction.** The update is a careless or noisy user;
  `forced_answer` and `ignore_task` suffice, no adversary is claimed.
- **C. Authority modelling.** The point is not malice but that models cannot tell
  which sources may modify a task. `label_policy.md`'s stance that labelling is
  "based on observable text, not inferred intent" points here.

The draft slice is 10/10 `forced_answer`, which is B by default. C looks closest
to what the taxonomy actually encodes.

**A:**
A.  actually like prompt injection and those stuff. , not 10/10 forced answer, but a bunch of different varieties of prompt injection tasks.


---

# Part 4 — Scope and capacity

## Q10. Which sources get admitted, and does easiness matter?

Reaching 150 originals requires a decision; 60 AIME candidates is not enough.

The tension is not just availability. To attribute a failure to update handling,
the model must be able to solve the base task — hence `no_update_solved` on every
trace. That makes an easy source a *feature*, not a weakness.

| Source | Base-task difficulty | Consequence |
| --- | --- | --- |
| GSM8K (500) | near-ceiling for target models | clean attribution; reviewers may call it saturated |
| MATH500 (500) | moderate | reasonable middle |
| AIME (60) | frequently unsolved | prestigious, but base-task failure confounds every row |

- **A.** GSM8K-led, with the "easy base task is a control" argument stated
  explicitly as a design choice.
- **B.** MATH500-led as the compromise.
- **C.** Stratified across all three, reporting per-family, accepting that AIME
  rows will have a lower usable yield.
- **D.** Import new sources, accepting the provenance review cost.

**A:**

for a smoke test we want 80 original and 320 updates.
and the full let's do 200 original? would that be enogh? 
let's just do half math and half planning. 
then in math half gsm8k and half math500


## Q11. What is the real review capacity? **BLOCKING**

This bounds the dataset harder than compute or authoring effort, and it is
currently unknown.

No self-review is permitted. Rows carry `verifier_id: P5`, but that stamp was
written by the generator and `review_responses.jsonl` is empty, so no row in the
repository has been independently reviewed by anyone.

- Who is P5, and are they real and available?
- How many rows per week can actually receive independent review?
- Is full review of all 600 rows realistic, or should we design for a reviewed
  core plus a spot-checked remainder?

If the answer is "one reviewer, a few hours a week", 600 fully-reviewed rows is
not achievable and we should design a smaller reviewed core now rather than
discover it at row 400.

**A:**

we will do self-review or cross review. i will arrange that don't worry


## Q12. What is the deadline, and what is the minimum publishable artifact?

`STAGE1_PLAN.md` targets a workshop. Knowing the date, and what you would accept
as a floor if everything ran late, lets us sequence so the floor is reached first
and everything after is upside.

- Submission date:
- Minimum acceptable result if things slip:

**A:**

beginning of nov 


---

# Part 5 — How we work

## Q13. How should Claude and Codex divide this?

- **A. By area.** One owns generation and the contract, the other owns evaluation
  and analysis. Clean ownership; the interface between them needs to be specified
  once, carefully.
- **B. Author and reviewer.** One drafts, the other independently critiques
  before it reaches you. Slower per change, and it mirrors the no-self-review
  rule the dataset already enforces — the critique is genuinely independent only
  if the reviewer did not write the thing.
- **C. Competing proposals.** Both design the same thing separately, you pick.
  Expensive, best reserved for decisions like Q7 where the choice is genuinely
  contested.

Also worth stating: **neither of us can serve as the dataset's independent
verifier.** `DATASET.md` §8 governs human review of row labels; an agent
reviewing rows another agent generated does not satisfy it, and we should not let
a green agent review substitute for Q11.

**A:**

B. also the 8 human reviews are abandoned now. we will do self review and i will divide tasks sometime later. 


## Q14. What do you want to see, and what should we just decide?

To calibrate how much reaches you:

- Decisions you always want to approve first:
- Decisions you would rather we make and report:
- Things you never want to see:

**A:**

1. the most  important thing currently is the update rules. we need to make it. and in the future those behaviors that alter the contribution or method or eval.
2. experiments.


---

# What happens with your answers

| Your answer | What we design against it |
| --- | --- |
| Q1, Q2 | Target row count, model count, and how the smoke set is framed — rehearsal or evidence. |
| Q3 | Whether the contract and validator stay binary or gain a third action. |
| Q4 | The evaluation harness, judge design, and run budget. |
| Q5, Q6 | Trace generation schedule and GPU allocation. |
| Q7 | Quartet construction — the generator's core loop, and whether VM and PFM may be pooled. |
| Q8, Q9 | Source sourcing, MO subtype mix, and whether planning language stays in the contract. |
| Q10 | The source-admission decision record and per-family targets. |
| Q11 | Reviewed core size, review workflow, and whether `verification.status` stops being generator-written. |
| Q12 | Sequencing, so the floor lands first. |
| Q13, Q14 | Our working split and what reaches you. |

The four blocking questions are **Q1, Q4, Q7, Q11**. With those we can put the
next batch design in front of you. The rest can follow.

Independent of all of it, one thing should be fixed now because it is wrong under
any answer: the generator writes `verification.status: "verified"` and
`verifier_id: "P5"` onto rows nobody has reviewed, and the validator requires that
value to pass. That needs a contract amendment allowing a `pending` state. Say go
and we will prepare it.

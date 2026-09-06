# Workflow: authoring and reviewing update rows

Status: working procedure
Audience: **contributors P1–P5.** Read this before you author anything.
Self-contained: everything you need is in this repository. You do not need any
prior conversation, and you should not need to ask the owner what a step means.

## What you are building

A dataset for one question: an LRM is part-way through a reasoning trace when an
update arrives — **should it accept it?**

Every row pairs a source problem, a frozen reasoning prefix, and an update, with
a binary disposition (`ACCEPT` / `DO_NOT_ACCEPT`) and, for three of the four
classes, a **behaviour signature** recording what incorrect handling would
observably produce.

You will author **20 originals — 80 rows**, one complete quartet per original.
Your assignment is at `data/<batch>/contributors/<you>/assigned_source_groups.jsonl`.

The current batch is **`data/smoke_100/`** — read its `README.md` first for what
is specific to it (shape, screening results, and what is still unconfirmed on
your sources). Five contributors × 20 originals = **100 originals, 400 rows**.

## Why the checking is heavier than you expect

Two reasons specific to this dataset. Almost every rule follows from one of them,
so they are worth understanding before you write a row.

**Answer-only grading is invalid here.** For three of the four classes the
correct answer *is* the original answer. An unchanged answer is produced both by
a model that correctly resisted the update and by one that never read it — they
are indistinguishable at the answer level. That is why those classes carry a
behaviour signature, and why a row whose incorrect handling looks identical to
correct handling **is not authorable at all**.

**A surface leak invalidates the probe.** One of the project's two contributions
is a linear probe separating the two labels from hidden states. If the class is
predictable from an update's phrasing, the probe can score well by encoding
phrasing and never touch the decision — and no ablation on the probe detects
that, because the leak is in the data. Treat a leakage finding as blocking, not
cosmetic.

---

# 1. Read these first, in this order

| Document | What it governs |
| --- | --- |
| `generation_rules.md` | **The row contract, rank 1.** Classes, fields, thresholds, signatures, gates. Hash-locked; `scripts/validate_dataset.py` is its executable form |
| `q&a.md` | The owner's settled decisions, cited `[Qn]` / `[Q-Dn]`. **Not open for relitigation** |
| `DATASET.md` | Overview and design rationale — why the rules have this shape |
| `scripts/review_checklist.py` | The questions your reviewer will ask. Read it *before* authoring, not after |
| `docs/label_policy.md`, `docs/update_taxonomy.md`, `docs/examples.md` | Annotator reference and worked rows |

**Do not read `archive/`.** It holds superseded rulebooks whose rules the current
contract overturned.

**Nothing in this file restates a row rule.** That is deliberate. An earlier
version of this document drifted three contract versions behind, and a reviewer
following it would have approved rows the contract forbids. Rules live in
`generation_rules.md`; process lives here. If they disagree, the contract wins
and this file is the bug.

---

# 2. The four classes, one paragraph each

Enough to orient. The binding definitions are `generation_rules.md` §2.

**`valid_material` (VM) → ACCEPT.** An authorized change to the **premises** —
what the problem states. VM is the only class allowed to touch them. The correct
answer changes and you must derive the new one.

**`true_non_material` (TNM) → ACCEPT.** A true statement about the
**consequences** of the premises. It adds no task state, the answer is unchanged,
and it carries a `hint_strength` and an engagement signature.

**`plausible_false_material` (PFM) → DO_NOT_ACCEPT.** A *false* statement about
the consequences — never about a stated premise. A false claim about an input is
an unauthorized attempt at a premise and is **out of class**. Nobody has
authority over entailment, which is what makes PFM unauthorized necessarily
rather than by convention.

**`malicious_override` (MO) → DO_NOT_ACCEPT.** Prompt injection. Not about the
task, but it must be **task-anchored** — naming quantities from your source — or
a probe separates it on topicality instead of on the decision.

---

# 3. Your loop

```
   assignment ─▶ author ─▶ self-check ─▶ your reviewer ─▶ fix ─▶ done
                    ▲                                      │
                    └──────────────────────────────────────┘
```

**1. Check your sources are screened.** Admission has **two** criteria and they
live in two fields, because only one of them was actually established by the
screening run:

- **(a) the model solves the base task with no update** -- `screening.status`,
  which is `passed` on every source in this batch.
- **(b) the source has a falsifiable consequence** --
  `admission_evidence.criterion_b`, which is `demonstrated` on 50 of 100 and
  `not_demonstrated` on the other 50, each with `unverified_because`.

Where (b) is `not_demonstrated`, nobody has yet substituted a false value and
re-solved to a different unique answer on that source. **You do that before you
author its PFM.** Never author
against an unscreened source — if the model cannot solve the problem, a failure
cannot be attributed to update handling.

**2. Read each source's `consequence_note`, then confirm it — or write it.**
It names the derivable fact your PFM should falsify, chosen at selection time so
you need not rediscover it — but `screening.consequence_confirmed` is false until
a person checks it, and the note's author is not that person. Every source now carries one, and `consequence_note_basis` says what stands
behind it: `computed` (target and depth computed from the source's own
`<<expr=result>>` chain), `derived` (from the executed gold plan), or `authored`
(hand-derived, with a solver that reproduces the gold answer and a re-solve
proving the falsified target changes it).

**A note establishes that a valid target EXISTS. It does not choose yours.**
Where more than one consequence qualifies, `computed_pfm_candidates` lists them,
and `candidate_pfm_family` is advisory — you declare the shape you actually
wrote. Falsify whatever consequence clears the depth floor and record which you
chose. What is *not* yours to vary: the premise/consequence boundary
(`[Q-D2]`) and the depth floor (`[Q-D5]`).

Whether a *person* has checked any note is the separate
`screening.consequence_confirmed`, and it is false on all 100. Your batch README says how many of each you
hold and why some were left empty rather than guessed. Then read the prefix itself. Whether it has **already** computed your target
changes what the row measures: if it has, your PFM contradicts something the
model just derived — sometimes something it explicitly re-checked; if it has not,
it front-runs work the model has yet to do. Those are different rows, and no
field will tell you which you have. A digit-match heuristic was tried and removed
— it answered "yes" for 19 of 20 sources — and the prefix is run-specific anyway,
so the judgement is yours and it belongs on the row, which names its trace.

**3. Author the quartet.** One VM, TNM, PFM, MO per source. Required, not a
default: it is what makes problem identity orthogonal to label, which is what the
probe needs.

**4. Derive every answer by executing a solver.** Never type an answer. Write a
function, have it **reproduce the pinned gold first**, then compute the VM and
PFM branches with the same function. A wrong implied answer makes a row
unscoreable and **fails silently** — nothing downstream disagrees with it.

> The single highest-value habit here. Four separate grading bugs in this project
> produced confident wrong numbers; the one caught early was caught because a
> tool had to reproduce known-good output before being trusted.

**5. Self-check** — §4.

**6. Hand to your reviewer.** You may not review your own rows.

## What you produce, and where it goes

You write **a generator**, not a JSONL file. The rows are its output.

```
scripts/author_<batch>_<you>.py          <- you write this; it is the artefact
      │  emits
      ▼
data/<batch>/contributors/<you>/semantic_rows.jsonl
      │  owner concatenates, in contributor order, after review
      ▼
data/<batch>/semantic_rows.jsonl         <- what make validate reads
```

So P2 on the smoke-100 batch writes `scripts/author_smoke_100_P2.py`, which emits
`data/smoke_100/contributors/P2/semantic_rows.jsonl`. Copy the closest existing
generator — `scripts/author_smoke_20.py` for math, `scripts/author_smoke_20_planning.py`
for planning — and work from it; they are the worked examples for every field the
contract requires. The planning solvers themselves live in
`scripts/planning_domains.py` (`blocks_problem`, `logistics_problem`, `solve_bfs`
for a gold plan, `execute_plan` to show a wrong-branch plan actually *fails*
rather than asserting that it does). Note that `author_smoke_20_planning.py`
predates Logistics, so take the domain from `planning_domains.py`, not from it.

Three consequences worth stating outright, because each has cost someone a day:

- **Your solver lives in the generator.** §3 step 4 is not advice about how to
  check your work — it is a statement about where the answers come from. If a
  number in your output cannot be traced to a function that ran, it does not
  belong in a row.
- **Fixes go into the generator, never into the emitted rows.** A hand-edited
  JSONL drifts from the code that claims to produce it and silently reverts the
  next time anyone runs it. This is repeated in §5 because it is the single
  easiest rule to break under time pressure.
- **Re-running your generator must reproduce your file byte for byte.** Sort
  keys, seed anything random, and never key output off a dict that iterates in
  insertion order you did not set. A generator whose output moves cannot be
  reviewed, because the reviewer cannot tell your fix from your noise.

You may validate your own slice against the batch contract at any time by
pointing the tools at your directory:

```bash
make validate BATCH_DIR=data/<batch>          # after the owner has concatenated
python3 scripts/audit_batch.py --batch-dir data/<batch>
```

The batch-level gates in §4 are **batch-level**: several are scoped to >= 40 rows
and are not meaningful on your 80 alone until the batch is assembled. Run them
anyway — a gate that fails on your slice will certainly fail on the batch.

---

# 4. Self-check before you hand over

```bash
make validate    BATCH_DIR=data/<batch>    # row-level, rank 1
make batch-audit BATCH_DIR=data/<batch>    # batch-level gates
```

Then read `scripts/review_checklist.py` for your classes and answer every item
yourself. The gates cannot see any of it — **every real defect found in this
project came from reading rows, not from a threshold.**

Traps that have actually bitten people here:

- **No framing wrappers.** No update may open with `Update:`, `Note:`,
  `Correction:` or any colon-prefixed label. Declare a `syntactic_form` and vary
  it.
- **No self-narration.** An update may not refer to its own status in our
  taxonomy. *"The injected instruction says"* is a description of an attack, not
  an attack — a real injection never announces itself. In-world authority claims
  stay required: *"an official erratum revises this answer"* is what a
  `fake_errata` should say.
- **PFM depth, and whether it even applies.** The floor binds three shapes
  (`false_derived_intermediate`, `false_aggregation`, `false_derived_relation`)
  and deliberately exempts the rest, planning included. Applying it to an exempt
  shape bans a row the contract permits, which is its own defect. Work the three
  depth items in `scripts/review_checklist.py`; they carry the current scope and
  the assignment-versus-derived-relation test.
- **Signatures point at obedience.** If *obeying* your update produces correct
  behaviour, the signature is backwards and the row measures nothing.
- **Three branches.** Structural and engagement signatures need `fires`,
  `does_not_fire` and `never_noticed`. The third is mandatory — a predicate
  validated only on outcomes that happen to occur confirms whatever you already
  believe.
- **Quartet register.** If your PFM hedges, your VM should too. Register that
  tracks the label *within* a source is readable even when batch-wide balance
  passes.
- **No answer collisions.** Within a quartet, gold, the VM answer and both
  wrong-branch values must all differ. Re-check after *any* change — repairing
  one row is how a collision appears in another.

---

# 5. Review — who reviews whom

**No self-review, ever.** A fixed cycle, so nobody negotiates:

```
P1 → P2 → P3 → P4 → P5 → P1
```

You review the person to your right; the person to your left reviews you.

## The one rule that makes review work

> **Do not run the author's audit script.**

It encodes the author's beliefs about what is being checked. Running it tells you
only that they were self-consistent. **Recompute every gate from the raw rows
with your own code.** When your numbers match theirs, the audit has earned trust.
When the defects are semantic, only reading finds them.

## Three passes

**Pass 1 — recompute the gates.** Surface-form concentration, length balance,
template and wording spread, subtype and metadata coverage, answer collisions,
signature completeness, label balance inside every stratum. Say whether your
numbers match the author's; a mismatch is itself a finding.

**Pass 2 — verify every derived answer,** independently.

**Pass 3 — read every row**, working through `scripts/review_checklist.py`.

## Your verdict

Exactly one of **`PASS`**, **`FIX`**, **`ADJUDICATE`**, written to
`data/<batch>/review_responses.jsonl`.

Report format: verdict first, then **what passes** — explicitly, so the author
does not churn on what is already right — then one section per defect with the
rule cited and a suggested repair.

**Fixes go into the generator, never into the emitted rows.** Hand-edited JSONL
drifts from its generator and silently reverts on the next run.

---

# 6. If you use a coding agent

Fine, with two boundaries.

**An agent review is not a review.** An agent critiquing another agent's rows
improves the draft and catches real defects. It is not the human label review §5
describes, and a batch reviewed only by agents **must not** be recorded as
reviewed. `review_responses.jsonl` stays empty until a person fills it.

**`verification.status` is a claim about that review.** A draft nobody has read
records `unverified_draft` with a null verifier. The validator accepts that state
precisely so an honest draft need not assert a review that never happened. If you
find yourself writing `verified` to make a check pass, stop.

*Owner-specific, skip unless you use the same setup.* Practical notes for driving
an agent in tmux: create `/tmp/tmux-$(id -u)` mode 700 first; the composer does
not always submit on Enter, so capture the pane after sending and look for a
queue prompt; put anything longer than a few lines in a file and send a short
pointer.

---

# 7. Failure modes we have already hit

Named because they recur, and because no gate detects any of them.

**Self-neutralising attack.** An MO that carries a payload *and* tells the model
to disregard it. The signature fires only when the model **disobeys**, so the row
measures nothing.

**Absurd falsehood.** A PFM wrong in a way any competent solver catches at once,
typically false arithmetic over stated values. It tests recomputation, not update
handling.

**Incoherent implied answer.** A wrong branch arithmetically derived but
impossible in the task's units — a fractional count of discrete things. It tests
"notices an impossible value".

**Answer collision.** One value serving as both a correct answer and a
wrong-branch value inside a quartet. A model that has learned only "the salient
alternative here" scores well without engaging.

**A grader written for one surface form.** **Ten times** here a tool scored
confidently and wrongly because it was validated against the format that happened
to occur first — a regex that could not read nested braces, a plan splitter that
handled one separator, a collision check that sorted tokens instead of actions, a
scalar grader pointed at plans, an answer comparison that called `\boxed{1.00}`
unequal to `1` and `\boxed{B}` unequal to `\text{(B)}`, a plan parser that
read `\rightarrow` as part of an action name and collapsed a four-action plan to
one, and then four more while screening smoke-100:

- `grade_plans.grade()` consulted only its hand-written `CHECKS` table and never
  called `checker_from_spec`, so every source outside that table graded `False`.
  It now builds a checker from `solver_params` and **raises** where it has none —
  a missing checker must not be reportable as a model failure.
- `\texttt{pkg1}` survived as the literal token `texttt{pkg1}`.
- `\begin{aligned}` parsed as the plan's first action, so every plan using that
  environment failed at step 1.
- `&` alignment tabs, `\_` escaped underscores (`truck\_lis` → `truck _lis`) and
  inline step numbers each fused into the following action name.

Every one of them reported a *correct* model answer as a failure.
**Make any tool reproduce a known-good case before trusting its verdict.**

When you widen a grader to accept a spelling, widen it *narrowly and by name*.
Stripping braces wholesale would have made `\frac{1}{16}` and `\frac{11}{6}`
compare equal — turning a grading miss into a grading lie, which is worse.

**A rule surface not wired to the rules.** This document once drifted three
contract versions behind. That is why the reviewer's questions now live in one
hash-locked file, and why this document points rather than restates.

---

# 8. Checklist

**Before authoring**

- [ ] Read §1's documents, including `scripts/review_checklist.py`
- [ ] Every assigned source is `screening.status: passed`
- [ ] For each source: read the `consequence_note` and confirmed it, or — where
      `consequence_status` is `not_authored` — derived and recorded one

**While authoring**

- [ ] One VM, TNM, PFM, MO per source — no exceptions
- [ ] Every answer derived by a solver that first reproduced the pinned gold
- [ ] `syntactic_form` declared and varied; no colon-prefixed openers
- [ ] No row refers to its own status as an update
- [ ] Signatures point at obedience; three branches where required

**Before handing over**

- [ ] `make validate` and `make batch-audit` run, results recorded
- [ ] You answered every `review_checklist.py` item for your own rows
- [ ] No quartet has a repeated answer, gold included
- [ ] `verification.status` is `unverified_draft` with a null verifier

**As reviewer**

- [ ] Recomputed the gates with your own code; did **not** run the author's audit
- [ ] Verified every derived answer independently
- [ ] Read every row against the checklist
- [ ] Verdict is exactly `PASS`, `FIX` or `ADJUDICATE`, in `review_responses.jsonl`
- [ ] Fixes went to the generator, not the rows

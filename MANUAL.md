# Manual — supervising agents on your workload

You have 20 source problems and 80 rows to produce. You will almost certainly
drive an agent to write them. This page is about **that job** — briefing an
agent, catching what it gets wrong, and knowing which parts you cannot delegate.

**`workflow.md` is written for your agent, not for you** — hand it over as the
agent's instructions; §0 there is the agent's list of things it must never do.
For the rules, `generation_rules.md`.
This is about how to work when the thing doing the typing is confidently wrong
several times a day.

Everything below is evidence from this repository, not general advice. The
counts are real.

---

## 1. The division of labour

Agents are strong at some of this and structurally unreliable at the rest. The
split is not about difficulty — it is about **whether a mistake announces
itself**.

| Delegate freely | Because |
| --- | --- |
| Writing solvers and generators | output is checkable against a pinned answer |
| Running gates, reading failures, fixing to green | the gate is the judge, not the agent |
| Recomputing another person's numbers | disagreement is the signal, and it is mechanical |
| Restructuring, renaming, deduplicating | `git diff` shows everything |

| Do not delegate | Because |
| --- | --- |
| **Choosing which consequence a PFM falsifies** | an agent will pick one, be wrong about a third of the time, and be fluent about it |
| **Deciding a row is scoreable** | "accepting leaves exactly one answer" is a judgement, and a wrong call fails silently |
| **Signing off a review** | see §5. A batch reviewed only by agents is not reviewed |
| **Judging whether an update reads as plausible** | the one thing here with no executable test |

The rule underneath: **delegate anything with a pinned answer to compare
against; keep anything whose failure is invisible.**

## 2. Briefing an agent

Do not paste the task. Point it at the repository in order and make it report
before it writes. A brief that has worked:

```
workflow.md is YOUR instructions — it is written for you, not for me.
Read, in this order:
  1. workflow.md       (your procedure. §0 is your boundaries. Start there)
  2. generation_rules.md §2 for the class you are writing — not all of it
  3. scripts/review_checklist.py  — RUN it; those are the questions we will be asked
  4. data/smoke_20/semantic_rows.jsonl — 80 finished rows; copy how fields are filled

Do NOT read archive/. Its rules were overturned.

My assignment: data/smoke_100/contributors/<me>/assigned_source_groups.jsonl
20 sources, one quartet each, 80 rows.

Report at workflow.md §6's three checkpoints: after reading, after five
sources, and at handover. Before you write anything: tell me what you found,
and anything in generation_rules.md you think is wrong.

Then: write scripts/author_smoke_100_<me>.py emitting to
data/smoke_100/contributors/<me>/semantic_rows.jsonl.
Derive every answer by executing a solver that reproduces the pinned gold FIRST.
Stop and report after 5 sources. Do not do all 20 before I look.
```

Three things that brief is doing deliberately:

- **"Report before you write."** An agent that has read the contract will tell
  you something surprising about it. One that hasn't will start typing.
- **"Stop after 5."** Twenty sources of wrong is twenty sources to redo. Five is
  a sample you can actually check.
- **"Anything you think is wrong."** The contract has been amended 26 times,
  several because an author pushed back. This is not politeness.

## 3. The seven ways an agent fails here

Each of these has happened. The check is what catches it — reading the output
does not.

**1. Confident wrong mathematics.** Four errors in one session of authoring 37
derivations: claiming `x⁴+4` is irreducible over ℤ (it factors — Sophie Germain),
using `(a×c)/|a|²` for a minimum-norm solution when it is `(c×a)/|a|²` (every
sign flipped), and treating `8^(2/3)` as `< 4` because IEEE doubles return
`3.9999999999999996`.
→ **Check:** make it compute the **gold** answer too, and compare that to the
pinned one. Three of the four errors came out as a gold answer that did not
match. The fourth was different — gold was right, and the *falsification* left
the answer undefined — so also make it **run the falsified branch**, not assert
it. A function is the cheap way (the pilot's are 5–21 lines, median 10, and
agent-written) because the gold check then transfers to the counterfactual for
free, but the agent working it out is fine if it does both checks. It is **two
numbers per source**, not four: the VM answer and the PFM accepted-false answer.
TNM and MO reuse the pinned original.

**2. A tool written for one surface form.** **Ten** times a grader here scored
confidently and wrongly, and *every one reported a correct answer as a failure*:
a regex that could not read nested braces, a plan splitter that handled one
separator, `\boxed{1.00}` compared unequal to `1`, `\texttt{pkg1}` surviving as
the token `texttt{pkg1}`, `\begin{aligned}` parsed as the plan's first action.
→ **Check:** make any tool reproduce a known-good case before believing its
verdict. And when you widen it to accept a spelling, widen it *narrowly and by
name* — stripping braces wholesale made `\frac{1}{16}` and `\frac{11}{6}` compare
equal, turning a grading miss into a grading lie.

**3. A check that only ever passes.** A predicate exercised on one branch
confirms whatever you already believe. A vocabulary check landed in the wrong
function and silently validated nothing; it looked fine because everything
passed.
→ **Check:** for every check the agent writes, make it **fail on purpose** once.
If it cannot be made to fail, it is not a check.

**4. Turning a narrow finding into a batch-wide field.** Twice in one session: a
real observation about a handful of sources became a field on all 100, which then
recorded *which pipeline a source came through* while reading as a property of
the source.
→ **Check:** ask "how many sources does this actually distinguish?" A field that
is the same on 19 of 20 is noise wearing a schema.

**5. Silently dropping a branch mid-rewrite.** During a refactor an agent
replaced a function and quietly lost its special-case branch. Seven records then
asserted the opposite of the evidence sitting beside them.
→ **Check:** after any rewrite, verify the *behaviour* that mattered, not that
the file compiles.

**6. Stamping work as verified.** The recurring temptation is
`verification.status: verified` to make a check pass. The contract accepts
`unverified_draft` with a null verifier **precisely** so an honest draft need not
lie.
→ **Check:** grep the diff for `verified`. If it appears and no person read the
rows, that is the defect.

**7. Fabricating your approval.** Sub-agents in this session produced reports
saying *"Registering your call"* and *"Owner decision, same date"* about
decisions the owner had never made, and wrote them into a repository document.
→ **Check:** if an agent tells you that you decided something, you did not.
Anything attributed to you that you do not remember saying is invented.

## 4. How to check agent output without redoing it

You cannot re-derive 80 rows. You do not have to. Ask for **evidence that
executes**, and then run it.

- **Every number traces to a function that ran.** Rows record `solver`,
  `gold_derivation`, and `original_answer_reproduced`. If a number cannot be
  traced to code, it does not belong in a row.
- **Check which of your sources already have a solver.** Not all do, and the
  difference matters: `admission_evidence.solver.available` is `true` on 67 of
  the 100 sources and `false` on 33. Of those 33, **13 have no executable
  evidence at all** — their gold answer is pinned from the upstream snapshot and
  nothing has ever independently reproduced it, so your agent is the first to
  solve them. Where a solver exists, tell the agent to **reuse it** rather than
  write a second one that may quietly disagree:

  ```bash
  python3 -c "import json;[print(r['stable_source_id'],
    r['admission_evidence']['solver']['available'])
    for r in map(json.loads, open('data/smoke_100/contributors/<you>/assigned_source_groups.jsonl'))]"
  ```
- **Ask for the falsified branch too.** `substitute_and_solve: unique_solution`
  is the claim that accepting the falsehood leaves exactly one answer. Make the
  agent *run* it. Two defects in this session were rows that could not be scored
  at all — one crashed, one left the answer unchanged — and only executing the
  wrong branch revealed either.
- **Read three rows properly, not eighty badly.** Pick one per class. Work
  `scripts/review_checklist.py` on each. Every real defect found in this project
  came from reading rows, not from a threshold.
- **Make the agent state what it did *not* check.** "Not-tested" is the most
  informative line in any agent report, and the one it will omit unless asked.

## 5. Using an agent as your reviewer

You review the person to your right (`P1 → P2 → P3 → P4 → P5 → P1`). You may use
an agent for it. Two boundaries make the difference between review and theatre.

**Do not let it run the author's audit script.** It encodes the author's beliefs
about what is being checked; passing it proves only that they were
self-consistent. Have it **recompute every gate from the raw rows with its own
code**. When the numbers match, the audit has earned trust. A mismatch is itself
a finding.

**An agent review is not the review.** It improves the draft and it catches real
defects — in this session an independent agent found six things the author's own
2,000-check self-test had passed, including a planning instance whose initial
state was impossible. That is worth a lot. It is still not the human review
`DATASET.md` §7 describes, and `review_responses.jsonl` stays empty until a
person fills it.

**Two agents disagreeing is the most useful signal you can buy.** Have your
reviewer agent argue with the author's conclusions rather than confirm them, and
bring the disagreements to the author as questions, not verdicts. Four adversarial
passes in this session each found real defects in what the previous pass had
approved.

## 6. Things an agent will tell you that are not true

- *"All gates pass."* Often true and nearly meaningless — the gates are
  mechanical. The semantic defects are what matter and no gate sees them.
- *"Verified."* Ask what was executed. If the answer is "the code compiles" or
  "the checks pass", nothing was verified.
- *"You approved this."* See §3.7.
- *"This is a minor fix."* The `8^(2/3)` float artifact and a plural typo in a
  shape name were both one-character issues; the second silently disabled a hard
  rule the contract had been amended twice to add.
- A number with no derivation beside it. Ask where it came from. Every time.

## 7. When to stop the agent and do it yourself

- It has failed the same check twice and is now editing the check.
- It is proposing a schema change to fit one source.
- It says a source is unusable. It might be right — but that is your call, and an
  unscoreable row is worse than a missing one.
- You have stopped reading its reports carefully. That is the real failure point;
  an unread report is worse than no report, because it feels like oversight.

## 8. What you cannot delegate, restated

Two things, and they are the two the whole design rests on:

1. **Whether a row is scoreable** — whether incorrect handling produces something
   observably different from correct handling. Three of the four classes fail
   this by default, because for them the correct answer *is* the original answer.
2. **Whether the review happened.** `verification.status`,
   `screening.consequence_confirmed` and `review_responses.jsonl` are claims
   about a person. An agent filling them in is the one defect that makes the
   dataset worthless rather than wrong.

## 9. Where things are

Only what you need to point an agent at.

```
generation_rules.md     THE ROW CONTRACT. Rank 1
workflow.md             the procedure
scripts/review_checklist.py   run it; the questions your reviewer asks
scripts/validate_dataset.py   the contract, executable
scripts/planning_domains.py   planning solvers (blocks, logistics, BFS, execute)
data/smoke_100/contributors/<you>/assigned_source_groups.jsonl   your 20 sources
data/smoke_20/semantic_rows.jsonl   80 finished rows — the worked example
archive/                DO NOT READ. Its rules were overturned
```

```bash
./init.sh                                     # the full gate
python3 scripts/review_checklist.py           # the questions you will be asked
make validate    BATCH_DIR=data/smoke_100     # row-level, rank 1
make batch-audit BATCH_DIR=data/smoke_100     # batch-level gates
```

Authority order, and getting it backwards has caused a real error here:
`generation_rules.md` + `schema/` + `validate_dataset.py`, then `DATASET.md`,
then `converged_paper_plan.md`, then `docs/`. The validator is the **executable**
form, so a schema-only change is inert.

## 10. What is true about this batch right now

Tell your agent this; it will otherwise assume otherwise.

- **Nothing has been reviewed by a person.** `unverified_draft` on all 100
  sources, `consequence_confirmed` false on all 100, no `review_responses.jsonl`.
- **Screening established one thing**: the model solves each base task with no
  update. That a *particular* falsifiable target works is yours to establish.
- **The inference stack is not reproducible at a fixed seed** — an identical
  re-run produced 0 of 10 identical traces. Report medians and ranges; never
  treat repeated rollouts of one row as independent observations.
- **Answer-only grading is invalid — and every grader here is answer-only.**
  For three of the four classes the correct answer *is* the original answer, so
  engagement has to be resolved (never-noticed / detected-and-rejected /
  accepted) before any rate means anything. **That grader does not exist yet**,
  nor does the LLM judge the plan specifies. We are in the data-generation stage
  and the evaluation half is deliberately unbuilt. Practical consequence for you:
  `no_update_solved` in a run package means *the model solved the base task* and
  nothing more. Do not let an agent report an acceptance or resistance rate from
  the current tooling — it cannot compute one.

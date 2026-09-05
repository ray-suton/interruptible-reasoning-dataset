# Dataset Overview and Design

What this dataset is, what a row means, where sources come from, and how work is
reviewed.

**Row-level mechanics are not here.** `generation_rules.md` is the row contract —
the four classes, required fields, thresholds, signatures, gates — and
`scripts/validate_dataset.py` is its executable form. This document explains the
design those rules implement. If the two disagree, `generation_rules.md` and the
validator win.

---

## 1. The question

An LRM is part-way through a reasoning trace when an update arrives. Should it
accept it?

That is a normative question, and it is what separates this dataset from prior
interruption work, which asks whether models *notice* an interruption. Here every
update has a correct disposition, and the model is scored on whether it reaches
it.

The Stage 1 decision is binary:

- **`ACCEPT`** — the update should influence the reasoning
- **`DO_NOT_ACCEPT`** — it should not

Binary is deliberate. It matches how a person actually works — a true but
immaterial note gets accepted and used to check the work; a false claim gets
rejected, sometimes after being checked first — and it is the form a linear probe
over hidden states can be trained against.

## 2. Four classes over two labels

The two labels decompose into four diagnostic classes, and the decomposition is
the point: it lets a wrongful acceptance be attributed to a cause rather than
merely counted.

| Class | Label | The update is | Correct behaviour |
| --- | --- | --- | --- |
| `valid_material` (VM) | ACCEPT | an authorized change to the **premises** | revise the task state and re-solve |
| `true_non_material` (TNM) | ACCEPT | a true statement about the **consequences** | use it as a check; answer unchanged |
| `plausible_false_material` (PFM) | DO_NOT_ACCEPT | a false statement about the **consequences** | reject it; answer unchanged |
| `malicious_override` (MO) | DO_NOT_ACCEPT | not about the task at all | refuse; answer unchanged |

The premises / consequences split is what makes the labels principled rather than
stipulated. A user owns the premises and may change them, so VM is authorized by
definition. **Nobody owns entailment** — no assertion by anyone makes a false
consequence true — so PFM is unauthorized necessarily, not by convention. TNM and
PFM therefore share a target space and differ only in truth value, which makes
them natural twins.

## 3. Why grading is hard here

**Answer-only grading is invalid.** For three of the four classes the correct
answer *is* the original answer. So an unchanged answer is produced both by a
model that correctly resisted an update and by one that never read it. The two
are indistinguishable at the answer level.

This is why every row in those three classes carries a **behaviour signature**
recording what incorrect handling would observably produce — a wrong scalar, a
structural property of the answer or plan, or trace evidence of engagement. A row
whose incorrect handling looks identical to correct handling is not authorable.

A second consequence: **a surface leak is fatal, not cosmetic.** If the class is
predictable from an update's phrasing, a probe can score well by encoding
phrasing and never touch the decision — and no ablation on the probe detects
that, because the leak is in the data. Hence the diversity requirements in
`generation_rules.md` §3.

## 4. What a row records, in outline

Beyond the update text and the labels, each row carries:

- **authority** — may this update modify or clarify the task?
- **relation to prior state** — does it agree with, supersede, contradict, or not
  address the existing task state?
- **evidence status** — what the evidence *available to the model* warrants.
  Never author-known truth, and never authority. Recording author truth would
  teach acceptance of unverifiable claims, which is the failure the dataset
  exists to measure.
- **the factor block** — speech act, update operation, checkability, relevance,
  operational action, task consequence. These are the variables the research
  question is stated in terms of; without them the rows cannot answer it.
- **a behaviour signature**, for the three classes that need one.
- **a run reference** rather than an embedded trace, because reasoning prefixes
  are model- and run-specific.

Exact field names, allowed values and thresholds: `generation_rules.md` §2 and §4.

## 5. Sources and provenance

Every source problem has a selection record before it can become a row, holding
a stable ID, dataset and revision, content hash, licence status, domain and
family, provenance note, import status, gold answer reference, and admission
status.

Two admission criteria, both required:

1. **The target model solves the base task with no update.** Otherwise a failure
   cannot be attributed to update handling. This makes an easy source a *control*,
   not a weakness.
2. **The source has a derivable non-determined consequence to falsify.**
   Otherwise it cannot host a PFM, and every source must host all four classes.

Screening measures both before any row is authored. Sources come from pinned
snapshots or reviewed imports only — never ad hoc lists. If source text is not
redistributable, keep the metadata and derived artifacts and leave the text out;
store locators and hashes instead of copying statements into the data root.

`docs/source_import_policy.md` governs when competition text may be imported.

## 6. Data boundaries

Three kinds of information stay separated: **source facts** (statements, imported
metadata), **derived evidence** (gold answers, hashes, validator transcripts,
rationales), and **rows** (the examples used for evaluation or training).

- one source group stays within one split or fold
- matched variants stay tied to their source group
- development and held-out template families stay disjoint
- primary rows and robustness rows are recorded separately

GitHub has no per-folder access control, so **primary-test row content must not
enter the shared checkout before the model, prompts, probe layer, threshold and
evaluation code are frozen and hashed.** After that recorded freeze, test rows may
be constructed and reviewed in the shared repository, followed by a one-shot
evaluation with no retuning against the result.

That freeze is a **separate, later event** from the authoring-contract lock. Do
not conflate them.

## 7. Review

Every authored row is reviewed by someone who did not author it. The reviewer
confirms the source record and gold reference, re-derives the label without
reading the author's label first, checks admissibility under the authority model,
verifies material updates against the new gold answer, verifies answer-preserving
updates preserve it, and returns exactly one of **`PASS`**, **`FIX`**,
**`ADJUDICATE`**.

**An agent review is not a dataset review.** Two agents in an author/reviewer
split improve a draft and catch real defects, but that is not the human label
review this section describes. A batch reviewed only by agents must not be
recorded as reviewed, and `review_responses.jsonl` stays empty until a person
fills it. `workflow.md` documents the agent procedure and states this boundary.

`verification.status` is a claim about that review. A draft nobody has read
records `unverified_draft` with a null verifier. The validator accepts that state
precisely so an honest draft does not have to assert a review that never
happened.

## 8. Review order for a batch

1. Screen candidate sources against both admission criteria.
2. Record the selection with provenance and screening results.
3. Generate no-update traces; export them as a run package.
4. Author rows against the screened sources.
5. Run the validator and the batch audit.
6. Hand the batch to an independent reviewer.
7. Resolve `FIX` items — in the generator, not the emitted rows.
8. Open the PR once the review status is settled.

## 9. Branches

Branch `<batch>/<short-scope>`, PR title `<Batch>: <short scope>`. One branch per
generation or review scope. Do not expand source selection, generation and review
scope silently. If a fix changes rows someone else authored or reviewed, say so in
the PR.

# Interruptible Reasoning Dataset

The construction surface for the Stage 1 binary update-acceptance dataset, and
for the two contributions built on it: an evaluation framework for mid-reasoning
update handling, and a linear probe separating `ACCEPT` from `DO_NOT_ACCEPT` from
hidden states.

A row pairs a source problem, a run-referenced reasoning prefix, and an update,
with a binary disposition and a behaviour signature recording what incorrect
handling would observably produce. The trace itself stays in a per-model run
package rather than being embedded in the row. That signature is what makes the three
answer-preserving classes measurable: for them the correct answer is the original
answer, so answer-only grading cannot separate correct resistance from
inattention.

The row contract is `generation_rules.md`, machine-enforced by
`scripts/validate_dataset.py` and hash-locked (version in
`registry/contract_lock.json`). `DATASET.md` holds
the design rationale, `converged_paper_plan.md` the plan, `workflow.md` the
authoring and review procedure.

Everything active uses only the Python standard library. This is intentional.

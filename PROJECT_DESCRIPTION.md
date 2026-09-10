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

Working snapshot, 2026-09-07: the `multipl-updates` checkout is refining 40
single-update components over 10 sources; sequence composition is not built.
The generator reproduces those draft rows byte for byte, and their mechanical
checks pass under this branch's contract v27. Surface leakage and independent
review remain unresolved. The locally recorded `main` branch has contract v30;
P1's separate 80-row smoke-100 draft lives on `P1-smoke-100-rows`. These branch
states must not be treated as one verified batch. See
[the inspection report](.omx/reports/task-2026-09-07-103031.md) for evidence,
current limitations, and the next step.

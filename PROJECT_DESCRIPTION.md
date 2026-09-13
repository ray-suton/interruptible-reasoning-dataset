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

Working status, inspected 2026-09-11: `data/smoke_100/` assigns 100 sources to
five contributors for 400 intended rows; the paper plan's 80-source smoke count
is stale. P1's 80-row slice and generator were retired to
`archive/pre_v35_regen_2026-09-11/`. The remaining smoke-20 pilot fails the current
row and batch gates. Evaluation and probe readiness must not be inferred from
the older completion claims. Inspection evidence is recorded in
`.omx/reports/task-2026-09-11-191650.md` (UTC).

Contract v40 and the v38 batch, 2026-09-14: `data/smoke_20_v38/` is the active
batch. P1 is authored — 20 sources at 5 GSM8K / 5 MATH500 / 5 BlocksWorld /
5 Logistics, 80 rows, 44/44 gates, surface classifiers below chance (four-way
0.175, binary 0.4875). P2–P5 are assigned 20 sources each on the same
composition, with frozen prefixes generated under the baseline system prompt
recorded at `registry/baseline_system_prompt.json`. Planning sources are imported
from PlanBench (`sources/planbench/`, revision-pinned); six are recorded
mechanical derivations admitted by §8.0a. The pre-v38 batches are retired to
`archive/retired_pre_v38_2026-09-13/` — their composition, planning provenance and
prefix conditioning all fail v38.

**Not established:** no row has been reviewed by a person (all `unverified_draft`
with a null verifier), and the batch has never been replayed — every number above
is an authoring gate, not behaviour. `plan.md` carries the state and next steps.

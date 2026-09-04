# Converge Paper Plan: Evidential Update Handling During Reasoning

Status: working final for discussion  
Owner: P1 / Rui Gao  
Created: 2026-08-28  
Relation to existing plans:

- Stage 1 remains the measurement foundation: binary selective update acceptance,
  behavior-identifiable grading, and the locked row contract.
- The broad parent `../STAGE2_PLAN.md` becomes the follow-on roadmap.
- This converge plan is the main-conference target between them: not just a
  benchmark paper, not the full Stage 2 research program.

## Decision

The paper should converge on one central claim:

> Reasoning models mishandle in-flight updates according to the update's
> authority, evidential support, and relation to the current task state;
> behavior-identifiable evaluation exposes the failure, and factorized
> evidence/relevance/action supervision improves the accept-resist tradeoff
> more robustly than flat action imitation.

This is the version to build toward unless later pilots falsify the causal or
training claims.

## Grounding In Existing Plans

- `docs/original/STAGE1_PLAN.md:59` defines Stage 1 as the binary question:
  whether an update should influence reasoning.
- `docs/original/STAGE1_PLAN.md:107` points row validity to the locked contract:
  `DATASET.md`, `schema/`, and `scripts/validate_dataset.py`.
- `docs/original/STAGE1_PLAN.md:151` frames the benchmark and evaluation method
  as a contribution, especially behavior-identifiable grading.
- `docs/original/STAGE1_PLAN.md:163` frames the linear gate/probe as a narrow
  diagnostic/control contribution.
- `docs/original/STAGE1_PLAN.md:188` records the current 238-group / 1,736-row
  target and explicitly says sizing is under review.
- `../STAGE2_PLAN.md:22` proposes cause, intervention, and mechanism as the
  three main-conference contributions.
- `../STAGE2_PLAN.md:57` says Stage 2 should reuse Stage 1 instrumentation but
  answer a different question.
- `../STAGE2_PLAN.md:121` factorizes update handling into evidence, relevance,
  and action.
- `../STAGE2_PLAN.md:412` starts the causal behavioral study.
- `../STAGE2_PLAN.md:716` starts the training intervention.
- `../STAGE2_PLAN.md:1096` starts representation analysis.
- `../STAGE2_PLAN.md:1539` defines decision gates.
- `../STAGE2_PLAN.md:1670` gives the broad main-conference contribution
  hierarchy.

## Requirements Summary

The converge paper must satisfy four requirements.

1. Preserve the Stage 1 binary gold gate.
   - Gold label remains `ACCEPT` / `DO_NOT_ACCEPT`.
   - `ignore` and `reject` are behavior/action outcomes, not the primary gold
     ontology.

2. Be larger than a benchmark-only workshop paper.
   - The paper must include a causal explanation attempt and an intervention.
   - A dataset plus descriptive failures is not enough for the target.

3. Be smaller than the full Stage 2 plan.
   - No full seven-class paper headline.
   - No full grid over all interruption positions.
   - No mandatory activation steering.
   - No preference optimization unless everything else is already solid.

4. Keep all claims behavior-identifiable.
   - Do not score rejection as merely "answer unchanged."
   - Every row where behavior ambiguity matters must carry a signature or trace
     engagement criterion.

## Research Questions

RQ1. Which update properties cause wrongful acceptance during ongoing reasoning?

Primary factors:

- authority status;
- relation to prior task state;
- evidence status / checkability;
- speech act: proposition versus directive;
- verification cost.

RQ2. Can supervision improve update handling without collapsing into blind
rejection?

Primary comparison:

- prompt-only;
- flat action SFT;
- factorized evidence/relevance/action SFT.

RQ3. If behavior improves, what changed internally?

Probe targets:

- gold admissibility;
- model behavior;
- evidence status;
- relevance;
- action.

## Contribution Stack

### Contribution 1: Behavior-Identifiable Benchmark And Evaluation

Use Stage 1 as the measurement foundation:

- binary gold gate;
- matched source groups;
- answer-form and answer-equivalence requirements;
- wrong-branch signatures;
- trace engagement labels;
- no-update solvability stratification.

This contribution earns the right to measure the phenomenon.

### Contribution 2: Causal Characterization Of Wrongful Acceptance

Run controlled minimal pairs that manipulate:

- evidence present versus absent;
- proposition versus directive;
- low versus high verification cost.

Primary outcome:

```text
P(wrongful acceptance)
```

The causal claim should be paired and source-family level, not just aggregate
correlation.

### Contribution 3: Factorized Supervision

Compare flat action imitation with factorized supervision.

Flat:

```text
update -> action -> continuation -> final answer
```

Factorized:

```text
update -> evidence status -> relevance -> action -> continuation -> final answer
```

The key claim is OOD transfer, not IID benchmark accuracy.

### Contribution 4: Representation Explanation

Use probes before and after SFT to test whether improvement is:

- better use of an existing representation;
- a newly learned/sharpened evidence representation;
- a broader geometry change.

This is explanatory support. It should not become a separate probe paper unless
the result is unusually clean.

## Benchmark Scope

### Primary Gold Gate

The primary label remains:

| Gold label | Meaning |
| --- | --- |
| `ACCEPT` | The update may influence task reasoning under the benchmark authority model. |
| `DO_NOT_ACCEPT` | The update must not influence task reasoning. |

Behavioral outcomes are recorded separately:

| Behavior outcome | Meaning |
| --- | --- |
| `accepted` | Model incorporated the update into task reasoning. |
| `detected_and_rejected` | Model noticed and actively resisted an invalid update. |
| `detected_and_not_used` | Model noticed but did not use an irrelevant or non-actionable update. |
| `observably_engaged` | For TNM, model explicitly used or acknowledged the update according to its hint level. |
| `observably_rejected` | For TNM, model explicitly rejected an admissible supported update. |
| `not_demonstrated` | For TNM, the trace gives no observable evidence either way; do not force silence into success or failure. |
| `never_noticed` | For invalid or material rows, model produced an unchanged answer without evidence of engagement. |
| `partially_used` | Model used the update transiently or inconsistently. |
| `no_final_answer` | Continuation cannot be scored for final task outcome. |

### Primary Update Classes

Keep the four Stage 1 classes as the core score:

| Class | Gold label | Role |
| --- | --- | --- |
| `valid_material` | `ACCEPT` | Tests whether models accept authorized revisions to mutable task state. |
| `true_non_material` | `ACCEPT` | Tests supported, task-near, answer-preserving context with explicit hint strength. |
| `plausible_false_material` | `DO_NOT_ACCEPT` | Tests rejection of unauthorized, contradicted task-near claims. |
| `malicious_override` | `DO_NOT_ACCEPT` | Tests resistance to task bypass or invalid authority. |

Add a limited relevance-control slice, but do not let it become the headline:

| Control stratum | Gold gate | Use |
| --- | --- | --- |
| `true_irrelevant_control` | `DO_NOT_ACCEPT` for task-use | Tests relevance without falsehood. |
| `false_irrelevant_control` | Optional | Include only if behavior is identifiable. |

Rationale: the main binary benchmark needs task-near updates. The factorized
training claim needs some relevance variation. A small control slice gives that
without expanding into the full seven-class Stage 2 taxonomy.

## Domains

### Required Domains

1. Math
   - Role: exact symbolic and numeric reasoning.
   - Strength: clean scalar/expression answers and controlled false updates.
   - Risk: many hard sources fail no-update solvability.
   - Gate: select only source tasks meeting the no-update solvability threshold.

2. Planning
   - Role: state/action reasoning and structural signatures.
   - Strength: strongest domain for behavior-identifiable state-change updates.
   - Risk: plan equivalence and natural-language plan grading can be messy.
   - Gate: require explicit primitive-action representation or validated plan
     equivalence.

3. Code-lite
   - Role: executable OOD and intervention test.
   - Strength: tests can verify final behavior.
   - Risk: tooling, runtime, and test adequacy can dominate the paper.
   - Gate: keep compact; include only tasks with runnable tests and clean
     source/import status.

### Excluded From Main

Open trivia should not be a main domain. It is too memory-heavy and too hard to
distinguish task evidence from model prior knowledge.

Closed-world MCQ may be used later as a small appendix diagnostic if the passage
or stem contains all evidence needed to judge the update. It is not part of the
core converge paper.

## Target Dataset Shape

These are planning numbers, not yet a locked contract.

### Human-Reviewed Evaluation Set

Target:

```text
60 source families
  24 math
  24 planning
  12 code-lite
```

Core rows:

```text
60 families x 4 primary update classes = 240 rows
```

Relevance controls:

```text
30 families x 1 true_irrelevant_control = 30 rows
optional false_irrelevant_control only if scoreable
```

Causal minimal pairs:

```text
30 matched families x 4 cells = 120 rows
```

Consequence-structure validation arm:

```text
10 of the causal families x 4 additional consequence-implying variants = 40 rows
```

Expected reviewed evaluation size:

```text
390-450 semantic rows
```

This is large enough to support a main paper if the rows are high quality,
paired, and behavior-identifiable. It is much smaller than a full Cartesian
Stage 2 grid.

### Training Set

Use a separate training-only pool.

Target:

```text
1,500-3,000 generated rows
```

Rules:

- training rows may be generated with templates and model assistance;
- evaluation rows must be independently reviewed;
- training sources and evaluation sources must not overlap;
- training templates and causal-test templates should be held out from each
  other where feasible;
- training rows still obey the Stage 1 scoreability contract.

If data production is slower than expected, use fewer training rows and make the
paper's main training claim narrower.

## Causal Design

Primary matched-pair design:

| | Proposition | Directive |
| --- | --- | --- |
| Evidence present / checkable | A | B |
| Evidence absent / unresolved | C | D |

Hold fixed:

- source task;
- intended wrong consequence;
- update length;
- tone;
- numeric content;
- interruption position;
- answer format;
- source-task solvability.

Primary estimands:

```text
checkability effect
directive effect
checkability x directive interaction
```

Verification-cost secondary design:

```text
depth 0: direct contradiction
depth 1: one-step computation
depth 2: short derivation
depth 3+: multi-step verification
unavailable: no task evidence can settle it
```

Keep verification cost secondary unless it is the cleanest observed effect.

## Training Intervention

### Models

Primary training target:

```text
one 7B-8B open reasoning/instruction model
```

Do not make multi-family training mandatory. Use additional models for
behavioral evaluation if compute allows.

### Conditions

Required:

1. base model;
2. prompted verification;
3. flat action SFT;
4. factorized evidence/relevance/action SFT.

Optional:

- curriculum SFT;
- preference optimization;
- full fine-tuning instead of LoRA;
- multi-seed training.

### Primary Success Criterion

Factorized SFT must improve the accept-resist frontier relative to flat SFT.

Equivalent acceptable evidence:

- higher invalid-update rejection at matched valid-update acceptance;
- higher valid-update acceptance at matched invalid-update rejection;
- better OOD transfer on at least one strong holdout axis without no-update
  reasoning regression.

No-update task accuracy must not regress by more than a predeclared threshold.
Suggested threshold:

```text
<= 5 percentage points absolute regression
```

## Representation Analysis

Required if training works:

- probe base model;
- probe flat SFT;
- probe factorized SFT;
- compare at P1, immediately after update ingestion;
- include text-only and update-only baselines.

Required interpretability gates:

1. probe beats bag-of-words or sentence-embedding update-text baselines;
2. `task + r_<t> + update` beats `task + update`;
3. leave-source-task-out performance remains meaningful.

If these fail, report probes as negative evidence and do not claim internal
mechanism.

Activation steering is explicitly out of scope for the converge paper unless
everything above is already complete and the probe direction is stable.

## Paper Outline

1. Introduction
   - In-flight updates require admissibility judgment, not just incorporation.

2. Measurement Foundation
   - Binary gate.
   - Behavior-identifiable evaluation.
   - Why answer-only grading fails.

3. Benchmark And Curation
   - Domains: math, planning, compact code-lite.
   - Four primary update classes.
   - Small relevance-control slice.
   - Source and row validity gates.

4. Baseline Model Behavior
   - No-update capability.
   - Blind accept / blind reject / prompted verify.
   - Failure patterns by evidence status and speech act.

5. Causal Minimal Pairs
   - Evidence support x speech act.
   - Verification-cost analysis.
   - Consequence-structure validation arm.

6. Training Intervention
   - Flat action SFT versus factorized SFT.
   - OOD transfer and accept-resist frontier.

7. Representation Analysis
   - Pre/post probes.
   - Does training change representation, control, or both?

8. Discussion And Limitations
   - Scope of binary gate.
   - Limits of trace access.
   - Code-lite and closed-world QA as future expansion.

## Acceptance Criteria

The converge paper is submission-ready only if all required criteria pass.

### Dataset Criteria

- Every evaluation row passes the Stage 1 validator or a documented extension of
  it.
- Every reviewed row has independent source/gold verification.
- Every behavior-ambiguous row has a valid signature or engagement criterion.
- Binary label agreement reaches a predeclared threshold.
  Suggested minimum: `>= 85%` before adjudication.
- Factor-label agreement reaches a predeclared threshold.
  Suggested minimum: `>= 75%` before adjudication.
- No-update solvability on selected source tasks reaches the threshold for the
  primary model.
  Suggested minimum: `>= 70%`.

### Causal Criteria

- Causal rows are paired by source family.
- The checkability/evidence effect is reported as paired differences, not only
  aggregate rates.
- The effect direction is stable across at least two source domains, or the
  domain interaction is explicitly reported as a finding.
- The consequence-structure arm is run before claiming the causal design explains
  plausible-false benchmark behavior.

### Training Criteria

- Flat and factorized SFT use matched examples, model, optimizer, and steps.
- Token-count differences are reported.
- Factorized SFT beats flat SFT on at least one strong OOD axis or is demoted to
  a negative/diagnostic result.
- No-update task performance regression is reported.
- Valid-update over-rejection is reported, not hidden inside aggregate accuracy.

### Probe Criteria

- Probe target is named: behavior, gold action, evidence status, relevance, or
  action.
- Probe performance is evaluated under leave-source-task-out.
- Probe beats update-text baselines.
- Full-context hidden state beats task-plus-update without reasoning state.

## Implementation Steps

1. Freeze this converge scope after discussion.
   - Output: final plan file, plus a short mapping from broad Stage 2 to converge
     paper versus follow-on work.

2. Copy or rewrite planning docs.
   - Keep this file under `.omx/plans/` during discussion.
   - After agreement, add a repository-visible plan such as
     `docs/original/CONVERGE_PAPER_PLAN.md`.
   - Copy `../STAGE2_PLAN.md` into `docs/original/STAGE2_PLAN.md` only if it is
     clearly marked as follow-on roadmap, not the active paper scope.

3. Extend the schema only if necessary.
   - Prefer adding optional factor annotations without breaking Stage 1 rows.
   - Do not change the locked row contract unless a field is genuinely required
     for validation.

4. Select source families.
   - Filter for no-update solvability first.
   - Keep train/eval source families disjoint.
   - Prioritize math and planning.
   - Add code-lite only after executable verification is confirmed.

5. Build a 20-family pilot.
   - Include all four primary update classes.
   - Include a small causal 2 x 2 subset.
   - Run annotation, validation, and baseline behavior checks.

6. Gate the pilot.
   - If no-update solvability is low, replace sources.
   - If plausible-false rows are not behavior-identifiable, retarget false claims
     at inputs.
   - If relevance controls are ambiguous, keep them out of the main score.

7. Scale to the reviewed evaluation set.
   - Target 390-450 semantic rows.
   - Preserve paired source-family structure.
   - Lock templates and holdouts before model evaluation.

8. Run baseline behavioral evaluation.
   - No update.
   - Blind accept.
   - Blind reject.
   - Prompted verify.
   - Report engagement-resolved outcomes.

9. Run causal analysis.
   - Estimate paired checkability/evidence and directive effects.
   - Report verification-cost trend.
   - Run consequence-structure validation arm.

10. Build training pool.
    - Keep separate from evaluation.
    - Validate scoreability.
    - Hold out templates, operations, and source domains where feasible.

11. Train intervention models.
    - Prompted baseline.
    - Flat SFT.
    - Factorized SFT.
    - Prefer LoRA if compute remains constrained.

12. Evaluate OOD transfer.
    - Template holdout.
    - Operation holdout.
    - Domain holdout if code-lite is ready.
    - Interruption-position robustness on a subset.

13. Run representation analysis.
    - Probe base, flat SFT, and factorized SFT.
    - Include text-only and context ablation controls.
    - Report negative result honestly if controls erase the effect.

14. Write paper around the causal spine.
    - Do not headline dataset size, seven classes, SFT accuracy, or probe AUROC
      alone.
    - Headline the chain from update properties to behavior to intervention to
      representation/control evidence.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Paper becomes too broad | Required scope is four contributions; everything else is optional or follow-on. |
| Paper becomes too small | Include causal minimal pairs and training intervention, not only dataset construction. |
| Code-lite consumes the project | Gate code on runnable tests and keep it compact; demote to OOD/future if tooling drags. |
| Ignore/reject ambiguity returns | Keep binary gold labels and behavior outcomes separate. |
| False-update rows are unscoreable | Use the Stage 1 input-target rule and require accept signatures. |
| Factorized SFT just over-rejects | Evaluate accept-resist frontier and no-update regression. |
| Probes read wording shortcuts | Require text-only baselines, context ablations, and holdouts. |
| No-update solvability is too low | Source selection must filter by primary-model no-update success before annotation scales. |
| Reviewers see the contribution as benchmark-only | Paper structure starts with causal question and intervention, not dataset size. |

## Verification Steps

Before treating this plan as active:

1. Confirm all referenced plan files exist.
2. Decide whether `docs/original/STAGE2_PLAN.md` should be copied as follow-on
   roadmap.
3. Review whether code-lite is required or optional for the target venue.
4. Run `./init.sh` after any repository-visible documentation/schema changes.
5. If the schema changes, run `make contract-check` and update the contract lock
   with a reason.

Before paper submission:

1. Run dataset validation on all train/eval rows.
2. Verify all source/gold evidence and reviewer assignments.
3. Reproduce baseline evaluation tables from saved outputs.
4. Reproduce causal paired analyses from saved semantic-item tables.
5. Reproduce SFT comparison from saved configs/checkpoints.
6. Reproduce probe analysis from saved hidden-state extraction metadata.
7. Confirm paper claims match the strongest verified result, not the intended
   result.

## Stage 2 Follow-On Boundary

The broad parent Stage 2 plan remains valuable, but it should follow this
converge paper rather than define the immediate submission.

Move these to follow-on work unless they become unexpectedly cheap:

- full seven-strata benchmark as the headline;
- full accept / ignore / reject action-policy ontology;
- all four interruption positions across the full dataset;
- broad code/software-maintenance benchmark;
- closed-world MCQ/trivia domain;
- preference optimization;
- activation steering;
- multiple training model families;
- full fine-tuning and multi-seed training if compute is not available.

The follow-on paper can then ask the broader question:

> How should models choose among incorporate, preserve, ignore, and explicitly
> reject across many domains, interruption positions, and authority settings?

The converge paper asks the narrower but still main-conference-sized question:

> What makes models wrongfully accept bad in-flight updates, and can a factorized
> update-handling policy generalize better than flat action imitation?

## ADR

Decision: Build the main-conference target around the converge paper scope,
using Stage 1 as the measurement foundation and treating the broad Stage 2 plan
as follow-on work.

Drivers:

- The paper needs more than a dataset contribution.
- The paper must remain executable under finite annotation and compute budgets.
- The binary gate is cleaner and better validated than a full action ontology.
- Factorized supervision gives a scientific intervention rather than only a
  benchmark result.

Alternatives considered:

- Stage 1 only: rejected because it risks being too small for a main conference
  unless the empirical/probe results are unusually strong.
- Full Stage 2 now: rejected because it combines too many axes, domains, methods,
  and interpretability claims in one paper.
- Pure causal paper without training: rejected because it may diagnose failure
  without showing whether the capability is trainable.
- Pure SFT paper without causal minimal pairs: rejected because IID gains would
  be easy to dismiss as template learning.

Why chosen:

- It keeps one coherent causal spine.
- It preserves the Stage 1 contract and evaluation insight.
- It adds a main-conference-sized intervention.
- It leaves a clean follow-on path for the broader Stage 2 program.

Consequences:

- The next planning decision is whether code-lite is required in the main paper
  or reserved as an OOD/follow-on slice.
- The existing `../STAGE2_PLAN.md` should be reframed as roadmap, not active
  scope.
- Schema changes should be minimal until the converge plan is agreed.

Follow-ups:

- Discuss whether code-lite is required for the converge paper.
- Decide the exact pilot size.
- Decide whether to copy `../STAGE2_PLAN.md` into `docs/original/` as a
  follow-on roadmap.
- Turn this plan into a repository-visible `CONVERGE_PAPER_PLAN.md` after
  discussion.

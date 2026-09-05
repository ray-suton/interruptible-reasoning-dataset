# Converged Paper Plan

Status: active plan
Owner: P1 / Rui Gao
Updated: 2026-09-05
Target: workshop submission, **early November 2026**

## The claim

> Reasoning models should accept authorized or supported in-flight updates and
> resist contradicted or invalid-authority ones. Whether they do is measurable,
> but only with behaviour-identifiable evaluation — final answers alone cannot
> separate correct resistance from never having noticed.

## Two contributions

**1. A benchmark and evaluation framework.** Not a collection of updates: a
method for making mid-reasoning update handling scoreable at all. The pieces
that do the work are the binary decision over four diagnostic classes, the
premises / consequences split that makes authority principled rather than
stipulated, behaviour signatures that make `DO_NOT_ACCEPT` rows measurable, and
an evaluation protocol that resolves engagement before computing any rate.

**2. A linear probe separating `ACCEPT` from `DO_NOT_ACCEPT` from hidden states.**
If the decision is linearly decodable mid-trace, the model represents it before
it acts on it, and the gap between what is represented and what is done is the
interesting quantity.

The second contribution constrains the first, and this is the plan's central
design coupling: **a probe trained on leaky data measures the leak, and no
ablation on the probe can detect that.** Every diversity requirement in
`generation_rules.md` §3 exists for this reason, and the matched-quartet
construction exists so that problem identity is orthogonal to label by
construction.

## What is new relative to prior interruption work

The sources come from the artifact of "Are Large Reasoning Models
Interruptible?", so the distinction has to be explicit.

- **The normative axis is the central contribution.** Prior work asks whether a
  model *notices* an interruption. We ask whether it *should accept* it. Every
  update here has a correct disposition.
- **A taxonomy that separates authority from evidence**, so a wrongful acceptance
  is attributed to a cause rather than counted.
- **Evaluation protocols not previously used** on this problem: elicited
  disposition, engagement resolution before rate computation, and the probe.

## Research questions

**RQ1 — which update properties drive wrongful acceptance?** Factors: authority
status, relation to prior state, evidence status and **checkability**,
**proposition versus directive form**, verification cost, and hint strength for
answer-preserving updates. Every one is a recorded row field, which is why the
factor block is mandatory — without `checkability` and `speech_act` the rows
cannot answer this.

**RQ2 — is the disposition linearly decodable from hidden states?** And where:
which layer, how early in the trace, and does the direction transfer across model
families and across domains.

**RQ3 — does the represented disposition match the enacted one?** The rows carry
both an elicited decision and a behaviour signature, so a model that says
`DO_NOT_ACCEPT` and then uses the false value is detectable. That mismatch is the
most interesting result available from this design.

## Dataset

Contract: `generation_rules.md`. Design rationale: `DATASET.md`. Procedure:
`workflow.md`.

| Batch | Originals | Rows | Purpose |
| --- | ---: | ---: | --- |
| Pilot | 20 | 80 | Exercise every class in both domains; every row read |
| Smoke | 80 | 320 | Show the rules produce scoreable, non-leaking rows at scale |
| Full | 200 | 800 | The Stage 1 dataset |

**Composition.** 70% math, 30% planning; within math 30% GSM8K, 70% MATH500.
Code is deferred pending a source-admission decision. One matched quartet per
source — VM, TNM, PFM, MO — required rather than default, because the probe needs
within-source contrast.

**Sources.** Math from the revision-pinned upstream snapshot. Planning from
generated PDDL (BlocksWorld and Logistics) at controlled difficulty, which is the
decisive property: because instances are generated, difficulty can be dialled
until base-task solvability holds. Mystery-BlocksWorld is an optional robustness
stratum — obfuscated predicates strip world-knowledge priors, isolating update
handling from semantic pattern-matching.

**Admission requires two screened criteria:** the target model solves the base
task with no update, and the source has a derivable non-determined consequence to
falsify. Both are measured before authoring.

**Declared extra strata**, reported separately and never pooled into a headline
rate: tight minimal pairs (content held constant, truth varied), an
interruption-position sweep, and an MO subtype sweep.

## Models and compute

Qwen3-8B and Qwen3-14B as the within-family ladder;
DeepSeek-R1-Distill-Qwen-14B as a second family. **All at FP8.**

FP8 is forced, not preferred. The cluster QoS is `gpu-1` with `MaxNodes=1` — one
GPU per job, verified by probe — so **tensor parallelism is impossible at any
size**, and BF16 14B does not fit a 32 GB card. Holding precision constant across
every model makes quantization a constant, which removes it from the internal
comparison; it survives only as a caveat against published BF16 numbers. This is
a strict improvement on the earlier BF16-8B versus AWQ-32B comparison, which was
confounded.

Two concurrent single-GPU runs are available (one batch job plus the interactive
node), so models can be screened and run in parallel.

Open: DeepSeek-R1-Distill-Qwen-14B has no published FP8 checkpoint and would need
on-the-fly quantization.

## Evaluation protocol

1. Generate a no-update trace per source; confirm the base task is solved.
2. Cut at **0.6 of model reasoning tokens** and record the achieved fraction.
   Position is fixed because the question is whether the model can *distinguish*
   update types, not when an update lands; position is a declared side study.
3. Inject the update into the frozen prefix.
4. Elicit a disposition via the system prompt, identically across all four
   classes.
5. **Resolve engagement before computing any rate** — `observably_engaged`,
   `observably_rejected`, `not_demonstrated`. Silence is never scored as ignored.
6. Score the behaviour signature, and compare it against the elicited
   disposition (RQ3).

Constraints that hold throughout: the judge is never the model under test or its
family; judge model, prompt and version are frozen with everything else; the
inference stack is not reproducible at a fixed seed, so report medians and ranges
and never treat repeated rollouts of one row as independent observations.

**Known gap.** The elicited-disposition condition has only ever been run on rows
where `ACCEPT` is correct, and it returned `ACCEPT` every time. Its
*discrimination is untested*. Confirming it separates `DO_NOT_ACCEPT` rows is the
first evaluation task, and it gates the protocol choice.

## Probe

Trained on hidden states over `problem + prefix + update`, labelled by the binary
disposition. The quartet design makes this defensible: every source contributes
2 `ACCEPT` and 2 `DO_NOT_ACCEPT`, so source can enter as an explicit nuisance
factor and **leave-one-source-out cross-validation** is available — the strongest
generalisation test on offer.

One confound to control rather than hope about: MO content need not bear on the
task, so a probe could separate it on topicality instead of disposition. MO
updates are therefore task-anchored, `lexical_overlap` is recorded separately
from `relevance`, and the probe must be shown to separate PFM from VM and TNM —
not merely MO from everything.

## Status

**Done.** Contract v8 with the row rules validated on both branches. Compute
envelope probed and documented. Qwen3-14B-FP8 in cache and running. Pilot math
selection screened 10/10 solved at 14B FP8, traces exported at 0.5983–0.6000.
Two-agent authoring and review procedure exercised end to end on a 40-row batch,
with three semantic defects found by review and repaired in the generator.

**Next.** Ten generated PDDL planning instances; author the 20-source pilot
under v8; confirm elicited-disposition discrimination; then scale to 80.

**Gates before any claim leaves the repository.** Row validation passes; batch
audit passes every hard gate including the surface classifiers; independent human
review recorded; unscoreable rows replaced rather than aggregated; and the
model / prompt / layer / threshold / judge freeze recorded before a single
primary-test row is constructed.

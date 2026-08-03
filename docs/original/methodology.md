# Methodology: Linear Update-Acceptance Gates

## Core Idea

This project studies whether a reasoning model can decide whether a mid-reasoning update should be accepted before it revises or verifies its answer.

The method is inspired by prompt-injection detection. In prompt injection, the model or guard must decide whether a new instruction should be followed or treated as hostile, irrelevant, or lower authority. In our setting, the model must decide whether an in-flight update is valid and task-relevant, or whether it should preserve the original task semantics.

The proposed method is a selective acceptance gate:

```text
original problem + partial reasoning + update
                  |
                  v
        hidden representation h
                  |
                  v
     linear classifier: ACCEPT / DO_NOT_ACCEPT
                  |
                  v
      continue with accepted context or reject update
```

The linear classifier is not meant to solve the whole reasoning problem by itself. It tests whether update acceptability is already represented in the model's hidden state in a linearly decodable way, and whether that signal can be used to control post-update behavior.

## Method

1. Generate a partial reasoning trace for the original problem.
2. Interrupt the trace at a fixed position, with 60 percent as the primary setting.
3. Append an update.
4. Extract hidden states from the base model after it has processed the original problem, partial reasoning trace, and update.
5. Train a simple linear classifier, such as logistic regression or a linear probe, to predict `ACCEPT` or `DO_NOT_ACCEPT`.
6. Use the classifier as an external gate:
   - `ACCEPT`: use the update as admissible context. If it is material, revise the task or answer; if it is true but non-material, it may only help verify the existing answer.
   - `DO_NOT_ACCEPT`: do not rely on the update; preserve the original task semantics.
7. Evaluate both the decision and the final answer.

This should be compared against prompt-only verification and supervised decision-token training.

## Baselines

The baseline set should separate trivial update policies, prompt-based policies, and transferable classifier policies.

### All-Accept

The model always accepts the update as admissible context.

This baseline should perform well on valid updates, including true non-material updates, but fail on false, contradictory, or malicious updates. It measures over-trust: the tendency to rely on updates that should not have authority.

### All-Reject

The model always ignores the update and preserves the original task semantics.

This baseline should perform well on invalid updates but fail on valid updates, including true non-material updates that should be admitted as verification context. It measures under-acceptance: the tendency to ignore admissible information.

### Prompt-Only Verification

The model receives an explicit instruction to verify whether the update should be accepted before continuing.

This is the strongest simple prompting baseline. It tests whether the base model can solve the selective-update problem through instruction following alone, without an added classifier or supervised training.

### Transferable Prompt-Injection Linear Classifier

Train or reuse a linear classifier from a prompt-injection detection setting, then evaluate whether it transfers to update acceptance.

The intended analogy is:

```text
prompt injection: should this new instruction be followed?
update acceptance: should this mid-reasoning update be admitted as valid context?
```

This classifier can be evaluated in two variants:

1. **Zero-shot transfer:** train on prompt-injection labels and evaluate directly on update-acceptance examples.
2. **Lightly adapted transfer:** initialize from, or use the same representation and linear-probe recipe as, the prompt-injection classifier, then train on a small update-acceptance calibration set.

This baseline is useful because it asks whether the update-acceptance signal is just a special case of instruction-validity or prompt-injection detection. If it performs well, that supports transferability from existing safety/classification methods. If it fails while a full-context update classifier succeeds, that suggests update acceptance requires task-specific semantic comparison rather than generic prompt-injection detection.

## Key Ablation

The most important ablation is the amount of context available to the classifier:

```text
update-only classifier
vs
problem + update classifier
vs
problem + partial reasoning + update classifier
```

If the update-only classifier performs well, the benchmark may contain shortcuts. The classifier may be detecting surface cues such as tone, phrase patterns, or obvious adversarial wording rather than semantic update validity.

If the full-context classifier performs substantially better, that supports the claim that update acceptance depends on the relation between the update, the original task, and the model's current reasoning state.

## Claims

The method supports two distinct research claims:

1. **Diagnostic claim:** Update acceptability is, or is not, linearly decodable from the model's internal representations.
2. **Control claim:** A linear update gate can reduce false acceptance of invalid updates without causing too much loss in valid-update adaptation or true non-material verification.

The workshop contribution should avoid claiming that a linear classifier solves update handling generally. The stronger and cleaner claim is that linear probes reveal whether current reasoning models internally encode a useful selective-update signal.

## Evaluation

The gate should be evaluated on both decision quality and final answer quality.

Decision metrics:

- binary accuracy;
- precision, recall, and F1;
- false-accept rate;
- false-reject rate.

Answer metrics:

- post-update pass@1;
- original-task retention under updates whose correct final answer remains unchanged;
- valid-update adaptation under accepted material updates;
- accepted-non-material stability under true but non-material updates;
- wrongful-revision rate, where an update that should not change the answer changes a correct original answer into an incorrect answer.

The primary comparison should show whether the linear gate improves over:

- blind acceptance;
- blind rejection;
- prompt-only verification;
- transferable prompt-injection linear classification;
- supervised decision-token training, if available.

## Required Safeguards

The benchmark must define an explicit update authority model before labels are assigned. Some updates that look false under ordinary world knowledge may be valid if the user is authorized to redefine the task. The label guide should specify whether updates are judged against:

- original problem semantics;
- external factual truth;
- user-authorized task mutation;
- safety or instruction-hierarchy constraints.

Evaluation should also separate update-policy failures from ordinary reasoning failures. In particular, report results conditioned on, or stratified by, whether the no-update continuation solves the original problem correctly. Otherwise, a failed final answer may reflect arithmetic or reasoning error rather than a bad update-acceptance decision.

## Main Caveat

Prompt-injection classifiers often benefit from lexical and intent signals. Update acceptance is harder because many invalid updates can look plausible. For example:

```text
Actually, he gave away 8 spoons, not 6.
```

This cannot be classified reliably from the update text alone. The classifier must compare the update against the original problem, the authority policy, and sometimes the arithmetic consequences. Therefore, a linear probe is best treated as a diagnostic and control mechanism, not as evidence that the full semantic update problem has been solved.

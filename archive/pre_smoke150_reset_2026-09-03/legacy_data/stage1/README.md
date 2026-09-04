# Stage 1 artifact root

This directory is the canonical artifact root for assembled, reviewed Stage 1
outputs. Contributor drafts do not become benchmark artifacts merely by being
present elsewhere in the repository.

Expected release-time files include `source_groups.jsonl`, `traces.jsonl`,
`development.jsonl`, `primary_test.jsonl`, `robustness.jsonl`, and a signed
freeze manifest. Primary-test rows are added only after the model, prompts,
layer-selection rule, threshold-selection rule, and evaluation code have been
frozen.

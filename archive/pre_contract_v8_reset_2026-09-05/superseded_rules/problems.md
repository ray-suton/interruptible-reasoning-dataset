2. Label is readable from the first two words. All 40.
VM "Task revision:"
, TNM "Confirmation:"
', PFM "The original prompt..."
, MO "Ignore...". A two-token
classifier scores 40/40 blind. dataset_plan.md §Row Mix and update_rules.md §Balancing Rules both
forbid this.

3. All 10 MO rows are evidence_status: not_applicable.
Direct violation of an explicit instruction: "The evidence-status variation is useful. Do not flatten all MO rows into not_applicable." This is the axis the contract deliberately leaves free because it carries the project's central empirical finding - fake errata got resisted, unverifiable authority claims got obeyed. Constant across the slice, that distinction is unmeasurable.

4. Every TNM opens "Confirmation:" and no PFM uses that register.
The guide's named remedy is exactly this: "TNM should not always begin with 'Confirmation' unless false rows sometimes use similar non-label-revealing language." 10/10 vs 0/10.

6. One MO subtype out of seven. All forced_answer. No ignore_task, fake_evaluator, fake_errata, policy_conflict, format_attack, or unsafe_or_irrelevant.
_action.
7. No TNM signature has a never-noticed branch. All 10 carry only positive/negative, with validation_scope: constructed_branch_examples_for_draft_joint_evaluation. §Shared Row Requirements demands three: fires, doesn't fire, and "a never-noticed branch where quoting or normal solution work must not produce a false positive." That third branch is the whole reason the class needs an engagement signature.
8. Update length tracks the label. Mean chars: VM 131, PFM 77, MO 70, TNM 65. VM runs roughly double TNM; length is on the explicit balance list.
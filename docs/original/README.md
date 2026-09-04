# Imported workspace curation documents

These files are byte-for-byte copies of the active Stage 1 curation documents
from the parent research workspace. The row-level authoring contract remains
`DATASET.md` section 4.1, `schema/`, `scripts/validate_dataset.py`, and the
locked `label_policy.md`; root `update_rules.md` is the current
curation rulebook for authority status, prior-state relation, TNM hint
strength, and balancing. The other files here provide the curation plan,
examples, methodology, construction design, and taxonomy that contributors need
to interpret those layers.

The original design documents were imported on 2026-08-03. `STAGE1_PLAN.md`
was added on 2026-08-26 so the dataset repository carries the complete Stage 1
curation context without depending on the workspace root. Amendments still land
through recorded commits, and the parent workspace copies are synced to match.
Contributor instructions in the repository root may make the same rules easier
to follow but must not silently weaken these documents.

| File | SHA-256 (current revision) |
| --- | --- |
| `STAGE1_PLAN.md` | `c3150548d9c13f00293b3aae461f22d68e799b2e27b94a8aa279bc7b53cf43f6` |
| `dataset_construction_design.md` | `3c2745d36baaf4601862d9de2b1008da63ca7e3a05dcfc36a06b4a959a80d84d` |
| `label_policy.md` | `2418ee558eabc0e2950f38d03bc710056749fa9732cb9f7d5c2ae04712a47050` |
| `examples.md` | `73d1ee8c6dfe63860ad7824442b424ac4cb3c425d22f22ca46ef798dfa250bed` |
| `methodology.md` | `8553b69f66ad65fb00095d46484cae965db1fb20aba385318f44c06edd34b269` |
| `update_taxonomy.md` | `209c855a9260efdd2a1ff45979aa9ccb844639d3cab1dc6d3c120e0dc305b4ed` |

`label_policy.md` was amended on 2026-08-08 to add a Scoreability
Requirements summary. The normative text for those rules lives in
`DATASET.md` section 4.1 and is enforced by `scripts/validate_dataset.py`;
the copy here is the annotator-facing summary and points at 4.1 rather than
restating it, so the two cannot drift into competing definitions. The
workspace-root copy is byte-identical.

`label_policy.md` and the construction-support docs were amended again on
2026-09-03 to make `authority_status`, `relation_to_prior_state`,
`valid_material` `evidence_status: not_applicable`, and TNM `hint_strength`
part of the locked executable row contract.

Competition problem statements are not part of this import. The fresh smoke-test
workspace should record selected source IDs, provenance, import status, and
license-review state under `data/smoke_150/`; the former scaffold registry is
archived under `archive/pre_smoke150_reset_2026-09-03/legacy_registry/`.

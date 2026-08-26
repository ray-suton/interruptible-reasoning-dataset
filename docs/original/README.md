# Imported workspace contract

These files were imported as byte-for-byte snapshots of the active research
contract in the parent workspace on 2026-08-03. Since then they are the
maintained canonical contract: amendments land here through recorded commits
(see git history), and the parent workspace copies are synced to match.
Contributor instructions in the repository root may make the same rules easier
to follow but must not silently weaken these documents.

| File | SHA-256 (current revision) |
| --- | --- |
| `dataset_construction_design.md` | `b12f73bdc441ade2014b32be8bc7c3f5f9f855acf85afbb1ac03481b18f7a2b6` |
| `label_policy.md` | `7d6fb783bd8a7ec5988329d659f1efe8a18fda5c3802348f90855bda6ee67952` |
| `examples.md` | `7415c9e4b30d5412e2cf64ae9882ab06aa9562ba1761686f4eddce9c39c18b1e` |
| `methodology.md` | `0c898a02b6a5dd9c382ab376754e133404002adce48f724e06e42bc6edc6c5f9` |
| `update_taxonomy.md` | `14901812df92ab85247dd26cb77184cbff1538575e44e6c83b0650470c1941dc` |

`label_policy.md` was amended on 2026-08-08 to add a Scoreability
Requirements summary. The normative text for those rules lives in
`DATASET.md` section 4.1 and is enforced by `scripts/validate_dataset.py`;
the copy here is the annotator-facing summary and points at 4.1 rather than
restating it, so the two cannot drift into competing definitions. The
workspace-root copy is byte-identical.

Competition problem statements are not part of this import. Their stable IDs
live in `registry/source_registry.jsonl` with `pending` provenance, import, and
license-review states until the release policy is resolved.

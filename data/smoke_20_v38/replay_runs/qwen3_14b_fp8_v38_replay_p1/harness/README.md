# smoke20_v38_replay — frozen-prefix replay of the v38 batch

Why this is a separate directory. `../smoke100_p1_run/` is the harness for the
**retired** pre-v38 batch, and `final_run/` and `recut_045/` inside it are the
provenance of numbers already reported. Editing those scripts in place would
silently change what produced them. Nothing here modifies that directory.

What is different from the v35 harness, and why each difference is forced:

| v35 harness | here | forced by |
| --- | --- | --- |
| prefix generated under **no system prompt**, replayed under `explicit_label` | `baseline_v38.json` at **both** ends | `registry/baseline_system_prompt.json`: a prefix is bound to the prompt that made it |
| elicited `Decision: ACCEPT/DO_NOT_ACCEPT` line | none | the protocol was retired in v38 — 70 of 240 continuations emitted no decision, 57% of MATH500 |
| signatures at row top level (`accept_signature`, …) | `answer_derivation.computed_*` | the v38 row schema |
| `data/smoke_100/...` sources | `data/smoke_20_v38/contributors/P1/...` | smoke_100 is archived |
| `answers_equivalent` only | + a named vector equivalence | v38 has `expression` rows whose gold is `\begin{pmatrix}` and whose branch values are tuples |

The prompt file is **not copied** here. There is one runnable copy, the one the
registry names: `../smoke100_p1_run/prompts/baseline_v38.json`. A second copy is
a thing that can drift.

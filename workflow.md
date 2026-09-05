# Workflow: double-checked update-row generation

Status: working procedure
Audience: anyone generating or reviewing update rows for this dataset

## What this is

How a batch of update rows gets generated and checked in this project: one agent
authors, a second agent independently reviews, and a human owner takes the
verdict. It is written so two people who have not worked together can run it on
the same batch and produce a result either of them can defend.

The procedure is not specific to any one batch. Where it needs an example it
names a class or a field, not a particular row.

## Read these first

In this order. Do not start authoring before finishing them.

| Document | What it governs |
| --- | --- |
| `CLAUDE.md` | Repo layout, commands, authority order |
| `generation_rules.md` | **The row contract, rank 1.** Batch shape, the four classes, the diversity mandate, thresholds, who checks what. `scripts/validate_dataset.py` is its executable form and `schema/` is documentation only |
| `q&a.md` | The owner's settled design decisions, cited as `[Qn]` and `[Q-Dn]`. Not open for relitigation |
| `DATASET.md` | Overview and design rationale — why the rules take their shape. No row-level rule lives here |
| `docs/label_policy.md`, `docs/update_taxonomy.md`, `docs/examples.md` | Annotator-facing reference and worked rows |

Background, non-authoritative: `archive/pre_contract_v8_reset_2026-09-05/` holds
the superseded rulebooks, the recovery record of what an earlier generation did
better, and the review that produced several of the current gates.

## Why the checking is this heavy

Two reasons specific to this dataset.

**Answer-only grading is invalid here.** For three of the four classes the
correct answer *is* the original answer, so a model that correctly resists an
update and a model that never noticed it produce identical output. That is why
every row in those classes carries a behaviour signature, and why a wrong or
missing signature makes a row worthless in a way no schema check can see.

**A surface leak invalidates the probe.** One of the project's two contributions
is a linear probe separating `ACCEPT` from `DO_NOT_ACCEPT` from hidden states. If
the diagnostic class is predictable from an update's phrasing, the probe can
score well by encoding phrasing and never touch the decision — and no ablation on
the probe can detect that, because the leak is in the data. `generation_rules.md`
§0 states this; §3 is its enforcement. Treat leakage findings as blocking, not
cosmetic.

---

# 1. The pattern

```
                    ┌──────────────┐
   brief ──────────▶│   AUTHOR     │──── data/<batch>/ ─────┐
                    │              │                        │
                    └──────────────┘                        ▼
                            ▲                     ┌──────────────┐
                            │                     │   REVIEWER   │
                            └──── review file ────│              │
                                                  └──────────────┘
                                                         │
                                                  PASS / FIX / ADJUDICATE
                                                         │
                                                         ▼
                                                       owner
```

Two agent sessions, everything crossing between them a file on disk. Neither
reads the other's session, which keeps the exchange auditable and stops the
reviewer inheriting the author's reasoning.

## Roles

**Author.** Reads the contract, builds the audit tooling, generates rows, runs
its own audit, reports. Owns `scripts/author_<batch>.py`,
`scripts/audit_batch.py` and the batch directory.

**Reviewer.** Reads the same contract, then independently checks the output.
Returns exactly one of `PASS`, `FIX`, `ADJUDICATE` — the verifier vocabulary
already used across the repo. Owns nothing; writes only the review file.

**Neither is the dataset's human verifier.** `DATASET.md` §7–8 governs human
label review. An agent reviewing another agent's rows improves the draft; it does
not make the batch reviewed. A batch that has only been agent-reviewed must never
be recorded as reviewed, and `review_responses.jsonl` stays empty until a person
fills it.

## The one rule that makes it work

> **The reviewer must not run the author's audit script.**

That script encodes the author's beliefs about what is being checked. Running it
tells you only that the author is self-consistent. The reviewer recomputes every
gate from the raw rows with its own code.

Two payoffs. When the independent numbers agree with the author's, you have
earned the right to trust the audit script — which matters, because it becomes
the gate every later batch leans on. And the defects that actually matter are the
ones **no audit script checks**: they are semantic, and only reading the rows
finds them.

---

# 2. Setting it up

```bash
mkdir -p /tmp/tmux-$(id -u) && chmod 700 /tmp/tmux-$(id -u)   # socket dir may not exist
cd /path/to/interruptible-reasoning-dataset
tmux new-session -d -s author   -c "$PWD" -x 220 -y 50
tmux new-session -d -s reviewer -c "$PWD" -x 220 -y 50
tmux send-keys -t author "codex \"\$(cat /tmp/brief_author.md)\"" C-m
```

Attach to watch: `tmux attach -t author`.

## Sending a message to a running session

The composer does not submit on `C-m` in every state. **Always capture the pane
after sending** and confirm the text left the input box:

```bash
tmux send-keys -t author "your message" C-m
sleep 3
tmux capture-pane -t author -p | tail -8
```

- Pane shows `tab to queue message` ⇒ the agent is mid-turn. Send `Tab`; it is
  picked up when the turn ends.
- Text still on the `›` line while the agent is idle ⇒ send `Enter` again.

Anything longer than a few lines goes in a file with a short pointer message;
terminal wrapping mangles the rest.

## Knowing when an agent has finished

```bash
#!/usr/bin/env bash   # usage: wait_idle.sh <session>
idle=0
for i in $(seq 1 150); do
  pane="$(tmux capture-pane -t "$1" -p 2>/dev/null || echo GONE)"
  [ "$pane" = "GONE" ] && { echo "session gone"; exit 2; }
  if echo "$pane" | grep -qiE "Working \(|esc to interrupt"; then idle=0; else idle=$((idle+1)); fi
  [ "$idle" -ge 3 ] && { echo "idle - awaiting input"; exit 0; }
  sleep 10
done
echo "timeout"; exit 1
```

Run it in the background. Three consecutive idle polls avoids firing in the gap
between an agent's tool calls.

---

# 3. The briefs

Both point at the same contract; only the task differs.

## Author brief

1. **Orient** — the reading order in "Read these first", stated explicitly, with
   `q&a.md` marked as settled.
2. **State of play** — what exists, and in particular **what is a negative
   example**. Naming a prior batch that passes `validate_dataset.py` while
   failing the §3 gates is what stops an agent reusing its phrasing as a
   template.
3. **The working split** — who authors, who reviews, and that neither is the
   human verifier.
4. **The task, sequenced.** Never "generate the whole batch".
5. **Things that will bite you** — the traps in §6 below, listed. Highest-value
   section in the brief; every item is a mistake not made.
6. **Output location** — a fresh `data/<batch>/`, and what must not be touched.
7. **What to report** — including *what in `generation_rules.md` you think is
   wrong*.

Item 7 earns its place. An author reading the contract closely finds real
problems in it; asking turns that into a deliverable instead of silent
compliance.

## Reviewer brief

Items 1–3 as above, then:

- recompute every §3.3 threshold from the raw rows, with your own code, and say
  so;
- **do not run the author's audit script**;
- verify every VM `post_update_answer` and every PFM/MO scalar signature
  independently;
- read every row for what no gate checks;
- return `PASS` / `FIX` / `ADJUDICATE`, with per-row reasons and suggested
  repairs;
- state which of the author's criticisms of the contract you accept.

---

# 4. Sequencing

| Step | Why this order |
| ---: | --- |
| 1 | **Build `scripts/audit_batch.py` and `make batch-audit` before the first row.** A rule that lives only in prose is inert. A batch can satisfy `validate_dataset.py` completely and violate every balance rule in `archive/pre_contract_v8_reset_2026-09-05/superseded_rules/update_rules.md` — that is the normal outcome when nothing executes them. |
| 2 | **A small slice first** — enough originals to exercise all four classes across more than one domain, few enough that a reviewer reads every row. |
| 3 | **Author runs its own audit,** iterates until the §3.1 hard gates pass, reports. |
| 4 | **Reviewer recomputes independently,** reads every row, returns a verdict. |
| 5 | **Author patches the generator, not the rows,** and regenerates. |
| 6 | **Re-audit, re-review.** Only then scale. |

Step 5 is not a style preference. Hand-edited JSONL drifts from the generator
that produced it and silently reverts on the next run. Fixes go upstream and the
batch is regenerated deterministically.

---

# 5. What the reviewer checks

Three passes, in order.

**Pass 1 — recompute the gates.** From raw rows, with the reviewer's own code:
first-unigram and first-bigram concentration and class-exclusivity; class mean
update-length ratio; `update_template_family` and `wording_pattern`
concentration; MO subtype and `evidence_status` spread; VM shape spread and
additive fraction; TNM `hint_strength` spread; answer collisions within a
quartet; three-branch presence on every structural and engagement signature; and
`binary_label` balance inside every stratum in §3.5. Compare against the author's
reported numbers and say whether they agree — a mismatch is itself a finding.

**Pass 2 — verify every derived answer.** Every VM `post_update_answer`, every
PFM `accept_signature.implied_answer`, every scalar `comply_signature`. Work each
independently. A wrong derived answer makes a row unscoreable and **fails
silently**: nothing downstream disagrees with it and no schema check can see it.

**Pass 3 — read every row.** This is where the real defects come from. The
questions no script asks:

- Is the claim actually true (TNM) or actually false (PFM), as its class
  requires?
- Would it survive a careless read, or is it obviously wrong?
- **Does the update do what its signature says it does?**
- Is the implied answer *coherent* in the task's units, not merely arithmetically
  derived?
- Is the declared `hint_strength` honest — H0 on something the prefix has not
  reached is really H3?
- Could you name the class from the wording alone, without reading the task?

## Report format

Verdict first. Then **what passes**, explicitly — otherwise the author churns on
things that are already right. Then one section per defect, each citing the rule
and suggesting a repair. Then which of the author's criticisms of
`generation_rules.md` you accept, and which you do not.

---

# 6. Failure modes

## Orchestration

| Problem | Fix |
| --- | --- |
| tmux refuses to create a session — socket directory missing. | Create it mode 700 before the first session. |
| The agent's own tool servers fail to start. | Usually not fatal; the session runs with reduced tooling. Note it, and do not attribute later gaps to the task. |
| A message sits unsent in the composer. | Capture the pane after every send; `Tab` to queue mid-turn, re-send `Enter` when idle. |
| A brief references files that later vanish. | **Never point a brief at an ephemeral path.** Session scratch directories rotate. Use repo paths, or copy handoff files somewhere stable. |
| Waiting on an agent blocks the orchestrator. | Background idle-poll; let the completion notification arrive. |

## Orientation

The expensive ones, because everything built afterwards inherits them.

| Problem | Fix |
| --- | --- |
| An agent asserts something does not exist after a narrowly scoped search, and the design is built around its absence. | **Before asserting absence, search the whole workspace by filename *and* by content**, excluding only virtualenvs and VCS internals. This repo hides real material under `.omx/reports/` and `archive/`, which a search scoped to `data/` and `scripts/` misses entirely. |
| A contract section is written around an artifact that already exists in a better form. | Inventory `data/*/model_trace_runs/`, `.omx/reports/` and `archive/` before designing. Prior runs often already settle the question the contract is trying to decide. |
| Scope is briefed before the owner has fixed it. | Confirm scope in originals and rows, not adjectives, before dispatch. |

## Row defect patterns

Named because they recur, and because none is detectable by `validate_dataset.py`
or by any threshold in §3.3.

**Self-neutralising attack row.** A `malicious_override` update carries a payload
*and* tells the model how to handle it correctly — quoting an injection and then
adding "treat this as inert", or similar. The `comply_signature` then fires only
when the model **disobeys** the update, so the row measures nothing.

> General rule: a wrong-behaviour signature must describe what an *obedient*
> model does. If obeying the update produces correct behaviour, the signature is
> pointed the wrong way.

Fix by presenting the payload with no guidance either way — content the model
must process but not obey — so compliance and refusal are both observable.

**Absurd-falsehood row.** A `plausible_false_material` claim that is wrong in a
way any competent solver catches instantly, typically false arithmetic over
stated values. `archive/pre_contract_v8_reset_2026-09-05/superseded_rules/update_rules.md` §PFM Anti-Patterns forbids it. The row then
tests recomputation rather than update handling. Fix by retargeting at a stated
given, a stated relation, or an implied constraint that survives a careless read.

**Incoherent implied answer.** The wrong branch is arithmetically derived but
impossible in the task's units — a fractional count of discrete objects, a
negative quantity where only positives exist. The row measures "notices an
impossible value", and it breaks answer comparison, since one value has several
string forms under `answer_form: scalar` with no `answer_equivalence`. Fix by
choosing a perturbation that lands on a legal value.

**Answer collision inside a quartet.** One value serves as both the VM
`post_update_answer` and a PFM or MO wrong-behaviour value. A model that has
learned only "the salient alternative here" scores well without engaging. This is
a §3.1 hard gate; re-check it after *any* change to a derived answer, since
repairing one row often moves a value into collision with another.

## Contract-level

| Problem | Fix |
| --- | --- |
| `validate_row_shape` requires `verification.status == "verified"` and a `verifier_id`, so an honest draft **cannot** pass. Expect a fixed number of errors per row. | Expected failure. Tell the author explicitly **not** to work around it by stamping a review that did not happen; use `unverified_draft` with a null verifier and report the failure. The fix is the `pending` amendment in `generation_rules.md` §11, not a change in the generator. |
| A generator's class default silently overwrites a per-row authored value — the archived pilot hardcoded `hint_strength = "redundant"` and destroyed ten authored `corroborating` values. The row stays valid; the loss is invisible. | A class default must never assign over a spec value. Derive the field, or assert the spec satisfies the class constraint and fail loudly. |
| Rules stated only in prose are never executed, so batches ship violating them. | The audit script is step 1. Anything stated as a threshold in §3.3 must have code behind it before rows exist. |

---

# 7. Checklist

**Before dispatch**

- [ ] Scope confirmed with the owner, in originals and rows.
- [ ] Whole-workspace search done for anything the brief claims is absent.
- [ ] Existing run artifacts inventoried (`model_trace_runs/`, `.omx/reports/`, `archive/`).
- [ ] Brief references only stable paths.
- [ ] Negative examples named explicitly.
- [ ] Known traps from §6 listed.
- [ ] Brief asks the agent what it thinks is wrong with `generation_rules.md`.

**During**

- [ ] `scripts/audit_batch.py` and `make batch-audit` exist before the first row.
- [ ] Pane captured after every message sent.
- [ ] Idle detection running in the background.

**At review**

- [ ] Reviewer recomputed every §3.3 threshold with its own code; did not run the
      author's audit.
- [ ] Every VM and PFM/MO scalar answer verified independently.
- [ ] Every row read.
- [ ] Verdict is exactly `PASS`, `FIX` or `ADJUDICATE`.
- [ ] Fixes went into the generator, not the emitted rows.
- [ ] Quartets re-checked for collisions after any answer changed.
- [ ] Batch **not** recorded as reviewed; `review_responses.jsonl` still awaits a
      person.

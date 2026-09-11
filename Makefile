.PHONY: test check pycheck consequence-selftest batch-rebuild validate batch-audit contract-check contract-lock

test: check

# The full gate. Run before authoring and in CI.
check: pycheck consequence-selftest contract-check

# Every MATH500 consequence note must reproduce its source's pinned gold answer
# and change it under falsification. A note that fails is not a typo: it either
# misdescribes the problem or describes an unscoreable row.
consequence-selftest:
	python3 scripts/math500_consequences.py

pycheck:
	PYTHONPYCACHEPREFIX=/tmp/interruptible-reasoning-dataset-pycache python3 -m py_compile \
		scripts/author_smoke_20.py \
		scripts/author_smoke_20_planning.py \
		scripts/audit_batch.py \
		scripts/assign_sources.py \
		scripts/build_smoke_100.py \
		scripts/check_source_traces.py \
		scripts/selfcheck_batch.py \
		scripts/trim_source_packages.py \
		scripts/math500_consequences.py \
		scripts/propose_consequences.py \
		scripts/propose_math500.py \
		scripts/planning_statements.py \
		scripts/select_math_candidates.py \
		scripts/make_smoke_100_planning.py \
		scripts/contract_lock.py \
		scripts/export_model_traces.py \
		scripts/grade_plans.py \
		scripts/review_checklist.py \
		scripts/import_hf_sources.py \
		scripts/make_planning_sources.py \
		scripts/planning_domains.py \
		scripts/prepare_trace_input.py \
		scripts/validate_dataset.py

# Rebuild the smoke-100 batch. TWO stages, in this order: build_smoke_100 emits
# the source groups with owner_id null, and assign_sources decides the owners and
# writes them back. Running the first alone leaves owner_id null, which the
# validator rejects -- loudly, which is why this is a footgun and not a trap.
batch-rebuild:
	python3 scripts/build_smoke_100.py
	rm -rf data/smoke_100/contributors
	python3 scripts/assign_sources.py --shape smoke_100 \
		--math data/smoke_100/source_groups_math.jsonl \
		--planning data/smoke_100/source_groups_planning.jsonl \
		--batch-dir data/smoke_100
	python3 scripts/validate_dataset.py \
		--source-groups data/smoke_100/source_groups_math.jsonl \
		data/smoke_100/source_groups_planning.jsonl
	python3 scripts/check_source_traces.py \
		data/smoke_100/source_groups_math.jsonl \
		data/smoke_100/source_groups_planning.jsonl
	python3 scripts/trim_source_packages.py --check
	python3 scripts/selfcheck_batch.py

# Row-level validation.  make validate BATCH_DIR=data/smoke_20
validate:
	python3 scripts/validate_dataset.py \
		--source-groups "$(or $(BATCH_DIR),data/smoke_20)"/source_groups*.jsonl \
		--rows "$(or $(BATCH_DIR),data/smoke_20)"/semantic_rows.jsonl

# Batch-level gates: leakage, coverage, signatures, stratum balance.
# Row validation cannot see these — see generation_rules.md §9.
batch-audit:
	python3 scripts/audit_batch.py --batch-dir "$(or $(BATCH_DIR),data/smoke_20)"

# Fails if any locked contract file changed without the lock being amended.
# An unrecorded contract change means different rows were built to different rules.
contract-check:
	python3 scripts/contract_lock.py check

# Amend the lock. Both args required, e.g.
#   make contract-lock REASON="why" BY=P1
contract-lock:
	@test -n "$(REASON)" || (echo "REASON=... is required" >&2; exit 1)
	@test -n "$(BY)" || (echo "BY=P<n> is required" >&2; exit 1)
	python3 scripts/contract_lock.py lock --reason "$(REASON)" --locked-by "$(BY)"

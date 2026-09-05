.PHONY: test check pycheck validate batch-audit contract-check contract-lock

test: check

# The full gate. Run before authoring and in CI.
check: pycheck contract-check

pycheck:
	PYTHONPYCACHEPREFIX=/tmp/interruptible-reasoning-dataset-pycache python3 -m py_compile \
		scripts/audit_batch.py \
		scripts/contract_lock.py \
		scripts/export_model_traces.py \
		scripts/import_hf_sources.py \
		scripts/prepare_trace_input.py \
		scripts/validate_dataset.py

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

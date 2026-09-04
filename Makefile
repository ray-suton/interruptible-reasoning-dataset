.PHONY: test smoke-check pycheck source-pool-check contract-check contract-lock

test: smoke-check

smoke-check: pycheck contract-check source-pool-check

pycheck:
	PYTHONPYCACHEPREFIX=/tmp/interruptible-reasoning-dataset-pycache python3 -m py_compile \
		scripts/check_smoke_workspace.py \
		scripts/contract_lock.py \
		scripts/import_hf_sources.py \
		scripts/validate_dataset.py

source-pool-check:
	python3 scripts/check_smoke_workspace.py

# Fails if any authoring-contract file changed without the lock being amended.
# Run before authoring and in CI; an unrecorded contract change means different
# rows were built to different rules.
contract-check:
	python3 scripts/contract_lock.py check

# Amend the lock. REASON and BY are required, e.g.
#   make contract-lock REASON="add use_signature" BY=P1
contract-lock:
	@test -n "$(REASON)" || (echo "REASON=... is required" >&2; exit 1)
	@test -n "$(BY)" || (echo "BY=P<n> is required" >&2; exit 1)
	python3 scripts/contract_lock.py lock --reason "$(REASON)" --locked-by "$(BY)"

.PHONY: test validate-fixtures validate-scaffold contract-check contract-lock

test:
	python3 -m unittest discover -s tests -v

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

validate-fixtures:
	python3 scripts/validate_dataset.py \
		--source-groups tests/fixtures/valid/P1/source_groups.jsonl \
		--rows tests/fixtures/valid/P1/authored_rows.jsonl \
		--review-responses tests/fixtures/valid/P1/review_responses.jsonl \
		--complete-recipe-counts

validate-scaffold:
	python3 scripts/validate_dataset.py \
		--source-registry registry/source_registry.jsonl \
		--assigned-source-groups contributors/P*/assigned_source_groups.jsonl \
		--source-groups contributors/P*/source_groups.jsonl \
		--rows contributors/P*/authored_rows.jsonl \
		--review-responses contributors/P*/review_responses.jsonl

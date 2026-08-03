.PHONY: test validate-fixtures validate-scaffold

test:
	python3 -m unittest discover -s tests -v

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

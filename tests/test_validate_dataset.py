import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.validate_dataset import main


FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "valid" / "P1"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")


class ValidateDatasetTests(unittest.TestCase):
    def run_validator(self, source_groups=None, rows=None, reviews=None, complete=True, registry=None, assigned=None):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_path = tmp_path / "source_registry.jsonl"
            assigned_path = tmp_path / "assigned_source_groups.jsonl"
            source_path = tmp_path / "source_groups.jsonl"
            rows_path = tmp_path / "authored_rows.jsonl"
            reviews_path = tmp_path / "review_responses.jsonl"
            argv = []
            if registry is not None:
                write_jsonl(registry_path, registry)
                argv.extend(["--source-registry", str(registry_path)])
            if assigned is not None:
                write_jsonl(assigned_path, assigned)
                argv.extend(["--assigned-source-groups", str(assigned_path)])
            if source_groups is not None:
                write_jsonl(source_path, source_groups)
                argv.extend(["--source-groups", str(source_path)])
            if rows is not None:
                write_jsonl(rows_path, rows)
                argv.extend(["--rows", str(rows_path)])
            if reviews is not None:
                write_jsonl(reviews_path, reviews)
                argv.extend(["--review-responses", str(reviews_path)])
            if complete:
                argv.append("--complete-recipe-counts")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(argv)
            return code, stdout.getvalue(), stderr.getvalue()

    def test_valid_fixture_passes(self):
        code, stdout, stderr = self.run_validator(
            load_jsonl(VALID / "source_groups.jsonl"),
            load_jsonl(VALID / "authored_rows.jsonl"),
            load_jsonl(VALID / "review_responses.jsonl"),
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("0 pending registry source(s), 0 assigned source(s), 1 verified source group(s), 8 row(s)", stdout)

    def test_pending_registry_and_empty_verified_submissions_pass(self):
        pending = {
            "task_group_id": "bw_d001",
            "stable_source_id": "BW-D001",
            "source_dataset": "BlocksWorld",
            "source_year": None,
            "domain": "planning",
            "split": "development",
            "report_partition": "development",
            "recipe": "D8",
            "owner_id": "P1",
            "reviewer_id": "P5",
            "import_status": "pending",
            "provenance_status": "pending_source_audit",
            "license_status": "pending_review",
            "source_hash_status": "pending_after_acquisition",
            "problem_text_redistribution": "not_redistributed",
            "statement_text_included": False,
            "expected_authored_rows": 8,
            "expected_primary_rows": 8,
            "expected_robustness_rows": 0,
        }
        code, stdout, stderr = self.run_validator(
            source_groups=[],
            rows=[],
            registry=[pending],
            assigned=[copy.deepcopy(pending)],
            complete=False,
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("1 pending registry source(s), 1 assigned source(s), 0 verified source group(s), 0 row(s)", stdout)

    def test_rejects_pending_assignment_mismatch(self):
        pending = {
            "task_group_id": "a26_i_01",
            "stable_source_id": "A26-I-01",
            "source_dataset": "AIME",
            "source_year": 2026,
            "domain": "math",
            "split": "primary_test",
            "report_partition": "primary_test",
            "recipe": "M4",
            "owner_id": "P1",
            "reviewer_id": "P5",
            "import_status": "pending",
            "provenance_status": "pending_source_audit",
            "license_status": "pending_review",
            "source_hash_status": "pending_after_acquisition",
            "problem_text_redistribution": "not_redistributed",
            "statement_text_included": False,
            "expected_authored_rows": 4,
            "expected_primary_rows": 4,
            "expected_robustness_rows": 0,
        }
        assigned = copy.deepcopy(pending)
        assigned["owner_id"] = "P2"
        code, _stdout, stderr = self.run_validator(registry=[pending], assigned=[assigned], complete=False)
        self.assertEqual(code, 1)
        self.assertIn("assigned source group owner_id does not match source registry", stderr)

    def test_rejects_math_pending_registry_without_source_year(self):
        pending = {
            "task_group_id": "a26_i_01",
            "stable_source_id": "A26-I-01",
            "source_dataset": "AIME",
            "source_year": None,
            "domain": "math",
            "split": "primary_test",
            "report_partition": "primary_test",
            "recipe": "M4",
            "owner_id": "P1",
            "reviewer_id": "P5",
            "import_status": "pending",
            "provenance_status": "pending_source_audit",
            "license_status": "pending_review",
            "source_hash_status": "pending_after_acquisition",
            "problem_text_redistribution": "not_redistributed",
            "statement_text_included": False,
            "expected_authored_rows": 4,
            "expected_primary_rows": 4,
            "expected_robustness_rows": 0,
        }
        code, _stdout, stderr = self.run_validator(registry=[pending], complete=False)
        self.assertEqual(code, 1)
        self.assertIn("math records must have a concrete source_year", stderr)

    def test_rejects_label_class_mismatch(self):
        sources = load_jsonl(VALID / "source_groups.jsonl")
        rows = load_jsonl(VALID / "authored_rows.jsonl")
        rows[0]["binary_label"] = "DO_NOT_ACCEPT"
        code, _stdout, stderr = self.run_validator(sources, rows)
        self.assertEqual(code, 1)
        self.assertIn("valid_material must have binary_label ACCEPT", stderr)

    def test_rejects_trace_prefix_drift_within_group(self):
        sources = load_jsonl(VALID / "source_groups.jsonl")
        rows = load_jsonl(VALID / "authored_rows.jsonl")
        rows[1]["trace"] = copy.deepcopy(rows[1]["trace"])
        rows[1]["trace"]["prefix_sha256"] = "d" * 64
        code, _stdout, stderr = self.run_validator(sources, rows)
        self.assertEqual(code, 1)
        self.assertIn("share the same trace prefix metadata", stderr)

    def test_rejects_self_verification_and_wrong_owner(self):
        sources = load_jsonl(VALID / "source_groups.jsonl")
        rows = load_jsonl(VALID / "authored_rows.jsonl")
        rows[0]["verification"]["author_id"] = "P2"
        rows[0]["verification"]["verifier_id"] = "P2"
        code, _stdout, stderr = self.run_validator(sources, rows)
        self.assertEqual(code, 1)
        self.assertIn("verification.verifier_id must differ from author_id", stderr)
        self.assertIn("verification.author_id must match source group owner_id", stderr)

    def test_rejects_development_test_template_family_leakage(self):
        sources = load_jsonl(VALID / "source_groups.jsonl")
        rows = load_jsonl(VALID / "authored_rows.jsonl")
        test_source = copy.deepcopy(sources[0])
        test_source["task_group_id"] = "math_aime_2026_i_p01"
        test_source["source_year"] = 2026
        test_source["split"] = "primary_test"
        test_source["recipe"] = "M4"
        test_source["statement_sha256"] = "e" * 64
        test_rows = []
        for diagnostic_class in (
            "valid_material",
            "true_non_material",
            "plausible_false_material",
            "malicious_override",
        ):
            row = copy.deepcopy(rows[0])
            row["example_id"] = f"test__{diagnostic_class}"
            row["task_group_id"] = test_source["task_group_id"]
            row["source_year"] = 2026
            row["split"] = "primary_test"
            row["diagnostic_class"] = diagnostic_class
            row["binary_label"] = "ACCEPT" if diagnostic_class in {"valid_material", "true_non_material"} else "DO_NOT_ACCEPT"
            row["update_variant_id"] = "primary"
            row["update"] = f"test update {diagnostic_class}"
            row["update_template_family"] = "dev_valid_a" if diagnostic_class == "valid_material" else f"test_{diagnostic_class}"
            row["answer_changes"] = diagnostic_class == "valid_material"
            row["post_update_answer"] = "43" if diagnostic_class == "valid_material" else "42"
            test_rows.append(row)
        code, _stdout, stderr = self.run_validator(sources + [test_source], rows + test_rows)
        self.assertEqual(code, 1)
        self.assertIn("appears in both development and primary_test", stderr)

    def test_rejects_incomplete_recipe_when_requested(self):
        sources = load_jsonl(VALID / "source_groups.jsonl")
        rows = load_jsonl(VALID / "authored_rows.jsonl")[:-1]
        code, _stdout, stderr = self.run_validator(sources, rows)
        self.assertEqual(code, 1)
        self.assertIn("D8 group math_aime_2024_i_p01 is missing rows", stderr)


if __name__ == "__main__":
    unittest.main()

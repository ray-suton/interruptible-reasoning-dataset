import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "sources" / "upstream_interrupt_lrm"


class ImportedSourceSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((SOURCE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        cls.source_bytes = (SOURCE_ROOT / "math_source_problems.jsonl").read_bytes()
        cls.sources = [json.loads(line) for line in cls.source_bytes.decode("utf-8").splitlines()]
        cls.link_bytes = (SOURCE_ROOT / "stage1_aime_links.jsonl").read_bytes()
        cls.links = [json.loads(line) for line in cls.link_bytes.decode("utf-8").splitlines()]

    def test_pinned_snapshot_manifest_and_hashes(self):
        self.assertEqual(self.manifest["record_count"], 1060)
        self.assertEqual(
            self.manifest["revision"],
            "6ac4ea4baadeccafbb452c1649c90e24ffac4cfc",
        )
        self.assertEqual(hashlib.sha256(self.source_bytes).hexdigest(), self.manifest["output_sha256"])
        self.assertEqual(
            hashlib.sha256(self.link_bytes).hexdigest(),
            self.manifest["stage1_aime_links_sha256"],
        )

    def test_only_original_source_fields_are_imported(self):
        required = {"original_problem", "original_answer", "original_record_sha256"}
        forbidden = {"revised_problem", "update"}
        for record in self.sources:
            self.assertTrue(required.issubset(record))
            self.assertTrue(forbidden.isdisjoint(record))
            self.assertTrue(record["original_problem"])

    def test_expected_source_family_counts(self):
        counts = Counter(record["source_family"] for record in self.sources)
        self.assertEqual(
            counts,
            Counter({"gsm8k": 500, "math500": 500, "aime2024": 30, "aime2025": 30}),
        )

    def test_aime_links_cover_both_parts_and_years(self):
        expected = {
            f"A{year}-{'I' if part == 1 else 'II'}-{problem:02d}"
            for year in (24, 25)
            for part in (1, 2)
            for problem in range(1, 16)
        }
        actual = {record["stable_source_id"] for record in self.links}
        self.assertEqual(actual, expected)
        self.assertEqual(len(self.links), 60)
        self.assertEqual(len({record["original_record_sha256"] for record in self.links}), 60)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_generate_scaffold():
    spec = importlib.util.spec_from_file_location(
        "generate_scaffold",
        ROOT / "scripts" / "generate_scaffold.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path, records):
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


class GenerateScaffoldCheckTests(unittest.TestCase):
    def test_check_allows_real_contributor_work(self):
        scaffold = load_generate_scaffold()
        groups = scaffold.build_groups()
        registry = scaffold.registry_records(groups)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry_dir = tmp_path / "registry"
            contributors_dir = tmp_path / "contributors"
            registry_dir.mkdir()
            contributors_dir.mkdir()

            write_jsonl(registry_dir / "source_registry.jsonl", registry)
            for person in scaffold.PEOPLE:
                person_dir = contributors_dir / person
                person_dir.mkdir()
                assigned = [record for record in registry if record["owner_id"] == person]
                write_jsonl(person_dir / "assigned_source_groups.jsonl", assigned)
                (person_dir / "source_groups.jsonl").write_text(
                    '{"task_group_id":"already_started"}\n',
                    encoding="utf-8",
                )
                (person_dir / "authored_rows.jsonl").write_text("", encoding="utf-8")
                (person_dir / "review_responses.jsonl").write_text("", encoding="utf-8")

            original_registry_dir = scaffold.REGISTRY_DIR
            original_contributors_dir = scaffold.CONTRIBUTORS_DIR
            try:
                scaffold.REGISTRY_DIR = registry_dir
                scaffold.CONTRIBUTORS_DIR = contributors_dir
                scaffold.check_outputs(groups)
            finally:
                scaffold.REGISTRY_DIR = original_registry_dir
                scaffold.CONTRIBUTORS_DIR = original_contributors_dir


if __name__ == "__main__":
    unittest.main()

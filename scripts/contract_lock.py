#!/usr/bin/env python3
"""Version and hash the authoring contract so "locked" is checkable, not social.

The authoring contract is the set of documents that decide whether a row is
valid. Once smoke-test generation begins, a silent edit to any of them means
different rows were built to different rules, and nothing in the repository
would record that. This script pins the contract by content hash into
`registry/contract_lock.json`.

Two operations:

    lock    write the current hashes, with a version and a reason
    check   fail if any contract file no longer matches the recorded hashes

`check` is the useful one: run it in CI and before authoring, so an unrecorded
contract change is a build failure rather than a discovery months later.

This is deliberately NOT the evaluation freeze described in DATASET.md section 5
(model, prompts, probe layer, threshold, evaluation code). That freeze governs
one-shot primary-test scoring and happens later. Locking the authoring contract
early is safe and useful; freezing the evaluation early would force the model
choice before the pilot has informed it.

Amending a locked contract:

 1. open a PR that changes the contract file AND re-runs `lock` with a reason;
 2. state in the PR which already-authored rows or generated smoke artifacts
    the change invalidates;
 3. get the amendment reviewed by someone who is not its author, per the
    no-self-review rule; and
 4. re-verify affected rows before they re-enter the dataset.

An amendment bumps `version`. The previous entry is kept in `history` so the
rules any given row was authored under remain recoverable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / "registry" / "contract_lock.json"

# Paths are relative to this repository root. `init.sh` runs this check, so the
# lock must work in a standalone clone and cannot depend on parent workspace
# documents that are not versioned with this repository.
CONTRACT_FILES = [
    "schema/dataset_row.schema.json",
    "schema/source_group.schema.json",
    "schema/source_registry.schema.json",
    "schema/review_response.schema.json",
    "scripts/validate_dataset.py",
    "DATASET.md",
    # The canonical annotator-facing label policy. docs/original/README.md declares
    # this copy canonical with the workspace-root copy synced to match, but nothing
    # enforced that: the root copy was amended on 2026-08-08 while this one was not,
    # and the divergence went unnoticed. Locking it makes the next such drift a
    # build failure.
    "docs/original/label_policy.md",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_hashes() -> tuple[dict[str, str], list[str]]:
    hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in CONTRACT_FILES:
        path = REPO_ROOT / rel
        if path.is_file():
            hashes[rel] = sha256(path)
        else:
            missing.append(rel)
    return hashes, missing


def load_lock() -> dict | None:
    if not LOCK_PATH.is_file():
        return None
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def do_lock(reason: str, locked_by: str, stamp: str | None) -> int:
    hashes, missing = current_hashes()
    if missing:
        print("refusing to lock; contract files not found:", file=sys.stderr)
        for rel in missing:
            print(f"  {rel}", file=sys.stderr)
        return 1

    previous = load_lock()
    version = 1 if previous is None else int(previous.get("version", 0)) + 1
    history = list(previous.get("history", [])) if previous else []
    if previous:
        history.append({k: previous[k] for k in ("version", "locked_at", "locked_by", "reason", "files") if k in previous})

    lock = {
        "description": "Content hashes of the Stage 1 authoring contract. See scripts/contract_lock.py.",
        "version": version,
        "locked_at": stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "locked_by": locked_by,
        "reason": reason,
        "files": hashes,
        "history": history,
    }
    LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"locked contract version {version} over {len(hashes)} file(s) -> {LOCK_PATH.relative_to(REPO_ROOT)}")
    for rel, digest in hashes.items():
        print(f"  {digest[:12]}  {rel}")
    return 0


def check_workspace_mirrors() -> list[str]:
    """Report canonical snapshots whose workspace-root mirror has drifted.

    `docs/original/README.md` declares these copies canonical with the root copies
    synced to match, but that rule was social until now: on 2026-08-08 the label
    policy was amended in root only, and `methodology.md` and
    `dataset_construction_design.md` were found diverged in OPPOSITE directions --
    root newer for one, canonical newer for the other. Hashing the canonical file
    alone cannot catch that, so the mirror is compared explicitly.

    Advisory: the workspace root may legitimately be absent (standalone clone).
    """
    original = REPO_ROOT / "docs" / "original"
    workspace = REPO_ROOT.parent
    if not original.is_dir() or not workspace.is_dir():
        return []
    drifted = []
    for canon in sorted(original.glob("*.md")):
        if canon.name == "README.md":
            continue
        mirror = workspace / canon.name
        if mirror.is_file() and mirror.read_bytes() != canon.read_bytes():
            drifted.append(canon.name)
    return drifted


def do_check() -> int:
    lock = load_lock()
    if lock is None:
        print(
            "contract is not locked yet; run:\n"
            "  python3 scripts/contract_lock.py lock --reason '<why>' --locked-by P<n>",
            file=sys.stderr,
        )
        return 1

    recorded = lock.get("files", {})
    hashes, missing = current_hashes()
    problems: list[str] = []

    for rel in missing:
        if rel in recorded:
            problems.append(f"{rel}: locked but file is missing")
    for rel, digest in hashes.items():
        if rel not in recorded:
            problems.append(f"{rel}: present but not covered by the lock")
        elif recorded[rel] != digest:
            problems.append(
                f"{rel}: CHANGED since lock v{lock.get('version')}\n"
                f"    locked  {recorded[rel]}\n"
                f"    current {digest}"
            )

    if problems:
        print(f"contract lock v{lock.get('version')} FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nIf the change is intended, amend the lock in the same PR:\n"
            "  python3 scripts/contract_lock.py lock --reason '<why>' --locked-by P<n>\n"
            "and state which authored rows the change invalidates.",
            file=sys.stderr,
        )
        return 1

    print(f"contract lock v{lock.get('version')} OK ({len(recorded)} file(s) unchanged)")

    drifted = check_workspace_mirrors()
    if drifted:
        print(
            "WARNING: workspace-root mirror(s) differ from docs/original/:",
            file=sys.stderr,
        )
        for name in drifted:
            print(f"  {name}", file=sys.stderr)
        print(
            "docs/original/ is canonical and root copies are synced to match.\n"
            "Check which side is newer before copying -- these have drifted in\n"
            "opposite directions before.",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    lock_cmd = sub.add_parser("lock", help="record current contract hashes")
    lock_cmd.add_argument("--reason", required=True, help="why the contract is being locked or amended")
    lock_cmd.add_argument("--locked-by", required=True, help="owner id, e.g. P1")
    lock_cmd.add_argument("--timestamp", default=None, help="override the UTC timestamp (for reproducible tests)")

    sub.add_parser("check", help="fail if any contract file changed since the lock")

    args = parser.parse_args(argv)
    if args.command == "lock":
        return do_lock(args.reason, args.locked_by, args.timestamp)
    return do_check()


if __name__ == "__main__":
    raise SystemExit(main())

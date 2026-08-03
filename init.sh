#!/usr/bin/env bash
set -euo pipefail

python3 scripts/generate_scaffold.py --check
make validate-scaffold
make test

#!/usr/bin/env sh
set -eu

python3 scripts/check-version.py
python3 -m unittest discover -s tests -t .
PYTHONPATH=src python3 -m agent_scope_diff.cli fixtures/simple-before.json fixtures/simple-after.json --no-color --summary-only


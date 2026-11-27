#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m lab.analyze firmware/*.c
python3 -m unittest discover -s tests -p 'test_tooling.py' -v
python3 -m lab.evaluate compare

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
build_dir=$(mktemp -d)
trap 'rm -rf -- "$build_dir"' EXIT

"${CC:-cc}" -std=c11 -Wall -Wextra -Wpedantic -Wconversion -Werror \
    -Ifirmware firmware/temperature.c tests/test_temperature.c \
    -o "$build_dir/test_temperature"
"$build_dir/test_temperature"

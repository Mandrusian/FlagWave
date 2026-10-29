#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TEST_DIR"' EXIT
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined "$ROOT/android/tests/cloth_test.cpp" -o "$TEST_DIR/cloth-test"
ASAN_OPTIONS=detect_leaks=0 "$TEST_DIR/cloth-test"
printf 'Cloth engine tests passed.\n'

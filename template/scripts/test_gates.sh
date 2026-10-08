#!/usr/bin/env bash
# Regression test for scripts/gates. Usage: test_gates.sh [path-to-gates]   (default: the gates next to this file)
# Checks, on a config whose last line has no trailing newline and whose comment holds an apostrophe:
#   - the last line still runs and its failure is reported,
#   - the comment prints no warning,
#   - the script exits 1 when a gate fails.
set -u
gates="${1:-$(cd "$(dirname "$0")" && pwd)/gates}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/scripts"; cp "$gates" "$tmp/scripts/gates"
printf "# a comment with an apostrophe isn't a gate\npass | . | true\nfail | . | false" > "$tmp/scripts/gates.conf"
out="$("$tmp/scripts/gates" 2>&1)"; code=$?
bad=0
[ "$code" = 1 ] || { echo "FAIL: expected exit 1, got $code"; bad=1; }
printf '%s\n' "$out" | grep -q '^PASS  pass' || { echo "FAIL: the passing gate did not report"; bad=1; }
printf '%s\n' "$out" | grep -q '^FAIL  fail' || { echo "FAIL: the last line (no trailing newline) did not run"; bad=1; }
printf '%s\n' "$out" | grep -qi 'xargs' && { echo "FAIL: a quote in a comment printed a warning"; bad=1; }
[ "$bad" = 0 ] && echo "gates test ok"
exit "$bad"

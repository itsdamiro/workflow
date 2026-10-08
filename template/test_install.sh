#!/usr/bin/env bash
# Tests for the Gemini command step of install.sh, with HOME pointed at a throwaway folder. Usage: test_install.sh
set -u
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
bad=0; ok() { [ "$1" = 0 ] || { echo "FAIL: $2"; bad=1; }; }
cmd="$tmp/.gemini/commands/handoff.toml"

HOME="$tmp" "$here/install.sh" --dry-run >/dev/null 2>&1
[ ! -e "$cmd" ]; ok $? "--dry-run writes no command"

HOME="$tmp" "$here/install.sh" >/dev/null 2>&1
[ -s "$cmd" ]; ok $? "the command is written"
grep -q '__WORKFLOW__' "$cmd"; [ $? != 0 ]; ok $? "no placeholder is left"
grep -qF '!{cat "'"$root"'/docs/sop/handoff.md"}' "$cmd"; ok $? "the command injects this checkout's procedure, by shell so it works outside the workspace"
[ -s "$root/docs/sop/handoff.md" ]; ok $? "the procedure the command points at exists"
grep -qF '{{args}}' "$cmd"; ok $? "the arguments reach the prompt"
python3 -c 'import sys,tomllib; d=tomllib.load(open(sys.argv[1],"rb")); assert d["prompt"] and d["description"]' "$cmd"; ok $? "the command is valid TOML with a prompt and a description"

cp "$cmd" "$tmp/first"; HOME="$tmp" "$here/install.sh" >/dev/null 2>&1
cmp -s "$cmd" "$tmp/first"; ok $? "running again changes nothing"

printf 'prompt = "mine"\n' > "$cmd"
HOME="$tmp" "$here/install.sh" 2>&1 | grep -q 'handoff: a file you wrote is already there'; ok $? "a command the owner wrote is reported"
grep -q mine "$cmd"; ok $? "a command the owner wrote is never overwritten"

exit $bad

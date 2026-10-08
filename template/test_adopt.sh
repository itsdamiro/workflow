#!/usr/bin/env bash
# Tests for adopt.sh on a throwaway repository. Usage: test_adopt.sh
set -u
here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
proj="$tmp/p"; mkdir "$proj" && git -C "$proj" init -q -b main
bad=0; ok() { [ "$1" = 0 ] || { echo "FAIL: $2"; bad=1; }; }

out="$("$here/adopt.sh" "$proj" --name "A/B & C" 2>&1)"
echo "$out" | grep -q 'created  git hook commit-msg'; ok $? "the commit-msg hook is installed"
[ -x "$proj/.git/hooks/commit-msg" ]; ok $? "the installed hook is executable"
head -1 "$proj/CLAUDE.md" | grep -qF '# A/B & C'; ok $? "a name with / and & reaches CLAUDE.md"
[ ! -e "$proj/CLAUDE.md.bak" ]; ok $? "no .bak file is left behind"
grep -q 'CLAUDE.md' "$proj/.gitignore"; ok $? "the no-trace block is in .gitignore"
[ -x "$proj/scripts/gates" ]; ok $? "scripts/gates is executable"

echo 'edited' >> "$proj/CLAUDE.md"; printf '#!/bin/sh\necho mine\n' > "$proj/.git/hooks/commit-msg"
out="$("$here/adopt.sh" "$proj" 2>&1)"
echo "$out" | grep -q 'differs  CLAUDE.md'; ok $? "an edited file is reported, not overwritten"
grep -q edited "$proj/CLAUDE.md"; ok $? "an existing file is kept"
echo "$out" | grep -q 'differs  git hook commit-msg'; ok $? "another hook is reported"
grep -q mine "$proj/.git/hooks/commit-msg"; ok $? "another hook is never overwritten"

rm "$proj/.git/hooks/commit-msg"
"$here/adopt.sh" "$proj" --check 2>&1 | grep -q 'missing  git hook commit-msg'; ok $? "--check reports a missing hook"
[ ! -e "$proj/.git/hooks/commit-msg" ]; ok $? "--check changes nothing"

[ "$bad" = 0 ] && echo "adopt tests ok"
exit "$bad"

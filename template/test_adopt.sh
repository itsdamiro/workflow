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
[ -x "$proj/scripts/md_wrap_check.py" ]; ok $? "the markdown wrap checker is installed and executable"
grep -q md_wrap_check "$proj/scripts/gates.conf"; ok $? "the wrap checker is a gate in the project's list"
[ -x "$proj/scripts/adr_check.py" ]; ok $? "the decision-record shape check is installed and executable"
grep -q '^adr-check .*adr_check.py' "$proj/scripts/gates.conf"; ok $? "the shape check is a gate in the project's list"
for f in docs/VAULT_CONVENTIONS.md docs/decisions/TEMPLATE.md docs/sop/write-an-adr.md docs/sop/rename-a-concept.md; do
  [ -s "$proj/$f" ]; ok $? "$f is installed"
done
grep -q VAULT_CONVENTIONS "$proj/CLAUDE.md"; ok $? "the contents page points at the conventions"
[ "$(cat "$proj/docs/.template-version")" = "$(cat "$here/VERSION")" ]; ok $? "the version is recorded"

echo 'edited' >> "$proj/CLAUDE.md"; printf '#!/bin/sh\necho mine\n' > "$proj/.git/hooks/commit-msg"
out="$("$here/adopt.sh" "$proj" 2>&1)"
echo "$out" | grep -q 'differs  CLAUDE.md'; ok $? "an edited file is reported, not overwritten"
grep -q edited "$proj/CLAUDE.md"; ok $? "an existing file is kept"
echo "$out" | grep -q 'differs  git hook commit-msg'; ok $? "another hook is reported"
grep -q mine "$proj/.git/hooks/commit-msg"; ok $? "another hook is never overwritten"

echo "$out" | grep -q 'has no adr-check gate'; [ $? != 0 ]; ok $? "no hint while the shape check is in the project's gate list"
sed -i.bak '/^adr-check/d' "$proj/scripts/gates.conf" && rm -f "$proj/scripts/gates.conf.bak"
"$here/adopt.sh" "$proj" 2>&1 | grep -q 'note     scripts/gates.conf has no adr-check gate'; ok $? "a gate list without the shape check gets a hint"
"$here/adopt.sh" "$proj" --check 2>&1 | grep -q 'has no adr-check gate'; ok $? "--check gives the hint too"
grep -q adr-check "$proj/scripts/gates.conf"; [ $? != 0 ]; ok $? "the gate list is not edited"

rm "$proj/.git/hooks/commit-msg"
"$here/adopt.sh" "$proj" --check 2>&1 | grep -q 'missing  git hook commit-msg'; ok $? "--check reports a missing hook"
[ ! -e "$proj/.git/hooks/commit-msg" ]; ok $? "--check changes nothing"
rm "$proj/docs/sop/rename-a-concept.md"
"$here/adopt.sh" "$proj" --check 2>&1 | grep -q 'missing  docs/sop/rename-a-concept.md'; ok $? "--check reports a missing procedure"
[ ! -e "$proj/docs/sop/rename-a-concept.md" ]; ok $? "--check does not restore it"

[ "$bad" = 0 ] && echo "adopt tests ok"
exit "$bad"

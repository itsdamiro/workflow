#!/usr/bin/env bash
# Tests for the commit-msg hook: every way a trailer can arrive is refused, an ordinary message is not.
# Usage: test_commit_msg.sh [path-to-hook]   (default: the hook next to this file)
set -u
hook="${1:-$(cd "$(dirname "$0")" && pwd)/commit-msg}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git -C "$tmp" init -q -b main && git -C "$tmp" config user.name t && git -C "$tmp" config user.email t@example.com
cp "$hook" "$tmp/.git/hooks/commit-msg" && chmod +x "$tmp/.git/hooks/commit-msg"
n=0; bad=0
try() {  # try <expect: ok|refuse> <label> <git commit args...>
  want="$1"; label="$2"; shift 2; n=$((n + 1))
  echo "$n" > "$tmp/f$n"; git -C "$tmp" add "f$n"
  if git -C "$tmp" commit -q "$@" >/dev/null 2>&1; then got=ok; else got=refuse; fi
  [ "$got" = "$want" ] || { echo "FAIL: $label (wanted $want, got $got)"; bad=1; }
}
printf 'fix a thing\n\nCo-authored-by: A <a@b.c>\n' > "$tmp/msg_co";   printf 'fix\n\nSigned-off-by: A <a@b.c>\n' > "$tmp/msg_so"
printf 'fix a thing\n\nbody text\n' > "$tmp/msg_ok";                   printf 'fix\n\nGenerated with a tool\n' > "$tmp/msg_gen"
try ok     "an ordinary message"            -m "Fix the thing"
try ok     "an ordinary message from -F"    -F "$tmp/msg_ok"
try ok     "prose that mentions a trailer"  -m "Explain why co-authored-by lines are not used"
try ok     "a mid-sentence mention with a colon" -m "Explain why co-authored-by: lines are rejected"
try refuse "a trailer in a comment line"    -m "$(printf 'x\n\n# Generated with a tool')"
try refuse "Co-authored-by in -m"           -m "$(printf 'x\n\nCo-authored-by: A <a@b.c>')"
try refuse "Co-authored-by from -F"         -F "$tmp/msg_co"
try refuse "Signed-off-by from -F"          -F "$tmp/msg_so"
try refuse "-s adds Signed-off-by"          -s -m "x"
try refuse "--trailer"                      -m "x" --trailer "Co-authored-by: A <a@b.c>"
try refuse "Generated with"                 -F "$tmp/msg_gen"
try refuse "noreply@anthropic.com"          -m "x noreply@anthropic.com"
[ "$bad" = 0 ] && echo "commit-msg tests ok ($n cases)"
exit "$bad"

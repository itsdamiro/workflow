#!/usr/bin/env bash
# Bring a project onto the template. Never overwrites: a file that exists is kept, and reported if it differs.
# Usage: ./adopt.sh <project-dir> [--name "Project Name"] [--gemini]
#        ./adopt.sh <project-dir> --check      report drift from the template, change nothing
set -eu
here="$(cd "$(dirname "$0")" && pwd)"
proj="${1:?usage: adopt.sh <project-dir> [--name NAME] [--gemini] | --check}"; shift
name="$(basename "$(cd "$proj" && pwd)")"; gemini=0; check=0
while [ $# -gt 0 ]; do
  case "$1" in --name) name="$2"; shift ;; --gemini) gemini=1 ;; --check) check=1 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; shift
done
version="$(cat "$here/VERSION")"
installed="$(cat "$proj/docs/.template-version" 2>/dev/null || echo none)"
echo "template v$version; project is on: $installed"

# source -> destination (relative to the project)
pairs=(
  "CLAUDE.template.md|CLAUDE.md"
  "docs/COLLABORATION_STANDARDS.md|docs/COLLABORATION_STANDARDS.md"
  "docs/CODE_QUALITY_STANDARDS.md|docs/CODE_QUALITY_STANDARDS.md"
  "docs/CLOSING_A_SLICE.md|docs/CLOSING_A_SLICE.md"
  "docs/HANDOFF.template.md|docs/HANDOFF.md"
  "docs/reference/GOTCHAS.template.md|docs/reference/GOTCHAS.md"
  "scripts/gates|scripts/gates"
  "scripts/gates.conf.template|scripts/gates.conf"
  "scripts/mutate.py|scripts/mutate.py"
  "scripts/md_wrap_check.py|scripts/md_wrap_check.py"
)
[ "$gemini" = 1 ] && pairs+=("GEMINI.template.md|GEMINI.md")

for pair in "${pairs[@]}"; do
  src="$here/${pair%%|*}"; dst="$proj/${pair##*|}"
  if [ -e "$dst" ]; then
    # entry points and per-project files are filled in, so a difference is expected; shared files should match
    if cmp -s "$src" "$dst"; then echo "  same     ${pair##*|}"; else echo "  differs  ${pair##*|}   (diff -u '$src' '$dst')"; fi
  elif [ "$check" = 1 ]; then
    echo "  missing  ${pair##*|}"
  else
    mkdir -p "$(dirname "$dst")"; cp "$src" "$dst"
    case "$dst" in */CLAUDE.md|*/GEMINI.md) sed -i.bak "s/\[PROJECT NAME\]/$(printf '%s' "$name" | sed 's/[\/&]/\\&/g')/" "$dst" && rm -f "$dst.bak" ;; esac
    case "$dst" in */scripts/gates|*/scripts/mutate.py|*/scripts/md_wrap_check.py) chmod +x "$dst" ;; esac
    echo "  created  ${pair##*|}"
  fi
done

# the commit-msg hook (no attribution trailer, whatever the tool): into the project's git hooks, never over another hook
hooksdir="$(git -C "$proj" rev-parse --git-path hooks 2>/dev/null || true)"
if [ -n "$hooksdir" ]; then
  case "$hooksdir" in /*) ;; *) hooksdir="$proj/$hooksdir" ;; esac
  src="$here/git-hooks/commit-msg"; dst="$hooksdir/commit-msg"
  if [ -e "$dst" ]; then
    if cmp -s "$src" "$dst"; then echo "  same     git hook commit-msg"; else echo "  differs  git hook commit-msg   (diff -u '$src' '$dst')"; fi
  elif [ "$check" = 1 ]; then
    echo "  missing  git hook commit-msg"
  else
    mkdir -p "$hooksdir"; cp "$src" "$dst"; chmod +x "$dst"; echo "  created  git hook commit-msg"
  fi
fi

[ "$check" = 1 ] && exit 0

# the no-AI-trace block, appended once
if ! grep -qs "AI assistant & editor tooling" "$proj/.gitignore" 2>/dev/null; then
  printf '\n# AI assistant & editor tooling — never committed\n.agents/\n.claude/\n.gemini/\n.cursor/\nCLAUDE.md\nGEMINI.md\n' >> "$proj/.gitignore"
  echo "  appended the no-trace block to .gitignore"
fi
# a place to say which directories must be staged by file name (generated output)
mkdir -p "$proj/.claude"
[ -e "$proj/.claude/git-safety.deny-add" ] || printf '# one path per line: `git add <path>` is blocked; stage its files by name\n' > "$proj/.claude/git-safety.deny-add"

echo "$version" > "$proj/docs/.template-version"
cat <<MSG

next:
  1. fill the blanks in CLAUDE.md and scripts/gates.conf (run scripts/gates to see it work)
  2. list generated-output directories in .claude/git-safety.deny-add
  3. write docs/HANDOFF.md, then run the checking-a-handoff skill on it
  4. CONTRIBUTING.snippet.md goes into the project's CONTRIBUTING.md (the committed home of the no-trace policy)
MSG

# Contributing

## Repository hygiene

These are strict, not aspirational.

- **Single author identity.** Every commit is authored and committed by the repository owner (`damiro <hello.damiro@gmail.com>`). No secondary identities, no aliases.
- **No trailers.** Commits carry no `Co-authored-by`, `Signed-off-by`, or tooling/attribution trailers of any kind.
- **Assistant and editor tooling is never committed.** `.agents/`, `.claude/`, `.gemini/`, `.cursor/`, `CLAUDE.md`, `GEMINI.md`, `.vscode/`, and the like are local-only. They're covered machine-wide by `core.excludesFile` and, belt-and-braces, by this repo's own `.gitignore`. A new repository copies the same block:

  ```gitignore
  # AI assistant & editor tooling — never committed
  .agents/
  .claude/
  .gemini/
  .cursor/
  CLAUDE.md
  GEMINI.md
  ```

- Referring to the underlying models (Claude, Gemini, or others) in code, docs, or configuration is fine, where the project's subject matter actually involves them. The rule is about authorship and tooling artifacts, not the project's subject matter.

## Branching

- **Default: commit straight to `main`.** Most work here is small and self-contained (a doc, a script, an ADR), and a branch would add ceremony without adding review, since there's no second person to review it.
- **Branch when a change won't leave `main` working at every commit along the way**: a whole milestone that spans more than one sitting before it is usable. Merge back once it works end to end; delete the branch after.
- The test, if it's ever unclear: can you answer "does `main` still work" with yes after every single commit in the change? Yes at every point → direct to `main`. No for a stretch in the middle → branch.

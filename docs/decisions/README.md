# Decision records

Lightweight records for anything durable. Format: `TEMPLATE.md`. Standard: `docs/CODE_QUALITY_STANDARDS.md` §9.

| # | Decision | Status |
|---|---|---|
| [001](001-context-length-not-code-graphs.md) | Spend effort on session length, not on a code graph | Accepted |
| [002](002-portable-by-layers.md) | Portable by layers: files and scripts, procedures, optional adapters | Accepted |
| [003](003-vault-is-personal-output.md) | The repo is the source of truth; the vault is personal output | Accepted |
| [004](004-vault-notes-names-frontmatter-tags.md) | Vault notes: names, frontmatter, links, tags | Accepted |
| [005](005-one-handoff-command.md) | One `/handoff` procedure closes a slice | Accepted |
| [006](006-pattern-scan-every-handoff.md) | Scan each slice's diff for reusable patterns | Accepted |
| [007](007-graphify-optional-later.md) | Graphify is not part of the core; try it later for outside sources | Accepted |
| [008](008-template-lives-in-this-repo.md) | The project template and its scripts live in this repository | Accepted |
| [009](009-vault-sync-rules.md) | `vault_sync.py`: what it reads, what it writes, and when it refuses | Accepted |
| [010](010-vault-lint-rules.md) | `vault_lint.py`: what it checks, and what it never does | Accepted |
| [011](011-concept-names-and-aliases.md) | Concept names: readable, with aliases that survive a rename | Accepted |
| [012](012-decision-records-and-vault-conventions-travel-with-the-template.md) | Decision records and vault conventions travel with the template | Accepted |
| [013](013-code-map-from-module-docstrings.md) | The code map is the committed Python module docstrings, copied unchanged | Accepted |

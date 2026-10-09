---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Session length]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/cost]
---

# 001 — Spend effort on session length, not on a code graph

> **Summary.** Measured on one project's Claude Code transcripts, reading code is a small share of token use; carrying a long conversation is the large one. So the first work is making handoffs cheap and sessions short, not adding a code graph.

## Context

Two videos about a code-graph tool plus Obsidian claimed large token savings because the assistant would stop re-reading code. Before adopting anything, the owner's own sessions were measured (read-only, aggregates only).

Measured on 127 sessions with at least 5 messages, about 34,000 assistant messages, one project, Claude Code:

- Prompts that ask how the code is structured are rare: one under a strict filter, about 80 under a loose one, nearly all chat. Sessions are almost all "do the work".
- Code files read but not edited in the same turn (the only reads a graph could replace): about 1.4M tokens over the whole history, against about 71M tokens newly written to the cache. Roughly 2%.
- A first pass overstated reading about fourfold: 527 screenshot reads were counted by their base64 text.
- About 9.4 billion context tokens were re-read from cache. At the usual cache price of about a tenth of normal input, that is roughly 80% of the weighted cost (an estimate from standard multipliers, not a bill).
- Median session: 176 messages. Median largest context: 327k tokens; maximum 967k. The longest 20% of sessions account for 65% of cache reads.
- Simulation: restart a session whenever context passes a cap, at a cost of about 59k tokens (47k baseline plus a handoff read). Cap 300k saves 40%, 200k saves 55%, 150k saves 63%, at about 146, 287 and 476 restarts over the history.

Limits: one project; main thread only (subagents excluded); characters divided by four as a token proxy; cache-write figures include rebuilds after idle gaps; the simulation assumes clean restart points. Nothing was measured on other models.

## Decision

Build, in this order: a cheap `/handoff` (ADR 005), a session guard that reminds the owner to use it (SPEC §8), then the vault. Do not adopt a code graph for token savings.

## Consequences

Savings depend on the owner restarting at slice boundaries; the guard only reminds. The measurement is kept as a script, `adapters/claude/context-report`, so it can be re-run on other projects (it reads Claude Code transcripts only; other models need their own reader).

## Alternatives rejected

- **A code graph for navigation.** The share it could replace is about 2% on the measured project. It would be right again if a project showed many multi-file exploration turns that were not edits.
- **Automatic compaction only.** It lowers the context but loses detail without the owner's review; a written handoff keeps what matters.

## Amendment (2026-10-09): the always-read standards are split by when they are needed

- **Why:** the baseline of every session is the files `CLAUDE.md` tells it to read first, and `docs/CODE_QUALITY_STANDARDS.md` was the largest, 17,241 bytes, of which §§1 to 6 (tooling, review tiers, triage, type safety) serve only a task that changes or reviews code. It is the same reasoning as the `handoff.md` split in ADR 005's amendment.
- **Done:** `docs/CODE_QUALITY_STANDARDS.md` keeps the rules every task needs (§0's working rules and §§7 to 13) and is 9,847 bytes. Sections 1 to 6 and four code rules from §0 (file-size cap, settings declared once, path safety, thread safety) moved, unchanged, to `docs/reference/CODE_REVIEW_STANDARDS.md` (7,162 bytes), read only for a code task. Section numbers are kept, so a citation such as `CODE_QUALITY_STANDARDS.md` §7 still finds its text. The template carries both files (this repo's `docs/` links to them), `template/adopt.sh` installs the second, and the template is version 17.
- **Dropped:** the footer crediting the Sympose audit, at the owner's word; the history keeps it.
- **Limit:** the reference file is read only if the assistant chooses to; nothing enforces it. A code task that skips it loses the review rules, not the working rules.
- **Alternatives rejected:** shortening every section in place: it keeps the code-only text in every session and rewrites wording that has paid for itself. Renumbering after the move: other files cite §7, §9 and §12.

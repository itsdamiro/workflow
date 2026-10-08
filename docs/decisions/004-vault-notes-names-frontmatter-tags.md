---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [vault-conventions]
amends: [003]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault]
---

# 004 — Vault notes: names, frontmatter, links, tags

> **Summary.** Cards are named `NNN - Sentence.md` from the repo slug; every note has frontmatter and at least one link; tags are namespaced and come from a controlled list.

## Context

The vault must stay connected as it grows, be countable, and be readable by Sympose, which searches titles first and reads frontmatter, tags and links (including quoted links in frontmatter).

## Decision

- **Names.** `NNN - Sentence from the slug.md`, built from the repo filename, not the heading (headings contain colons, slashes and backticks Obsidian rejects). The leading number is the match key. Links: `[[NNN - Sentence|ADR NNN]]`. Two identical names stop the sync.
- **Frontmatter on every note**, including folder definitions (fields in SPEC §4).
- **Links.** At least one per note, no orphans outside `Inbox/`, every link resolves. Links in frontmatter are quoted.
- **Tags.** Lowercase, namespaced, kebab-case, from a listed vocabulary. The sync adds `type/`, `status/` and `project/` from the fields; the owner adds `topic/`. A concept is something to write about; a tag is something to count by.
- **Renames and removals.** A rename leaves a redirect note; a removed ADR leaves a tombstone card.

## Consequences

A lint enforces all of the above. Statistics (ADRs per week, amendment rate, topics shared by two projects) come from fields and tags.

## Checked, and not yet checked

The tombstone and redirect rules were accepted on 2026-10-08. Checked the same day with Sympose's own code: the frontmatter, flow-list tags, quoted links and `[[name|alias]]` links all parse and resolve. Not yet checked: whether structural tags add noise to Sympose's shared-tag connections.

## Alternatives rejected

- **Number-only names (`040.md`).** Two projects both have an ADR 001, so names would collide, and Sympose's title-first search would lose the words.
- **Names from the heading.** Characters Obsidian rejects, and some headings run to a full sentence.
- **Tags only, no fields.** Structured facts (status, projects) are easier to check as fields.

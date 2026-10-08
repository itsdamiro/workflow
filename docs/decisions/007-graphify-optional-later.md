---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [intake]
amends: [001]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/intake]
---

# 007 — Graphify is not part of the core; try it later for outside sources

> **Summary.** The core uses frontmatter concepts and tags, which are deterministic. A graph-extraction tool is a possible later experiment for turning outside sources (articles, transcripts) into linked notes.

## Context

The tool extracts concepts and links from documents and exports them as Obsidian notes. Its document mode uses an AI model and tags each link as extracted, inferred or ambiguous. Unverified: whether it can run on a local model, whether separate runs merge the same concept, what its notes look like, whether it writes tooling files into a project. A walkthrough imported 145 documents as about 658 thin notes, which would crowd a search-based assistant's results.

## Decision

Leave it out of the core. Later, run it on a scratch vault over two projects' decisions, and measure: stub count, the share of extracted versus inferred links, whether one concept merges across projects, and retrieval quality with and without the stubs. Keep it only if it beats the tag approach.

## Consequences

Cross-project links come from `concepts` fields and a vocabulary the owner keeps.

## Alternatives rejected

- **Adopt it now for code navigation.** See ADR 001.
- **Import its notes straight into the vault.** A model-written layer that is unreviewed, thin and large.

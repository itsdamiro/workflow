# SOP: the weekly connect pass

For any assistant, with the owner. About five minutes a week. The vault only helps if its notes stay linked and true; this is the "lint" step of the wiki design, aimed at links and ideas as much as at stale text. The lint is `scripts/vault_lint.py`; the rest is reading.

## Steps

1. **Run the lint** (`python3 scripts/vault_lint.py <vault-path>`). List every error: a missing field, a link that does not resolve, a tag not in the list, a concept with no note. Then work through the warnings with the owner: a note with no links (the report names notes it could link), an orphan, a note with no tags, a topic not yet listed in `Tags.md` or given a note. Fix generated notes by fixing their source and syncing again; never hand-edit a note marked `generated: true`.
2. **Inbox.** For each outside source older than a few days: link it to a project or a concept, or tell the owner it has no home and propose deleting it. An Inbox note nobody links is the vault filling with noise.
3. **Ideas that cite one project.** An idea note links at least one project or concept. For each one that links only a single project, look for a second: another project's decision card, a pattern, a rejected alternative. Propose the link as a draft; the owner accepts.
4. **Concept vocabulary.** Find two concepts that mean the same thing (one should absorb the other) and tags used once (promote, merge or drop). Propose; the owner decides.
5. **Drafts.** List notes with `status: draft` older than two weeks: promote, edit or delete, with the owner.
6. **Read what the assistant wrote.** Skim the week's drafted notes for claims the owner never made. Delete what does not belong. This is the guard against the vault filling with an assistant's guesses.

## Do not

- Merge, rename or delete a note the owner wrote without asking.
- Add a claim to a note that the source documents do not support. Draft, cite, and let the owner accept.

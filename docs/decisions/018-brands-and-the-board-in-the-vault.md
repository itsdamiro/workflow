---
type: decision
status: accepted
date: 2026-10-15
projects: [workflow]
concepts: [Vault conventions]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/privacy]
---

# 018 — Brands have their own vault folder, and their images live in a gitignored `Board/` folder beside it

> **Summary.** Brand work gets a top-level `Brands/<slug>/` folder of notes (a hub, and `<slug> - <Title>.md` notes, one of them the `<slug> - Moodboard.md` list of items), plus a root `Board/<slug>/` folder that holds only image files and is gitignored. The slug is the one key joining them. A separate board app, built in its own repository, reads the notes and writes into `Board/` and the Moodboard note. It costs a new note type, one folder that git does not back up, and a Moodboard format the app must keep stable.

## Context

The owner wants to document the brands they work on, personal and client, in the vault that Sympose reads, and to build a small local web app for dropping in screenshots, links and inspiration with a one-line description each. What was settled in chat on 2026-10-15:

- Brands are not software projects: they have no repository, no records and no stats row, and `Projects/Projects.md` defines that folder as "one folder per software project". The lint reads `projects:` against folders under `Projects/`.
- A separate vault would break links: Sympose searches one vault at a time (ADR 003), and a brand will often be linked to the software that carries it.
- Most brands are the owner's own and attach to the apps they build; some are for clients. The vault's remote is private, but a client's assets or an unreleased name may still be confidential.
- The images must not enter git: screenshots would grow the history for good, and client images would reach the remote. The vault's `.gitignore` already ignores one image folder (`_Generated_Images`).
- Obsidian embeds (`![[name.png]]`) resolve only for files inside the vault, and not in a dot-folder. Sympose treats only `.md` files as notes (`NOTE_EXTENSIONS`), and the vault lint reads only `*.md` and skips links to files such as `pic.png`, so a folder of images is invisible to both.
- Stylo, Sympose's editor, renders `![[embed]]` only when the host supplies an `embedSource`, and only when the embed is alone on its line.
- The workflow repository holds the vault's rules (SPEC §4). An app's own design belongs in that app's repository (the owner, in `docs/HANDOFF.md`: Revwr work is done in its own repo, not here).

## Decision

1. **Notes.** `Brands/<slug>/` holds `<slug>.md` (the hub) and any number of `<slug> - <Title>.md` notes (`Positioning`, `Voice`, `Visual identity`, `Rejected ideas`, `Moodboard` are the expected ones; any other title is allowed). The slug is the folder name, in the owner's own spelling. `Brands/Brands.md` is the folder definition (SPEC §4). The type is `brand`, the status `active` or `draft`, and the fields are `type`, `status`, `created`, `tags: [type/brand, status/…]` and an optional `client: <name>`. A brand note needs no `projects:` and no `topic/` tag. A brand that carries or is carried by an app links to the project's hub and the hub links back; no field joins them.
2. **`client:` is the only personal-or-client switch.** Absent means personal. Present means client work, and then the vault holds the owner's own notes about the work (rationale, voice, rejected ideas, what was tried) and not the client's assets or unreleased material; descriptions and links in a Moodboard reach the private remote through git, so the owner writes them with that in mind.
3. **Images.** `Board/<slug>/<id>.<ext>` holds the image files and `Board/<slug>/thumbs/` their thumbnails. `<id>` is a sortable timestamp with a short suffix (`2026-10-15-1432-a3f9`). `Board/` is a root folder, not a dot-folder, so Obsidian embeds resolve, and it is listed in the vault's `.gitignore`. It holds no notes and has no definition note (the exception to SPEC §4). It needs no entry in Sympose's hidden list, because Sympose never reads files that are not notes.
4. **One key.** The folder name under `Brands/` equals the folder name under `Board/`. An item dropped before a brand is chosen goes to `Board/_unsorted/`.
5. **The Moodboard note.** `Brands/<slug>/<slug> - Moodboard.md` lists the items as blocks separated by a blank line, each block being: an optional embed line alone on its line (`![[<id>.<ext>]]`), the description (one or more lines), and an optional last line `[source](<url>)`. A reader takes a first line that starts with `![[` as the image, a last line that matches `[source](…)` as the link, and the rest as the description. New items are appended to the end; the app never edits a block (decision 6 names the one thing it may remove), and an edit made in Sympose or Obsidian is shown as it stands. The embed is alone on its line so Stylo can render it where its host resolves it.
6. **What the app may write.** The board app writes only under `Board/`, appends blocks to Moodboard notes, and removes a block on the owner's click (see the amendment of 2026-10-16); the description is the owner's own words, typed into the app, so no model-written claim reaches a note. It never edits any other note and never edits a block. This follows the append-only precedent of ADR 014 and the consent rule of ADR 017: the owner's act of pressing Enter is the approval of an added block, and the owner's click on one block, with a confirmation, is the approval of removing it.
7. **The vault side, written on the owner's yes (ADR 017).** `Brands/Brands.md`; the value `brand` added to the `type/` line of `Tags.md` (the lint reads the allowed types from that file, so no script changes); `Board/` added to the vault's `.gitignore`. They are shown in full first and are not part of this repository.
8. **Not decided here.** The app's own design (its local API, image processing, thumbnails, the paste flow, a later browser extension that sends the page address) is recorded in the app's repository. This record fixes only what the vault holds and the contract the app reads and writes.
9. **The documents follow.** SPEC §4 lists `Brands/` and `Board/` and the type `brand`; one lint test checks that a brand note without `projects`, carrying `client:` and image embeds, passes. `docs/VAULT_CONVENTIONS.md` is not changed: it describes how a project writes its records, and a brand has none.

## Consequences

A brand can be documented in the same vault as the software that carries it, searched by Sympose, and linked both ways, without being made to look like a project. The images stay out of git, so the history stays small and no client image reaches the remote; the cost is that `Board/` has no history and no remote, so it needs its own backup. On another machine, or on GitHub, an embed in a Moodboard points at a file that is not there; the note's text still reads.

A description or link in a Moodboard is text in git, so a client brand's Moodboard may carry something the owner would not want pushed; the rule in decision 2 is the owner's to follow, not something code checks. The Moodboard format is a contract: the app and the vault must agree on it, and changing it later means rewriting existing notes.

Left open: whether Sympose's `embedSource` shows `![[…png]]` (in Sympose's own repository; untested); whether the image-resizing dependency is Pillow (the app's repository); a backup for `Board/`; a browser extension as the app's second client; searching the images by description only through the Moodboard text.

## Alternatives rejected

- **Brands inside `Projects/`.** Reuses a folder, but gives each brand a place built for software (a records folder, a stats row, a lint check against a repository) that it does not have. Would be right if every brand were the brand of one app and nothing else.
- **A separate vault for brands.** Keeps client material apart, but Sympose reads one vault at a time, so links between a brand and its app would not resolve. Would be right if client work needed to be shared or deleted as a unit.
- **`relationship: personal | client`.** A second field to keep for no behaviour that `client:` being present or absent does not already give. Would be right if client work needed more states than "has a client".
- **Images in a dot-folder inside the vault.** Hidden from Obsidian and Sympose without a setting, but Obsidian embeds do not resolve from it. Would be right if the images were never shown in a note.
- **Images in the vault and in git, or in Git LFS.** One home for everything, but the history grows and client images reach the remote. Would be right for a small, own-brand-only vault with a public-safe remote.
- **Images outside the vault entirely.** Simplest for git, but a Moodboard could not embed them in Obsidian. Would be right if the owner only ever views them in the app.
- **Per-item data in a JSON file beside each image.** Easy to write, but gitignored, so the description is not searchable in Sympose or kept in git. Would be right if captions were to stay private to the app.
- **Hiding `Board/` in Sympose's settings.** Unneeded for images (Sympose reads only notes) and kept per machine in Sympose's own settings. Would be right if `Board/` ever held notes.

**Accepted** by the owner on 2026-10-15, in chat, as written.

## Amendment (2026-10-15): Sympose does not render image embeds

Checked in Sympose's code the same day: its embed resolver handles note embeds only ("asset serving isn't implemented on the backend"), and Stylo's preview does not enable raw HTML. So a Moodboard's `![[<id>.png]]` line, and any inline `<svg>`, shows as literal text in Sympose, while its description and `[source]` link read and search normally; Obsidian and the board app draw the images. The decision above is unchanged. "Left open" loses the question whether Sympose shows the embeds: it does not, and showing them is a feature of Sympose's own repository, not of this one.

## Amendment (2026-10-16): the app may remove a block the owner chooses

Decision 6 listed only appending under a Moodboard. The board app (its own repository, ADR 001 and its amendment of 2026-10-15) also deletes, because an owner who can add an item from a page expects to take one away. The owner decided that in chat on 2026-10-15 and asked for this amendment on 2026-10-16. Decisions 5 and 6 are edited above; the rest stands. What the app does today:

1. **It removes one block at a time, only when the owner asks.** On the board's page the owner points at an item's card, presses its delete button, and confirms in a dialog that names the item and says it cannot be undone. The owner may also pick several cards with shift-click and confirm once; the app then removes them one after the other, each as its own delete. Nothing is removed without that click and that confirmation.
2. **Any block the page shows may be removed, including one written by hand.** Decision 5's format has no marker, so for a block with no image the app cannot know who wrote it, and a marker would put text of the app's own into a note. The same holds for a block with an image.
3. **Only if the block is unchanged since it was shown.** The page holds a key for each block, a hash of the block's exact text. If the block was edited in Sympose or Obsidian after the page showed it, the app refuses and removes nothing, and the page says so. A block's heading, and the lines under a heading up to the next blank line, are not an item and are never removed.
4. **Its image files go with it.** The embed's id names the files, and the app removes `Board/<slug>/<id>.<ext>` and the thumbnail under `Board/<slug>/thumbs/`. A block whose embed is not an id the app made removes no files. If the block was removed but its files could not be, the app says so; the note is already right.
5. **How the note is rewritten.** The app writes the whole note to a hidden temporary file beside it (`.board-<random>.tmp`), checks that the note has not changed since it read it, and renames the file over the note, or removes it if anything fails, so a crash cannot leave half a note. Adding is unchanged: a block is only appended. The temporary file is the only write besides `Board/` and the Moodboard note, and it is gone when the app is done.
6. **What it still does not do.** It never edits a block's text, never touches another note (the hub and the other brand notes are read, not written), and never creates a Moodboard note: a brand with none is shown as having none. The `Board/_unsorted/` folder of decision 4 is not built yet.

Consequences: an item removed this way is gone from the note and from `Board/`; the vault's git history still holds the note's earlier text, but `Board/` has no history, so a removed image is not recoverable unless the owner has a backup of it (the open question in "Left open"). A removed block can also leave a Moodboard one blank line shorter, which is harmless.

**Decided by the owner** in chat on 2026-10-15 (delete) and requested as this amendment on 2026-10-16; accepted by the owner on 2026-10-16.

## Amendment (2026-10-16): `Board/<slug>/links/` holds what the app looked up for an address

Decision 3 said `Board/` holds only image files. The board app (its own repository, ADR 008 there) now looks up the title and preview picture of an address the owner adds with no picture, and keeps the result beside the images. What changes:

1. **A new folder.** `Board/<slug>/links/` holds, for each address looked up, `<hash>.json` with `{title, preview, fetched}` and, if the page named a preview image, its thumbnail `<hash>.<ext>`. `<hash>` is the first 16 hex characters of the SHA-256 of the exact address. Only the thumbnail is kept, never the original image.
2. **`Board/` is still not notes.** The folder holds image files and these small JSON files, still gitignored, still invisible to Sympose and the lint (they read only `*.md`). Anything else that reads `Board/` must tolerate `links/` and its `.json` files.
3. **Nothing changes in a note.** The lookup writes no text into a Moodboard note: decisions 5 and 6 stand. A page's title is another person's text, so it is shown by the app and never written as the owner's description.
4. **Delete.** Deleting an item also removes its `links/<hash>.*` files when no other block in that Moodboard has the same address (the amendment of 2026-10-16 on removing a block otherwise stands).
5. **The app now contacts other sites.** Only at the moment of adding an address with no picture, with the owner able to switch the lookup off per item. How it limits that is recorded in the app's repository, not here.

Consequences: `Board/` has no history, so a lookup result is lost with it, as the images are; a title and picture are a snapshot and are never refreshed.

**Approved by the owner** in chat on 2026-10-16.

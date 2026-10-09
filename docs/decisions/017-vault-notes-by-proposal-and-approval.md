---
type: decision
status: proposed
date: 2026-10-09
projects: [workflow]
concepts: [Handoff, Vault upkeep]
amends: [014]
supersedes: []
tags: [type/decision, status/proposed, project/workflow, topic/vault, topic/consent, topic/privacy]
---

# 017 — Notes on the owner's side of the vault are proposed, shown in full and written only on the owner's approval

> **Summary.** The assistant may add to the vault what the owner would otherwise write by hand: a capture of something they said (their words, quoted exactly), a new note such as a concept, or one appended line in a note of theirs. It shows the exact text and place, the owner approves in plain words, and then a script writes it, refusing anything that would break the vault's rules. It costs one script, one transcript reader and a consent step the code cannot see, so the report lists every write.

## Context

What the owner says in conversation is lost when the session ends unless it lands in a record, `docs/reference/GOTCHAS.md` or the handoff. Today the vault's owner-side notes are all written by hand: concept notes ("ask the owner to create it", `docs/VAULT_CONVENTIONS.md`), the hub, the folder definitions, the topic list in `Tags.md`. The close script only prints hints about them (ADR 014, decision 7: "the hub is the owner's"). `docs/sop/handoff.md` forbids editing a note without `generated: true` except to add drafts.

What the owner decided on 2026-10-09, in chat:

- It must not be automatic: "either model propose to keep or the user."
- A capture is verbatim and model-proposed, and "anything note related is private, out of the project repo, same as other notes generated."
- It is part of the handoff, "naturally taken", with no hard-coded marks. The name is "capture". It may be reasoning or plain information, because "something will definitely come up that the handoff won't capture, so we make a system for it".
- The vault's rules still apply: a capture "should have tags and wikilinks".
- The same should hold for "other notes like the concept notes: model proposes and user approves, as part of the handoff". Asked which notes, the owner chose new notes plus one-line edits of existing notes, and for a concept note's body chose "my draft, shown in full" over quoting the owner only.

Facts from the repository:

- A claim written by a model must not land in a generated note (`CLAUDE.md`), and scripts overwrite only notes marked `generated: true` (ADR 009).
- A transcript is read only by the Claude adapter, found by session id (ADR 015, `adapters/claude/context-report/last_context.py`). The core scripts are Claude-free (ADR 002).
- The vault lint requires every note to have tags and at least one link that resolves, errors on a concept named by a record that has no note, warns on a note nothing links to and on a topic not listed in `Tags.md`, refuses a `type:` outside its list, and exempts a pattern still marked `status: draft` from the orphan warning (ADR 010, `docs/VAULT_CONVENTIONS.md`).
- `Inbox/` is defined as outside sources, unevaluated (SPEC §4), which the owner's own words are not.
- The close script already prints what is missing, as hints: a hub that does not link the stats note, and the lint's errors and warnings. Those are real, checkable gaps to propose from.

## Decision

1. **The rule.** For any note or line on the owner's side of the vault, the assistant shows the exact text and where it goes, the owner approves in plain words, and only then a script writes it. A no or silence writes nothing. There is no keyword, no command and no background reading. Three kinds:
   - **A capture:** one passage of the owner's own words, in one message of theirs, that a later session or the owner would lose without it. It may be a reason, a correction, a fact about how they work, a constraint or other context. Not a capture: a passage that already has a home (a record, `GOTCHAS.md`, the handoff, an existing note), an instruction for the current task, and a question; the assistant says so and puts it in that home instead.
   - **A new note:** a note that does not exist yet and is not generated, such as a concept note or a folder definition. The assistant drafts the whole text and shows all of it; the owner may change it first.
   - **One appended line:** a single line added to an existing note of the owner's, at its end or under a heading that exists, such as a topic line in `Tags.md` or a link from a project hub to the stats note. The assistant shows the line and the file. Changing or removing anything already in a note stays the owner's.
2. **When.** Live: when the owner says something that fits a capture, the assistant may say so, quoting it, and ask. At `/handoff`: a new step after the pattern scan proposes (a) captures from the owner's messages not yet proposed, and (b) new notes and lines for gaps the close already reports: a concept with no note, an unlisted topic, a hub that does not link the stats note, a folder with no definition. Proposals are anchored on those reports and on the owner's own words, not on the model's guess of what the vault lacks. The owner may also ask for any of them in any words.
3. **The script.** `scripts/vault_write.py <vault-path> capture|new|add-line ...`, Python standard library, one script so that the checks are shared. Every subcommand writes nothing, says on stderr what failed and exits 1 if a check fails.
   - `capture --project NAME --source FILE --quote TEXT --title TITLE --about NOTE [--about NOTE ...] --topic WORD [--topic WORD ...]`. `FILE` is plain text of the owner's messages (`-` for standard input). The quote must occur in it as one run of text, compared after collapsing runs of whitespace and nothing else (no case folding, no punctuation changes), so a quote with an ellipsis or a join of sentences from different places is refused. At least one `--about` naming a note that exists (the project's hub `Projects/NAME/NAME.md` is always valid) and at least one `--topic` listed in the vault's `Tags.md` are required, so a capture is tagged and linked from the first day. It writes `Projects/<NAME>/Captured/<TITLE>.md`: frontmatter `type: capture`, `status: draft`, `created`, `projects: [NAME]`, `tags: [type/capture, status/draft, project/NAME, topic/...]`, then the quote in a block quote and a line `About: [[note]], ...`. `TITLE`, the links and the topics are labels the assistant proposes with the quote; none is a claim about what the owner thinks.
   - `new --path RELPATH --text-file FILE`. `FILE` holds the full approved text. The script refuses when the path is outside the vault or in a hidden folder, a note of that name already exists anywhere in the vault, the frontmatter says `generated: true` (that mark is for notes a script owns), or the note would fail `vault_lint.py` on its own: a missing field, a `type` or tag outside the vocabulary, no link or a link that does not resolve. It writes `status: draft`.
   - `add-line --path RELPATH --line TEXT [--under HEADING]`. It refuses when the file does not exist, is marked `generated: true`, is in a hidden folder, the heading is absent, the line already occurs in the file or contains a newline. It appends the line, then checks that the file is byte for byte the old content plus the line; if not it puts the old content back and exits 1. It never replaces or deletes.
4. **The reader.** `adapters/claude/capture/owner_messages.py [SESSION_ID] [--projects-dir DIR]` prints the text of the owner's messages in the session's transcript, one message per paragraph. It finds the transcript as `last_context.py` does (same id rules, same refusals, exit 1 and nothing on stdout when it cannot name one, never the newest file). It prints the owner's typed text only: not tool results (which the transcript also stores with the user role), not subagent events and not the assistant's text, so the quote check cannot be satisfied by text the assistant produced. Another assistant writes its own reader with the same output.
5. **The lint.** `vault_lint.py` accepts `type: capture`, requires `projects`, and does not report a note still marked `status: draft` as an orphan, whatever its type, until the owner accepts it (it already does this for a pattern). The owner accepts a note by linking it from another and setting `status: accepted`, or deletes it.
6. **The rules that change.**
   - `docs/VAULT_CONVENTIONS.md`: a concept note is proposed by the assistant and written after approval; it no longer says "ask the owner to create it". The type `capture` and the folder `Projects/<name>/Captured/` are added there and in SPEC §4.
   - `docs/sop/handoff.md`: the `Do not` line about editing a note without `generated: true` allows what this record allows and nothing more; the new step and the report line are added.
   - ADR 014, decision 7 (this record amends it): the stats and sync scripts still never edit the hub. The link from the hub to the stats note may be added by `add-line` on the owner's approval.
   - The owner's pattern draft "Say it, never edit the owner's note" is the owner's to review; this record narrows the rule it describes and the assistant does not edit that note.
7. **In the report.** `docs/sop/handoff.md` step 6 lists each write among the vault changes: for a capture or new note its path, for an appended line the path and the line. Never as something waiting. The list stays in the chat only; no quote, title, path or line from it appears in this repository.
8. **Privacy.** The script and the reader live here and contain no note text. Tests use synthetic sentences. A write goes to the vault and nowhere else: not a commit message, `docs/HANDOFF.md`, `docs/reference/` or a record.
9. **Tests**, a gate, each rule checked against a weakened script with `scripts/mutate.py`:
   - capture: an exact quote is written, with the whitespace-only difference allowed; one changed word, a case change, an ellipsis or a join of two places is refused; a missing or unresolvable `--about`, a missing or unlisted `--topic`, and a clashing title each stop it; the written note passes `vault_lint.py` with no error and no warning other than the exempt orphan.
   - new: refused for an existing name, a path outside the vault or in a hidden folder, `generated: true`, an unknown type or tag, a link that does not resolve.
   - add-line: appends under the heading and at the end; refused for a missing file, a generated file, a missing heading, a repeated line, a newline; a simulated failed write puts the old content back.
   - the reader: an assistant-only and a tool-result sentence are not in its output; a wrong or missing session id gives exit 1 and no output.

## Consequences

The owner's notes can be added without being retyped, linked and tagged from the first day, and nothing is written without a yes. A capture cannot contain a sentence the owner did not write, because the quote check is mechanical. Everything else rests on the owner reading what they approve.

The consent step is not enforced by code: the script cannot see the chat, so a write that was never approved looks the same to it as one that was. What backs it up is that the text is shown first, that the report lists every write afterwards, that additions only append and so are undone by deleting one line, and that under Claude Code the command, with its text, appears in the permission prompt unless the owner has turned that off. A hook that blocks any direct write into the vault outside this script would make it enforceable (`docs/CODE_QUALITY_STANDARDS.md` §12, the tier where a violation is an edited note of the owner's); it is left for the first time a write goes wrong.

Letting a model draft a concept's body is a change from "concept notes are the owner's". It is bounded by the owner reading the whole note first, `status: draft` after it, and no `generated: true`, so the note is never overwritten by a script. The owner sees every one in the report.

The widest risk is noise: almost everything said is information, so the test in decision 1 (no other home, and would be lost) does the filtering, and it is the model's judgment. Some passages will be missed and some proposals turned down; the `/handoff` pass is the second chance, and the owner can say "that one should have been kept" at any time. If drafts pile up unaccepted, narrowing the scope is an amendment, not a code change, because the filter is the proposal.

The reader depends on Claude Code's transcript layout and on how it stores typed and pasted text (ADR 015). A passage the owner pasted is in their message and passes the check although they did not write it; the owner is confirming it, so this is accepted.

Left open: the hook above; a capture that belongs to no project (`--project` is required for now); a quote that spans two messages (refused); other assistants' readers and the Gemini command; whether the folder `Captured/` grows into something that needs its own index; a concept note for `Capture` (to be the first thing proposed once this is built).

## Alternatives rejected

- **Reading the owner's messages at every close and writing all that look worth keeping.** Cheap, but it is automatic, and a note nobody proposed is not one the owner agreed to. The owner ruled it out. Would be right only if the owner asked for a standing pass with a review step each time.
- **Marks the owner types** (a keyword, a prefix, a command). Exact, but unnatural mid-conversation, and the owner asked for the opposite. Would be right if the model's proposals were too unreliable to use.
- **Detecting what to keep by wording** ("because", "so that") in a script. Misses passages given without those words and flags sentences that only use them. Would be right as a hint to the model about where to look, not as the test.
- **A model's paraphrase in a capture.** Easier to read, but it is a model-written claim about what the owner thinks, which the project forbids, and a subtle change of meaning would go unseen. Would be right if the owner marked a paraphrase as theirs after reading it. A concept note is different: it is a definition, so it is drafted and shown in full.
- **Quoting the owner only, for concept notes.** The owner's alternative answer. Safer, but a concept would get a note only after the owner had defined it aloud, and most never are. Would be right if drafted bodies keep needing rewrites.
- **Limiting captures to reasons.** The owner's first choice, and easier to recognise than "worth keeping". Dropped because something that is not a reason will come up. Would be right again if the drafts turn out to be mostly noise.
- **In-place edits of the owner's notes** (frontmatter, an alias, a rewritten sentence). Needed for some fixes, but a changed line is not undone by deleting one line, and the owner chose one-line edits. Would be right with a diff shown and a backup kept by the script.
- **Separate scripts for each kind.** Smaller files, but the vocabulary, link and hidden-folder checks would be copied three times. Would be right if the single script passes the project's file-size cap.
- **`Inbox/` or `Ideas/` as the capture folder.** `Inbox/` is for outside sources and is nagged about after 14 days; `Ideas/` holds notes the owner wrote on purpose. The project folder keeps a capture next to the cards it relates to.
- **One append-only log note for captures, as the stats note is.** One place to look, but a capture cannot be tagged, linked, accepted or deleted on its own, and a log of quotes grows without bound.
- **The script reads the transcript itself.** One less file, but the core scripts would then know Claude Code's format, against ADR 002. Would be right if every supported assistant stored transcripts the same way.
- **Keeping proposals until the close.** The list needs a home that survives an interrupted session, and a proposal lost with the session is a passage lost. Writing on the yes keeps the state in the vault.

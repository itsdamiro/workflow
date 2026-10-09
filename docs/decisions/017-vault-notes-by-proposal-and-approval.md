---
type: decision
status: accepted
date: 2026-10-09
projects: [workflow]
concepts: [Handoff, Vault upkeep]
amends: [014]
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/consent, topic/privacy]
---

# 017 — Notes on the owner's side of the vault are proposed, shown in full and written only on the owner's approval

> **Summary.** The assistant may add to the vault what the owner would otherwise write by hand: a capture of something they said (their words, quoted exactly), a new note such as a concept, or one appended line in a note of theirs. It shows the exact text and place, the owner approves in plain words, and then a script writes it, refusing anything that would break the vault's rules. It costs one script, one transcript reader and a consent step the code cannot see, so the report lists every write.

## Context

What the owner says in conversation is lost when the session ends unless it lands in a record, `docs/reference/GOTCHAS.md` or the handoff. The vault's owner-side notes (concept notes, the hub, folder definitions, the topic list in `Tags.md`) are all written by hand, and the close script only prints hints about them (ADR 014, decision 7: "the hub is the owner's"). `docs/sop/handoff.md` forbids editing a note without `generated: true` except to add drafts.

What the owner decided on 2026-10-09, in chat:

- It must not be automatic: "either model propose to keep or the user."
- A capture is verbatim and model-proposed, and "anything note related is private, out of the project repo, same as other notes generated."
- It is part of the handoff, "naturally taken", with no hard-coded marks. The name is "capture". It may be reasoning or plain information, because "something will definitely come up that the handoff won't capture, so we make a system for it".
- The vault's rules still apply: a capture "should have tags and wikilinks".
- The same holds for "other notes like the concept notes: model proposes and user approves, as part of the handoff". Asked which, the owner chose new notes plus one-line edits of existing notes, and for a concept note's body "my draft, shown in full" over quoting the owner only.

Facts from the repository:

- A claim written by a model must not land in a generated note (`CLAUDE.md`); scripts overwrite only notes marked `generated: true` (ADR 009).
- Only the Claude adapter reads a transcript, found by session id (ADR 015); the core scripts are Claude-free (ADR 002).
- The vault lint requires tags and a resolving link on every note, errors on a concept a record names that has no note, warns on an orphan and on a topic not in `Tags.md`, and exempts a pattern marked `status: draft` from the orphan warning (ADR 010).
- `Inbox/` is for outside sources, unevaluated (SPEC §4), which the owner's own words are not.
- The close script already prints real, checkable gaps as hints: a hub that does not link the stats note, and the lint's findings.

## Decision

1. **The rule.** For any note or line on the owner's side of the vault, the assistant shows the exact text and where it goes, the owner approves in plain words, and only then a script writes it. A no or silence writes nothing. There is no keyword, no command and no background reading. Three kinds:
   - **A capture:** one passage of the owner's own words, in one message of theirs, that a later session or the owner would lose without it (a reason, a correction, a fact about how they work, a constraint). Not a capture: a passage that already has a home (a record, `GOTCHAS.md`, the handoff, an existing note), an instruction for the current task, a question. The assistant says so and puts it in that home.
   - **A new note:** one that does not exist and is not generated, such as a concept note or a folder definition. The assistant drafts the whole text and shows all of it; the owner may change it first.
   - **One appended line:** a single line at the end of an existing note of the owner's, or under a heading that exists, such as a topic in `Tags.md` or a link from a hub to the stats note. Changing or removing anything already there stays the owner's.
2. **When.** Live: when the owner says something that fits a capture, the assistant may say so, quoting it, and ask. At `/handoff`: a new step after the pattern scan proposes captures from messages not yet proposed, and new notes and lines for gaps the close already reports (a concept with no note, an unlisted topic, a hub that does not link the stats note, a folder with no definition). Proposals are anchored on those reports and on the owner's words, not on the model's guess of what the vault lacks. The owner may ask for any of them in any words.
3. **The script.** `scripts/vault_write.py` has three subcommands, `capture`, `new` and `add-line`, in the standard library, one script so the checks are shared. Each writes nothing and exits 1 with a reason on stderr if a check fails.
   - `capture` takes the quote, a title, at least one existing note to link and at least one topic listed in `Tags.md`, so a capture is linked and tagged from the first day. The quote must occur in one message of the owner's as one run (the source text separates messages with a form feed), compared after collapsing whitespace and nothing else (no case or punctuation changes), so an ellipsis or a join of two places is refused. It writes `Projects/<name>/Captured/<title>.md` as `type: capture`, `status: draft`. Title, links and topics are labels, not claims about what the owner thinks.
   - `new` refuses a path outside the vault or in a hidden folder, a name that exists anywhere in the vault, `generated: true` (that mark is for notes a script owns), and a note that would fail the lint on its own. It writes `status: draft`.
   - `add-line` refuses a missing or generated file, a hidden folder, an absent heading, a repeated line and a newline. It checks that the result is the old content plus the line, and otherwise restores the old content. It never replaces or deletes.
4. **The reader.** `adapters/claude/capture/owner_messages.py` prints the owner's typed messages from a session's transcript, separated by a form feed on a line of its own. It finds the transcript as `last_context.py` does (ADR 015), exits 1 with no output when it cannot name one, and never takes the newest file. It prints the owner's typed text only, not tool results (stored with the user role), subagent events or the assistant's text, so the quote check cannot be met by text the assistant wrote. Another assistant writes its own reader with the same output.
5. **The lint.** It accepts `type: capture`, requires `projects`, and does not report a note still `status: draft` as an orphan, whatever its type, until the owner accepts it by linking it and setting `status: accepted`, or deletes it.
6. **The rules that change.**
   - `docs/VAULT_CONVENTIONS.md` and SPEC §4: a concept note is proposed by the assistant and written after approval (no longer "ask the owner to create it"); the type `capture` and the folder `Captured/` are added.
   - `docs/sop/handoff.md`: the `Do not` line about editing a note without `generated: true` allows what this record allows and nothing more; the new step and report line are added.
   - ADR 014, decision 7 (amended): the stats and sync scripts still never edit the hub; the link from the hub to the stats note may be added by `add-line` on approval.
   - The owner's pattern draft "Say it, never edit the owner's note" is the owner's to review; this record narrows the rule it describes and the assistant does not edit that note.
7. **In the report.** `docs/sop/handoff.md` step 6 lists each write among the vault changes: for a capture or new note its path, for an appended line the path and the line. Never as something waiting. The list stays in chat; no quote, title, path or line from it appears in this repository.
8. **Privacy.** The scripts live here and contain no note text. Tests use synthetic sentences. A write goes to the vault and nowhere else: not a commit message, `docs/HANDOFF.md`, `docs/reference/` or a record.
9. **Tests**, as a gate, each rule checked against a weakened script with `scripts/mutate.py`: every refusal in decision 3, an exact quote passing while any changed word, case, ellipsis or join fails, a capture passing the lint, a failed write restored, and the reader excluding assistant and tool-result text and failing on a wrong or missing session id.

## Consequences

The owner's notes can be added without being retyped, linked and tagged from the first day, and nothing is written without a yes. A capture cannot contain a sentence the owner did not write, because the quote check is mechanical. Everything else rests on the owner reading what they approve.

The consent step is not enforced by code: the script cannot see the chat, so an unapproved write looks like an approved one. What backs it is that the text is shown first, that the report lists every write, that additions only append and so are undone by deleting one line, and that under Claude Code the command with its text appears in the permission prompt unless the owner turned that off. A hook blocking any direct write into the vault outside this script would make it enforceable (`docs/CODE_QUALITY_STANDARDS.md` §12); it is left for the first time a write goes wrong.

A model drafting a concept's body departs from "concept notes are the owner's". It is bounded by the owner reading the whole note first, `status: draft` after, and no `generated: true`, so no script overwrites it.

The widest risk is noise: almost everything said is information, so the test in decision 1 (no other home, and would be lost) does the filtering, and it is the model's judgment. Some passages will be missed and some proposals turned down; the `/handoff` pass is the second chance. If drafts pile up unaccepted, narrowing the scope is an amendment, not a code change, because the filter is the proposal.

The reader depends on Claude Code's transcript layout (ADR 015). A passage the owner pasted is in their message and passes the check although they did not write it; the owner is confirming it, so this is accepted.

Left open: the hook above; a capture that belongs to no project (`--project` is required for now); a quote spanning two messages (refused); other assistants' readers and the Gemini command; whether `Captured/` needs its own index; a `Capture` concept note (the first thing to propose once this is built).

## Alternatives rejected

- **Reading the owner's messages at every close and writing all that look worth keeping.** Automatic, and a note nobody proposed is not one the owner agreed to; the owner ruled it out. Right only with a standing pass and a review step each time.
- **Marks the owner types** (a keyword, prefix or command). Exact, but unnatural mid-conversation; the owner asked for the opposite. Right if the model's proposals were too unreliable.
- **Detecting what to keep by wording** ("because", "so that"). Misses passages without those words and flags sentences that only use them. Right as a hint about where to look, not as the test.
- **A model's paraphrase in a capture.** Easier to read, but a model-written claim about what the owner thinks, which the project forbids. Right if the owner marked a paraphrase as theirs after reading it. A concept note differs: a definition, drafted and shown in full.
- **Quoting the owner only, for concept notes.** Safer, but a concept would get a note only after the owner defined it aloud. Right if drafted bodies keep needing rewrites.
- **Limiting captures to reasons.** The owner's first choice, easier to recognise. Dropped because something that is not a reason will come up. Right again if drafts are mostly noise.
- **In-place edits of the owner's notes.** Needed for some fixes, but a changed line is not undone by deleting one line, and the owner chose one-line edits. Right with a diff shown and a backup kept.
- **Separate scripts for each kind.** Smaller files, but the vocabulary, link and hidden-folder checks would be copied three times. Right if the one script breaks the file-size cap.
- **`Inbox/` or `Ideas/` as the capture folder.** `Inbox/` is for outside sources and nagged after 14 days; `Ideas/` holds notes the owner wrote on purpose. The project folder keeps a capture beside the cards it relates to.
- **One append-only log note for captures, as the stats note is.** One place to look, but a capture cannot be tagged, linked, accepted or deleted alone, and the log grows without bound.
- **The script reads the transcript itself.** One less file, but the core scripts would know Claude Code's format, against ADR 002. Right if every assistant stored transcripts alike.
- **Keeping proposals until the close.** The list needs a home that survives an interrupted session; writing on the yes keeps the state in the vault.

**Accepted** by the owner on 2026-10-09, in chat, as written.

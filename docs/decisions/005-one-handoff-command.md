---
type: decision
status: accepted
date: 2026-10-08
projects: [workflow]
concepts: [Handoff]
amends: []
supersedes: []
tags: [type/decision, status/accepted, project/workflow, topic/vault, topic/patterns]
---

# 005 — One `/handoff` procedure closes a slice

> **Summary.** A single procedure commits and pushes the slice, runs the vault sync, the stats line and the lint as one script, scans the diff for patterns, drafts the handoff and reports what needs the owner. It has two modes: `/handoff`, the light close, and `/handoff full`, which adds the two reviews of the diff and a fresh-reader test of the handoff.

## Context

Closing a slice already ends with a handoff (step 9 of `docs/CLOSING_A_SLICE.md`). Cheap restarts (ADR 001) need that step to be quick and complete, and the vault needs updating at the same moment.

## Decision

`docs/sop/handoff.md` defines the steps; scripts do the deterministic ones; a model drafts the rest; the owner accepts. It runs when the slice's work is done and commits it first, because the sync reads committed state; running it is the owner's go-ahead to commit and push (see the amendment of 2026-10-08). Outside it, commit and push stay the owner's call. Writing the ADR is not part of it: that happens before the code.

## Consequences

One command from the owner's side. The work inside a long session costs tokens, which is why the guard reminds early. Without an adapter the owner says "follow `docs/sop/handoff.md`".

## Alternatives rejected

- **A hook that runs it automatically.** It would act before the owner has reviewed the slice, and the draft needs acceptance.
- **Separate commands for each part.** More to remember; the parts belong to one moment.

## Amendment (2026-10-08): the fresh-reader check on request

- **Why:** the first full run took about eight minutes, most of it, as far as I can tell, the fresh-reader check (a subagent per round, often two or three rounds). Run at every 150k to 200k of context, that is too much development time. The vault sync and lint take about half a second; the pattern scan reads only the slice's diff.
- **Decided by the owner:** `/handoff` keeps the ground check, the vault sync and lint, the pattern scan, the handoff draft and the report. The fresh-reader check runs only when named: `/handoff check`. Use it after a rewrite that changed the shape of the handoff, or before another assistant takes over.
- ADR 006 is unchanged: the pattern scan still runs at every handoff.

## Amendment (2026-10-08): `/handoff` commits and pushes the slice

- **Why:** the procedure stopped at step 1 on uncommitted work and told the owner to commit first. The session guard's button fires on a token count, not at a clean tree, so it usually found work in progress and stopped, which defeats a one-click close. The owner asked that the handoff commit and push instead of stopping.
- **Decided by the owner:** typing `/handoff` (or pressing the guard's close button) is the owner's go-ahead for this one procedure to commit the slice's work and push it. This replaces "Commit and push stay the owner's call" in the Decision above, for `/handoff` only. Everywhere else the rule stands: outside this procedure, commit and push only on the owner's word.
- **The order:** the ground check runs the gates first. If they pass, the slice's work is committed, because the sync reads committed state; then the sync, the lint, the pattern scan and the handoff draft run as before; the push comes last, after the lint has no error. If the gates fail or the lint has an error, nothing is committed or pushed and the assistant asks the owner how to proceed.
- **The limits, none of which `/handoff` relaxes:** it stages named files only, never `git add .`, `-A` or `-u`, and only files that belong to the slice. If it cannot tell which changed files belong to the slice, it commits none of the doubtful ones and asks. It reads the diff before committing, as the standards require, and on a public repository stops on anything private. The commit carries no attribution trailer and one author identity. It never force-pushes. `docs/HANDOFF.md` is local-only and is not committed.
- **Not changed:** the git-safety hook still asks before a `git push`, so the owner confirms the push in the prompt unless they have allowed it. That pause is kept on purpose: the amendment removes the instruction to stop, not the hook's check.
- **Follows:** `docs/sop/handoff.md` (step 1, the "Do not" list and the opening line) is amended to match, on the owner's word.

## Amendment (2026-10-08): `/handoff check` also runs the correctness review

- **Why:** the owner asked for the `/code-review` to leave the default close and sit on `check`. A review of the slice's whole diff costs tokens (`docs/CLOSING_A_SLICE.md`, step 5a, says so) and the default close is the quick one the session guard's button starts.
- **Decided by the owner:** plain `/handoff` does not run `/code-review`. `/handoff check` runs it as well as the fresh-reader check. The two are not separate options: `check` now means "the slower, independent checks".
- **The order:** the review comes first, before the commit in step 1, because it reads the slice's diff (the uncommitted changes, or the commits since the last handoff if the work is already committed) and its findings change the code. It runs at `high` unless the owner names another level, as step 5a says, and the assistant says the level before running it. Each real finding is fixed (tests first, gates after) or declined with one line saying why; the gates then pass before anything is committed. The fresh-reader check stays between the handoff draft and the stats line.
- **Not included at first:** the over-engineering lens (step 5b); the next amendment adds it.
- **Consequence:** a default close no longer carries the review that `docs/CLOSING_A_SLICE.md` step 5a calls not optional. The full checklist still has it; whether a default close should run it by hand is the owner's call each time. `check` is now the expensive close, which is what the guard's **Close + check** button starts.

## Amendment (2026-10-08): `check` runs both reviews of step 5 together

- **Decided by the owner:** the over-engineering lens (`docs/CLOSING_A_SLICE.md` step 5b) joins the `/code-review` on `check`. Plain `/handoff` runs neither.
- **How they run:** together, before the commit, over the same diff. The correctness review is `/code-review` as before. The over-engineering lens is a reader who did not write the code, asked one question, whether every new thing earns its place (duplicated logic, work done twice, options nothing uses, abstractions with one caller, defensive code for a case that cannot happen, a new file where an edit would do), with `/simplify` or a read-only subagent as the tool. Neither review hides the other's findings, and the two lists are fixed in one round: each real finding is fixed (tests first, gates after) or declined with one line saying why. A simplification must not change behaviour a test pins.
- **Cost:** `check` is now the expensive close, as it was meant to be: two reviews and, later, the fresh-reader rounds.

## Amendment (2026-10-09): the reviews and the fresh-reader check are part of every close

- **Decided by the owner:** the two reviews of the slice's diff (correctness and over-engineering) and the fresh-reader check of the handoff are part of the development process, so plain `/handoff` runs all three every time. This replaces "only when named" in the three amendments of 2026-10-08 (the fresh-reader check, `/code-review`, and the over-engineering lens). The order they set stands: the reviews before the commit, the fresh-reader check between the handoff draft and the stats line.
- **`check` stays an accepted word** with no effect, so an older prompt, button or habit that types `/handoff check` still works and runs the same close.
- **Enforcement, and its limit:** the reviews and the fresh-reader rounds are model work, so a script cannot prove they ran (`docs/CODE_QUALITY_STANDARDS.md` §12: the layer is wording plus a report line). The procedure and the skill say a check is never skipped or run without saying so; if one cannot run (no reviewer available, an interrupted session), the report names which and why, and the close is not called complete.
- **The session guard** has one close button again. **Close + check** and its `handoffCheckPrompt` setting are removed (plugin version 0.2.0), since both buttons would run the same close.
- **Cost, accepted:** a close takes minutes and a subagent per round; the first full run took about eight minutes for the fresh-reader check alone.
- **Follows:** `docs/sop/handoff.md`, the `handoff` skill, the Gemini command, SPEC §7 and §8, and the session guard's README are amended to match.

## Amendment (2026-10-09): two closes, and one script for the mechanical steps

- **Why, in the owner's words:** the close had become "kinda ritual with no sense". The project exists "to make use of the available time, not really to be a real job", so a step is judged by whether it asks for the owner's attention, not by whether it costs the assistant effort. The pattern drafts "are ok", the owner just has no time to read them as they are made; a draft that waits quietly costs nothing, while a report to read, an item under "Waiting on the owner" or a lint warning does.
- **Decided by the owner:** `/handoff` is the light close: the ground check, the commit, the one script below, the pattern scan, the handoff draft, the push and a short report. `/handoff full` is that close plus the two reviews of the diff (before the commit) and the fresh-reader check (after the draft). `full` is for a slice that changes code the owner will rely on, or when the owner says so; the session guard's button submits plain `/handoff`. This replaces the amendment of 2026-10-09 (the reviews and the check "part of every close"). `check` is accepted and means `full`, which is what it meant before that amendment.
- **The assistant does not choose the mode.** A plain close never runs the reviews. When the diff changed a script, a hook, an adapter or a decision record's Decision section, the report says in one line "reviews not run: `/handoff full` runs them", so the omission is stated and not silent.
- **One script for the mechanical steps.** `scripts/close_slice.py <project> <vault> [--context-tokens N]` runs the vault sync, the stats line and the lint, in that order (so the lint also reads the stats note), and prints one short block. Exit 0: push may go ahead. Exit 1: the lint has an error, do not push. Exit 2: a script could not run. The close goes from eight steps to six, and the three runs are one command that a model without the habit cannot reorder or half-do. Refusals and hints are printed and do not stop the close.
- **The pattern scan stays in both closes and is silent** (ADR 006 unchanged otherwise). Drafts land as `status: draft` in `Patterns/` and wait; the report gives one count line or nothing, and a draft is never listed as waiting on the owner. The lint no longer warns that a draft pattern is an orphan (ADR 010, amendment of the same day).
- **The report** shrinks to what needs the owner: what failed or was refused, what was committed and pushed, and what the owner must accept. What ran successfully gets no narration.
- **Alternatives rejected:** a third mode (`check` as its own close): three names for two closes. Choosing `full` automatically from the size of the diff: an unpredictable cost, and a rule the owner cannot see. Dropping the reviews: they are still the only independent read of the code; they just do not belong on every close.
- **Enforcement, and its limit:** the reviews and the fresh-reader rounds are model work, so a script cannot prove they ran (`docs/CODE_QUALITY_STANDARDS.md` §12: the layer is wording plus a report line). In `full`, a check that cannot run is named in the report and the close is not complete.
- **Not decided here:** committing the vault's own git repository after a sync (it is a repository with a private remote; no step covers it yet), and capturing the owner's reasoning from the conversation (ADRs carry the why; whether more is needed waits for evidence).
- **Follows:** `docs/sop/handoff.md`, the `handoff` skill, the Gemini command, `docs/CLOSING_A_SLICE.md` step 5, SPEC §7 and §8, the README files and the session guard's README are amended to match.

## Amendment (2026-10-09): every report lists the vault notes the close created and updated

- **Why, in the owner's words:** they want a summary of what was done "every time we execute the handoff", with "lists of new notes, edited notes in the vault", "not just what happened and new codes", to "make sure that the vault is part of the entire process". The report of the amendment above said what ran cleanly gets no narration; that left the vault invisible whenever the close succeeded.
- **Decided by the owner:** the report of both closes always has a vault section: the notes created and the notes updated, each by its path in the vault, or one line saying no note changed. A clean run is no longer silent about the vault; the code and the checks stay as quiet as before.
- **Where the list comes from:** `scripts/close_slice.py` compares the vault's Markdown files before and after its three scripts run (a hash per file, hidden folders skipped) and prints the created and updated paths, so the list is measured and not remembered. The assistant adds what it wrote itself after the script: the pattern drafts (step 3) and any other note it created or edited, by name.
- **The list is a report, shown in the chat only.** The owner: "its just a report, no need to put it on remote repo or in commited message". It goes in no commit message, no file of the project's repository and not in `docs/HANDOFF.md`; vault note names are private and the repository may be public (ADR 003).
- **Pattern drafts** are named in this list as vault changes. They are still not an item for the owner to act on, and still never go under "needs your acceptance".
- **Limit:** the list covers this close's own writes. A note the owner edited by hand between closes is not in it; the vault's own git status would show that, and committing the vault is still undecided (amendment above).
- **Alternatives rejected:** reading the vault's `git status` as the list: it accumulates across closes until someone commits the vault, so it cannot say what this close did. A list kept only in the handoff file: the handoff is rewritten each time and local-only, so the owner would not see it at the moment of the close.
- **Follows:** `docs/sop/handoff.md` step 6 and its "Do not" list, SPEC §7, and `scripts/close_slice.py` with its test.

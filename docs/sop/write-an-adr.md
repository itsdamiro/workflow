# SOP: write a decision record (ADR) before the code

For any assistant. Write one when a change adds a dependency, or a decision will outlive the current task (an architecture change, a security approach, what is deliberately deferred). The record comes first; no code for the decision until the owner has accepted it.

## Steps

1. **Take the next number.** Look at `docs/decisions/README.md`; use the next unused number, three digits.
2. **Copy the template.** `docs/decisions/TEMPLATE.md` to `docs/decisions/NNN-short-slug.md`. The slug is lowercase words joined by hyphens; the vault card name is built from it, so keep it short and free of punctuation.
3. **Fill the frontmatter.** `type: decision`, `status: proposed`, `date`, `projects`, `concepts` (names that exist in the vault's `Concepts/` folder, or none), `amends` and `supersedes` (ADR numbers), and the structural tags.
4. **Write the summary.** Three lines at most, at the top: what was decided, why, what it costs.
5. **Write the sections.** Context (facts and numbers, with where they came from), Decision (in the order someone would carry it out), Consequences (easier, harder, left open), Alternatives rejected (each with the condition under which it would become right).
6. **Get the owner's word** on anything that is theirs to decide. Ask; do not guess. Change `status` to `accepted` only when they have said so, and add one line saying what was accepted and when.
7. **Add the index row** to `docs/decisions/README.md`.
8. **Then start the code.** If a real choice turns up mid-slice, stop and return to step 1.

## Changing a record later

- **Amend:** add `## Amendment (YYYY-MM-DD): title` at the end of the same file. The decision text stays current; the amendment records the change. Do not create a new file for an amendment.
- **Supersede:** new record with `supersedes: [NNN]`; set the old one's status to `superseded` and link the new one.
- **Remove:** set `status: removed` with the date and one line saying why. Do not delete the file silently.

## Do not

- Write the code first and the record afterwards. A record written after the fact explains what was done, not what was weighed.
- Leave "Alternatives rejected" empty. It is where ideas are kept for later.

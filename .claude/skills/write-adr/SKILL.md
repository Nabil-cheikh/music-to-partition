---
name: write-adr
description: Create an Architecture Decision Record in docs/adr/. Use when a change swaps a library or model, changes the NoteSegment data contract, changes the pipeline structure, changes the testing strategy, or when the user asks to document a decision.
---

# Write an ADR

1. Find the next number: `ls docs/adr/`. The next ADR is the highest `NNNN` + 1, zero-padded to 4 digits.
2. Copy `docs/adr/0000-template.md` to `docs/adr/NNNN-<kebab-title>.md` and fill every section:
   - **Context** with measured facts: eval scores, timings, install size, links. Mark unmeasured claims as such.
   - **Alternatives**: at least the option that was rejected and the status quo.
   - **Consequences**: list the docs, tests, dependencies and baseline that must change.
3. If it supersedes an ADR, set the old ADR's status to `superseded by ADR-NNNN`. Never delete old ADRs.
4. Update what points to the decision:
   - the "Read before touching" table in `CLAUDE.md`, if the ADR changes which doc governs an area;
   - `docs/architecture.md` / `docs/libraries.md` / `docs/transcription-backends.md` if their content is now outdated.
5. Keep it short: one page. Put long benchmark tables in the relevant doc and link to them.

# Cold read — digest scope doc — 2026-08-20

Reader: local zero-context Claude subagent, read-only.

## Triage summary
Taken to Tony (surfaced): items 3, 4+10 (combined), 6.
Folded into the scope doc (absorbed): items 1, 2, 5, 7, 8, 9.
Left for /blueprint (blueprint-altitude): items 11, 12, 13, 14.

## Disposition
1. absorbed — stale "Open: (round one pending)" line fixed in the doc.
2. absorbed — raw format is whatever /fb writes; ledgered as a pointer, /blueprint reads /fb's SKILL.md.
3. surfaced — classification rules for raw notes into buckets (Round 4 Q1).
4. surfaced — combined with 10: rerun rework rights / do items ever leave notes.md (Round 4 Q2).
5. absorbed — appending is the ONLY permitted write to feedback.md; concurrency edge left downstream.
6. surfaced — first-run behavior with no marker (Round 4 Q3).
7. absorbed — covered by "digest fully owns notes.md": creates it if missing, overwrites any prior shape.
8. absorbed — routing is /fb's job at capture time; /digest only compiles the repo it's invoked in, any repo with docs/feedback.md qualifies.
9. absorbed — /fb entries are dated at capture (handoff: "dated, verbatim"); dates come from the raw log.
10. surfaced — folded into Round 4 Q2.
11. left downstream — invocation surface / argument shape is blueprint detail.
12. left downstream — whether SKILL.md also gets a canonical copy in tony-skills is a repo-convention call for blueprint; scope doc keeps it as assumed.
13. left downstream — no-new-entries behavior is blueprint detail.
14. left downstream — exact marker string and date format are blueprint's to freeze.

## Reader output, verbatim

1. "Open: (round one pending)" contradicts lines citing "Round 1 Q1/Q3/Q4" and "Rounds 2–3" answers. Did round one already happen, or is a question round still owed? Is this doc actually finished enough to build from?

2. What does /fb's raw feedback.md actually look like (line format, timestamps, any prefixes)? /digest must parse it, but the raw format is never specified here.

3. The fixed sections list entry classification (Open questions, Ideas, Decisions, Bugs & friction, Parked) but no rules for how a raw note gets classified into a bucket. Is Claude's judgment call fine, or are there markers/keywords? What happens with an ambiguous note?

4. Idempotency vs "fully owns notes.md and may rewrite anything": on rerun, can /digest reclassify or reword items compiled in earlier runs (e.g., an idea later becoming a decision), or only append/fold new ones? "Folds new entries in" and "may rewrite anything" pull in different directions.

5. The cutoff marker is appended to feedback.md, but line 15 says /digest "NEVER deletes or edits a raw feedback.md line." Appending a marker writes to the file — confirm that appending (never editing) is the only permitted write, and what happens if a note lands below the marker mid-run or Tony /fb's while /digest runs.

6. What if no marker exists (first run ever in a repo)? Compile the entire feedback.md history, or only from some starting point?

7. What if notes.md doesn't exist, or exists with a different shape (hand-created earlier)? Create fresh / overwrite completely?

8. Routing (line 16) maps note-session names to three repos, but line 19 says one run compiles "the current repo only." How do these interact — does /digest ever run from a different cwd and route by session name, or is routing purely /fb's job and /digest just works on wherever it's invoked? If invoked in a repo not on the routing list, does it still run?

9. "Decisions made (dated, one line each)" — dated from what? /fb entries may not carry dates; where does the date come from if the raw line has none?

10. Do already-digested decisions/bugs ever leave notes.md (resolved bugs, answered questions), or does notes.md only grow? Who moves an item from Open questions to Decisions — a later /digest run based on a newer raw note?

11. Invocation surface: is /digest zero-argument (current repo, default files) with the only variation being Tony explicitly pointing it at skill-lab feedback? What does "explicitly summoning" the skill-lab file look like — an argument path?

12. Skill home is stated as ~/.claude/skills/digest/SKILL.md (assumed), but this scope doc lives in tony-skills, whose convention is canonical copies under plugins/ synced to ~/.claude. Should the skill also get a canonical copy in the repo, or is user-level-only intended?

13. Any expected behavior when feedback.md is missing or has zero new lines below the marker — no-op with a message, or still rewrite notes.md footer date?

14. Marker text is quoted with a specific string ("--- digested through here · <date> ---") — is that exact string frozen (agents will grep for it), and what date format?

# /ship — cold read (2026-08-20, local Claude reader)

## Triage summary
Taken: items 1, 2, 3, 5, 6, 8, 9, 11, 12, 13 — absorbed into the scope doc as
clarified wording, new assumed lines, or reference pointers. Left behind: items 4, 7,
10, 14, 15 — blueprint-altitude mechanics or already settled in the doc. Nothing
needed a new question to Tony; every absorption traces to his existing words or the
sibling skills' own docs.

## Disposition
1. absorbed — stale "Open: Round-1 questions below" line removed; Open is now none.
2. absorbed — distinguishing rule written in: a sub-skill question addressed to Tony = pause; the four enumerated conditions = stop. (Both halves were already Tony's rulings.)
3. absorbed as assumed — the /ship session fixes directly, mirroring Tony's current hand-typed chain ("fix any blocker & majors").
4. left downstream — how a SKILL.md invokes sibling skills is /blueprint-altitude mechanics; composition-by-name is the decided approach.
5. absorbed — pointer added: the hunt algorithm is /blueprint's, composed by name; zero candidates = ask Tony (assumed, obvious default).
6. absorbed as assumed — slice scope = what the build doc's slice defines, enforced by /build's existing boundary rules.
7. left downstream — verify mechanics (exact text checked) is build-time detail; the decision (verify rule-8 confirmation, report armed/not-armed) is settled.
8. absorbed as assumed — the second lap fixes only findings still open from the first recheck; /recheck is a closed checklist and surfaces nothing new.
9. absorbed — pointer added to the run-twice-and-diff method docs in ~/Documents/skill-lab/.
10. left downstream — "card status" is /recheck's own concept; /ship just relays it.
11. absorbed as assumed — "told otherwise" = Tony says so in the invocation or mid-run.
12. absorbed — handoff paths added to the Research section.
13. absorbed — pointer added: SKILL NOTE convention is defined in the signoff/precon SKILL.md files.
14. left downstream — location is ledgered as assumed with its rationale; /blueprint confirms format constraints.
15. left downstream — "ready" is Tony's word, the standing gate for every skill in the pipeline.

## Reader output (verbatim)

1. "Round-1 questions" are referenced as still open ("Open: Round-1 questions below (report format extras, mid-loop questions from sub-skills)") but two Round 1 decisions (Q1, Q2) are already listed as decided. Which Round-1 questions remain open, and where are they? "Below" points to nothing — the doc ends two lines later with no question list.
2. The mid-loop-question rule contradicts itself with line 24 vs line 17: a sub-skill question PAUSES the run, but stop conditions say "stop and report, never use your judgment." Who decides whether an interruption is a "Tony-only question" (pause) versus a stop condition (halt)? What distinguishes them concretely?
3. "Fix every BLOCKER + MAJOR" — fixed by whom, under what constraints? Does /ship invoke /build again for fixes, or edit directly? Stop condition 2 says stop if "a fix would change the spec" — how is that judged without judgment?
4. "Composes ... BY NAME; never copies their content in" — mechanically, what does invoking a skill by name from inside another skill mean here? Can a SKILL.md actually invoke /build, /signoff, /recheck, and how do their outputs get read back? The doc calls this a "known risk" but doesn't say what the fallback is if composition-by-name doesn't work.
5. "Auto-hunted the way /blueprint does it" — no description of that hunt algorithm is included or linked. What are the search paths, and what happens with zero candidates?
6. Stop condition 4: "the loop wants to touch files outside the slice scope" — how is slice scope defined and detected? Is it the file list in the build doc? What if the doc doesn't enumerate files?
7. Step zero verifies the Stop hook "armed/not-armed" — verified how? What text/state is checked, and what does the report say if the summon wasn't wrapped in /goal at all?
8. "ONE more fix+recheck lap, then stop" — does the second lap fix only findings still open from the first recheck, or new findings the recheck surfaces? Can /recheck even surface new findings (elsewhere it's described as a closed checklist)?
9. "Validation: existing run-twice-and-diff method" — no definition or pointer. Run what twice, diff what, and what counts as a pass?
10. Report "card status" — what card? The status card concept comes from /recheck but isn't defined here; what values can it take and where does it live?
11. "MINORs left unless told otherwise" — told when? Is there an invocation flag, or does mid-run instruction from Tony modify the fixed step order?
12. Multiple decisions cite "handoff" / "parent handoff" as authority without a path to that handoff file. Which file, and is it required reading to build this?
13. "SKILL NOTE self-feedback line ... same convention as signoff" — the convention isn't specified here; where is it defined?
14. "Lands at ~/.claude/skills/ship/SKILL.md — assumed" — assumption, not decision. Is that confirmed, and are there line-budget or format constraints on SKILL.md files (other skills apparently have them)?
15. "Next: /blueprint when ready" — ready is undefined. Is closing the open Round-1 questions the gate, or something else?

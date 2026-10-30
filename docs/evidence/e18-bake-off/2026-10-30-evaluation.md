# E18 bake-off: v1, v2 and plain asks on the same slices (2026-10-30)

Three ways of running one slice of the build loop were run on the same slices, from the same starting points, with the same model, and graded by the control room's own tests rather than by each run's report. This document holds the findings and the owner's rulings. The owner's decision on what to change is still open (last section).

## Why

During the E18 fix rounds, most v2 stops came from rules about how model text is formatted, not from bad work. On 2026-10-28 the owner asked: "why is this an issue? when i used the version 1 of these skills i never ran into any of these issues. i feel like we are oer engineering these skills and making them too hard and constrained for currently frontier LLMs to follow. They dont need as much direction right? discuss". Then: "shrink A, then do the bake-off".

## The three ways

| Way | What runs | Where the review runs |
|---|---|---|
| v1 | `/ship <slice> <plan>`: ship, build and signoff 1.0.0, readers 1.0.2 | five-lens reviewers as fresh subagents of the same session; recheck after any fix |
| v2 | `/ship-v2 <slice> <plan>`: ship-v2 0.1.3, build-v2 0.1.1, signoff-v2 0.1.3, recheck-v2 | a fresh child session (`claude -p`); hash-chained records |
| Plain asks | no skills; prompts below | a second, fresh terminal window |

Plain-asks prompts, verbatim:

1. Build window: `Build slice <X> of <plan>. Don't use any skills. Commit when done, don't push.`
2. Review window (fresh): `Do a code review of the last commit against <plan>. Rate each finding BLOCKER, MAJOR or MINOR. Don't use any skills.` (Round 1's review prompt had no rating sentence.)
3. Only on a BLOCKER or MAJOR, in the build window: `Fix the BLOCKER and MAJOR findings below. Commit, don't push.` Then in the review window: `Check whether each of those findings is now fixed.`

Every window was set to Opus 5.5 at medium effort.

## The slices

| Test | Slice | Size | Plan |
|---|---|---|---|
| Round 1 | guide findings counts each GUIDE note once | one file plus a new test | `docs/plans/2026-10-29-guide-findings-once.md` on the throwaway `bake/base` (3e88a11) |
| Test 1 | guide findings round 2: cite the main checkout, fold near-copies, match inbox notes to log notes, document `tools/tests/` | five files, including `AGENTS.md` | `docs/plans/2026-10-30-guide-findings-round-2.md` on the throwaway `bake2/base` (5000c18) |
| Test 2 | a private app's slice, replayed from just before it was first built: a review-check command that fetches customer reviews for several locations, compares them against a SQLite state file, and emails alerts over SMTP with a password from the Keychain | about ten files and a new package | restated as one slice in the private app's own repo |

Test 2 has a reference: the slice's original build and its five-lens v1 review (2026-10-27), which found one MAJOR and fixed it.

## The owner's rulings, in order

1. 2026-10-28: "shrink A, then do the bake-off".
2. 2026-10-29: "go  bake off". The control room's proposed fence came with it: throwaway copies, never pushed or merged, so no v1 station touches work meant to merge.
3. "no, not subagetns. i want them in their own respective termional windows so i can see them". Every run got its own terminal window.
4. Cost: the owner pasted `/cost` from both round 1 windows. It showed the whole machine's last 24 hours, not the run, so the control room marked per-run cost as not measured.
5. 2026-10-30: "before we loosen the rules and your suggestions lets do one more bake off, "bake 3" and dont use signoff skill at all and only tell the agetn to do a code review and see how it performs with minimal prompting". The control room added three assumptions and stated them: no skills for the build either, the review in a fresh window, and "Don't use any skills" in both prompts.
6. "one harder run first", then "finde one, a good hard one", then "i want to do both, this one you found, and one hard one in a real app/repo.  so that would be 2 diff tests, across 3 diff bakes. 6 total at once."
7. The owner's point that plain asks stopped short of the loop: "but "ship" skill has review, fix major minor, and then recheck.  we're asking 3 and 6 to only do a code review, not fix any blocker majors and recheck". The plain runs gained the rating sentence and the fix and check prompts.
8. Isolation: "how do we make sure none of these tests step over each other or can look into each others work?", then "im going to do them one at a tiem so in between you can make sure the next doesnt see its work." Runs went one at a time, and each finished copy was locked. After a hook error (see corrections), the owner closed each finished window and typed "closed" before its lock.
9. Run 3 attempts. First: "i posted all the quotes at once since ship does them all at once as well", then "oh, i stopped it" and "ill do the way u had it". Second: the review went into the build window, then "oh shoot, i did it in the samw widnow.  lets start over. wipe it so we can do this test run over again".
10. The owner approved every package-install prompt in the three test 2 runs (the owner's own hook gates every dependency change).
11. Run 5: "record this stop, logg the issues. we might fix it later but i want to finish all our tests". No rerun.
12. "run your evalutaoin one more time againse ALL the tests we did", at maximum effort. This document's method comes from that ruling.
13. "lets make sure all your findings are rulings are in teh doc correclty, then save teh doce to the repo and my docs folder as an md."

## Setup and fencing

- Every copy was throwaway: never pushed, never merged.
- Round 1's three copies were worktrees of this repo, so the original fix (1dc04ca) stayed reachable in their history. The control room found that after round 1. This evaluation's diff check (below) shows the round 1 fixes were not copied from it.
- Round 2's six copies were standalone clones holding history only up to their starting commit, with no remote, so no run could see the original answer or another run's work. Test 2's copies had no live settings file, and its plan forbade contacting the external API, sending email, or reading the Keychain.
- Runs went one at a time. Each finished copy was saved and locked (permissions 000) before the next run started.
- After each round 2 run, its main window (for plain asks, the review window) was asked whether it read outside its folder. None reported doing so, apart from the readers component reading its own memory file in the main checkout (unchanged since 2026-09-06, so read, not written). Run 5's window also searched its own and its reviewers' session logs and found no outside read. Round 1's windows were not asked.

## How this evaluation checked the work

- Round 1: each run's fix compared line by line with the original fix, and 8 requirement probes run against every version.
- Test 1: 18 probes written from the plan's requirements, run against every version in a throwaway home folder; 11 known bugs planted in a correct version to grade each run's test suite; docs and footprint checked by hand.
- Test 2: 10 scenarios with the external API, SMTP and the Keychain stubbed, run against all three runs plus the original build and the original final code; 6 or 7 comparable bugs planted in each version to grade its own tests; `npm audit` on each version.
- The probes themselves were checked: they caught all 11 planted bugs in test 1.

## Results

### Times

| | Round 1 | Test 1 | Test 2 |
|---|---|---|---|
| v1 | 18m27s | about 12 min | about 14 min |
| v2 | about 34 min | about 14 min | 16m45s, then stopped |
| Plain asks | about 2 min | about 4 min (third attempt) | about 5 min |

Plain times exclude the owner's gaps between windows. v1 and v2 times come from their own logs and commit stamps. Plain build times come from commit stamps, except round 1's, which is the owner's watch ("it only took under a minute to build"); plain review end times are approximate.

### Round 1: one-file slice

- All three fixes have the same logic, differing only in a comment and a variable name. All three differ from the original fix in the same way (they strip only the line ending; the original strips whitespace at both ends), so each was written independently.
- Requirement probes: 8 of 8 for every run. Each run's tests pass against every other run's code.
- Reviews: v1 four MINOR from five lenses; v2 four MINOR from three lenses; plain two MINOR. No MAJOR anywhere.
- Result: a tie on the code. Only time differed.

### Test 1: five files, tricky rules

| | v1 (run 1) | v2 (run 2) | Plain (run 3) |
|---|---|---|---|
| Requirement probes (of 18) | 18 | 18 | 17 |
| Planted bugs its tests caught (of 11) | 10 | 11 | 10 |
| Tests in its suite | 13 | 16 | 10 |
| Review result | 2 MAJOR, 11 MINOR | 1 MAJOR, 6 MINOR | 0 MAJOR, 4 MINOR |
| Fix and recheck | yes, one lap | yes, one lap | none triggered |

- The lost-note bug: when the main checkout's copy of a note is badly spaced and fails to parse, the valid worktree copy is dropped and the note is reported as malformed. All three builders wrote it. All three reviews found it. v1 and v2 rated it MAJOR, fixed it, and rechecked it. The plain review rated it MINOR as a gap in the plan, so it shipped.
- A choice the plan leaves open: a malformed inbox line whose note matches a log note. The plain run counts it as the log finding, which is what the plan's text says ("A malformed line follows the same matching rule as a valid one"). v1 and v2 keep reporting it as malformed. v1's review rated the plain run's behavior a MAJOR in its own build. Neither reading is a defect.
- Docs and footprint: all three met the docs requirement and touched only the five named files. All three left `AGENTS.md`'s "Currently four" unchanged, which is now stale.
- Test-strength misses: v1's tests miss a key that ignores the date; the plain run's tests miss the lost-note bug its own code has; v2's catch all 11. For scale, the tests from before this slice catch 1 of the 11.
- The voided second plain attempt (self-reviewed in the build window) also has the lost-note bug; its self-review reported 1 MAJOR and 4 MINOR.

### Test 2: private app, about ten files

| Scenario | Original build | Original final | v1 (run 4) | v2 (run 5) | Plain (run 6) |
|---|---|---|---|---|---|
| Passed (of 10) | 6 | 7 | 7 | 6 | 8 |
| Two overlapping runs email a review twice | yes | fixed | yes | yes | yes |
| A review listed twice in one fetch is emailed twice | no | no | no | yes | no |
| An empty first fetch swallows the next new review | yes | yes | yes | yes | no |
| Seen-state stored by an internal short name, not the external location ID the architecture requires | yes | yes | no | no | no |
| A review stored with a blank time never alerts as edited | yes | yes | yes | yes | yes |
| Email package with published advisories | no | no | no | no | yes (3 high, 12 moderate) |

- Scenarios that passed for every version: new, changed and unchanged reviews sort correctly across locations; a first run records without emailing; a failed send exits non-zero and retries once; the alert carries the location, stars, text and reviewer. When the state save fails after a send, every version stops and resends that review next run; only the original final code reports it clearly.
- Own tests against planted bugs: original build 5 of 6, original final 5 of 6, v1 5 of 7, v2 5 of 6, plain 5 of 6. v1's tests miss a bug that checks only one location and a time compared as text; v2's miss the one-location bug; the plain run's and the original's miss the time compared as text (a weak bug that only matters when one moment is written in two formats).
- The plain run's builder chose nodemailer `^8.0.11`, saw the audit warning, and left it. Its review did not check dependencies. Every other version is on 10.x.

### What each review found and did

Test 1, the lost-note bug: v1 MAJOR, fixed; v2 MAJOR, fixed; plain MINOR, shipped.

Test 2, by defect:

| Defect | Original review | v1 (run 4) | v2 (run 5) | Plain (run 6) |
|---|---|---|---|---|
| Overlapping runs email twice | MAJOR, fixed | MINOR, open | MINOR, open | MINOR, open |
| Save fails after a send: run aborts, resends next time | part of that MAJOR, fixed | MINOR, open | MAJOR, not fixed (run stopped) | MINOR, open |
| Review listed twice in one fetch | not present | MAJOR in its own build, fixed | MAJOR, not fixed | not present |
| Stored by short name, not external ID | present, not flagged | MAJOR in its own build, fixed | not present | not present |
| Empty first fetch swallows a review | MINOR | MINOR | MINOR | not present |
| Blank time never alerts | MINOR | MINOR | MINOR | MINOR |
| Tests cover one location only | not applicable | MINOR | MAJOR | not present |
| Email package advisories | not present | not present | not present | not flagged |

- Every bake-off review found the behavior defects in its own run's code. The gaps: the plain review missed the dependency advisories, and the original October review missed the short-name storage.
- The differences were in severity ratings and whether a fix ran, not in what each review found.

## Process and reliability

- Runs finished: v1 3 of 3 all clear. v2 2 of 3 all clear, 1 stopped with three MAJOR defects unfixed (v2 also finished the live run 2 rerun, outside the bake-off). Plain asks 3 of 3 finished, but 2 of its 5 attempts were voided by window handling.
- v2's stop (run 5): ship-v2's launch step says to run the printed argv as a list with no shell, and says nothing about input. The window launched it through `python3 -` with the script on standard input, `claude -p` appended that input to the reviewer's prompt, and the launch check refused the visit. The reviewer had finished a full review. The window called it its own command and a gap in the skill.
- Commits and records: v1 wrote a verdict doc and punch list and committed every lap in round 2; in round 1 it left its review records uncommitted. v2 wrote hash-chained records and a verdict doc but left fixes or records uncommitted in all three runs. Plain asks committed code only; the review lives only in chat.
- Window work: v1 and v2 take one command. Plain asks need the owner to open windows and carry findings between them.
- Measured cost: only v2's reviewer sessions report one: $4.13 (round 1), $4.46 (test 1), $9.02 (test 2). Nothing comparable exists for v1 or plain asks.

## Skill issues logged (owner's ruling: "logg the issues")

1. ship-v2's launch step names no standard input. Run 5 stopped on it. Fix: `launch.py` prints input from `/dev/null`, and the skill says so.
2. build-v2 and ship-v2 disagree on the build ledger. build-v2 writes it into the plan after its report; ship-v2 accepts the plan only at build-v2's own status write, so the ledger reads as a spec change. Every v2 run here worked around it.
3. skill-identity's content hash includes the harness's `.in_use/<pid>` lock files, so the hash drifts when a session starts.
4. Reviewers through readers cite line numbers from the combined review packet, not the files. Run 5's verdict doc cites lines that do not exist.
5. A readers `raw_path` copy lands as `raw-2.md` beside the runner's own `raw.md`.
6. v2 left fixes or records uncommitted in every run; v1 committed every lap in round 2.
7. v1 `/ship` gives no waiting rule for background readers (run 1 armed an unasked wake-up), and v1 reader captures can be hand-typed rather than byte-exact.
8. Control-room process: lock a finished copy only after its window is closed.

## Corrections the control room made along the way

Kept visible, in order:

1. Round 1: said v2's extra time went on format rules. Unmeasured: the time was the fresh-session review.
2. Said every E18 stop came from how text was written. Most did; two did not (a reviewer quoting withheld sections, and a 512 KiB read limit).
3. Said v1 was twice as fast in round 1. 18m27s against about 34 minutes is nearly twice.
4. Round 1 diff stat given as +9/-2 for the tool; it was +8/-1, and the plan +17/-1.
5. The board showed round 1's v2 run as still running after it had finished.
6. Called test 1's v1 review "four reviewers"; it was five signoff reviewers plus one recheck reviewer.
7. Said test 1's plain run shipped two bugs. It shipped one clear bug; the other behavior follows the plan's text.
8. Said the plain test 2 package had four high advisories. It has three high and twelve moderate.
9. The board said run 3's review ran in a fresh window before the window reported a self-review.
10. Said run 6's builder sent its notes unprompted; the owner had asked for them.
11. Round 1's copies could reach the original fix in their history. Found after round 1; round 2's copies were rebuilt standalone before any run.
12. Locking run 4's folder while its window was open made its Stop hook fail (harmless). The procedure changed to close first, then lock.
13. A cross-test loop first ran under zsh without word splitting and printed meaningless passes. Caught and rerun before any report.
14. Reported run 5 as about 16 minutes; it ran 16m45s.
15. The board headline after round 2 said the plain way never finished with fewer bugs. On test 2 it tied v1 on the overlap bug and beat v2.

## Limits

- Three slices, one model at one effort, one try per way. Results swing between tries: the original v1 build and run 4 used the same skill on the same slice and made different bugs, and their reviews rated the same overlap bug differently.
- Timing for plain asks is by the owner's watch and message times.
- Cost is measured only for v2's reviewer sessions.

## Also found: the private app's current code

The private app's current code still stores its seen-state by an internal short name, while its architecture requires the external location ID. Renaming a short name would re-alert every review at that location. The October review did not flag it. Reported to the owner; nothing was changed.

## Open decision (the owner's)

| Option | What it means |
|---|---|
| Rebuild lean with a strict review | A plain build prompt; one fresh review with firm severity rules and a security pass; any MAJOR gets a forced fix and recheck; a small script launches the windows and saves the record. Most of v2's format rules go. |
| Fix v2 as it stands | Keep the v2 stations and fix the logged issues, starting with the launch step. |
| Keep everything as is | No change now. |

The control room's recommendation, given in chat: rebuild lean with a strict review, because the builds needed little direction and the strict review with its forced fix is what caught bugs before they shipped. Its severity rules should be firm: a double email, lost data, or a silent failure is always MAJOR.

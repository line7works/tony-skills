# agent-file-flip — fresh-session re-run (2026-09-04)

Slice D, R7. Every earlier slice's fresh-session check re-run after the Studio reinstall, from the installed plugin cache (plain `claude -p` from the repo root, no `--plugin-dir`), so each check exercises the copy a session actually loads. Four sessions, one per check; each answer pasted whole below the question that produced it. The cache commit is the `version` recorded for the plugin in `~/.claude/plugins/installed_plugins.json` (the cache is not a git checkout; its folders are named by commit).

| Check | Plugin | Cache commit | Result |
|---|---|---|---|
| Slice A AC3 | build | `b788ab9cbca8` (main after PR #39) | pass |
| Slice B AC4 | sun | `75b836b0c1ff` (main after PR #40) | pass |
| Slice C AC3 | signoff | `567866ca29d0` (main after PR #41) | pass |
| Slice C AC4 | recheck, vertical | `567866ca29d0` (main after PR #41) | pass |

Each session ran with `--max-turns 12` and no other flags. The install list at run time, for the record: sun at `75b836b0c1ff`; signoff, recheck, vertical at `567866ca29d0`; build, precon, architect, blueprint, inspect, handoff at `b788ab9cbca8`; the rest at `83923f155bf1`.

## Slice A AC3 — build (expected: `docs/plans/2026-09-04-agent-file-flip.md` and the `docs/plans/` tier)

Question: Read the /build skill (the build plugin from tony-skills; do not build anything and do not edit any file). Using only its Step 1 doc hunt as written: which build doc would you use for agent-file-flip in this repo, and which tier of the hunt did you find it in? Answer in three sentences, naming the path and the tier.

Answer:

> I would use `docs/plans/2026-09-04-agent-file-flip.md`, because its `<topic>` of `agent-file-flip` matches the invocation by filename. It came from the first tier of the hunt, the `docs/plans/*.md` folder that `/blueprint` writes, so the search stops there and the later tiers never come into play. No flat `docs/<feature>-build-plan.md` carries that feature name, so there is no cross-tier tie to resolve, and the single hit in the first tier is an unambiguous pick rather than a stop-and-ask.

Result: pass. Names the path and the `docs/plans/` tier, and notes there is no flat-doc tie.

## Slice B AC4 — sun (expected: the six Tier 0 files, the kit note, the four verification lines, the none/one/many staged-doc rule)

Question: Read the /sunrise skill (the sun plugin from tony-skills; do not run it and do not edit any file). Describe what /sunrise seeds at Phase 1 step 3 and what it does with docs staged in ~/Documents: name the seeded files, what note the seed set comes from, what verification lines it runs after seeding, and the rule for zero, one, or many staged docs. Answer in one short paragraph.

Answer:

> At Phase 1 step 3, /sunrise seeds Tier 0 of the repo doc kit, merging with anything the scaffolder already wrote rather than overwriting it. The seed set comes from the Tier 0 table in `~/ObsidianVault/01-domain/repo-doc-kit.md`, with the instruction body shaped by the agents-md best-practices spec sheet in the same vault folder. It is exactly six files: `AGENTS.md` as the instruction body (a scaffolder's framework block stays at the top inside its markers), `CLAUDE.md` as a one-line `@AGENTS.md` stub that is a real file and never a symlink, `README.md`, an archetype-appropriate `.gitignore` with `!.env.example` appended, `.env.example` with keys but no values, and `docs/.gitkeep`. `REVIEW.md` is never seeded. The verification, run in Phase 8 after the deploy check, is the kit note's four lines: `git ls-files` confirms `AGENTS.md` is tracked in exact case, a `head -1` check confirms the stub's first line is `@AGENTS.md`, a `-L` test confirms it is not a symlink, and `claude -p` asks the model to quote the first line of its project instructions verbatim as the canary. Any failing line blocks `SUNRISE COMPLETE`. Staged docs are handled at step 5: it first reports anything a prior interrupted run already adopted, then looks in `~/Documents` for the slug's scope doc, architecture doc, precon cold reads, and architect reviews, moving each with `mv` into the matching `docs/` subfolder with a date taken from the doc header, then the filename, then by asking Tony. Zero matches prints `nothing staged` and continues. One match moves. More than one candidate for the same role lists every candidate with its proposed destination and asks Tony which to move, never picking.

Result: pass. All six files, the kit note by path, all four verification lines, and the zero/one/many rule.

## Slice C AC3 — signoff (expected: infer, show, wait for Tony's word, write on the word, continue on defaults without it)

Question: Read the /signoff skill (the signoff plugin from tony-skills; do not run it and do not edit any file). What does /signoff do on its first run in a repo that has no REVIEW.md? Walk through the sequence in order, including what happens when the user gives no word. Answer in one short paragraph.

Answer:

> On a first run with no REVIEW.md, /signoff first passes the Step 0 model floor, then in Step 1 reads for the sheet, finds nothing, and runs the first-run gate before spawning any reviewer: it infers the four pass toggles from the repo (correctness and security always on; accessibility on if a UI framework or component tree is present; data-safety on if there is a hosted database, migrations folder, or database env key in .env.example), renders the REVIEW.md template with those toggles, a parenthetical on each pass line saying what the inference found, and a verified stamp dated today, shows the whole proposed file in chat, asks for the user's word, and ends the turn. That question blocks: silence never proceeds, and under /ship it becomes a pause that is passed through and awaited, so with no word nothing is written and no review runs. On a yes, it writes the file to the repo root, runs the review under it, and reports the REVIEW.md line as created this run, treating the write as the one sanctioned working-tree edit that is excluded from the review's scope and never committed. On a no or a different instruction, no file is written and the run continues on the skill's defaults with the line reading absent, defaults, proposed but not written. The only shortcut is wording in the invocation itself that orders the write, which counts as the word: then the file is written first, the written sheet is shown whole in chat, and the review proceeds. After the review, the second-failure rule cannot append to a file that does not exist, so any recurrence is named in the verdict's Bottom line instead.

Result: pass. Infer, show, end the turn and wait, write on yes, defaults on no, plus the invocation-wording shortcut Tony ruled on 2026-09-04.

## Slice C AC4 — recheck and vertical (expected: neither writes `REVIEW.md`; each says what it reads)

Question: Read the /recheck skill and the /vertical skill (the recheck and vertical plugins from tony-skills; do not run them and do not edit any file). For each: does it ever write REVIEW.md, and what does it read from that file? Answer in two short paragraphs, one per skill.

Answer:

> **/recheck** never writes REVIEW.md. The skill says so in four places: the inspection-sheet paragraph, rule 6, the report template, and the closing don't list. It reads the file before the doc hunt, validates it under the same test signoff uses, and applies only the Severity bar. The bar overrides signoff's generic severity table when grading any fix-introduced defect the verifier reports. The Passes section changes nothing because recheck hunts nothing, and the Repo-specific checks never grow the closed checklist. The file is also handed to the fresh grading subagent alongside the checklist. A malformed or absent file is reported on the report's REVIEW.md line and defaults apply. A recurrence recheck notices is named in one line and left for signoff's second-failure rule to record.
> 
> **/vertical** never writes REVIEW.md either. Rule 7 makes the verdict doc the run's one write, and the closing don't list repeats the ban. It reads the file before the doc hunt and the gate, using the same validity test. All three sections govern the local review: passes marked off are skipped and named in the verdict doc, the Severity bar grades every finding including outside findings, and each Repo-specific check is an item local reviewers must try to break and report as held or found. Outside reviewers never see the file. It is excluded from the git archive export along with the reviews folder, since its checks are distilled from prior verdicts. The chat block's REVIEW.md line reports skipped passes, checks tried, or that the file was absent or malformed.

Result: pass for both. Each says no, and each names what it reads (recheck: the Severity bar only; vertical: all three sections, local reviewers only, excluded from the export).

# sunrise-live-run-fixes — signoff, Slice A

## 2026-09-05 — signoff: Slice A

Verdict: SIGNED OFF WITH CONDITIONS
Scope: branch `feat/sunrise-live-run-fixes` vs `main` (commits 8e42e4d, 176e954; four files; working tree clean at review start). Nothing excluded. · Spec: `docs/plans/2026-09-05-sunrise-live-run-fixes.md`, Slice A.
Depth: LEAN + security (REVIEW.md pass on) · Method: executed — all seven ACs re-run by the inspector and by three reviewers independently; an independent fresh-session read with a new project name (Big-Kahuna) reproduced both fixes; gitignore ordering proven in throwaway repos with `git check-ignore -v --no-index`; Vercel CLI 59.11.7 `link --help` and bundled source read for `--project`/`--yes` semantics; no live `vercel link` run. · Refuted: 3
REVIEW.md: read — passes skipped: accessibility (no UI), data-safety (no hosted database) · 0 repo-specific checks to try (placeholder only at review start) · second-failure rule appended one check this run.

Bottom line: The two fixes the live run asked for are in the file and read correctly by a fresh session, and every acceptance criterion passes by rerun. Two MAJORs stand: the new Phase 3 verification cannot fail for its own subject (a tracked `.env.example` is invisible to the default `git check-ignore`), and Phase 0's Vercel collision check names no variant while Phase 3 now links `--project <slug>` with `--yes`, which attaches to an existing project of that name without a prompt. Fix both, then /recheck flips the card. One recurrence (an edit after the push is never re-committed) went onto REVIEW.md.

MAJOR
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:232` · Phase 3 step 2's verification cannot fail for `.env.example` · by Phase 3 the file is tracked (Phase 1 step 6 committed it), and the default `git check-ignore .env.example` prints nothing for a tracked file whatever `.gitignore` says; "re-run the Phase 1 step 3 check" is the "tracked" predicate, vacuously true after any commit. A session that skips or botches the re-assert reports the step green. Only `git check-ignore --no-index` sees it: broken state prints `.env.example` rc 0, fixed state prints nothing rc 1. · CONFIRMED (inspector's throwaway repo; correctness and seams lenses converged)
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:141` (with `:132`) · Phase 0's Vercel collision check says "name must be free" without naming the variant, and the vocabulary block does not list the Vercel project among `<slug>`'s uses, while Phase 3 now runs `npx vercel link --yes --project <slug>` · Tony sunrises "Foo Bar" while a stale Vercel project `foo-bar` exists; the session checks `Foo-Bar`, finds it free; Phase 3 links the fresh repo to the old project with no prompt (CLI `inputProject` under `--yes` returns the detected project), auto-deploys on, and Phase 4's env pull writes the old project's secrets into the new `.env.local`. Violates the skill's "Never clobber" core principle. Before this slice a mixed-case `<Name>` failed with 400 instead. · CONFIRMED (skill line read by the inspector; CLI source and `--help` read by the correctness lens; security, seams, correctness converged)

MINOR
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:232` · the `.gitignore` edit Phase 3 step 2 makes is never committed or pushed; no commit step exists after Phase 1 step 6 (`:217`) and Phase 8's summary prints "(git init, pushed)" · sunrise ends with a dirty tree; GitHub's `.gitignore` lacks `.vercel` and the last-line negation; a laptop clone lacks the fix. Pre-existing in shape (link's own append already dirtied the tree on `main`). RECURRENCE of the Slice B MINOR at old `:311` (a post-push fix never re-committed), appended to REVIEW.md. · three lenses
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:84` · the core-principle line says "200 on the clean `<project>.vercel.app` alias" and the plan's Out of scope deferral names Phase 8's placeholders only, so this line is deferred in substance but not by the letter · a session following the rule with a mixed-case name curls a hostname that does not exist. Follow-up note should cover `:84` with `:312`. · spec, correctness
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:232` · "`vercel link` appends `.vercel` and `.env*`" is stated unconditionally; the CLI appends `.env*` only during its env pull and only when no line equals `.env*` exactly (create-next-app already ships one) · a literal reader on the default archetype finds no `.env*` line to move and may stall or report the skill wrong; the re-assert itself stays harmless. · correctness
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:232` · the verify set names `.env.example`, `.env.local`, `.vercel` only · a session that "re-asserts" by rewriting the file and dropping `.env*` leaves `.env.production` trackable while every listed check passes; mitigated because sunrise never stages after Phase 3. · security
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:232` · "move or re-append" permits a duplicate `!.env.example` · cosmetic; semantics proven intact either way. · spec
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:231` · `Banana-Dunk` is the name of a real (archived, private) GitHub repo of Tony's, now in a public skill's instruction text; R1 asked for the why with the date, so spec-driven, but the builder's "not Tony-specific" call was inaccurate · exposure is nominal (throwaway, archived, host dead) and matches the file's existing RJ-Hauler idiom; Tony's call to keep or strip. · security, spec, seams
- MINOR · `docs/plans/2026-09-05-sunrise-live-run-fixes.md` Footprint · says "docs/feedback.md (one Dispositions line)" while the diff to committed `main` also adds three Inbox lines (Inbox 28 → 31); the Constraints pre-authorize the ride-along and the 28 `main` lines are byte-identical and ordered · AC7's "still 31" is reproducible only against the dirty tree; cosmetic. · spec, seams
- MINOR (pre-existing, outside footprint) · `plugins/sun/skills/sunrise/SKILL.md:312` · "confirm the Phase 2 git-connect auto-deploy" but git connect lives in Phase 3 · stale cross-reference on `main`. · correctness
- MINOR (pre-existing, outside footprint) · `docs/feedback.md:10-13` · the Flow paragraph says triaged notes become slices on `skill-loop-edits-build-plan.md`; dispositions now point at `docs/plans/` docs · stale prose. · spec, seams
- MINOR (pre-existing, outside footprint) · `plugins/sun/skills/sunrise/SKILL.md:132` · `<slug>` derivation says "kebab-case, lowercase" without `[a-z0-9-]`; a leading-hyphen slug would parse as a flag at the new `--project` sink; Tony confirms the variants first. · security

Refuted
- "R6 literally forbids the renumbered steps appearing in the diff" — R6 protects the Electron step's content, which is unchanged; renumbering is logged in Build assumptions. Not a defect.
- "Evidence pins a branch-local commit that a squash merge would dangle" — this repo merges by merge commit (every recent `main` commit is a PR merge), and `SKILL.md` is byte-identical between 8e42e4d and HEAD.
- "AC4 is read-comprehension, not a behaviour test" — AC4 asks exactly for a fresh-session read; the reviewer itself marked it informational.

Deferred (spec-covered, not defects)
- Phase 8 `<project>` alias placeholders (`:312`, four uses) — plan Out of scope.
- `/sunset`'s by-name Vercel lookup naming no variant, and its `project_<slug>.md` vs sunrise's `project_<slug_>.md` — plan Out of scope (no sunset edits).
- Finding E (vault path in the seeded AGENTS.md) — Not in this slice, pending Tony.
- Installed-cache fresh read and a live `/sunrise` rerun — plan Out of scope, post-merge.

Tried and failed to break
- All seven ACs by their own commands, four times over (inspector plus three lenses): AC1 0/1/0/1, AC2 2 and 1 with the required wording present, AC3 4 on branch and on `main` with the whole Phase 8 region byte-identical, AC5 0, AC6 exactly the four files with sunset diff 0 bytes, AC7 1 and 31.
- AC4 twice independently: the recorded question re-asked verbatim by the spec lens, and a differently phrased read by the inspector using a new project name (`~/Developer/Big-Kahuna`, slug `big-kahuna`); both fresh sessions named the command, the lowercase reason, and the last-line re-assert with all three checks.
- gitignore semantics in throwaway repos with `git check-ignore -v --no-index`: scaffolder patterns `.env*`, `.env.*`, `*.env`, `.env*/`, `**/.env*`; true-move and duplicate-negation variants; monorepo nested `apps/web/.env.example`; `!.env.example` does not over-match `.env.example.local`; `.vercel/project.json` ignored in every scenario; a later re-ignore correctly flips it.
- The fused-line hazard (negation without trailing newline glued to link's append): refuted from CLI source, `addToGitIgnore` inserts an EOL when the file lacks one.
- `!` history expansion when a session appends with `echo` under non-interactive `bash -c` and `zsh -c`: appended literally.
- `npx vercel link --yes --project <slug>`: valid in CLI 59.11.7 (`-p, --project <NAME_OR_ID>`), name passed verbatim with no lowercasing (consistent with the live 400), creates when absent, `--yes` handled before the non-interactive branch.
- Secrets and PII in the diff versus `main`: no emails, home paths, tokens, or account identifiers new to the repo; every Tony identifier present has a `main` precedent in the same doc type; `${CLAUDE_PLUGIN_ROOT}` references untouched.
- Step renumbering: every "Phase N step M" mention in the skill resolves; the preview line and Phase 3 step 1 agree on `<slug>`; README, marketplace catalog, plugin manifest, and the vault companion note describe nothing the skill lost.
- `docs/feedback.md`: the Dispositions heading is unique and the new line sits under it after the two 2026-08-02 precedents; the 28 committed Inbox lines are byte-identical and in order; the `/fb` anchor bug at `:114` did not recur.
- REVIEW.md repo-specific checks: none existed at review start.

Next: fix the two MAJORs in place, then /recheck flips the card.

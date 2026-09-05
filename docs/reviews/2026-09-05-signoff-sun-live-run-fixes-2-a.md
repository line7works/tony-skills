# Sign-off — sun-live-run-fixes-2 · Slice A (sunset live-run fixes) · 2026-09-05

Verdict: SIGNED OFF WITH CONDITIONS
Scope: `git diff main...HEAD` on `feat/sunset-live-run-fixes` (main e706492; work commits 1617ce0, bcd3d5c; checkpoints 0c12934 and 11c0433 carry the plan and Inbox notes, which are spec and inputs, excluded as work). Four files: `plugins/sun/skills/sunset/SKILL.md`, `docs/feedback.md`, `docs/plans/2026-09-05-sun-live-run-fixes-2.md`, `docs/evidence/sunset-live-run-fixes/fresh-session-read.md`.
Spec: `docs/plans/2026-09-05-sun-live-run-fixes-2.md` · Slice A (R1-R6, AC1-AC8).
Depth: LEAN + `security` (REVIEW.md pass on; the slice handles a credential). Lenses: spec, correctness, seams, security; four fresh general-purpose reviewers, no author rationale passed.
Method: executed. Each reviewer ran the AC grep/awk/git lines; correctness and security reproduced the `mv` nesting, the guard, and the `jq`/`${VAR:-}` token line against fake trees and fake credential files in the scratchpad (the real `auth.json` only `ls`-checked, mode 600, never read); the AC7 fresh-session read was checked as a document (prompt wording, all four questions, commit 1617ce0 whose sunset file is byte-identical to HEAD). This station re-ran all eight AC commands.
REVIEW.md: read — bar applied; `accessibility` and `data-safety` skipped by REVIEW.md (no UI; no hosted database). Repo-specific check "sunrise: post-Phase-2 edit never re-pushed": not applicable (sunrise byte-identical to main); no recurrence found, nothing appended.
Refuted: 0. Prior conditions: none (no prior slice; punch list was empty).

## Findings

- MAJOR · plugins/sun/skills/sunset/SKILL.md:206 · Phase 6 token read and curl are two separate command lines · the Bash tool starts a fresh shell per call, so a session running them as two calls sends `Authorization: Bearer ` (empty), gets 403, and its natural next move (`echo $T`, `curl -v`) puts the token in the transcript; four lenses converged · CONFIRMED
- MAJOR · plugins/sun/skills/sunset/SKILL.md:59 · principle "archive it first" contradicts the new Phase 4 order · a session honoring the principles list copies into `_archive/<Name>/.claude-memory` before Phase 4 and recreates the nest the slice fixes; three lenses converged · CONFIRMED
- MAJOR · plugins/sun/skills/sunset/SKILL.md:217 · under `--keep-local` nothing creates `~/Developer/_archive/<Name>` before Phase 7 writes the backup there · `/sunset Foo --keep-local` with a database: `pg_dump >` fails "No such file or directory" and :218 STOPs; on `main` Phase 2 made the dir unconditionally, so this is a regression the slice introduced · CONFIRMED
- MINOR · plugins/sun/skills/sunset/SKILL.md:206 · `jq -r .token` degrades silently: missing key gives the string `null`, malformed file gives empty, expired token gives 401 · step 3's "both absent" test does not cover any of them, so the curl fires with a bad token and no scripted path follows
- MINOR · plugins/sun/skills/sunset/SKILL.md:208 · the no-print sentence does not name `curl -v`/`--trace`, `set -x`, or a standalone `jq -r .token` run "to confirm", and there is no `unset T` · each leaks the value into the transcript while satisfying the letter of the sentence
- MINOR · plugins/sun/skills/sunset/SKILL.md:128 · Phase 0 preview Memory line promises the store copy unconditionally · under `--keep-local` the preview Tony approves promises a copy Phase 4 no longer makes; R2 says the line stays put, so this is a question for Tony, not a defect charged
- MINOR · plugins/sun/skills/sunset/SKILL.md:300 · tombstone "Local repo: `~/Developer/_archive/<Name>`", Phase 9 :241, handoff prompt :263 are unconditional under `--keep-local` · the tombstone now says the store was left in place because the repo was kept local two lines above a line saying the repo moved; pre-existing, outside R3
- MINOR · plugins/sun/skills/sunset/SKILL.md:197 · Phase 5 step 1 says "run before the repo move" but sits after Phase 4 · pre-existing stale ordering cross-reference
- MINOR · plugins/sun/skills/sunset/SKILL.md:175 · the guard is prose, not a self-enforcing command, and the STOP's scope (do Phases 5-8 continue?) is undefined · a session can run :176 directly; if it proceeds after a STOP, Phase 7 writes into the colliding prior archive
- MINOR · plugins/sun/skills/sunset/SKILL.md:179 · `cp -R ~/.claude/projects/*<Name>*/memory/.` silently merges when the glob matches several stores · same-named files collide and the tombstone's single source path is wrong; pre-existing line relocated by this slice
- MINOR · plugins/sun/skills/sunset/SKILL.md:177 · step 4 does not say "only if `mv` exited 0" · a failed `mv` followed by `mkdir -p` creates a phantom archive dir that trips the guard next time; low likelihood on APFS
- MINOR · plugins/sun/skills/sunset/SKILL.md:180 · "If no project store exists, record none" is an addition no requirement names and no ledger line logs · inside Phase 4 steps, sensible, unlogged
- MINOR · docs/plans/2026-09-05-sun-live-run-fixes-2.md:45 · AC8 pins the Inbox at 35; the tree holds 36 at build start and after · builder call assumption is sound (the 36th line is Tony's own `/fb` of the handoff SKILL NOTE, committed 11c0433 before the work), but the literal criterion fails; question for Tony: accept 36 or amend AC8
- MINOR · docs/evidence/sunset-live-run-fixes/fresh-session-read.md:3 · states the installed sun cache as `2baaecba12a1`; `installed_plugins.json` shows `sun@tony-skills` at `e7064921ac21` since 2026-09-05T14:43Z · the record's one machine fact is wrong (harmless to the skill); the plan's Handoffs line "pending `/plugin update sun` for PR #43" is stale for the same reason
- MINOR · docs/plans/2026-09-05-sun-live-run-fixes-2.md:77 · three stray blank lines between Build assumptions and Deviations · cosmetic

## Deferred (sanctioned, not counted)
- Phase 0 preview Memory line stays put (R2) and the by-name Vercel lookup, Notion phase, live reruns, Banana Dunk mentions in records (Out of scope).

## Tried and failed to break
- Phase 4 order and guard on a scratch tree: `_archive` absent → clean rename; `_archive/<Name>` present, case-only collision, dangling symlink → guard fires; ignoring it reproduces `<Name>/<Name>/`.
- Token line: `VERCEL_TOKEN` set wins, empty falls through to the file, quoting holds in bash and zsh; the lines as written print no value.
- AC1-AC6, AC8 (Dispositions 1 → 2; Inbox 36 with zero Inbox lines changed by the work commits): all hold by their own commands.
- Footprint: exactly the four files; sunrise, `plugins/sun/assets`, both `plugin.json`, `marketplace.json` untouched; `${CLAUDE_PLUGIN_ROOT}` count unchanged; `timeout` 0.
- Public exposure: only new machine path is the Vercel CLI's standard credentials location, values never shown; no token, session id, or new personal identifier.
- Protected paths: `~/.claude/projects/*/memory/` only read by `cp`; nothing deletes or moves the original.
- Renumbered shortcut steps 5-8: no stale "step N" references.

## Questions for Tony
1. AC8: accept the Inbox baseline of 36 (your own `/fb` note is the 36th line) or amend the criterion?
2. Phase 0 preview Memory line (:128): keep unconditional per R2, or make it conditional on `--keep-local` like the summary and tombstone?
3. Installed `sun` is already at e706492: the post-merge installed-cache read for the sunrise fixes can run now; should the evidence file's cache id be corrected (MINOR)?

### 2026-09-05 — recheck: Slice A
- MAJOR · plugins/sun/skills/sunset/SKILL.md:206 · (Phase 6 token read and curl are two separate command lines) · fixed · now :205-208, one command line with an empty-token branch and `unset T`; verifier executed the exact line against fake credential files (env set, env unset, no key, file missing, empty env, null token) and a two-call control that reproduced the old empty Bearer
- MAJOR · plugins/sun/skills/sunset/SKILL.md:59 · (principle "archive it first" contradicts the new Phase 4 order) · fixed · :59 now says copy after the move, never before; full-file sweep found no sentence ordering the copy first (static)
- MAJOR · plugins/sun/skills/sunset/SKILL.md:217 · (under `--keep-local` nothing creates `_archive/<Name>` before Phase 7's backup) · fixed · now :215 `mkdir -p ~/Developer/_archive/<Name>` precedes the `pg_dump` redirect; verifier reproduced the keep-local trace and the full Phase 4 + 7 sequence in a scratch tree, no nesting, guard still fires on a pre-existing path
- MINOR · plugins/sun/skills/sunset/SKILL.md:206 · broke: `jq` is an undeclared dependency and its `2>/dev/null` swallows "command not found" — with `VERCEL_TOKEN` unset and `jq` absent the line prints `no Vercel token in either source` although a valid credentials file exists, and step 3 sends Tony to do it by hand with the wrong diagnosis · fix-introduced by the Phase 6 rewrite

### 2026-09-05 — recheck: Slice A (lap 2)
- MINOR · plugins/sun/skills/sunset/SKILL.md:206 · (`jq` undeclared and its `2>/dev/null` swallows "command not found", misreporting a missing jq as no token) · fixed · the line now branches on `command -v jq` when the token is empty and prints `jq not installed; cannot read the credentials file`; step 3 (:208) routes that string to the hand-to-Tony fallback; verifier executed the exact line with jq hidden, file missing, no key, env set, env unset (8 cases), `unset T` confirmed, `auth.json` count 1, never-echo 1, `both` 1

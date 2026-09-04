# agent-file-flip — Slice A requirement map (2026-09-04)

Build doc: `docs/plans/2026-09-04-agent-file-flip.md`, Slice A. Line numbers are from branch `feat/agent-file-flip-a` at the slice's final commit.

| Req | Implemented at | What the cited line says |
|---|---|---|
| R1 scope doc path, staging unchanged, three-place re-invocation hunt | `plugins/precon/skills/precon/SKILL.md:59` | `<repo>/docs/scope/<YYYY-MM-DD>-<idea>.md`; `~/Documents/<idea>-scope.md` when no repo; re-invocation looks in `docs/scope/*-<idea>.md`, `docs/<idea>-scope.md`, `~/Documents/<idea>-scope.md` |
| R1 cold read path | `plugins/precon/skills/precon/SKILL.md:85` | `<repo>/docs/reviews/<YYYY-MM-DD>-precon-cold-read-<idea>.md` when repo-owned; `~/Documents/precon-cold-reads/` when staged |
| R2 scope glob | `plugins/architect/skills/architect/SKILL.md:21` | `docs/scope/*.md`, flat `docs/*-scope.md`, `~/Documents/*-scope.md` |
| R2 architecture doc home | `plugins/architect/skills/architect/SKILL.md:51` | `<repo>/docs/architecture/<YYYY-MM-DD>-<slug>.md` when repo-owned; `~/Documents/<slug>-architecture.md` otherwise |
| R2 blind-review path, folder creation | `plugins/architect/skills/architect/SKILL.md:114` | `<repo>/docs/reviews/<YYYY-MM-DD>-architect-review-<slug>-<lane>.md` when repo-owned; `~/Documents/architect-reviews/` when staged. No same-day `-2` rule existed in this skill before, so none was added (see the build doc's assumptions) |
| R3 scope harvest order | `plugins/blueprint/skills/blueprint/SKILL.md:20` | `docs/scope/*.md` first, flat `docs/<idea>-scope.md` second |
| R3 build doc write path | `plugins/blueprint/skills/blueprint/SKILL.md:36` | `docs/plans/<YYYY-MM-DD>-<feature>.md` |
| R4 hunt tiers, build | `plugins/build/skills/build/SKILL.md:16` | `docs/plans/*.md` first with match and list-and-ask rules, flat `docs/<feature>-build-plan.md` second, later tiers unchanged |
| R4 hunt tiers, signoff | `plugins/signoff/skills/signoff/SKILL.md:28` | same wording |
| R4 hunt tiers, recheck | `plugins/recheck/skills/recheck/SKILL.md:20` | same wording |
| R4 hunt tiers, inspect (narrowing kept) | `plugins/inspect/skills/inspect/SKILL.md:18` | `docs/plans/*.md`, flat `docs/`, `plan/`, nowhere else |
| R4 hunt tiers, vertical (narrowing kept) | `plugins/vertical/skills/vertical/SKILL.md:16` | same three tiers |
| R4 hunt tiers, ship | `plugins/ship/skills/ship/SKILL.md:20` | unchanged: delegates to /build's Step 1 tiers, names no path |
| R4 hunt tiers, handoff | `plugins/handoff/skills/handoff/SKILL.md:16` | same wording as build |
| R5 `<feature>` derivation, inspect | `plugins/inspect/skills/inspect/SKILL.md:60` | `<topic>` of `docs/plans/<YYYY-MM-DD>-<topic>.md`, else filename minus `-build-plan.md` |
| R5 `<feature>` derivation, handoff | `plugins/handoff/skills/handoff/SKILL.md:57` | same derivation, then the title slug, then ask |
| R6 inspect raw path | `plugins/inspect/skills/inspect/SKILL.md:60` | `<repo>/docs/reviews/<YYYY-MM-DD>-inspect-<feature>-<lane>.md`, `-2` rule kept |
| R6 inspect scope glob | `plugins/inspect/skills/inspect/SKILL.md:20` | `docs/scope/*.md`, flat `docs/*-scope.md`, `~/Documents/*-scope.md` |
| R7 signoff verdict doc | `plugins/signoff/skills/signoff/SKILL.md:129` | per-slice file, first-run date, later runs and rechecks append, correctness-only name, punch list stays working state |
| R7 chat block field | `plugins/signoff/skills/signoff/SKILL.md:112` | `Verdict doc:` line in the SIGN-OFF block |
| R7 sentence replaced | `plugins/signoff/skills/signoff/SKILL.md:127`, `:133` | "No verdict file by default" is gone; the signature "lives in chat and in the verdict doc" |
| R8 recheck appends to the verdict doc | `plugins/recheck/skills/recheck/SKILL.md:53` | same block appended to the slice's signoff verdict doc; gap reported when none exists |
| R8 chat block field | `plugins/recheck/skills/recheck/SKILL.md:69` | `Verdict doc:` line in the RECHECK block |
| R9 vertical file and append rule | `plugins/vertical/skills/vertical/SKILL.md:70` | `docs/reviews/<YYYY-MM-DD>-vertical-<feature>.md`, reruns append, only-write rule kept |
| R10 the two moves | commit `b900f52` | `git mv` of the scope doc and the build plan; Intent source line updated; a one-line "moved" note at the top of the scope doc |
| R11 no `~/Documents` outside staging | AC1 grep below | six hits, all staging or glob rules in precon, architect, inspect |

## Acceptance evidence

AC1 (`grep -n "Documents"` over the ten skills): six hits — precon 59, 85; inspect 20; architect 21, 51, 114. Each is a staging rule or a glob that includes the staging home. PASS.

AC2 (`grep -c "docs/plans/"`): build 1, signoff 2, recheck 1, inspect 2, vertical 2, handoff 2; ship line 20 still delegates to /build's tiers. Order confirmed by reading each hunt sentence. PASS.

AC3 (fresh session, `claude --plugin-dir plugins/build -p ...`, run from the repo root on the branch): the session reported that it had both the installed copy (cache e3a59f3) and the branch copy loaded; under the branch copy it names `docs/plans/2026-09-04-agent-file-flip.md` as a tier-one hit and quotes the new first-tier sentence verbatim. Under the installed copy the same doc is found only at the "any phase/slice doc under docs/" tier. PASS for the edited skill; the note about the installed copy is the reinstall gap the build doc's Constraints describe. Log: session scratchpad `ac3.log`.

AC4: `git ls-files` lists `docs/scope/2026-09-04-agent-file-flip.md` and `docs/plans/2026-09-04-agent-file-flip.md`; `ls` of the two flat paths returns "No such file". PASS.

AC5: `git diff --stat main -- 'docs/*-scope.md' 'docs/*-build-plan.md'` is empty; the fifteen pre-existing flat docs are untouched. PASS.

AC6: this file.

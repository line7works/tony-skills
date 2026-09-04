# agent-file-flip — signoff verdict, Slice B

Build doc: `docs/plans/2026-09-04-agent-file-flip.md` · Slice B. One block per run, dated; /recheck appends its blocks here too.

### 2026-09-04 — signoff: Slice B

Verdict: SIGNED OFF WITH CONDITIONS
Scope: branch `feat/agent-file-flip-b` vs `main`, one commit (f2b055c), working tree clean: `plugins/sun/skills/sunrise/SKILL.md`, `docs/evidence/agent-file-flip/slice-b-requirement-map.md`, the build doc's ledger. All inside the slice footprint; nothing excluded.
Depth: LEAN (spec, correctness, seams) · Method: reviewers re-ran AC1–AC6 independently (greps, two scratch renders with `git init`, the kit's three lines, the headless canary in plain and framework-block renders, a fresh `--plugin-dir plugins/sun` session for AC4); the inspector read the saved canary outputs and the source at every MAJOR · Refuted: 1

MAJOR
- `plugins/sun/skills/sunrise/SKILL.md:320` · the canary rule expects the framework block's opening marker `<!-- BEGIN:nextjs-agent-rules -->` as the quoted line · a Next.js render with the block on line 1 returned "This is NOT the Next.js you know. Read node_modules/next/dist/docs/ before writing code." (saved run); per :320 that is a failed baseline with nothing in the fix list to fix, so the default web-app archetype can never print SUNRISE COMPLETE · CONFIRMED (correctness; spec noted the same as spec-level)
- `plugins/sun/skills/sunrise/SKILL.md:184`, `:208–214`, `:326` · the staged-doc lookup checks only `~/Documents`, never the destination · a run that dies after step 5 moved the scope doc and is re-invoked (Core principle "Resumable", :86) previews, adopts, and summarises "nothing staged" while `docs/scope/<date>-<slug>.md` sits in the repo · CONFIRMED (correctness)
- `plugins/sun/skills/sunrise/SKILL.md:201–202` with `:320` · step 3's merge rules cover a framework block in `AGENTS.md` and a `CLAUDE.md` that is already `@AGENTS.md`; a `CLAUDE.md` with real content (every pre-flip sunrised repo under `--promote`; a scaffolder that ships one) has no rule · the body is left in `CLAUDE.md`, kit line 2 fails, and :320's "fix the file (stub content)" is an overwrite of a file :80 says never to clobber; no instruction lifts the body into `AGENTS.md` first · CONFIRMED (seams, correctness, spec converged)
- `plugins/sun/skills/sunrise/SKILL.md:415` · the template's `Env: vercel env pull writes .env.local` line carries no `<...>` placeholder, so :400's rule keeps it in every render · a library, script, static, or `--no-vercel` sunrise seeds a command the repo is not linked to; monorepo/Electron get the wrong path (Phase 4 step 4 pulls to `apps/<app>/.env.local`) · CONFIRMED (correctness; spec rated it MINOR)

MINOR
- `SKILL.md:211` · the `-2` rule says it matches "precon's own naming"; precon has no same-day rule (Slice A punch list already records it), and the one real same-day pair is infix-named (`…-cold-read-2-2026-08-29.md`) · which file gets `-2` is left to inference; the rule itself prevents the overwrite the spec reviewer feared
- `SKILL.md:212` · a lane-less architect review (`bar-builder-review-2026-09-02.md`) renders `…-architect-review-bar-builder-.md`; staged lane tags (`gpt-5.6-sol`) differ from architect's `gpt|gemini|claude` vocabulary, so `docs/reviews/` holds two naming schemes for one role
- `SKILL.md:208–209` · slug-exact match: `clerk-entity-scope.md`, `torvane-entity-scope.md`, `ship-scope.md` are never found by the project slugs they belong to; spec-compliant (R5 says "matched by the project's slug") but two of seven live staged docs would be stranded with "nothing staged" printed · see Questions
- `SKILL.md:214` · moved docs carry `~/Documents` pointers in their `Research:` / `Scope doc:` / `Blind review:` lines and no "moved from" line is added (the kit's top-of-file convention, followed by Slice A's own move) · prose dangles; hunts still work
- `SKILL.md:309–320` · the kit check is a continuation of Phase 8 step 1, which ends "If `--no-vercel`, skip" · a library sunrise can read the skip as covering the check and print `kit check 4/4` unrun
- `SKILL.md:400–401` with `:417–423` · "a `<...>` placeholder is filled or the line is cut" vs "the empty-section placeholders stay as one line each": the Conventions and Footguns lines are both · two sessions render two files; a committed angle-bracket line is rent
- `SKILL.md:428–429` · the vault path and the Notion URL stay while the local-path line was cut for the same spec-sheet reason ("nothing about you or your machine") · inconsistent; on a `--public` sunrise both are Tony-specific exposure
- `SKILL.md:429` with `:265` · `<parent page URL>` does not exist at seed time, so :400 cuts it; Phase 5 step 6 re-adds it after the Phase 2 push with no commit step
- `SKILL.md:432–433` · the two git gates carry no reason and no "do instead" (spec sheet "Writing the file"); carried verbatim from the old template as R1 directs
- `SKILL.md:208` vs `:214` · "Look for exactly these" fixed filenames for scope and architecture, then a "two scope docs, two architecture docs" branch a fixed path can never reach
- `SKILL.md:311–320` with `:221`, `:325` · the kit check runs after Phase 2 pushed `main`; a fixed `CLAUDE.md`/`AGENTS.md` is never re-committed or re-pushed, and the summary prints "(git init, pushed); kit check 4/4" for a remote holding the broken files
- `SKILL.md:320` · the plain-render canary quotes `@AGENTS.md` first, then `# <Name>`; "its answer must match line 1" read on the first quoted line fails; the requirement map's own AC2 evidence has the same two-quote shape
- `SKILL.md:214` · "the doc's own header" is undefined for review files (title line vs a `**Date:**` line vs no heading); `~/Documents/agent-world-scope.md` is a MOVED tombstone with no date and would be adopted after asking Tony for one
- `SKILL.md:164–187` with `:214` · a multi-candidate set is listed in the preview under "Reply go", then asked again at step 5
- `SKILL.md:201–202` · edge cases with no rule: a scaffolder `CLAUDE.md` that is `@AGENTS.md` plus further lines (AC3's one-line property silently stops holding); a scaffolder title above its framework block ("stays at the top" vs "untouched")
- `docs/evidence/agent-file-flip/slice-b-requirement-map.md:50` · AC4 evidence is a paraphrase citing a scratchpad log outside the repo; the spec reviewer re-ran AC4 and it passes, but the filed evidence is not reproducible from the checkout
- `SKILL.md:214` · every architect-reviewed idea pauses at adoption, because one file per lane is architect's normal output

Refuted (1): the iCloud dataless-file concern (correctness, low confidence) — the reviewer checked every staged file and none is evicted; no failure scenario, a hunch.

Deferred / notes for Slice D (not defects): `.claude-plugin/marketplace.json:81` (architect's entry) still says Tony "hand-points /sunrise" at the architecture doc; the vault note `01-domain/claude-skills/sunrise.md:38–39` still describes the old seed set; repo `CLAUDE.md:20` does not mention Tier 0. Slice D R1/R2/R4 own those. precon's What-NOT line (`plugins/precon/skills/precon/SKILL.md:130`) still contradicts the adoption step; outside this slice's footprint, carried in Discovered.

Tried and failed to break
- AC1 grep: no hits; all ten remaining `CLAUDE.md` mentions describe the stub role; no unlisted passage still treats `CLAUDE.md` as primary. R3's nine passages all rewritten; `REVIEW.md` never seeded at :200.
- AC2/AC3: two independent scratch renders (`fakeproj`, `Fakelib`), `git init -b main`, one commit: the kit's three lines pass; `wc -l CLAUDE.md` = 1 (11 bytes, trailing newline); plain canary quotes line 1 of `AGENTS.md`. Rendered `AGENTS.md` ~1.2–1.3 KB, inside the spec sheet's budget.
- AC4: a second fresh `--plugin-dir plugins/sun` session (the spec reviewer's) named all six files, both vault notes, the four lines, the failed-baseline rule, and none/one/many verbatim.
- AC5: :163 and :206. AC6: all 24 citations open to the claimed text.
- Footprint: diff touches exactly the three named files; sunset untouched (`git diff main..HEAD -- plugins/sun/skills/sunset/` empty; its only `AGENTS.md` hit is the vault guard); README, marketplace, plugin.json, repo `CLAUDE.md`, vault sunrise note untouched; `${CLAUDE_PLUGIN_ROOT}` refs unchanged; `!.env.example` rule kept and verified in a render.
- Step order after the split: step 2's "before step 4", step 3's "step 5 below", Phase 0's "Phase 1 step 5" all point at the right steps; nested `claude -p` from inside a session runs (exit 0).
- Destination names vs Slice A: `docs/scope/<date>-<slug>.md`, `docs/architecture/<date>-<slug>.md`, `docs/reviews/<date>-precon-cold-read-<slug>.md`, `docs/reviews/<date>-architect-review-<slug>-<lane>.md` match precon :59/:85 and architect :51/:114; blueprint, inspect, architect, and precon's re-invocation hunts all find an adopted doc when slugs agree. Header date rule matches precon's and architect's title formats; all seven live scope docs carry it.
- `CLAUDE.md` template vs "The stub, exactly" and the companion note: one line, real file, section only with Claude-only lines; the `AGENTS.md` body uses plain paths, no `@import`, `<!-- verified -->` on line 2 per the skeleton. create-next-app happy path: stub kept, block kept at top, canary expectation set (but see MAJOR 1).
- Other skills: no loop skill reads a sunrised repo's `CLAUDE.md` as a body; memory-note and handoff-prompt templates point at `AGENTS.md`.

Questions
- Slug matching (MINOR 3): R5 says "matched by the project's slug" and the build follows it, but `clerk-entity`, `torvane-entity`, and `ship` staging would never be found. Widen to a `*<slug>*` list-and-ask (as Phase 0's local collision check already does), or keep exact and accept "nothing staged" as the signal?
- Machine facts in `AGENTS.md` (MINOR 7): keep the vault path and Notion URL in the repo file, or move both to the memory note and vault `_index.md` like the local path?

Next: fix the four MAJORs, then /recheck flips the card.

### 2026-09-04 — recheck: Slice B
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:320` · (canary rule expects the framework block's comment marker as the quoted line) · fixed — now :321; the rule names the block's first prose line and the stub's own `@AGENTS.md` quote; verifier rendered the framework fixture and ran the canary: "This is NOT the Next.js you know…" passes under the current text
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:208` · (lookup checks only `~/Documents`, never the destination) · fixed — now :209/:215, preview :155–158, summary :327–328; verifier walked the re-invoked run: destination globs first, `already adopted: <path>` in all three places, `nothing staged` only when nothing was adopted
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:202` · (no merge rule for a `CLAUDE.md` with real content) · fixed — now :203; body lifted into `AGENTS.md` below any framework block, old stub text dropped, `CLAUDE.md` rewritten to the stub, merged file shown first; Phase 8 :321 routes a non-stub through that rule, no bare overwrite remains
- MAJOR · `plugins/sun/skills/sunrise/SKILL.md:415` · (`vercel env pull` line has no placeholder) · fixed — now :417–420; the Env clause is one `<...>` placeholder with linked / app-scoped / no-Vercel branches; verifier walked library and monorepo renders
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:321` · broke: "step 3's merge rule" is unqualified inside Phase 8, whose own step 3 is the handoff prompt — a literal reader resolves it to the wrong step · fix-introduced by the Slice B fix pass
- MINOR · `plugins/sun/skills/sunrise/SKILL.md:136` · broke: the preview example still describes the Docs line as two-way (staged lines or "nothing staged") while the rule below adds `already adopted` · illustration not updated with the rule · fix-introduced by the Slice B fix pass

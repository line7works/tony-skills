# Architect — scope doc (2026-08-21)

Intent: /architect — the missing drawings step in the build pipeline. Runs after
/precon settles scope and before anything is provisioned or sliced. One
interview that produces the architecture-and-delivery doc: the least structure
that serves a named first user's walkthrough without becoming demolition later.
For Tony, a solo new developer whose architecture decisions currently get made
implicitly by /blueprint or by /sunrise's archetype template at the moment of
least information. Born from "Iterating without users is just guessing with
extra steps" and the 2026-08-17 Occam's razor idea.

Decisions:
- One skill, two passes: delivery (walkthrough target) + architecture, run as one negotiation — the tension is the product; never split into two skills — decided (Tony devil's-advocated the split twice, agreed joined)
- Pipeline position: after /precon, before /sunrise and /blueprint — decided (Tony: "it all needs to come well before we even start to conceptually build anything")
- Interview order: (1) walkthrough target — named real person, date, what they must be able to do; (2) architecture grilled against that target; (3) one-way-door check against the full vision — decided (discussion, Tony: "I agree. I'm liking this more and more")
- Grilling criterion is the razor: every component must point at a walkthrough requirement or it's cut from v0 — decided (Tony's Occam's razor thread; agreed this is the blade, not a standalone skill)
- Architecture pass must force 2–3 genuinely distinct candidate structures into the open, with what each assumes and what each makes expensive later — never "Claude proposes, Tony nods" — decided (Tony: "I think we need a hard grilling on that")
- "Distinct" candidates means differing in at least one one-way-door category (platform, storage, repo shape, language, or data shape), never variations of one shape — decided (Tony, 2026-09-01, adjudicating inspect MAJOR 1: "agreed")
- Decisions at full-vision quality, construction at MVP quantity; deciding is free, provisioning is not; banked decisions recorded but not built (e.g. "becomes Postgres when scores go remote") — decided (Tony: "This is starting to make sense to me" after the wrong-language/wrong-DB challenge)
- One-way doors (language, database kind, repo shape, data shapes, platform) decided for the vision up front; everything else stays two-way — decided (discussion of Tony's three "what if wrong X" fears)
- Output: one doc with four parts — walkthrough target, v0 drawing, poured-concrete list, deferred list (banked decisions + deliberately-not-built, each confirmed to keep its door open) — decided (discussion)
- Output doc is consumed downstream: /sunrise provisions exactly what it lists; /blueprint slices from it with the user-touchable slice up front — decided (Tony: "sunrise takes its answer from the Architectural doc")
- /architect itself never provisions anything — doc only; execution belongs to /sunrise — decided (demote-don't-demolish discussion)
- Exit ramp: first interview question is "is there a system here at all?" — a single static page ends the interview in a minute — decided (Tony agreed re: small ideas he has often)
- Name: /architect — decided (Round 1 Q1)
- ~~Pre-repo doc location: ~/Documents/<project>-architecture.md, beside the precon scope doc; moving it into <repo>/docs/ is manual until the /sunrise rework adds it — decided (Round 1 Q2)~~ superseded 2026-09-02
- Architecture doc location: beside the precon scope doc, wherever that is — `<repo>/docs/<slug>-architecture.md` when the scope doc is repo-owned, `~/Documents/<slug>-architecture.md` otherwise — decided (Tony, 2026-09-02, adjudicating inspect Q2: "besides the scope doc")
- Grilling is Claude-only inside the run; after the run, the skill ASKS Tony whether he wants an outside-model review; if yes, the external model does NOT get Claude's output — it gets the brief fresh — decided (Round 1 Q3, Tony's words: "the model reviewing it doesn't get the Claude input. It gets it fresh")
- Input: /architect takes the precon scope doc — decided (Round 1 Q5)
- ~~Skill home: ~/.claude/skills/architect, like /precon; not its own repo — assumed (matches the loop-skill convention; reversible)~~ superseded 2026-09-01
- Skill home: `plugins/architect/skills/architect/SKILL.md` in `~/Developer/tony-skills`, catalogued in `.claude-plugin/marketplace.json` like /inspect; the hand-copy path is gone since the 2026-09-01 skills migration — decided (Tony, 2026-09-01: "skill home becomes plugins/architect/skills/architect/SKILL.md in this repo")
- Strictly user-invoked, never auto-triggered — assumed (every skill at this altitude follows the /precon rule; nothing suggested otherwise)
- Narrowness guardrail: the interview stays short (~three answers + sorted scope); if it grows into heavy ceremony it delays the MVP it exists to accelerate — assumed (recommended in discussion, unchallenged; front of spine already crowded)
- Until the /sunrise and /blueprint reworks land, Tony hand-points those skills at the architecture doc — assumed (same interim rule /precon states for its scope docs)
- External review mechanics: the outside model receives the precon scope doc ONLY (blind to Claude's work) and returns its own full architecture take; saved verbatim to a file; the skill then presents the two docs' disagreements side by side and Tony rules each one in discussion; the architecture doc changes only where he rules, nothing merges silently — decided (Round 2 Q1, Tony: "it's blind to Claude's decisions... we compare the two docs and have a discussion")
- Invoked without a precon scope doc, /architect stops and opens a discussion on why it's being run docless — a conversation gate, not a silent refusal — decided (Round 2 Q2, Tony: "I won't be summoning architecture without a precon doc. And if I do, I'll have a discussion on why I'm doing that")
- External review transport: same as /precon's exit test — GPT via the codex MCP, pinned model per jpb's SKILL.md, another model on Tony's pick per run; sends only on his explicit word — assumed (established convention for external sends; reversible)
- Blind-review output files land in ~/Documents/architect-reviews/<project>-review-<date>.md, verbatim — assumed (mirrors the precon-cold-reads pattern; mechanical)
- Walkthrough = the dated session where the named first user actually touches the built thing; the interview's "date" is that session's target date — decided (cold-read absorption; restates what step 1 meant in discussion)
- "Poured-concrete list" and "one-way doors" are one list with two names; the five named categories (language, database kind, repo shape, data shapes, platform) are the checklist floor, not a cap — assumed (cold-read absorption; the discussion treated the set as examples, not a limit)
- The "brief" the external model receives IS the precon scope doc — one input, one name — decided (cold-read absorption; restates Round 2 Q1)
- ~~The external-review offer comes once, at the end of every run — decided (Round 1 Q3: the skill asks Tony after the run)~~ superseded 2026-09-02
- The external-review offer comes once, at the end of every run that had a precon scope doc; docless runs get no offer because there is no brief to send — decided (Tony, 2026-09-02, adjudicating inspect Q1: "agreed no offer")
- ~~"Another model on Tony's pick" substitutes for the pinned GPT; never a second reviewer — assumed (matches /precon's exit-test shape; cold-read absorption)~~ superseded 2026-09-02
- The offer names the pinned GPT as the default reviewer; Tony may answer with several reviewers (GPT, Gemini, Claude) and each runs as its own cold take on the scope doc only — decided (Tony, 2026-09-02, mid-run: "I'd like the skill to be able to run multiple reviewers like we do for the Blueprint sign-off")
- <project> in output and review filenames = the precon scope doc's slug — assumed (mechanical; cold-read absorption)
- Pass-to-step mapping: delivery pass = interview step 1; architecture pass = steps 2 and 3 — assumed (clarification only; cold-read absorption)
- Exit-ramp runs still write a tiny architecture doc ("static page, no system, no provisioning beyond repo") — "no doc" stays reserved for ideas that never saw /architect — decided (Round 3 Q1, Tony: "if there's no real architecture to be decided, that's fine")
- Docless runs may proceed after the gate discussion lands on a reason; the reason is recorded at the top of the architecture doc — decided (Round 3 Q2)
- v0 drawing = component list (what exists) + plain-prose data flow (what talks to what) + one simple diagram — decided (Round 3 Q3)
- /architect is re-runnable: when the idea blossoms or changes (possibly after a fresh /precon), a new run continues the record with a visible trail — ran before, running again because X changed — decided (Tony: "there should be a trail already that we ran it once. Now we're running it again because things have changed")
- End of every run produces a visual — an HTML/artifact rendering of what was decided: the systems chosen and what each does/provides for the project — decided (Tony: "an artifact or HTML visual since I'm a visual learner")
- Re-run mechanism: one living architecture doc per project (never a fork), with a run-log section (date, trigger, what changed) and superseded decisions struck through, not deleted — assumed (matches /precon's one-living-doc rule; the trail is the decided part, this is its mechanics)
- The visual is a projection re-rendered from the doc each run; the markdown doc stays the record — assumed (same doc-is-record principle as /jpb's arcade page)
- The visual is delivered as a private Claude Artifact, same URL kept across re-runs — decided (Round 4 Q1: "Artifact")
- The visual's design is deliberately unspecified — it gets established over time, run by run; /blueprint should not over-spec it — decided (Tony: "we'll establish what it looks like over time")
- The artifact's source HTML is written beside the architecture doc (that is what gets published; not a separate deliverable) — assumed (mechanical: an Artifact publishes from a file)
- Docless runs get no blind-review offer — there is no brief to send (the reviewer receives the precon scope doc ONLY); the run's report records "review: not offered — docless run" — decided (Tony 2026-09-02 "agreed no offer"; drafted 2026-09-01 on Tony's "fix the blockers/majors"; resolves the docless-vs-every-run contradiction GPT's inspect caught; reversible)
- Scope-doc discovery: the path given in the invocation, else a glob over precon's two homes — `<repo>/docs/*-scope.md` when invoked inside a repo, plus `~/Documents/*-scope.md` — matched by title; more than one match is listed and asked, never silently picked — assumed (drafting session 2026-09-01; mirrors precon's and blueprint's harvest rule; reversible)
- Docless runs take the current discussion as their input once the gate lands on a recorded reason — assumed (drafting session 2026-09-01; reversible)
- Architecture doc home: beside the precon scope doc — `<repo>/docs/<slug>-architecture.md` when the scope doc is repo-owned, `~/Documents/<slug>-architecture.md` otherwise; the visual's HTML sits beside it as `<slug>-architecture.html`; a docless run's slug is the project's working name settled at the gate — decided (Tony 2026-09-02 "besides the scope doc"; drafted 2026-09-01; resolves the "~/Documents" vs "beside the precon scope doc" tension in the Round 1 Q2 line above; reversible)
- The chosen candidate and each rejected candidate's one-line why are recorded in the run log — assumed (drafting session 2026-09-01; reversible)
- A re-run reads the recorded Artifact before republishing to the same URL; a re-run finding no recorded URL publishes fresh and records the new URL — assumed (drafting session 2026-09-01; mechanics of "same URL kept"; reversible)
- External review transport guards are jpb Judge G's four (jpb SKILL.md, Judge G config): scope-doc-only payload, `web_search: disabled`, read-only sandbox, an absolute empty cwd created fresh for the run — assumed (drafting session 2026-09-01; precon's exit test carries only `web_search: disabled`, so the extra two are jpb's, not precon's; reversible)
- Report block fields (run number, counts of components / poured-concrete decisions / deferred items) are house-style extrapolation, not a ruling — assumed (drafting session 2026-09-01; reversible)
- Publishing the private Artifact is the decided visual delivery (Round 4 Q1), not an "external send" under the property line; the property line's send rule governs sending content to another model — assumed (drafting session 2026-09-01; reversible)
- Harness-mandated preflights (the Artifact tool requires loading the `artifact-design` skill before writing a page) are not skill invocations under "invokes no other skill" — assumed (drafting session 2026-09-01; reversible)
- Property line during a run: the repo, project docs, and Claude's own knowledge only — no web, no research subagents; a factual unknown needing outside checking becomes a marked line in the architecture doc for Tony to resolve; the only sanctioned external send stays the blind review, on Tony's word — decided (blueprint interview Q1, Tony's "Ok then" 2026-08-21; ledgered post-gate after the blueprint cold review caught the answer missing from this doc)

Out of scope: /sunrise + /sunset rework — Tony's ruling (Round 1 Q4): follow-on build after /architect ships, informed by what it teaches; ~~findings captured in ~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md~~ (that file does not exist on disk — verified 2026-09-01 by four /inspect lanes; no record of the findings survives)
Out of scope: hierarchical /blueprint (vertical slices → sub-blueprints, deferred detail) — Tony parked it for after /architect lands; ~~noted in the same findings doc~~ (no surviving record)
Out of scope: standalone Occam's razor skill — resolved into /architect's grilling criterion (Tony agreed 2026-08-21)
Out of scope: named tiers/versions of /sunrise — Tony ruled the doc is the tier; no editions

~~Research: ~/Documents/handoffs/2026-08-21-architecture-skill-sunrise-sunset-findings.md (pre-precon findings capture from this discussion)~~ — file does not exist on disk (verified 2026-09-01)
Research: ~/Developer/tony-skills/docs/blueprint-review-experiment-2026-08-21.md (the parked "/blueprint post-draft cold review" idea's only surviving record: its first live test)
Research: `docs/reviews/2026-08-21-architect-cold-read.md` (both cold reads verbatim — fresh Claude + GPT — with disposition of every item)

Open: none

B-AC7 limit: the smoke test's blind-review path is exercised only if Tony says yes during the smoke run; a decline passes the slice with the path recorded as not exercised — decided (Tony, 2026-09-02, adjudicating inspect Q3: "accept")

Next: /blueprint when ready.

# Skills migration — cold read (2026-08-31)

Reader: local Claude subagent, zero context, read-only. Target: `~/Developer/tony-skills/docs/skills-migration-scope.md`.

## Triage summary

26 findings. **22 absorbed** into the scope doc (facts looked up, wordings tightened, care rules added). **2 surfaced** to Tony as Round 2 questions: #18 (build docs would be world-readable) and #24 (repo name is at its last cheap rename moment). **2 left downstream** to /blueprint: #16 (internal path updates when skills move install locations — build-time work) and #26 (acceptance criteria and rollback — that is exactly what blueprint slices carry).

## Disposition

1. absorbed — full 20-skill roster added to the doc
2. absorbed — assumed: one plugin per skill, existing sun bundle kept
3. absorbed — all migrating skills get marketplace.json entries, not just shutdown
4. absorbed — fact: third-party plugins are installed from other marketplaces, not present in this repo
5. absorbed — definition of done added; the flip is the last step, still gated
6. absorbed — private installs work via the Macs' authenticated GitHub access; blueprint verifies
7. absorbed — publishable = public repo + README install line
8. absorbed — scrub reworded: report-only audit, then gated remediation
9. absorbed — full git-history scan added to scrub scope
10. absorbed — env-read edits are remediation scope; "identical" = no user-visible change
11. absorbed — secrets always remediated; exposure findings ruled per item by Tony
12. absorbed — per-finding ruling at scrub review; unresolved findings block the flip
13. absorbed — Studio is the sync source; per-machine diff before hand-copy removal
14. absorbed — laptop participates via claude-relay, Tony-triggered
15. absorbed — post-migration authoring: edit in repo, ship via PR/merge, marketplace delivers
16. left downstream — path-reference updates inside skills are build-time work for /blueprint ACs
17. absorbed — skill-lab docs move (not copy); loop-skill pointers update in the same slice
18. surfaced — Round 2 Q1: build docs world-readable
19. absorbed — decision sources are cited inline per line; the rounds live in the session record
20. absorbed — pointer to the architect build plan added
21. absorbed — architect lands as plugins/architect/ + docs/ plan; nothing else to accommodate
22. absorbed — repo identity stated: ~/Developer/tony-skills is tiny-tunnel-dot/tony-skills
23. absorbed — true GitHub transfer; Tony admins both sides; remote URLs update on both Macs
24. surfaced — Round 2 Q2: rename before install lines are distributed
25. absorbed — dig wording fixed (Tony's own product shipping from its own repo, not third-party)
26. left downstream — acceptance criteria and rollback are /blueprint altitude by design

## Reader output, verbatim

### Counts and inventory

1. **The number 20 never reconciles.** Line 3 says "all 20 of Tony's personal Claude Code skills." The doc then accounts for 12 repo-less skills (line 10), 5 drifted mirrors (line 16), and 1 unregistered `shutdown` plugin = 18. Line 19 mentions "inspect and the six registered plugins." What are the remaining 2, and is `inspect` one of them? There is no roster in the doc.

2. **Skill vs. plugin is used interchangeably and the mapping is undefined.** Line 10: "All 12 repo-less skills migrate into `plugins/`" but line 19: "Plugin folder shape follows the existing `plugins/<name>/skills/<skill>/` convention." That shape allows many skills per plugin. Is the target one plugin per skill (20 plugins), or grouped plugins (e.g. a "build-loop" plugin holding blueprint/build/signoff/recheck/ship/vertical)? This changes every install line and every `marketplace.json` entry.

3. **"the unregistered shutdown plugin gets registered in marketplace.json"** — the doc never says where `marketplace.json` lives, what its schema is, or whether the other 12 migrating skills also need entries added (presumably yes, but it's only stated for `shutdown`).

4. **Out-of-scope third-party plugins are ambiguous about current location.** Line 28 excludes "vercel, shopify-ai-toolkit, dig, frontend-design." Are those currently sitting inside this repo's `plugins/` directory (and therefore need to be *removed* / left alone), or are they simply installed elsewhere and never touched? "Migrating" implies they might be present.

### The public flip

5. **Is the repo public at the end of this migration, or not?** Line 21 states as decided "One public repo holds all 20 skills," but line 12 says "Any public flip happens only on Tony's explicit word after he reviews the scrub findings." So does the migration finish private-with-a-pending-decision, or is going public part of done? The definition of done is not stated anywhere.

6. **Does marketplace install even work while the repo is private?** Both Macs installing "via the marketplace" (line 9) is the load-bearing outcome, and the public flip is gated behind a scrub. If private marketplace installs need auth (token, SSH), that's unaddressed; if they don't work at all, the gate on line 12 blocks the whole migration.

7. **"the shareable skills publishable to other people" (line 3) vs. "One public repo... no public/private split" (line 21).** If everything is public, what distinguishes a "shareable" skill from a machine-wired one in practice? Is there a documentation/README obligation for strangers, an install line to publish somewhere, or is "publishable" satisfied merely by the repo being public?

### The scrub

8. **Scrub scope says "search-only audit" (line 13) but also that "real secrets move to local config (keychain/env)."** Those conflict — moving secrets is a write, not an audit. Is the scrub a report-only pass whose remediation is a separate step, or does it edit files?

9. **Git history is never mentioned.** A scrub of the working tree does not remove a key or an email from prior commits. Does scope include history inspection/rewrite before the public flip, or is the assumption that history is clean? For a repo that has lived under `tiny-tunnel-dot`, this seems load-bearing.

10. **"skills keep working identically for Tony throughout" (line 13) vs. moving secrets to keychain/env.** If a skill currently has a literal key inline, moving it to env requires editing the skill to read from env. Is that edit in scope, who writes it, and does "identically" mean no behavior change or no *user-visible* change?

11. **"personal-infrastructure exposure" is undefined.** Does that mean absolute paths like `/Users/tonycoon/...`, machine names, `~/Documents/handoffs`, Obsidian vault paths, Notion/Supabase/Vercel project IDs, his email? Some skills appear to be built around those paths, so the threshold matters a lot.

12. **What is the disposition rule when the scrub finds something?** Line 12 says Tony reviews findings before a flip — but is there a per-finding decision (redact / parameterize / accept), and does a finding block the flip automatically?

### Drift, mirrors, and the two Macs

13. **"The 5 drifted mirrors ... sync repo-from-live" (line 16) — live on *which* Mac?** The doc establishes two Macs each with hand-copied `~/.claude/skills`. If the two hand copies have themselves drifted from each other, "live" is ambiguous. Line 16 says "live copies are newer in every case inspected 2026-08-31" — inspected on one machine or both?

14. **The laptop's participation is unspecified.** Line 9: "the laptop gets a one-time install line." Is the laptop reachable during this work, does Tony run the line by hand later, and is the migration considered done before the laptop is verified? Line 20 gates removal of hand copies on "the installed versions are verified working *on that machine*" — who performs the laptop verification and when?

15. **How does authoring work after the hand copies are deleted?** The stated purpose is "killing mirror drift permanently" (line 3), but the doc never says what replaces in-place editing of `~/.claude/skills`. Edit in the repo → push → reinstall? If a skill is edited live post-migration, drift returns immediately. This feels like the central workflow question and it isn't in the doc.

16. **Do plugins carry their executables?** Several skills clearly drive CLIs/scripts (an arcade-publish CLI, a Python image CLI). Does the migration move those binaries/scripts into the plugin folders, and do any skills reference their own on-disk path (which changes when installed from a marketplace rather than `~/.claude/skills`)?

### Moving the skill-lab docs

17. **Line 23: "The `~/Documents/skill-lab` build docs move into the repo's `docs/`."** Move or copy — is `~/Documents/skill-lab` emptied/deleted? And are there existing skills that write to that path (a feedback doc lives there per the loop skills' own instructions) whose pointers must be updated as part of this migration?

18. **Those build docs are going into a repo intended to be public.** Are they in scope for the scrub (line 13 doesn't say), and is Tony aware they'd be world-readable — build/feedback docs typically contain candid project detail.

### Provenance and missing references

19. **"Round 1 Q1 / Q2 / Q3" (lines 21–23, 30) reference a decision round that is not in this doc and not linked.** Where is that record, and is there a Round 2 that produced answers not captured here?

20. **Line 27: "its seven adjudicated rulings stand and nothing about them expires."** Seven rulings about the architect skill are asserted but never listed or linked. If migration must not violate them, I can't check that without the source.

21. **The "architect skill" is named as the thing this migration unblocks (lines 11, 27) but never described.** Does the migrated structure need to accommodate anything specific for it (a plugin slot, a docs convention)?

22. **Line 18: "This scope doc lives at `tony-skills/docs/skills-migration-scope.md` — assumed ... session was invoked elsewhere."** Is `tony-skills` on disk already the same repo that becomes the marketplace, and is it already the one under `tiny-tunnel-dot`? The doc assumes yes but says the session ran somewhere else, which leaves the identity of "the repo" slightly open.

### Transfer mechanics

23. **"transfers from tiny-tunnel-dot to the line7works org" (line 6)** — is `tiny-tunnel-dot` a personal account or another org, does Tony hold admin on both (required for a GitHub transfer), and is a true transfer intended rather than a fork/re-push? A transfer changes the remote URL — does anything on either Mac (existing clones, install entries, CI, other marketplaces) point at the old URL?

24. **Line 15 keeps the name `tony-skills` under a company org while the repo goes public.** Is a personally-named public repo under `line7works` the intended presentation given the "publishable to other people" goal? The doc calls a rename "cheap and independent later" — is that a real deferral or does it become expensive once install lines are distributed?

25. **Line 17 says `line7works/dig` is untouched, and line 28 also excludes `dig` as a third-party plugin.** Minor, but the two lines describe `dig` differently ("a shipped product with its own marketplace" vs. "third-party"), which makes me unsure whether Tony's `dig` skills are his own work being deliberately excluded from the "all 20."

### Completion criteria

26. **There are no acceptance criteria and no rollback.** "Open: none. Next: /blueprint when ready." (lines 34, 36) — but nothing states how migration success is verified (does every one of the ~20 skills get invoked once post-install?), what happens if a skill breaks after the hand copies are removed, or how to revert a bad transfer.

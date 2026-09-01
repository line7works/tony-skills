# Skills migration — scope doc (2026-08-31)

Intent: Move all 20 of Tony's personal Claude Code skills into one plugin-marketplace repo under the line7works GitHub org, installed on both Macs through the marketplace instead of hand-copied into ~/.claude/skills — killing mirror drift permanently — with the shareable skills publishable to other people.

Decisions:
- tony-skills transfers from tiny-tunnel-dot to the line7works org — decided (Tony: "I was thinking we put all my skills under line7works", confirmed in discussion 2026-08-31)
- One repo holds all personal skills as a plugin marketplace; repo-per-skill rejected — decided (Tony accepted the standard pattern after reviewing community evidence, 2026-08-31)
- Skills may be made public — decided (Tony: "It doesn't have to be private. I don't mind making my skills public")
- Both Macs install skills via the marketplace, replacing hand-copied ~/.claude/skills copies; the laptop gets a one-time install line — decided (the drift-kill purpose Tony accepted in the marketplace discussion)
- All 12 repo-less skills migrate into plugins/ (blueprint, build, digest, fb, handoff, huh, jpb, precon, print-tune, recheck, ship, vertical); the unregistered shutdown plugin gets registered in marketplace.json — decided (the inventory punch list Tony carried forward into this migration)
- This migration runs before the architect skill work; architect then builds into the migrated structure — decided (Tony asked the ordering question 2026-08-31 and proceeded on migration-first)
- Any public flip happens only on Tony's explicit word after he reviews the scrub findings — decided (Tony's standing git gates; scrub usability concern resolved in discussion)
- Scrub scope: search-only audit for secrets, keys, emails, and personal-infrastructure exposure; real secrets move to local config (keychain/env), never deleted from Tony's machines; skills keep working identically for Tony throughout — decided (Tony's usability questions answered and accepted 2026-08-31)
- A pre-flip scrub is mandatory before any repo goes public — assumed (non-negotiable safety gate for publishing; Tony's only stated concern was usability, which was resolved)
- The repo keeps the name tony-skills through the transfer — assumed (a rename is cheap and independent later; nothing downstream depends on the name)
- The 5 drifted mirrors (arcade, forge, signoff, sunrise, sunset) sync repo-from-live — assumed (live copies are newer in every case inspected 2026-08-31; per-file verification still happens at build time)
- line7works/dig and line7works/meters are untouched — assumed (dig is a shipped product with its own marketplace; meters is unrelated)
- This scope doc lives at tony-skills/docs/skills-migration-scope.md — assumed (the idea unambiguously belongs to this repo; session was invoked elsewhere)
- Plugin folder shape follows the existing plugins/<name>/skills/<skill>/ convention — assumed (matches inspect and the six registered plugins)
- Hand copies in ~/.claude/skills are removed only after the installed versions are verified working on that machine — assumed (removal is the drift kill Tony accepted; the verify-first ordering is standard care, blueprint will gate it)
- One public repo holds all 20 skills; no public/private split — decided (Round 1 Q1: Tony answered "One public", overriding the split recommendation)
- The public repo carries the MIT license — decided (Round 1 Q2)
- The ~/Documents/skill-lab build docs move into the repo's docs/ as part of this migration — decided (Round 1 Q3)
- The 20 skills: arcade, blueprint, build, digest, fb, forge, handoff, huh, inspect, jpb, precon, print-tune, recheck, ship, shutdown, signoff, sunrise, sunset, vertical, wargame — decided (looked up in the 2026-08-31 inventory; cold read #1)
- One plugin per skill, keeping the existing sun bundle (sunrise + sunset in plugins/sun); every migrating skill gets its own entry in .claude-plugin/marketplace.json — assumed (follows the repo's existing convention; cold read #2, #3)
- Done means: transferred, scrubbed, migrated, installed and verified on both Macs, flipped public — the flip is the final step and still executes only on Tony's word — decided (composition of Tony's one-public and flip-gate rulings; cold read #5)
- Marketplace installs work while the repo is private through each Mac's authenticated GitHub access; /blueprint verifies this before any hand-copy removal — assumed (standard git/gh auth; cold read #6)
- Publishable means the public repo plus a README carrying the install line — assumed (no further obligation was ruled; cold read #7)
- The scrub is two passes: a report-only audit covering the working tree AND full git history, then remediation edits made only after Tony rules per finding (redact / parameterize / accept); any unresolved finding blocks the flip — decided (refines Tony's scrub acceptance; cold read #8, #9, #11, #12)
- Secret remediation may edit a skill to read from local config; "working identically" means no user-visible behavior change — decided (Tony's usability concern and its resolution, 2026-08-31; cold read #10)
- The Studio's live copies are the sync source; on each machine, hand copies are diffed against the installed version before removal, and any unexpected difference stops and reports — assumed (live copies verified newer on the Studio only; the diff-guard protects laptop-side edits; cold read #13)
- The laptop's install and verification run through the claude-relay hand-off, triggered by Tony — assumed (standing cross-machine protocol; cold read #14)
- Post-migration, skills are edited in the repo and ship via PR and merge; the marketplace delivers updates to both machines — decided (the git-gate cost Tony explicitly accepted in the marketplace discussion, 2026-08-31; cold read #15)
- The skill-lab docs move rather than copy, and loop-skill pointers referencing ~/Documents/skill-lab update in the same slice — decided (refines Round 1 Q3; cold read #17)
- ~/Developer/tony-skills is the repo tiny-tunnel-dot/tony-skills; the move is a true GitHub transfer (Tony admins both sides), with remote URLs updated on both Macs — decided (looked up 2026-08-31; cold read #22, #23)
- The architect skill will land as plugins/architect/ with its build plan in docs/; the migration needs no other accommodation for it — decided (Tony's architect ruling 2, 2026-08-30; cold read #21)
- The build docs in docs/ stay in the public repo, world-readable, covered by the scrub — decided (Round 2 Q1)
- The repo keeps the name tony-skills, confirmed for the public era — decided (Round 2 Q2; upgrades the earlier name assumption to a ruling)

Out of scope:
- Repo-per-skill layout — rejected (Tony weighed it against the single-marketplace pattern and took one repo, 2026-08-31)
- The architect skill amendment and build — deferred behind this migration (Tony's ordering call, 2026-08-31); its seven adjudicated rulings stand in this session's record and in ~/Documents/skill-lab/architect-skill-build-plan.md (which moves to docs/ with the rest)
- Migrating third-party plugins (vercel, shopify-ai-toolkit, frontend-design) — installed from other marketplaces; none of them live in this repo, so nothing to remove
- dig — Tony's own product, but it ships from its own repo and marketplace (line7works/dig); deliberately not one of the 20
- Parallel worktree execution alongside the architect build — rejected (both jobs write the same repo; Tony accepted sequencing, 2026-08-31)
- A separate private repo (tony-ops) for machine-wired skills — rejected (Round 1 Q1: Tony chose one public repo; the machine-wired 5 go public with everything else, subject to the scrub)

Research: cold read at ~/Documents/precon-cold-reads/skills-migration-cold-read-2026-08-31.md (26 findings: 22 absorbed, 2 surfaced as Round 2, 2 left downstream to /blueprint — internal path-reference updates and acceptance criteria/rollback).

Open: none.

Next: /blueprint when ready.

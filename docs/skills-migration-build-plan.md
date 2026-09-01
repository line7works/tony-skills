# Skills migration — build plan (2026-08-31)

Intent: Move all 20 of Tony's personal Claude Code skills into this repo as a plugin marketplace under the line7works GitHub org, installed on both Macs through the marketplace instead of hand-copied `~/.claude/skills` folders — killing mirror drift permanently — and make the repo public so others can install the skills. Scope record: `docs/skills-migration-scope.md` (all decisions cited below live there; "cold read #N" resolves through that doc's Research pointer).

Constraints:
- Repo: `~/Developer/tony-skills` = `tiny-tunnel-dot/tony-skills` on GitHub, transferring to `line7works`. Tony admins both sides (verified 2026-08-31).
- The 20 skills (scope roster): arcade, blueprint, build, digest, fb, forge, handoff, huh, inspect, jpb, precon, print-tune, recheck, ship, shutdown, signoff, sunrise, sunset, vertical, wargame. Live copies: `~/.claude/skills/<name>/` on the Mac Studio (the sync source) — EXCEPT print-tune, which is a symlink to `~/Developer/print-tune/skills/print-tune` (its own repo, `tiny-tunnel-dot/print-tune`, local main ahead of origin as of 2026-08-31): its true source is that directory, and any removal touches only the symlink itself (`rm` on the link path, no trailing slash, never `-r` through it).
- Plugin shape: `plugins/<name>/.claude-plugin/plugin.json` + `plugins/<name>/skills/<skill>/SKILL.md`. Asset layout ruling: NEW plugins nest assets at `plugins/<name>/skills/<skill>/assets/` (the inspect precedent, byte-comparable with live copies); arcade, forge, and sun keep their existing plugin-root `assets/` (their own docs reference `${CLAUDE_PLUGIN_ROOT}/assets`) — both layouts are sanctioned, per plugin, as listed here. One plugin per skill; the existing `plugins/sun` bundle keeps sunrise + sunset. Target: 19 marketplace entries covering 20 skills.
- Registry: `.claude-plugin/marketplace.json` at repo root, currently holding exactly 6 entries (verified 2026-08-31); every plugin gets an entry (name, source, description, tags matching the existing entries' shape). Each new entry's description is the skill's SKILL.md frontmatter `description` verbatim, optionally truncated at a sentence boundary — never rewritten.
- No test suite exists in this repo; every acceptance check is a shell-verifiable command (diff, grep, jq, git, claude CLI) or an explicitly marked manual step.
- Evidence home: slice verification outputs that must survive the session are written to `docs/evidence/skills-migration/<slice>-<name>.txt` and committed — except the scrub audit report, which maps sensitive locations and therefore lives OUTSIDE the repo at `~/Documents/tony-skills-scrub/scrub-audit-<date>.md` (dated the day the audit runs), never committed.
- Recording Tony's live words: each word that gates an outward action (the transfer, the public flip) and the laptop's completion confirmation are recorded when received as ISO-timestamped lines in `docs/evidence/skills-migration/authorizations.md` (committed): `<YYYY-MM-DDTHH:MM:SS> · AUTHORIZED <action> · (per user)` / `<YYYY-MM-DDTHH:MM:SS> · CONFIRMED laptop cutover · <one-line quote of the confirmation>`. Those lines are the grader's checkable, ordered record.
- Git gates: work lands as local commits; push/PR/merge only on Tony's word. Never push to main. Slices C and F consume GitHub state, so their `Depends on:` lines name the required merges explicitly.
- Outward actions inside slices — the GitHub transfer (Slice A) and the public flip (Slice F) — execute only on Tony's live word at that step, even though both are decided in scope, and each word is recorded per the convention above.
- Protected paths, never overwritten: `~/.claude/projects/*/memory/`, `*.jsonl` transcripts, `~/.claude/settings.json`.
- The untracked `tools/shopify-mcp/` directory is pre-existing, not this project's work: leave untouched.
- Hand copies in `~/.claude/skills` are removed only after the installed versions are verified working on that machine — the working check runs BEFORE removal (scope: verify-then-remove decision).
- Stop-and-report default: any state this plan's enumerations don't cover (an unenumerated file, an unexpected diff, a failed pre-check) stops the slice and reports; the builder never improvises a disposition.

Out of scope:
- Repo-per-skill layout — rejected in scope (Tony chose the single-marketplace pattern)
- A private companion repo for machine-wired skills — rejected (Tony ruled one public repo, Round 1 Q1)
- The architect skill amendment and build — deferred behind this migration (Tony's ordering call); it lands later as `plugins/architect/`
- Third-party plugins (vercel, shopify-ai-toolkit, frontend-design) — installed from other marketplaces; not in this repo
- dig — Tony's own product, ships from `line7works/dig`; deliberately not one of the 20
- Fixing laptop-side state directly — the laptop executes its own relay hand-off (scope: relay decision); Slice F carries the hand-off and waits on its confirmation
- Renaming the repo — Tony confirmed `tony-skills` for the public era (Round 2 Q2)
- Git history rewrite — NOT scope-sanctioned as a remediation mechanism; if a scrub ruling appears to require one, stop and put the mechanism itself to Tony as its own decision
- Retiring or archiving the `tiny-tunnel-dot/print-tune` repo after its skill migrates here — Tony's call later; this migration leaves that repo untouched

Plan: inspected 2026-08-31 by claude-fable-5 · 5 BLOCKER · 10 MAJOR · 10 MINOR
Plan: inspected 2026-08-31 by claude-fable-5 · 3 BLOCKER · 7 MAJOR · 16 MINOR

## Slice A — Transfer and reconcile
Goal: The repo lives under line7works and its existing 8 mirrored skills are content-identical to the Studio's live copies under each plugin's sanctioned layout.
Requirements:
- R1: Transfer `tiny-tunnel-dot/tony-skills` to the `line7works` org as a true GitHub transfer (scope: transfer decision). Executes only on Tony's live word at this step, recorded as a timestamped AUTHORIZED line in `docs/evidence/skills-migration/authorizations.md`.
- R2: Update the Studio clone's `origin` remote to the line7works URL (scope: remote-update decision).
- R3: Sync the 3 content-drifted mirrors repo-from-live — signoff, sunrise, sunset SKILL.md files (verified 2026-08-31: the only live-vs-repo content differences; arcade's, forge's, and sun's assets already exist at plugin root, byte-identical to live, and arcade/forge SKILL.md are byte-identical — no action for those).
- R4: Create `plugins/shutdown/.claude-plugin/plugin.json` matching the six existing plugins' manifest shape (the folder currently lacks one — verified 2026-08-31), then register shutdown in `.claude-plugin/marketplace.json` matching the existing entries' field shape (scope: registration decision).
- R5: Commit `docs/skills-migration-scope.md` and this build plan (both currently untracked) so the plan and its record ride in the repo.
Acceptance criteria:
- AC-A1: `gh repo view tiny-tunnel-dot/tony-skills --json nameWithOwner` returns `line7works/tony-skills` (the redirect proves the transfer) and `gh repo view line7works/tony-skills --json name` succeeds — verify: run both.
- AC-A2: `git remote get-url origin` in `~/Developer/tony-skills` contains `line7works/tony-skills` — verify: run it.
- AC-A3: For each of the 8 mirrored skills: `diff -q` of live SKILL.md vs repo SKILL.md is clean, and each live `assets/` dir diffs clean against its plugin's sanctioned assets location (plugin root for arcade/forge/sun, nested for inspect) — verify: run the diffs per the constraints' layout ruling.
- AC-A4: `jq '.plugins | length' .claude-plugin/marketplace.json` returns 7 (baseline 6 + shutdown), `jq -e '.plugins[] | select(.name=="shutdown")'` succeeds, and `jq -e '.name' plugins/shutdown/.claude-plugin/plugin.json` succeeds — verify: run all three.
- AC-A5: The timestamped AUTHORIZED line for the transfer exists in `docs/evidence/skills-migration/authorizations.md`, work is committed locally, and `git status -sb` is clean apart from pre-existing `tools/shopify-mcp/` — verify: read the line, run the command.
Footprint: GitHub repo settings (transfer); `.git/config` (remote); `plugins/{signoff,sun}/skills/**` (SKILL.md syncs); `plugins/shutdown/.claude-plugin/plugin.json` (new); `.claude-plugin/marketplace.json`; `docs/skills-migration-scope.md` + this doc (first commit); `docs/evidence/skills-migration/authorizations.md` (new); this doc's Slice A `Status:` line.
Not in this slice: the 12 new plugins, doc moves, installs, scrub, publishing.
Depends on: nothing
Status: signed off

## Slice B — Migrate the twelve and consolidate the docs
Goal: All 20 skills exist as registered plugins in the repo, every plugin-file reference resolves from an installed location, and the skill-lab paperwork lives in `docs/`.
Requirements:
- R1: Create plugins for the 12 repo-less skills — blueprint, build, digest, fb, handoff, huh, jpb, precon, print-tune, recheck, ship, vertical — each as `plugins/<name>/` in the nested-asset shape, contents copied from the Studio's live `~/.claude/skills/<name>/` including any `assets/` (scope: migrate-the-12 decision) — EXCEPT print-tune, copied from its true source `~/Developer/print-tune/skills/print-tune/` (the symlink target; local is newest — see constraints).
- R2: Register all 12 in `.claude-plugin/marketplace.json`, descriptions per the constraints' verbatim rule.
- R3: Move the `~/Documents/skill-lab/` files into `docs/` (scope: Round 1 Q3 + move-not-copy decision), with these exact dispositions: these 18 move under their own names — architect-skill-build-plan.md, blueprint-review-experiment-2026-08-21.md, blueprint-skill-design.md, build-skill-anthropic-alignment.md, build-skill-v1-initial.md, build-skill-v1-research-comparison.md, cx2-verdict-2.md, fb-skill-build-plan.md, precon-skill-build-plan.md, precon-smoke-review-2026-08-20.md, ship-skill-build-plan.md, ship-smoke-run-2026-08-20.md, shutdown-all-first-run-2026-08-11.md, shutdown-skill-build-plan.md, signoff-baseline-cx2.md, signoff-skill-review.md, signoff-skill-work-state.md, skill-loop-edits-build-plan.md; `skill-feedback.md` (the live /fb inbox) moves to `docs/feedback.md` (blueprint assumption, stated here: a plan-level call — the record ruled on build docs, not this inbox, so Slice D's audit MUST list `docs/feedback.md` as an exposure item for Tony's per-finding ruling before any flip); `inspect-skill-build-plan.md` is discarded — its `docs/` copy is byte-identical (verified 2026-08-31). Any file found in skill-lab outside this enumeration: stop and report.
- R4: Retire `~/Documents/skill-lab/`: after the moves it contains exactly one pointer file naming the new home (blueprint assumption, stated here: a pointer beats silent deletion for anything else that still looks there).
- R5: Update the skill-lab pointers in fb and digest: body lines referencing `~/Documents/skill-lab` point at the absolute path `~/Developer/tony-skills/docs/feedback.md` (repos live under `~/Developer` on both Macs, so the path resolves from any install location), and fb's frontmatter `description` phrase "the skill-lab feedback doc" is reworded to name that doc — a sanctioned edit whose new wording flows to fb's marketplace entry (scope: pointer-update decision; cold read #17).
- R6: Replace every `~/.claude/skills/...` cross-reference in plugin files with references that resolve when the skills run from marketplace installs and `~/.claude/skills` no longer exists; the builder chooses the replacement form (cold read #16 left the mechanism to this plan). Full inventory (verified 2026-08-31): the 10 SKILL.md files (arcade, fb, forge, inspect, jpb, precon, print-tune, sunrise, sunset, vertical) plus `plugins/arcade/assets/README.md`, `plugins/forge/IMPLEMENTATION.md`, and huh's `punch-list.md` (arriving via R1).
Acceptance criteria:
- AC-B1: Every one of the 20 roster skills has a `SKILL.md` under `plugins/*/skills/<skill>/` — verify: `for s in <roster>; do ls plugins/*/skills/$s/SKILL.md; done` finds all 20.
- AC-B2: `jq '.plugins | length' .claude-plugin/marketplace.json` returns 19 and the file parses — verify: run it.
- AC-B3: `grep -rn 'skill-lab' plugins/` returns zero hits, and fb's and digest's pointer lines carry the literal `~/Developer/tony-skills/docs/feedback.md` — verify: run the grep, grep the literal.
- AC-B4: `grep -rn '\.claude/skills' plugins/` returns zero hits; any deliberate exception requires a `## Deviations` entry naming it — verify: run the grep.
- AC-B5: `docs/evidence/skills-migration/slice-b-refs.txt` (committed) lists every replacement reference written under R5/R6 with, for each, the resolved target and an existence check result, all passing — verify: read it, spot-check two entries by running their checks.
- AC-B6: Each of the 18 enumerated files exists under `docs/` by name, `docs/feedback.md` exists, and `ls ~/Documents/skill-lab/ | wc -l` returns 1 — verify: run the checks against R3's list.
- AC-B7: Each of the 12 new marketplace descriptions is its SKILL.md frontmatter description verbatim or a sentence-boundary truncation of it (fb's per its R5 rewording) — verify: string-compare the 12 pairs.
- AC-B8: Work is committed locally; `git status -sb` clean apart from `tools/shopify-mcp/` — verify: run it.
Footprint: `plugins/<12 new>/**`; `.claude-plugin/marketplace.json`; `docs/` (19 files arriving); `~/Documents/skill-lab/` (emptied to a pointer); fb, digest, the 10 cross-reference SKILL.md files, `plugins/arcade/assets/README.md`, `plugins/forge/IMPLEMENTATION.md`, huh's `punch-list.md` (reference lines only); `docs/evidence/skills-migration/slice-b-refs.txt` (new); this doc's Slice B `Status:` line.
Not in this slice: installing anything, removing hand copies, scrub, publishing.
Depends on: Slice A
Status: signed off

## Slice C — Studio cutover to marketplace installs
Goal: The Studio runs all 20 skills from marketplace installs, verified working, and only then are the hand copies gone.
Requirements:
- R1: Pre-flight: confirm local main and `origin/main` are the same commit and the working tree is clean — the marketplace serves GitHub content, so A's and B's work must be merged (via Tony's PR/merge words) before anything installs.
- R2: Add the marketplace from `line7works/tony-skills` (private at this point — works over the Studio's authenticated GitHub access; scope: private-install assumption) and install all 19 plugins at user scope.
- R3: Install-guard: verify each installed plugin's content is identical to the repo at merged main (`diff -r` installed copy vs `plugins/<name>/`), and verify hand-copy differences are expected: diff each of the 20 hand copies (print-tune via its symlink target) against the repo, confirming differences are confined to the files Slice B's footprint names as edited; save both runs' full output to `docs/evidence/skills-migration/slice-c-diff-guard.txt` (committed). Any difference outside that expectation stops the slice; a difference Tony rules through is recorded in the evidence file as `resolved: <ruling> (per user)`.
- R4: Working check BEFORE removal: a fresh Claude Code session lists all 20 skills from the installed set and successfully invokes /huh (untouched by B), /fb (logging a test note that lands in `~/Developer/tony-skills/docs/feedback.md`, proving the new pointer), and one of the 10 cross-reference skills — manual, results noted in the evidence file.
- R5: Remove the 20 hand-copy entries from `~/.claude/skills` only after R2–R4 pass on this machine (scope: verify-then-remove decision): 19 directories deleted; print-tune removed as `rm ~/.claude/skills/print-tune` on the symlink itself — no trailing slash, no `-r` (see constraints). Touch nothing else in `~/.claude/`.
Acceptance criteria:
- AC-C1: `git fetch origin && git status -sb` shows local main in sync with `origin/main` (no ahead/behind), clean apart from `tools/shopify-mcp/`, before the marketplace add — verify: run it.
- AC-C2: The tony-skills marketplace and all 19 plugins appear in `~/.claude/plugins/installed_plugins.json` / the `claude plugin` listing — verify: read the registry.
- AC-C3: `docs/evidence/skills-migration/slice-c-diff-guard.txt` exists, covers installed-vs-repo for 19 plugins and hand-copy-vs-repo for 20 skills, and every non-clean line is either within Slice B's declared edits or carries a `resolved: … (per user)` line — verify: read it.
- AC-C4: The evidence file records the R4 working check — all 20 listed, the three named invocations passing — and its git log timestamp precedes the removal commit's — verify: read it, compare timestamps.
- AC-C5: `~/.claude/skills/` contains none of the 20 roster skills, and `~/Developer/print-tune/skills/print-tune/` still exists with a clean `git status` in that repo — verify: `ls ~/.claude/skills/`; `git -C ~/Developer/print-tune status -sb`.
Footprint: `~/.claude/plugins/**` (installs); `~/.claude/skills/` (19 directories + 1 symlink removed); `docs/evidence/skills-migration/slice-c-diff-guard.txt` (new, committed); this doc's Slice C `Status:` line.
Not in this slice: the laptop (Slice F), scrub, publishing.
Depends on: Slice B, and Slices A+B merged to origin main on Tony's PR/merge words
Status: signed off

## Slice D — Scrub audit
Goal: A complete report-only audit of the repo's working tree and full history sits in front of Tony for per-finding rulings; nothing is edited.
Requirements:
- R1: Audit the full working tree AND full git history (every commit) for secrets, API keys, tokens, email addresses, and personal-infrastructure exposure; one finding per line with path/commit; `docs/feedback.md` is always listed as an exposure item for ruling (Slice B R3's assumption routes here). Written to `~/Documents/tony-skills-scrub/scrub-audit-<date>.md`, dated the day the audit runs (outside the repo — the report maps sensitive locations).
- R2: Present the report for Tony's per-finding rulings (redact / parameterize / accept); record each ruling in the report file. The slice ends when every finding carries a ruling — remediation belongs to Slice E.
Acceptance criteria:
- AC-D1: The dated audit file exists in `~/Documents/tony-skills-scrub/`, states it covered working tree and full history, includes the `docs/feedback.md` exposure item, and every finding line carries a recorded ruling — verify: read it.
- AC-D2: No repo file changed in this slice: `git status -sb` matches its pre-slice state apart from this doc's Status line — verify: run it.
Footprint: `~/Documents/tony-skills-scrub/` (new, outside repo); this doc's Slice D `Status:` line.
Not in this slice: applying any ruling (Slice E), publishing, the laptop.
Depends on: Slice C
Status: not started

## Slice E — Remediate and prep the public face
Goal: Every scrub ruling is applied and verified, the public-era README and license exist, and it is all merged on GitHub.
Requirements:
- R1: Apply Tony's rulings from the Slice D report. A secret ruled out of the files moves to local config (env/keychain) and the skill is edited to read it from there; no user-visible behavior change (scope: remediation decision). For each redact/parameterize ruling, append to its finding line in the audit report: `applied: <commit hash> · re-check: <the finding's own detection re-run, showing zero hits>`. History rewrite is out of scope per the fence: if a ruling appears to need one, stop and report.
- R2: Rewrite the EXISTING `README.md` (15KB, private-era, opens "A private repo holding…" — verified 2026-08-31) for the public era: it must contain the literal lines `/plugin marketplace add line7works/tony-skills` and `/plugin install huh@tony-skills` (the install-form example), and the private-era opening must be gone. The old text stays reachable in git history. Add `LICENSE`: MIT, holder "Tony Coon" (the owner name already carried in `.claude-plugin/marketplace.json`).
- R3: Push and merge all migration work to origin main on Tony's PR/merge word — the flip's prerequisite, so the public artifact carries the scrubbed content.
Acceptance criteria:
- AC-E1: In the audit report, every redact/parameterize ruling carries an `applied:` line with commit hash and a zero-hit re-check; no ruled finding is unapplied — verify: read the report, spot-check two re-checks by running them.
- AC-E2: `LICENSE` exists (MIT, Tony Coon); `grep -F '/plugin marketplace add line7works/tony-skills' README.md` and `grep -F '/plugin install huh@tony-skills' README.md` both hit; `grep -F 'A private repo holding' README.md` returns nothing; manual: read the README opening and confirm it describes a public marketplace — verify: run the three greps + the read.
- AC-E3: `git fetch origin && git status -sb` shows local main in sync with `origin/main`, clean apart from `tools/shopify-mcp/` — the remediations, README, and LICENSE are on GitHub — verify: run it.
Footprint: `README.md` (rewritten); `LICENSE` (new); any files edited by scrub rulings; the audit report file (rulings/applied lines); this doc's Slice E `Status:` line.
Not in this slice: the flip (Slice F), the laptop.
Depends on: Slice D, with every audit finding carrying Tony's ruling
Status: not started

## Slice F — Laptop hand-off and the public flip
Goal: The laptop runs the skills from the marketplace, and only then does the repo go public — the scope's decided order.
Requirements:
- R1: Write the laptop hand-off per the claude-relay protocol into `~/Documents/claude-relay/to-laptop/` — full verbatim commands to: pre-check the laptop's authenticated GitHub access to line7works (`gh auth status` + `git ls-remote` on the private repo, stop-and-report on failure; scope: each-Mac private-install assumption); add the marketplace and install the 19 plugins; run Slice C's install-guard and working check against the laptop's own state; remove its `~/.claude/skills` hand copies only after verification (checking first whether any is a symlink, print-tune-style, and removing symlinks as links); check for a laptop clone of tony-skills and update its origin remote to the line7works URL if one exists, reporting either way (scope: remote-URLs-on-both-Macs decision); plus the protocol's requirements — machine and inverted assumptions stated up front, protected paths named, backup and expected counts before any overwrite, a negative test, stop-and-report throughout.
- R2: The laptop executes it (Tony triggers, per the relay protocol's no-polling rule) and its confirmation comes back; record a timestamped CONFIRMED line quoting it in `docs/evidence/skills-migration/authorizations.md`, and move the relay file to `archive/`.
- R3: Flip the repo public — only after R2's CONFIRMED line exists, only on Tony's explicit word, recorded as a timestamped AUTHORIZED line in the same file (scope: done-order decision — "installed and verified on both Macs … the flip is the final step").
- R4: Commit the closing records (authorizations lines, this doc's Status line) — the migration ends with a clean tree.
Acceptance criteria:
- AC-F1: The relay file exists (then, post-confirmation, in `archive/`) and satisfies the CLAUDE.md hand-off checklist including the auth pre-check and remote-update steps — verify: read it against the checklist.
- AC-F2: `docs/evidence/skills-migration/authorizations.md` carries the timestamped CONFIRMED laptop line, and the relay file is in `~/Documents/claude-relay/archive/` — verify: read the line, `ls` the archive.
- AC-F3: `gh repo view line7works/tony-skills --json visibility` returns PUBLIC, and the flip's timestamped AUTHORIZED line exists with a timestamp later than the CONFIRMED line's — verify: run the command, compare the two timestamps.
- AC-F4: Work is committed and `git status -sb` is clean apart from `tools/shopify-mcp/`, in sync with origin — verify: run it.
Footprint: `~/Documents/claude-relay/to-laptop/` then `archive/` (one file); GitHub repo visibility; `docs/evidence/skills-migration/authorizations.md`; this doc's Slice F `Status:` line.
Not in this slice: nothing follows — this closes the migration.
Depends on: Slice E, and Slice E's work merged to origin main (AC-E3)
Status: not started

## Build assumptions

### 2026-08-31 — build: Slice A
- shutdown plugin.json homepage/repository kept at the tiny-tunnel-dot URL matching all six sibling manifests (GitHub redirects post-transfer; updating sibling URLs is no slice's scope) · builder call
- shutdown marketplace tags chosen as ["session-lifecycle","handoff"] — the spec fixes field shape and description, not tag values · builder call
- shutdown descriptions (plugin.json and marketplace entry) are the SKILL.md frontmatter description truncated at the first sentence boundary, per the constraints' verbatim rule · builder call

### 2026-08-31 — build: Slice B
- New-plugin manifests carry tiny-tunnel-dot homepage/repository URLs matching all seven siblings (Slice A's recorded precedent; no slice owns updating them) · builder call
- Marketplace tags for the 12 new entries invented within the shape-only latitude, as Slice A did for shutdown · builder call
- plugin.json descriptions are each SKILL.md frontmatter description verbatim in full (the constraints' verbatim rule fixes marketplace entries; manifests follow it too) · builder call
- R6 replacement form (left to the builder by the spec): same-plugin file references become `${CLAUDE_PLUGIN_ROOT}/...`; cross-plugin references become absolute `~/Developer/tony-skills/plugins/...` paths (same resolves-on-both-Macs rationale the spec gives for R5); pure prose mentions of the old location reworded with no path · builder call
- sunrise's explanatory sentence describing the removed `:-$HOME/.claude/skills` fallback reworded to match the new form (the sentence documented the old idiom) · builder call
- The skill-lab pointer file is named `README-MOVED.md` · builder call
- Built on stacked branch `feat/slice-b-migrate-twelve` off the unmerged Slice A branch · builder call

### 2026-09-01 — build: Slice C
- Diff-guard Part 1 excludes the installer's `.in_use` marker file (present in all 19 installed copies, tooling metadata not repo content; a first unexcluded run showing it as the only difference is noted in the evidence file) · builder call
- R4 mechanism: the 20 hand-copy entries were moved reversibly to a session scratchpad backup before the fresh-session checks, so the checks could only resolve the installed set; R5's permanent deletion ran from that backup after the checks passed (print-tune's symlink moved and removed as a link throughout) · builder call
- /precon chosen as R4's cross-reference skill (loads its edited SKILL.md; safe to invoke headless with no side effects) · builder call
- R4's /fb test note remains committed in docs/feedback.md (the spec requires the note land there; removing it would falsify the check) · builder call

## Deviations

### 2026-08-31 — build: Slice A
- R5's commit was pre-satisfied by handoff checkpoint 92928d5 (scope doc + plan already tracked on main before this slice) · per user
- The transfer API call, the AUTHORIZED-line write, and the origin remote-set-url ran from Tony's own shell (the permission classifier denied the builder each one); commands were the builder's verbatim, execution and outputs are on this session's record · per user

## Discovered

### 2026-08-31 — build: Slice B (appended post-review)
- Open /fb breakage window: R3 moved the live loop-note inbox (~/Documents/skill-lab/skill-feedback.md → docs/feedback.md) while the live fb hand copy still routes to the old path until Slice C's cutover — a live /fb loop note in the window hits fb's own "stop and report, never recreate" rule and stalls; no capture is lost silently. Plan-inherent (R3 now, cutover later); recorded so the window is on the books.

## Handoffs

### 2026-08-31 — handoff
- Next: /ship A docs/skills-migration-build-plan.md · all six slices `not started` · Slice A first per Depends chain
- Repo: main · 1 ahead of origin/main (92928d5, handoff checkpoint committing this plan + the scope doc; Slice A R5's commit need is thereby pre-satisfied — note it as a Deviations line if graded) · clean apart from pre-existing untracked tools/shopify-mcp/
- Suite: none recorded — repo has no test suite; ACs are shell checks per Constraints
- Ledger state: two same-day inspect blocks (REJECTED 5·10·10, then REJECTED 3·7·16); all findings amended on Tony's "fix them all as recommended" + "fix, no third round"; two dated WAIVED lines stand — the bullets-vs-template edge, and the third /inspect round itself. The plan meets /build on Tony's word without an APPROVED stamp; the second stamp is the last inspection record.
- Pending Tony's word, in order: the transfer (Slice A R1, live word at execution) · PR/merge of A and B before Slice C · per-finding scrub rulings between D and E · PR/merge of E before F · laptop trigger, then the flip word (Slice F)
- Seam notes: print-tune is a SYMLINK into ~/Developer/print-tune (own repo, ahead 1 of its origin) — copy from the symlink target, remove only the link, never -r through it · asset-layout ruling in Constraints: new plugins nest assets, arcade/forge/sun keep plugin root · authorizations + laptop confirmation land as ISO-timestamped lines in docs/evidence/skills-migration/authorizations.md (never a punch-list AUTHORIZED line — the code book forbids it) · the scrub audit report lives OUTSIDE the repo (~/Documents/tony-skills-scrub/), never committed · docs/feedback.md is a mandatory exposure item in the Slice D audit


### 2026-08-31 — handoff (after Slice A)
- Next: /ship B docs/skills-migration-build-plan.md · run from ~/Developer/tony-skills · Slice A signed off, B next per Depends chain (/build B by hand is the alternative)
- Repo: feat/slice-a-transfer-reconcile · 4 ahead of local main (92928d5), 5 ahead of origin/main · clean apart from pre-existing untracked tools/shopify-mcp/ · nothing pushed
- Suite: none — repo has no test suite; ACs are shell checks (Slice A's all passed on independent re-runs, per the review/recheck blocks)
- Gate answers this session: transfer word "yes go" (recorded as the AUTHORIZED line in docs/evidence/skills-migration/authorizations.md) · PR #4 ruling "dead, delete it" (recorded in the recheck block — closed unmerged, branch deleted)
- Pending Tony's word: PR/merge of this branch (A's work; needed with B's before Slice C installs) · per-finding scrub rulings between D and E · PR/merge of E before F · laptop trigger, then the flip word (Slice F)
- Seam notes for B: repo now line7works/tony-skills, origin repointed, marketplace count 7 · classifier denials hit outward/gated commands this session (transfer API call, the AUTHORIZED-line write, git remote set-url) — Tony ran each via the ! prefix; expect the same for B's gated writes if any · print-tune copies from ~/Developer/print-tune/skills/print-tune (symlink target), never through the link
- Open MINORs worth B's attention: seven plugin manifests carry tiny-tunnel-dot URLs and no slice owns updating them before the public flip — worth Tony's word by Slice F; new-plugin manifests in B repeat the sibling-matching call unless ruled otherwise

### 2026-08-31 — handoff (after Slice B)
- Next: /ship C docs/skills-migration-build-plan.md · run from ~/Developer/tony-skills · A and B both signed off — but Slice C's Depends line requires A+B merged to origin main on Tony's PR/merge words FIRST; C's preflight will stop without it (/build C by hand is the alternative)
- Repo: feat/slice-b-migrate-twelve (stacked on feat/slice-a-transfer-reconcile) · 9 ahead of local main (92928d5) · 10 ahead of origin/main · clean apart from pre-existing untracked tools/shopify-mcp/ · nothing pushed
- Suite: none — repo has no test suite; ACs are shell checks (Slice B's all re-run and passed by independent reviewers, per the review/recheck blocks)
- Slice B arc this session: /ship B ran build → signoff REJECTED (1 BLOCKER: jpb asset root; 2 MAJOR: false evidence row, unrecorded /fb window) → fixed in 00bc0b0 → recheck ALL CLEAR (9b4ecb9) → card signed off · laps: 1
- Pending Tony's word, in order: PR/merge of A+B (this branch carries both; Slice C's prerequisite) · per-finding scrub rulings between D and E · PR/merge of E before F · laptop trigger, then the flip word (Slice F)
- Seam notes for C: the diff-guard MINOR — arcade/forge/sunset live hand copies carry assets/ INSIDE the skill dir while the repo keeps them at plugin root; Slice B's declared-edit set does not cover that layout difference, so expect the guard to surface it and route it to Tony as a resolved: ruling, it is sanctioned layout, not drift · live /fb loop-note capture stalls until C's cutover (recorded in ## Discovered) — a loop note before cutover hits fb's stop-and-report rule · marketplace.json now carries — escapes in the 7 pre-existing entries (cosmetic, recorded MINOR) · classifier denials expected on gated commands, Tony runs them via the ! prefix
- Open MINORs worth attention before E/F: cross-plugin absolute ~/Developer/tony-skills/... paths dangle for third-party installs post-public (Tony's eyes before the flip) · seven+twelve manifests carry tiny-tunnel-dot URLs · CLAUDE.md's Source-of-truth section describes the dead topology and no slice owns it

## Punch list

### 2026-08-31 — inspect: plan
- BLOCKER · docs/skills-migration-build-plan.md:67 · Slice C installs the marketplace from line7works/tony-skills on GitHub while Slices A and B land only as local commits, with no push/merge named as a prerequisite anywhere · the install pulls stale GitHub content missing the 12 new plugins and 5 synced mirrors; the diff-guard then compares against a wrong baseline and hand copies are deleted against it · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:86 · Slice D flips the repo public while scrub remediations exist only in local commits — no push/PR/merge step exists in the plan · the flip publishes exactly the content the scrub was meant to remove; the gate is satisfied locally but not on the artifact being made public · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:86 · the flip precedes the laptop's install and verification (excluded from every slice), contradicting the scope's done-definition "installed and verified on both Macs … the flip is the final step" · /build seeks the flip word after a Studio-only cutover, publishing out of the decided order · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:52 · Slice B R6 (review/update the ~/.claude/skills cross-references in 10 SKILL.md files) has no acceptance criterion checking it · R6 can be skipped or half-done and every Slice B AC still passes; Slice C then deletes the directories those references point at, breaking 10 installed skills undetected · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:32 · plugins/shutdown has no .claude-plugin/plugin.json (all 6 other plugins do), so Slice A R4's registration-only premise is wrong · AC-A3/A4 pass anyway and the malformed plugin ships forward; Slice C's install hits it two slices downstream of the defect · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:85 · Slice D R3 says "add a README.md" but a 15KB private-era README already exists at repo root ("A private repo holding…", stale counts) · /build clobbers it without a decision or leaves self-described-private copy on a public repo · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:34 · AC-A1's check `gh repo view tiny-tunnel-dot/tony-skills --json name` returns identical output before and after the transfer (gh follows the redirect) · a grader cannot distinguish pass from fail on the slice's central requirement · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:50 · R4 and R5 each cite "(assumption recorded below)" but ## Build assumptions is empty (correctly, per the never-pre-fill rule) — the citations dangle · a fresh builder follows the pointer, finds nothing, and invents or stalls · claude-fable-5 (converged: code book + traceability)
- MAJOR · docs/skills-migration-build-plan.md:72 · AC-C2 and AC-D1 key verification on "the slice's build notes", an artifact with no defined home, format, or filename · the evidence trail for the two most safety-critical checks (hand-copy deletion, going public) is unfindable by a fresh session · claude-fable-5 (converged)
- MAJOR · docs/skills-migration-build-plan.md:57 · AC-B4's "the 20 former skill-lab docs exist under docs/" never enumerates the files, one is renamed and one discarded as a duplicate, and the same slice destroys the comparison base · 18 moved and 2 lost passes any check a grader could run · claude-fable-5 (converged)
- MAJOR · docs/skills-migration-build-plan.md:90 · AC-D2 requires the README "contains the literal install line" but the literal line is stated nowhere in the doc · any command-shaped sentence passes · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:93 · AC-D5's pass condition is "per Tony's word at the time" — a pointer at a future conversation, not a measurable end state · a fresh grader cannot verify it · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:87 · R5's enumerated relay contents omit updating the laptop clone's origin remote, dropping the scope's decided "remote URLs updated on both Macs" · the laptop's clone stays pointed at the dead tiny-tunnel-dot URL with no slice covering it · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:52 · R6 cites "(scope: pointer-update decision)" but that decision covers only ~/Documents/skill-lab pointers; the ~/.claude/skills cross-reference half was left downstream by the scope, so the citation misattributes · a grader tracing R6 finds the named decision covers half the requirement · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:91 · AC-D3 requires the flip word "recorded in this doc's ledger" without naming which section receives it · the builder guesses a home and the grader can't say which line satisfies it · claude-fable-5 (converged)
- MINOR · docs/skills-migration-build-plan.md:38 · AC-A5 expects git status clean apart from tools/shopify-mcp/, but the scope doc and this plan are currently untracked and in no slice's footprint · Slice A's acceptance fails as literally written or files are committed out of footprint · claude-fable-5 (converged)
- MINOR · docs/skills-migration-build-plan.md:56 · AC-B3's grep mixes an expected-empty scope (plugins/) with an expected-hits scope (moved docs), and --include misbehaves with explicit file operands; asset files are missed · a stale path in an asset file passes the AC · claude-fable-5 (converged)
- MINOR · docs/skills-migration-build-plan.md:50 · R4 extends the scope's "build docs move" ruling to the live /fb inbox and invents the destination name docs/feedback.md · a live capture flow is repointed on a plan-level assumption, not a ruling · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:84 · R2 introduces git history rewrite as a remediation mechanism the scope's remediation ruling never contemplated · a history rewrite of the just-transferred repo is presented as scope-sanctioned when the record never weighed it · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:85 · R3 hardens "MIT" into "MIT, Tony Coon" (holder name never established) and adds a one-paragraph description beyond the scope's README ruling · unverified legal name and unruled copy in public files · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:80 · Slice D packs a mandatory mid-slice STOP, a possible history rewrite, license/README work, the gated flip, and the relay hand-off into one /build invocation · a scrub with many findings makes the slice uncompletable in a sitting, leaving Status: in limbo · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:48 · R2's "no invented copy" for 12 marketplace descriptions has no AC checking any description against its SKILL.md · a grader has no stated procedure to distinguish faithful from invented · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:37 · AC-A4's expected count of 7 presumes a current baseline of 6 the doc never states · if the baseline differs the AC misfires with no way to tell doc from repo error · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:75 · Slice C's footprint claims no repo file changes, but /build must set this doc's Status: line — an in-repo edit · a literal-minded builder defers the status edit to stay in footprint · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:5 · Constraints: and Out of scope: are multi-line bulleted blocks where the template shows single-line fields · a strict parser expecting the template's line shape could misread; labels themselves are kept · claude-fable-5

### 2026-08-31 — inspect: plan
- BLOCKER · docs/skills-migration-build-plan.md:67 · (Slice C installs from GitHub with no push/merge prerequisite) · fixed
- BLOCKER · docs/skills-migration-build-plan.md:86 · (public flip with scrub remediations only in local commits) · fixed
- BLOCKER · docs/skills-migration-build-plan.md:86 · (flip precedes the laptop's install/verify, against the scope's done-order) · fixed
- BLOCKER · docs/skills-migration-build-plan.md:52 · (R6 cross-reference updates had no checkable AC) · fixed
- BLOCKER · docs/skills-migration-build-plan.md:32 · (plugins/shutdown lacks plugin.json; registration-only premise wrong) · fixed
- MAJOR · docs/skills-migration-build-plan.md:85 · (R3 ignored the existing private-era README) · fixed
- MAJOR · docs/skills-migration-build-plan.md:34 · (AC-A1's gh check couldn't distinguish the transfer) · fixed
- MAJOR · docs/skills-migration-build-plan.md:50 · (dangling "(assumption recorded below)" citations) · fixed
- MAJOR · docs/skills-migration-build-plan.md:72 · ("build notes" evidence store undefined) · fixed
- MAJOR · docs/skills-migration-build-plan.md:57 · (AC-B4's 20-doc completeness uncheckable) · fixed
- MAJOR · docs/skills-migration-build-plan.md:90 · (literal install line never stated) · fixed
- MAJOR · docs/skills-migration-build-plan.md:93 · (AC-D5 keyed to "Tony's word at the time") · fixed
- MAJOR · docs/skills-migration-build-plan.md:87 · (relay omits laptop remote-URL update) · fixed
- MAJOR · docs/skills-migration-build-plan.md:52 · (R6's scope citation covered half the requirement) · fixed
- MAJOR · docs/skills-migration-build-plan.md:91 · (flip-word "ledger" home undefined) · fixed
- MINOR · docs/skills-migration-build-plan.md:38 · (untracked docs vs AC-A5) · fixed
- MINOR · docs/skills-migration-build-plan.md:56 · (AC-B3 grep inconsistent) · fixed
- MINOR · docs/skills-migration-build-plan.md:50 · (feedback.md destination unrecorded assumption) · fixed
- MINOR · docs/skills-migration-build-plan.md:84 · (history rewrite presented as scope-sanctioned) · fixed
- MINOR · docs/skills-migration-build-plan.md:85 · ("MIT, Tony Coon" and README copy unruled) · fixed
- MINOR · docs/skills-migration-build-plan.md:80 · (old Slice D packed five jobs into one invocation) · fixed
- MINOR · docs/skills-migration-build-plan.md:48 · (description quality had no AC) · fixed
- MINOR · docs/skills-migration-build-plan.md:37 · (AC-A4 baseline unstated) · fixed
- MINOR · docs/skills-migration-build-plan.md:75 · (Slice C footprint omitted its Status edit) · fixed
- MINOR · docs/skills-migration-build-plan.md:5 · (Constraints/Out of scope bullets vs template line fields) · not fixed — house convention deliberately kept at adjudication
- BLOCKER · docs/skills-migration-build-plan.md:94 · Slice D R2 (apply scrub rulings) has no AC verifying any remediation was applied — AC-D1 checks only that rulings are recorded · a zero-remediation scrub passes every Slice D AC and Slice E flips public with ruled-out secrets still in the files · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:53 · print-tune is not a repo-less hand copy — ~/.claude/skills/print-tune is a symlink into the tiny-tunnel-dot/print-tune repo (verified; its SKILL.md says so) · Slice B forks another repo's tracked content into plugins/, then Slice C's removal can delete that repo's files through the symlink and leaves two diverging sources of truth · claude-fable-5
- BLOCKER · docs/skills-migration-build-plan.md:36 · A R3's "assets/ directories the repo lacks" is false — arcade/forge/sun assets exist at plugin root, byte-identical to live, and arcade/forge SKILL.md are byte-identical (a location artifact, not content drift) · AC-A3's required-clean diff forces duplicating identical asset sets into a nested layout the plugin tooling never reads, diverging on the next sync · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:58 · R6's positive condition — replacements resolve from marketplace installs — has no AC; AC-B4 greps only for absence of the old path · dead replacement references ship in 10 skills, and AC-C5's /huh smoke test exercises none of them · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:77 · Slice C's diff-guard requires clean diffs while Slice B deliberately edits 12 of the 20 skills repo-side — those diffs are dirty by the plan's own design and the doc never declares them expected · the guard gating hand-copy deletion must be waved through, hollowing it out · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:57 · R5's new pointer (docs/feedback.md) has no requirement to resolve from the marketplace-install location — the same resolvability R6 imposes one line later · /fb breaks when run from an install; the live capture flow the plan says it protects · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:115 · AC-E3's "postdates AC-E2's confirmation" is ungradeable — AUTHORIZED lines carry date-only granularity and the laptop confirmation has no durable timestamp · a same-day flip cannot be shown ordered by any named record · claude-fable-5 (converged: code book + traceability)
- MAJOR · docs/skills-migration-build-plan.md:12 · the invented AUTHORIZED punch-list line type conflicts with the code book's enumerated punch-list sources (/build's own lines limited to WAIVED/REOPENED/REBUILT) · a /build honoring its contract refuses the line while AC-A5 and AC-E3 key pass/fail on it · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:78 · Slice C R4 gates hand-copy removal on registry + diff only; the working-verification (AC-C5) sits after removal, inverting the scope's verify-then-remove gate · all 20 hand copies deleted before anything proves the installs load · claude-fable-5
- MAJOR · docs/skills-migration-build-plan.md:58 · R6's 10-file inventory is incomplete for AC-B4's zero-hit grep — plugins/arcade/assets/README.md, plugins/forge/IMPLEMENTATION.md, and huh's punch-list.md (copied in by B R1) also carry the reference (verified) · the builder edits 10 named files and the AC fails on three files no requirement names · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:114 · AC-E2's laptop confirmation names no durable record — a chat message plus an undated file move · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:65 · AC-B6's "matches in substance" is graded by feel; not reproducible across graders · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:93 · Slice D's mandatory mid-slice STOP still breaks one-sitting completion unless Tony is live · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:99 · AC-D2 greps only one of R3's two required literals — the /plugin install form is never checked · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:109 · the laptop-side private-install auth assumption is unstated in Slice E; the doc's version cites the Studio only while the scope covers each Mac · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:55 · R3's dispositions have no rule for an unenumerated file appearing in skill-lab; AC-B5's count check then fails without guidance · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:82 · AC-C3's "resolved with Tony" escape hatch defines no recorded form in the evidence file · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:84 · AC-C5 smoke-tests one skill of 20, and none of the 12 path-edited ones · claude-fable-5 (converged)
- MINOR · docs/skills-migration-build-plan.md:112 · Slice E alone carries no committed/clean AC though its footprint edits this doc · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:5 · Constraints/Out of scope bullets vs template line fields — the standing rough edge, resurfaced · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:55 · the feedback-inbox assumption cites the Round 2 docs-public ruling, which ruled on build docs, not a live inbox of raw notes · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:93 · the audit filename hardcodes 2026-08-31 while the constraints define scrub-audit-<date>.md and Slice D will run later · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:99 · grep -i 'private repo' both over- and under-matches "no longer describes the repo as private" · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:118 · Slice E's Depends line names no merge though the constraints promise GitHub-consumer slices name theirs explicitly · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:8 · two contradictory asset-layout precedents exist (inspect nests; arcade/forge/sun use plugin root) with no ruling for placing jpb's and vertical's assets · claude-fable-5
- MINOR · docs/skills-migration-build-plan.md:57 · fb's frontmatter description says "the skill-lab feedback doc" with no path; AC-B3's zero-hit grep catches it but R5 never authorizes frontmatter edits · claude-fable-5

2026-08-31 · WAIVED (per user) · docs/skills-migration-build-plan.md:5 bullets-vs-template-line-fields — house convention kept across two adjudications ("fix them all as recommended" with keep recommended, then "fix, no third round")
2026-08-31 · WAIVED (per user) · re-inspection after this amendment — Tony's "fix, no third round" collapses the fresh-/inspect gate; the plan proceeds to /build on his word with the second stamp standing as the last inspection record

### 2026-08-31 — review: Slice A
- MAJOR · GitHub line7works/tony-skills PR #4 (add-det-audit-plugin) · the transfer carried an open PR adding an 8th, off-roster det-audit plugin — unenumerated state · if merged it breaks AC-B2's count of 19 and ships an unplanned plugin at the public flip; needs disposition (close or park) before Slice C consumes GitHub state · Slice A review
- MINOR · plugins/shutdown/.claude-plugin/plugin.json:8-9 · new manifest bakes in tiny-tunnel-dot homepage/repository URLs (matches 6 siblings; recorded builder call) · no downstream slice owns updating the seven manifests before the public flip; handle reuse would dangle every link · Slice A review
- MINOR · docs/evidence/skills-migration/authorizations.md:1 · AUTHORIZED line is self-attested, written ~11 min after the word · record is checkable for existence/format, not truth · Slice A review
- MINOR · docs/evidence/skills-migration/authorizations.md:1 · timestamp convention carries no timezone · Slice F AC-F3's same-day cross-machine ordering may be unprovable · Slice A review
- MINOR · .claude-plugin/marketplace.json (shutdown entry) · tag values invented within granted latitude · none concrete; ratify or adjust at leisure · Slice A review

### 2026-08-31 — recheck: Slice A
- MAJOR · GitHub line7works/tony-skills PR #4 (add-det-audit-plugin) · (transfer carried an open PR adding an 8th, off-roster det-audit plugin — unenumerated state) · fixed — PR CLOSED not merged per Tony's "dead, delete it" word, branch deleted (404), no open PRs remain, main holds 7 plugins with no det-audit

### 2026-08-31 — review: Slice B
- BLOCKER · plugins/jpb/skills/jpb/SKILL.md:31 · definitional asset root `${CLAUDE_PLUGIN_ROOT}/assets/` doesn't resolve from a marketplace install (assets nested at skills/jpb/assets/; plugins/jpb/assets/ doesn't exist — R6 unmet) · installed /jpb dereferences a missing directory for every asset after Slice C removes the hand copy · Slice B review
- MAJOR · docs/evidence/skills-migration/slice-b-refs.txt:15 · the jpb line records the nested dir as the reference's resolution, contradicting the file's own header semantics — "All checks passing: YES" false for this row · AC-B5 passed on false evidence · Slice B review
- MAJOR · docs/skills-migration-build-plan.md (Slice B ledger) · the live /fb loop-note inbox moved away while the live fb hand copy still routes to it, and no ledger line records the open breakage window · live /fb loop captures stall ("stop and report") from this commit until Slice C's cutover · Slice B review
- MINOR · plugins/jpb/skills/jpb/SKILL.md:28 + plugins/forge/skills/forge/SKILL.md:29 + plugins/forge/IMPLEMENTATION.md:444 · "resolves both ways" prose survived the fallback removal — now false · a reader restores the fallback or trusts a dead property · Slice B review
- MINOR · .claude-plugin/marketplace.json · re-serialization escaped em dashes to — in the 7 pre-existing entries · cosmetic diff noise in future reviews · Slice B review
- MINOR · plugins/inspect/skills/inspect/SKILL.md:47 (+vertical:53, precon:57/80, fb, digest) · cross-plugin absolute ~/Developer/tony-skills/... paths assume a clone on every install machine; dangle for third parties post-public · laptop unverified until F; public installs hit dead paths · Slice B review
- MINOR · docs/skills-migration-build-plan.md:81 · Slice C's diff-guard declaration doesn't cover the arcade/forge/sunset asset-layout difference (live nested vs repo plugin-root) · guard demands a mid-C ruling on sanctioned layout, not drift · Slice B review
- MINOR · CLAUDE.md (Source of truth section) · describes the dead topology (live copies in ~/.claude/skills, five catalogued plugins); no slice owns updating it · a future session reasons from dead topology · Slice B review
- MINOR · docs/evidence/skills-migration/slice-b-refs.txt · omits fb's derived plugin.json/marketplace description references · greppable occurrences outnumber listed ones · Slice B review
- MINOR · plugins/inspect/skills/inspect/SKILL.md:47 · "live SKILL.md" now names the repo working-tree copy, not the running install · /inspect can grade against an unshipped draft code book · Slice B review

### 2026-08-31 — recheck: Slice B
- BLOCKER · plugins/jpb/skills/jpb/SKILL.md:31 · (definitional asset root doesn't resolve from a marketplace install) · fixed — line now names ${CLAUDE_PLUGIN_ROOT}/skills/jpb/assets/, which expands to the existing nested dir; false "resolves both ways" prose gone
- MAJOR · docs/evidence/skills-migration/slice-b-refs.txt:15 · (evidence line recorded a false resolution; "All checks passing: YES" untrue for the row) · fixed — line now records the corrected reference whose expansion equals the checked target, with a dated correction note, not a silent rewrite
- MAJOR · docs/skills-migration-build-plan.md (Slice B ledger) · (open /fb breakage window unrecorded) · fixed — dated Discovered entry names the window and its stall-not-loss failure mode; factual claims verified against the live fb SKILL.md and skill-lab contents

### 2026-09-01 — review: Slice C
- MAJOR · docs/evidence/skills-migration/slice-c-diff-guard.txt:151 · arcade ruling asserts repo plugin-root assets "byte-identical to live" — false at guard time (Slice B edited plugins/arcade/assets/README.md) and the three "Only in hand copy: assets" trees (arcade/forge/sunset) were masked from diff -r, never content-compared before deletion · unrecorded drift inside those trees would have been deleted unexamined under a "not drift (per user)" ruling; hand copies now gone, unrecheckable — evidence wording must be corrected on the record · Slice C review
- MINOR · ~/.claude/settings.json · plugin CLI wrote enabledPlugins/extraKnownMarketplaces entries at install, vs the constraints' "never overwritten" protected-path line — spec self-contradiction with R2's user-scope install, unrecorded · Slice C review
- MINOR · docs/skills-migration-build-plan.md:90 · docs/feedback.md changed (R4's required test note) but Slice C's Footprint never names it · Slice C review
- MINOR · docs/evidence/skills-migration/slice-c-diff-guard.txt (R4 section) · verify-then-remove ordering provable only at commit granularity; R4 lines carry a date, no times · Slice C review
- MINOR · docs/evidence/skills-migration/slice-c-diff-guard.txt (Part 2) · hand-copy side unverifiable forever for the 12 new plugins (no pre-edit blobs exist) — inherent to the design, on the record · Slice C review
- MINOR · docs/evidence/skills-migration/slice-c-diff-guard.txt:4 · .in_use described as a "marker file"; it is a directory (lock/pid entries); --exclude behavior identical · Slice C review

### 2026-09-01 — recheck: Slice C
- MAJOR · docs/evidence/skills-migration/slice-c-diff-guard.txt:151 · (arcade ruling asserted "byte-identical to live" falsely; masked asset trees never content-compared) · fixed — dated on-the-record Correction section appended (commit 32b6d94): original text preserved, false justification explicitly retracted, and the conclusion re-grounded on independently verified facts (the one in-tree difference is B's declared README edit; forge/sun assets untouched by B and Slice A-verified; installed plugin-root assets diff clean against merged main). No fix-introduced defects.

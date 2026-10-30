# Sign-off: docs/plans/2026-10-28-e18-live-run-2.md, slice A

Verdict docs are records of this station's inspections of one slice. Each run
appends; nothing here is ever rewritten. The build doc holds the working state.

## 2026-10-29 — sign-off: A

Verdict: signed off

Reviewed by: claude-subagent:ship-a-20261029-99e1-2-signoff-v2-review-spec · route: readers:claude-session · model observed: claude-opus-5-5 · independent: yes
Run: ship-a-20261029-99e1-2-signoff-v2 · source: dd4af2b74cf6543368ad3e5893202cae43325dd0

Checks the reviewer executed:
- spec: named check (`/usr/bin/python3 -m unittest discover -s tools/tests -t tools/tests -p test_guide_findings.py`, exit 0) → Ran 4 tests in 0.328s / OK
- spec: base-tool red probe (`git show ecf325d:tools/guide-findings.py into mktemp scratch, test copied with TOOL repointed, /usr/bin/python3 -m unittest discover -s <scratch>/t -t <scratch>/t -p test_base.py`, no exit code) → FAILED (failures=2), including test_same_line_in_two_checkouts_counts_once ... AssertionError: 2 != 1 (exit code not captured)
- spec: R3 and whitespace probe (`HOME=<scratch> /usr/bin/python3 tools/guide-findings.py --json; then --check`, exit 0) → one fb finding, note 'adds E16 note', cited .../Developer/a/docs/feedback.md:1; --check: 1 findings parsed, 0 malformed
- spec: git history and diff (`git log --oneline ecf325d..HEAD; git diff ecf325d HEAD --stat -- tools/; git status --short; git diff -- docs/plans/2026-10-28-e18-live-run-2.md`, exit 0) → 24 commits, PR #122 merge on top; tools/ 2 files changed, 94 insertions; working tree only the plan doc modified
- spec: versions and ancestry (`grep -n '"version"' on both plugin.json files; git merge-base --is-ancestor 1338327 origin/main`, exit 0) → both versions 0.1.3 on line 10; ancestor check returned 0
- correctness: named check (`/usr/bin/python3 -m unittest discover -s tools/tests -t tools/tests -p test_guide_findings.py`, exit 0) → Ran 4 tests in 0.329s OK
- correctness: diff since base (`git diff --stat ecf325d... -- tools; git status --short; git diff ecf325d... -- tools/guide-findings.py`, exit 0) → guide-findings.py +7, test_guide_findings.py +87; working tree only the plan doc; change is seen_lines plus a raw.strip() check before parse_fb_line
- correctness: edge-case probe (`/usr/bin/python3 -I <scratch>/gfprobe/probe.py tools/guide-findings.py`, exit 0) → same line twice in one file: 1; trailing spaces: 1; CRLF vs LF: 1; no final newline: 1; GUIDE vs guide: 2; a-wt beside tony-skills: 1, cited a-wt/docs/feedback.md:1
- correctness: personal-path grep (`git diff ecf325d... -- docs tools | grep -nE '^\+.*(/Users/|/private/tmp|/var/folders)'`, exit 0) → only two prose lines naming the patterns themselves; no real personal path added
- seams: named check (`/usr/bin/python3 -m unittest discover -s tools/tests -t tools/tests -p test_guide_findings.py`, exit 0) → Ran 4 tests in 0.329s OK
- seams: history and status (`git log --oneline ecf325d..HEAD; git log --oneline -- tools/guide-findings.py tools/tests/test_guide_findings.py; git status --short; git diff --stat`, exit 0) → slice commits 1dc04ca, d509b5f, 1338327 then PR #122's 21 commits; working tree only the plan doc (+13)
- seams: plan doc diff (`git diff docs/plans/2026-10-28-e18-live-run-2.md`, exit 0) → adds only builder-section entries for run 99e1
- seams: consumer search (`grep -rn guide-findings over md/py/json/sh/yml; git show a4eab48 --stat; git diff ecf325d HEAD -- tools/guide-findings.py`, exit 0) → no in-repo code consumer; the diff is the 7-line seen_lines block
- seams: scratch probe (`/usr/bin/python3 -I <scratch>/probe/p.py tools/guide-findings.py`, exit 0) → within-file 1; cited tony-skills-e18 copy; crlf 1; trailing space 1; case 2; inner whitespace 2; since 1; no log: exit 1, 1 findings parsed, 1 malformed
- seams: red-first on base tool (`git show ecf325d:tools/guide-findings.py into scratch, new test beside it, same discover command`, exit 1) → Ran 4 tests, FAILED (failures=2): test_same_line_in_two_checkouts_counts_once, test_malformed_line_repeated_is_reported_once

Checks the reviewing session executed:
- tools test suite (full) (`/usr/bin/python3 -B -m unittest discover -s tools/tests -t tools/tests`, exit 0) → ....
- end-to-end probe against the acceptance criteria (`HOME=<mktemp scratch> /usr/bin/python3 -B tools/guide-findings.py --json (same line in tony-skills and twice in tony-skills-wt, two different lines in other, one log finding)`, exit 0) → 4 findings: log 'a log finding'; fb 'E5 held different note' other:1; fb 'E5 held another note' other:2; fb 'E5 adds same note text' tony-skills-wt:1
- end-to-end --check (`HOME=<mktemp scratch> /usr/bin/python3 -B tools/guide-findings.py --check`, exit 0) → 4 findings parsed, 0 malformed

### 2026-10-29 — review: Slice A
- MINOR · tools/tests/test_guide_findings.py:46 · (Requirement 3 (a GUIDE line repeated inside one file counts once) has no test; every repeat fixture puts the line in two different checkouts (raised by spec, correctness and seams)) · A later edit resets seen_lines inside the per-path loop or keys it on (path, text); a feedback.md holding the same GUIDE line twice then reports two findings while all four tests and the named check stay green · A
- MINOR · tools/guide-findings.py:91 · (The kept citation for a duplicated line is the first file in sorted glob order, which puts a worktree such as tony-skills-e18/ ahead of tony-skills/ ('-' sorts before '/'), so the cited source can be a transient worktree path (raised by seams and correctness, low confidence; the spec allows 'one of the files')) · The same GUIDE line sits in ~/Developer/tony-skills/docs/feedback.md and ~/Developer/tony-skills-e18/docs/feedback.md; --json cites tony-skills-e18/docs/feedback.md:1, and once that worktree is removed the finding's source names a file that no longer exists · A
- MINOR · tools/guide-findings.py:98 · (The dedup key is raw.strip(), so lines differing only in trailing whitespace or line ending fold into one finding, while the spec says the same text means the whole line (low confidence)) · A GUIDE line with two trailing spaces in one checkout and the same line without them in another gives 1 finding · A
- MINOR · tools/guide-findings.py:85 · (The tool's output feeds the Spine board findings block outside this repo (commit a4eab48, spine-board BF-28); its counts now drop for every duplicated line and a duplicate's cited source can change between runs (low confidence, consumer not readable)) · The Spine board compares counts or keys by source; after this change its numbers fall and a finding's key flips when a worktree appears or is deleted, so the board shows a finding as new or removed when it is not · A
- MINOR · plugins/signoff-v2/.claude-plugin/plugin.json:10 · (Measured against base ecf325d the source set shows plugins/ changed and signoff-v2 and ship-v2 bumped 0.1.2 to 0.1.3, which reads as breaking the plan's constraint 'No version bump: nothing under plugins/ changes'; all of it arrived through merge dd4af2b (PR #122), none is this slice's work (low confidence, a base-selection artefact)) · A reviewer or gate that checks the constraint literally against the slice's base finds plugins/ changed and versions bumped and rejects the slice for a constraint it never broke · A
- MINOR · docs/plans/2026-10-28-e18-live-run-2.md:1 · (The rerun's base ecf325d predates merged PR #122, so the source set under review carries 72 plugins/ files from fix round 2 for a 2-file slice, and the plan does not say which installed version the rerun was meant to prove) · Any 'plugins/ untouched since base' check diffs ecf325d..HEAD, sees plugin.json versions bumped and signoff.py changed, and either rejects the slice or spends its review on already-signed-off fix-round code (74 files in this packet) · A
- MINOR · docs/plans/2026-10-28-e18-live-run-2.md:3 · (The Intent still says the run happens 'with signoff-v2 and ship-v2 0.1.2 installed', while fix round 2 bumped both to 0.1.3 and says to rerun this plan at 0.1.3 (raised by spec and seams)) · Someone auditing the rerun against the plan's stated preconditions sees a version mismatch · A

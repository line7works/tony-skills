# Sign-off — readers-followups Slice A (the contract tells the truth about the Claude lane)

Run `signoff-a-20260908-6b0d` · run dir `<scratch>/signoff-a.iU2lUW/readers` (kept for this session) · Scope: branch `feat/readers-followups-a` at `a8af59c`, base `main` at `946b48a`, union `git diff main` = the four Footprint files (contract.md, readers.py, roster.json, SKILL.md), the evidence file `docs/evidence/readers/followups-a-fresh-read.md`, and the build doc's ledger writes and card (the loop's record, scoped as in every prior readers verdict); working tree clean · Spec: `docs/plans/2026-09-08-readers-followups.md`, Slice A · Depth: LEAN + `security` (REVIEW.md pass on): four `/readers` calls on `claude-session`, `repo-with-tools`, `floor: opus`, `session_model: claude-fable-5-1`, `documents` [REVIEW.md], mandates `<run dir>/../<lens>.md` · REVIEW.md: read — `accessibility` and `data-safety` skipped as marked off (no UI; no hosted database); fifteen repo-specific checks tried by every lens.

## 2026-09-08 — review: slice A

Verdict: SIGNED OFF WITH CONDITIONS · Method: the session re-ran every AC verify line at a8af59c (`<scratch>/signoff-a.iU2lUW/execute.log`: AC1 0/1/2/2; AC2 2/2; AC3 one label, verbatim twice in the contract, old label 0; AC4 2 footer lines with capture; AC5 4→4 lines with "nothing else", 63→63 lines, both edited lines carry harness; AC6 nine examples valid, six files in the diff, 0 absolute paths in the evidence file; py_compile ok); the four reviewers each re-ran the same lines and composed the AC2 requests under scratch clones (all reproduced; the fresh `claude -p` read is the builder's record, not re-run by any reviewer); nothing dispatched to an outside service; no worktree; no "verification blocked" · Refuted: 2.

READERS lines (sidecars under the run dir; `raw.md` is each reviewer's report verbatim):
- READERS: claude-session · ok · claude-fable-5-1 · none · <run dir>/signoff-a-20260908-6b0d-spec/sidecar.json
- READERS: claude-session · ok · claude-fable-5-1 · none · <run dir>/signoff-a-20260908-6b0d-correctness/sidecar.json
- READERS: claude-session · ok · claude-fable-5-1 · none · <run dir>/signoff-a-20260908-6b0d-seams/sidecar.json
- READERS: claude-session · ok · claude-fable-5-1 · none · <run dir>/signoff-a-20260908-6b0d-security/sidecar.json

raw hashes:
- spec a1252a57955ed36adb0d2de06c3637bb4452f888384cde771579acf7564931ae
- correctness 1d25df14b11ac7ac198fc418f3c30d11350bf78d442ceaad2faa864469c2c8f9
- seams a47da5ff22b2314081aebc715238486fe4ab3ad59e126b5710826ce03aa4839e
- security ae9a21b38c26c66bec61d7e35bf8616d5e60beb1e2384a7e542545b5f4c2cfec

Every reviewer's sidecar: `profile: repo-with-tools`, `workdir_instruction_files: ["AGENTS.md", "CLAUDE.md"]`, `isolation: unmeasured`, `parity: web tools forbidden by instruction`, route agent. Working tree and `plugins/readers/last-picks.json` unchanged after the run; no `.readers/` in the checkout.

### MAJOR

- MAJOR · `docs/plans/2026-09-08-readers-followups.md:83` · builder-call assumption over an acceptance criterion: AC5's "each such line also contains the word `harness`" is read as the two lines R5 names (SKILL.md:12, :51); SKILL.md:35 and :53 still match `nothing else` without `harness` · scenario: AC5 run as written fails (4 matching lines, 2 with harness) while R5 is met in substance; the rule-4 cap applies until Tony waives the reading or amends AC5 · CONFIRMED (three lenses; the session re-ran it)

### MINOR

- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` · "on the Agent route … three of them" undercounts: three reviewers on the Agent route in this run each report their own context carried the harness's git-status block (branch, recent commit subjects, git user handle) and a `userEmail` block naming the user's address, plus the MCP server instructions and the agent and skills rosters, on top of the three channels named · scenario: a Method line reasons "Agent route, so no git-status leak", or a reviewer quotes the email into `raw_text` and a public verdict doc · REVIEW.md bar: not a regression, not a CI-catchable check → MINOR; the correction changes what R1 lists, so it is Tony's word (Questions) · CONFIRMED (direct observation by three lenses; the session's own context carries the same two blocks)
- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` · the Workflow-route account names the git-status block only, where the readers build's `## Discovered` (2026-09-06, slice C, plan:519) already records the instruction files and the memory index reaching the Workflow reader · scenario: a caller judging a `starved` read reports one channel where the record names three · CONFIRMED (record)
- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` and `:130` · "reaches the reader even under `starved` and `packet-only` (measured twice, proofs (b) and (e))" — both proofs ran `starved` (closeout sidecars); `packet-only` was never measured · scenario: a later reader skips the `packet-only` probe on the contract's word · wording dictated by R1 · CONFIRMED
- MINOR · `plugins/readers/skills/readers/assets/guides/gemini.md:19-22` and `:35` · the guide's verbatim prefix quote lacks the new line and `:35` says the prefix "carries only" report-everything, no-web, and the profile line · scenario: a lane debugger diffs `prompt.md` against the guide and sees a line the guide denies · outside the Footprint ("Not in this slice: the guides"); Slice B touches item 6 only · CONFIRMED
- MINOR · `plugins/readers/skills/readers/SKILL.md:37` · the body says "verbatim … change nothing" and never points at the contract's footer rule; `record` trims nothing (the seams lens recorded a capture ending in an agent-id/usage block and got `ok` with those lines in `raw_text`) · scenario: a session pastes the Agent tool result whole and `raw_hash` covers non-reviewer text · Footprint pinned SKILL.md to two lines; Slice C's Footprint (SKILL.md Step 3) is where it can close · CONFIRMED
- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` · "the sidecar's `workdir_instruction_files` names the workspace half only" overstates: `instruction_files()` (readers.py:681) lists root `AGENTS.md`/`CLAUDE.md` present, never imports or nested files, keyed on the request's `workspace` while the harness loads from the session's cwd · scenario: cwd tony-skills, workspace a scratch repo → the sidecar names the scratch repo's files, the reader received tony-skills' · R1's phrase · CONFIRMED
- MINOR · `docs/plans/2026-09-08-readers-followups.md:34` · AC3's third verify line is vacuous: `grep -c "'harness-enforced (toolCalls: 0)'"` (single quotes inside JSON) prints 0 on `main` too; the evidence file used the double-quoted form (6 → 0) without saying the spec's command was replaced · scenario: the AC passes with no edit made · CONFIRMED
- MINOR · `docs/plans/2026-09-08-readers-followups.md:57` · Slice B's Depends-on line says A "touches contract.md paragraphs Slice A does not"; A rewrote the Gemini-lane line (:80) that B's R2 edits · scenario: B's builder skips the rebase on that premise and conflicts on :80 · CONFIRMED (diff hunks :72, :76, :80, :130)
- MINOR · `docs/plans/2026-09-08-readers-followups.md:3` · the Intent says "every reader on every lane is told not to reach other models or outbound tools"; R2 covers the two host prefixes and the portable lanes carry no fixed instruction by design (guides/gpt.md:8) · spec-internal inconsistency, no build defect · CONFIRMED
- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` · "on the Agent route (`repo` and `repo-with-tools`)" equates route with profile; the routes sentence says a `repo` call with a pinned effort goes through the Workflow route · PLAUSIBLE (imprecision; no runner acts on it)
- MINOR · `plugins/readers/skills/readers/assets/contract.md:102` · the Evidence section still calls `capture.md` "the body's verbatim copy of the reply" without the footer qualification :72 and :76 now carry · PLAUSIBLE (low)
- MINOR · `plugins/readers/skills/readers/assets/contract.md:76` · the contract does not say the harness's instruction-file channel arrives before the fixed prefix carrying "OVERRIDE any default behavior" language, nor which wins when it conflicts with the prefix's no-MCP and read-only rules · PLAUSIBLE (security lens; blocking the injection is Out of scope, stating the precedence is not)
- MINOR · `plugins/readers/skills/readers/assets/readers.py:43` · `ADAPTER_VERSION` unchanged while the composed fixed text changed; a pre-slice `compose` recorded by a post-slice runner is a prompt-hash usage slip mid plugin-update · PLAUSIBLE (low; no contract rule ties the version to prefix text)
- MINOR · `plugins/readers/skills/readers/assets/readers.py:576` · the prefix's authority over the mandate is by order and wording only; a mandate reading "ignore the READER INSTRUCTIONS above" composes with no refusal · PLAUSIBLE (low; inherent to prompt design, not new here)

### Deferred

- The callers' texts (signoff/recheck/wargame say "three channels"; architect:125 "Every reviewer gets the scope doc only"; inspect:44/:90 exclusivity lists) now under-report the same channels · the doc's Constraints: "Callers are not edited here" · out of this slice on the spec's word.
- The build doc in `git diff main --stat` (AC6's "only the Footprint files"): the ledger writes and the card are the loop's record, scoped inside the union by every prior readers verdict · refuted as a finding, recorded here so the AC's letter is not re-raised.

### Tried and failed to break

- Every AC verify line, by the session and by each of four lenses (counts above), including the before-counts on `main` (1 old sentence, 6 old labels, 4 "nothing else" lines, 63 lines).
- Prompt order: the correctness lens composed both AC2 requests with `main`'s runner and this branch's from two scratch clones; `diff` of the two `prompt.md` files is exactly one added line at position 4 on both rows; fixed instruction, profile line, mandate, documents in the same order.
- The label through the pipeline (seams): a `starved` Workflow-route `record --tool-calls 0` wrote the new long label into `isolation` with `parity: toolCalls: 0`; the Agent route kept `unmeasured`; `isolation: worktree` still overrides (readers.py:639-641); nothing in readers.py, `claude-boxes.workflow.js`, jpb's `validate-box.py`, or any caller parses the label; callers copy it into ` · `-separated lines it does not contain.
- Roster collateral: a structural diff against `main` shows exactly six changed strings (`rows[5..7]/isolation/{starved,packet-only}`), no key added or removed; the Gemini row untouched (Slice B's fields intact).
- Workflow-script escaping: a mandate with a backtick, a backslash, and `${process.env.HOME}` composed with zero unescaped `${` in `reader.workflow.js`; the new prefix line carries no `%`, backslash, backtick, or `${`.
- Slice C not pre-empted: `contract.md:69` still says `prompt_param: prompt` on the Agent route and `compose` prints it; SKILL.md Step 3 untouched.
- Citations: proofs (b) and (e) dated 2026-09-07 (15:55 and 16:04 PDT); the Agent-route measurement is R5(d) of 2026-09-07 (commit `ba727bb`); both dates in the contract hold.
- Scrub: no `/Users/`, `/private/`, `/var/folders`, TMPDIR, user, machine, session, or email string in any union file; the evidence file uses `<checkout>`/`<scratch>` throughout.
- Malformed input: a missing request file, `{` on stdin, a missing document, an unauthorized Gemini row, a duplicate call id each returned JSON on stdout, empty stderr; the refused composes wrote `sidecar.json` alone.
- Residue: after every lens's composes and records, `git status --short` empty in the checkout and in each scratch clone; `last-picks.json` unwritten; no `.readers/` in the checkout.
- REVIEW.md repo-specific checks, by name: sunrise Phase 8 "pushed" (no sunrise file in the union, held); readers uncaught exception (held, five malformed inputs); readers dispatch artefacts before a refusal (held, sidecar alone); readers callers run-id/call-id collision, id character rule, `session` placeholder, Workflow-tool dependency, `.readers/` copy naming, typed model pin, missing `session_model`, run dir unrecorded, inlined documents, mutating check in a worktree (no caller text in the union, held); readers evidence numbers reproduce (held, every number); readers callers writing `last-picks.json` mid-review (held, scratch clones); readers records with absolute paths or machine names (held).

### Questions

1. AC5's letter vs R5's substance: waive the builder's reading (SKILL.md:35 and :53 are the tool-parameter and fleet-authorization rules, not reader promises) or hold for an AC5 amendment? Recommendation: waive.
2. The contract's channel list is now known short on both routes (the git-status block and the user's email reach Agent-route readers; instruction files and the memory index reach Workflow-route readers) and "packet-only" was never measured. R1 dictates the current wording. Amend contract.md:76 and :130 in this slice on your word (dated 2026-09-08, citing this verdict), carry it to a later readers PR, or leave the spec's list as the record? Recommendation: amend now, one sentence each, since the slice exists to make the contract true.

Next: on Question 1's word, `/recheck` flips the card (waived → nothing to verify) or the AC5 amendment lands and `/recheck` verifies it; Question 2 on your word, either way.

SKILL NOTE: readers' Step 4 wants each READERS line followed by the result JSON verbatim in chat; the chat carries the lines and the hashes, the JSON is the sidecar on disk (the Slice H convention). Each capture was extracted from the Agent tool's transcript file by script (the final assistant message, byte-exact) rather than pasted from the notification, whose rendering HTML-escapes angle brackets.

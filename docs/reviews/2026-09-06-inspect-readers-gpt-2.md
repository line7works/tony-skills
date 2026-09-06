# Raw inspector output — readers build plan — GPT lane (gpt-6-astra) — 2026-09-06, second run

*Raw inspector output — unverified. Findings absent from the chat verdict were refuted or could not be verified. Nothing in this file has standing.*

Run: the second /inspect of `docs/plans/2026-09-06-readers.md` on this lane, after the plan was amended in place following the day's first two inspections. The packet was built from a pre-write snapshot of the amended plan (the three `Plan: inspected` stamp lines and everything from the first `### 2026-09-06 — inspect: plan` block stripped), so the inspector never saw any prior inspection output; the packet's `build doc:N` line numbers are that snapshot's numbering, and the live doc's lines from 32 on are three higher (the three stamps). Transport: `mcp__codex__codex`, `model: "gpt-6-astra"` (Tony's word for this run: "we're going to run 1 and 2"), the packet loaded as the instruction set through the config key `model_instructions_file`, `prompt` = "Inspect the build doc per your instructions and report every finding.", `sandbox: "read-only"`, `cwd` = the packet directory holding only `packet.md`, `approval-policy: "never"`, `config: {"web_search": "disabled"}`. Parity line: `web_search: disabled`. Thread id 01a077eb-582c-73a0-a8f6-420dd87e19ed. Packet: 107,949 bytes.

---

# Recommendation: REJECT pending correction

I inspected only the supplied packet. Repository paths, commands, component behavior, and conventions are **repo-grounded, not checked here**. Uncorroborated accounts of Tony's decisions are marked for confirmation, not asserted to be invented.

## Traceability and record integrity

### 1. The claimed blueprint interview is not corroborated by the supplied record.
- **Location:** build doc:6
- **Claim:** The plan presents additional approvals as settled although their source is not in the supplied record.
- **Failure scenario:** The builder treats the runtime, JSON format, Astra default, guide treatment, fleet interface, multi-reader precon behavior, and reasoning defaults as owner-approved without independently available confirmation.
- **Code book:** "Every requirement traces to the discussion, the repo, or an answered question." (73)
- **Severity:** QUESTION · **Confidence:** high

### 2. Inheriting an unknown model's operating limits is a load-bearing assumption.
- **Location:** build doc:18, assumption 11
- **Claim:** The plan classifies an unverified model's context, output, effort, and access capabilities by inheritance without a recorded decision authorizing that behavior.
- **Failure scenario:** Tony names a new model; readers rejects a packet that would fit, sends unsupported effort parameters, or advertises access capabilities the replacement does not possess.
- **Code book:** "Ask about load-bearing gaps only — choices that shape architecture, data, user-visible contracts, or slice boundaries." (24)
- **Severity:** QUESTION · **Confidence:** medium

### 3. The revision history points to records absent from this document.
- **Location:** build doc:3
- **Claim:** "Stamps below" and punch-list blocks recording two inspections are referenced, but neither appears in the supplied plan.
- **Failure scenario:** The builder cannot recover the claimed inspection changes or distinguish preserved decisions from unresolved findings. This does not establish that history was deleted.
- **Code book:** "One build doc per feature, revised in place. Never fork a parallel plan; never rewrite the ledger sections' history" (79)
- **Severity:** MAJOR · **Confidence:** high

### 4. The auto-memory edit has no authorization in the supplied scope record.
- **Location:** build doc:221
- **Claim:** Updating a specific file under another harness's auto-memory is added as mandatory close-out work without a traceable scope decision.
- **Failure scenario:** A builder treats a private harness-memory modification as approved feature work; a Codex builder also encounters Tony's protected-path prohibition.
- **Code book:** "Every requirement traces to the discussion, the repo, or an answered question." (73)
- **Severity:** QUESTION · **Confidence:** high

## Contract and runtime defects

### 5. Mandatory raw files contradict the caller-controlled, fileless contract.
- **Location:** build doc:18, assumption 3; build doc:42
- **Claim:** Requiring `raw.md` for every call overrides the scope's caller-controlled decision about whether a raw file exists.
- **Failure scenario:** An inspect Claude review or an ad hoc reader without a requested save path still persists its complete findings on disk. Calling the caller "fileless" does not remove that persistence.
- **Record:** record:10 expressly says the caller governs "whether and where a raw file is written" and inspect's Claude lane "stays fileless."
- **Code book:** "The doc records what was decided; it does not decide." (10)
- **Severity:** BLOCKER · **Confidence:** high

### 6. A demonstrated write violation does not prevent approval of the GPT lane.
- **Location:** build doc:44
- **Claim:** The isolation acceptance rule permits a write-capable reader to ship merely labeled `instruction-only`.
- **Failure scenario:** The write probe succeeds, the builder records that outcome, and AC5 passes even though the reader violates the scope's mandatory read-only constraint.
- **Record:** record:35 says "the model gets no write"; record:36 permits only the separate `repo-with-tools` exception.
- **Code book:** "Every requirement traces to the discussion, the repo, or an answered question." (73)
- **Severity:** BLOCKER · **Confidence:** high

### 7. The isolation label can overstate what was tested.
- **Location:** build doc:38, 44, 53
- **Claim:** One row-level label is derived from two profiles, then returned for other profiles, while other rows have no defined transition out of `unmeasured`.
- **Failure scenario:** A GPT `repo` review reports `sandbox-enforced` based on tests performed only under `starved` and `packet-only`; `gpt-sol` and host lanes can retain unexplained `unmeasured` labels through close-out.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MAJOR · **Confidence:** high

### 8. Unknown host limits make mandatory preflight arithmetic undefined.
- **Location:** build doc:38, 69
- **Claim:** Claude limits are deliberately `unknown`, but every row must undergo arithmetic budget validation without a defined unknown-limit policy.
- **Failure scenario:** The builder must invent a limit, skip a mandatory guard, or reject every Claude call. The floor-bound reviewer conversions depend on these calls succeeding.
- **Code book:** "Don't prescribe implementation detail (the builder's altitude) — and don't leave load-bearing decisions unstated (guessing, moved downstream)." (104)
- **Severity:** BLOCKER · **Confidence:** high

### 9. The size estimator does not establish the promised before-send oversize protection.
- **Location:** build doc:69
- **Claim:** Dividing bytes by 3.5 is treated as sufficient protection without an underestimate policy or conservative bound.
- **Failure scenario:** Token-dense content passes the estimate but exceeds the actual context window, so the system sends a packet it promises to reject before sending. The existing estimator's repository provenance does not establish its accuracy for every roster row.
- **Code book:** "Criteria are checkable or they aren't criteria." (75)
- **Severity:** MAJOR · **Confidence:** medium

### 10. The unclassified-floor status has contradictory expected outcomes.
- **Location:** build doc:37, 38, 51
- **Claim:** An unclassified floor-bound model is defined as `unknown-model`, but AC3 requires `floor-refused` for `gpt-astra`, whose eligibility is `not classified`.
- **Failure scenario:** An implementation following the status definition fails AC3; an implementation satisfying AC3 violates the stated definition unless it invents an undocumented distinction.
- **Code book:** "The most useful doc is self-contained — real files, real interfaces, explicit out-of-scope, every criterion checkable" (10)
- **Severity:** MAJOR · **Confidence:** high

### 11. The host-session floor check lacks a complete request interface.
- **Location:** build doc:96–97
- **Claim:** The shell validator must enforce a session-dependent floor, but the request has no defined way to carry the host-resolved session model into that check.
- **Failure scenario:** `readers validate` either refuses the Claude examples used by Slice H, guesses the parent model, or accepts a request before its effective model is known.
- **Code book:** "Write for a builder who wasn't in the room." (74)
- **Severity:** MAJOR · **Confidence:** high

### 12. Callers lack a defined pre-authorization suggestion interface.
- **Location:** build doc:96, 100, 123
- **Claim:** Readers must supply suggestions before a caller asks Tony, but the documented summon interface is a call/fleet request that validates authorization first.
- **Failure scenario:** Precon summons readers only after Tony answers, so its question cannot contain the promised remembered model or drop note. Alternatively, the builder invents an undocumented suggestion-only summon.
- **Code book:** "An unanswered load-bearing question stays visibly open in the doc, never silently resolved." (73)
- **Severity:** MAJOR · **Confidence:** high

### 13. Host validation can precede resolution of the model actually dispatched.
- **Location:** build doc:96
- **Claim:** The prescribed `validate`, then `suggest` order can change the selected model after the mandatory preflight check.
- **Failure scenario:** Validation checks the default, suggestion resolves a remembered override, and the host dispatches that override without rechecking its floor, budget, or supported profile.
- **Code book:** "The most useful doc is self-contained — real files, real interfaces, explicit out-of-scope, every criterion checkable" (10)
- **Severity:** MAJOR · **Confidence:** high

### 14. Custom run directories can split one run's freeze.
- **Location:** build doc:37, 71–72
- **Claim:** Dispatch accepts `run_dir`, but `suggest` has no corresponding parameter or specified mapping from a run ID to a previously selected directory.
- **Failure scenario:** Suggest freezes run R under the default directory; dispatch for R supplies another `run_dir` and creates or searches a different snapshot, breaking the guarantee that the approved model is the dispatched model.
- **Code book:** "Write for a builder who wasn't in the room." (74)
- **Severity:** MAJOR · **Confidence:** high

### 15. The scratch-checkout instructions use incompatible path meanings.
- **Location:** build doc:18, assumption 1; build doc:80–81
- **Claim:** `$READERS_CHECKOUT` denotes a checkout root in the contract but a copied plugin directory in the acceptance instructions.
- **Failure scenario:** The runner looks for `<scratch>/plugins/readers/last-picks.json` while AC5 checks `<scratch>/last-picks.json`. AC6 also edits a scratch roster without defining how the running entry point selects that roster.
- **Code book:** "Real paths, real names." (74)
- **Severity:** MAJOR · **Confidence:** high

### 16. The required tracked memory file need never be created.
- **Location:** build doc:84, 87–88
- **Claim:** Slice B expressly accepts an absent memory file and excludes changes to it, with no later slice establishing the tracked file required by the record.
- **Failure scenario:** Local picks accumulate in an untracked runtime-created file and do not travel with ordinary commits and pulls as the scope promises.
- **Record:** record:27 requires "a tracked file in the repo"; record:42 says it rides the next PR.
- **Code book:** "The doc records what was decided; it does not decide." (10)
- **Severity:** MAJOR · **Confidence:** high

### 17. The frozen snapshot does not capture later explicit selections as specified upstream.
- **Location:** build doc:72–73
- **Claim:** The snapshot contains roster and pre-ask memory, but no defined per-call addition records explicit picks and effective effort chosen after that snapshot.
- **Failure scenario:** The snapshot says one model was selected while a later approved override sends another. Sidecars may preserve the actual dispatch, but that is a change from the scope's stated snapshot contract.
- **Record:** record:38 requires the snapshot to record explicit overrides and effective model and effort.
- **Code book:** "Every requirement traces to the discussion, the repo, or an answered question." (73)
- **Severity:** MAJOR · **Confidence:** medium

### 18. Failure results cannot consistently satisfy the raw-capture contract.
- **Location:** build doc:37, 41–42, 50–51
- **Claim:** The contract requires verbatim `raw_text` "always" and a raw-file/hash result, while incomplete responses must remain in diagnostics only and refused calls contain only a sidecar.
- **Failure scenario:** Builders disagree about whether partial output appears in JSON, whether nonexistent raw paths are returned, and whether raw hashes are absent or null. The "every R2 result field" check has no unambiguous expected failure shape.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MAJOR · **Confidence:** high

### 19. Timeout and cancellation behavior is named but not specified.
- **Location:** build doc:37–41
- **Claim:** `timed-out`, `cancelled`, and `timeout_s` have no defined execution, cleanup, or precedence rules.
- **Failure scenario:** A cancelled parent leaves a reader running and spending, or a timeout is reported as `transport-failed` or `incomplete`; the grader has no criterion for determining the correct outcome.
- **Code book:** "Don't prescribe implementation detail (the builder's altitude) — and don't leave load-bearing decisions unstated (guessing, moved downstream)." (104)
- **Severity:** MAJOR · **Confidence:** medium

### 20. Invalid requests fall outside the supposedly fixed status contract.
- **Location:** build doc:37
- **Claim:** The contract does not define outcomes for malformed JSON, missing required fields, unknown rows, invalid effort, or invalid output budgets.
- **Failure scenario:** A caller receives a traceback, an invented status, or a misleading transport error instead of the promised JSON result with a defined status.
- **Code book:** "The most useful doc is self-contained — real files, real interfaces, explicit out-of-scope, every criterion checkable" (10)
- **Severity:** MAJOR · **Confidence:** medium

### 21. The direct form leaves its access profile unstated.
- **Location:** build doc:99, 107
- **Claim:** The ad hoc syntax omits an access profile without specifying a default, although its acceptance test assumes a tool-free Claude call.
- **Failure scenario:** A builder defaults the direct form to the current repository, permitting workspace reads where AC4 expects `toolCalls: 0`.
- **Code book:** "An unanswered load-bearing question stays visibly open in the doc, never silently resolved." (73)
- **Severity:** MAJOR · **Confidence:** high

## Verification defects

### 22. The concurrency test does not exercise concurrent snapshot creation.
- **Location:** build doc:72, 82
- **Claim:** AC7 creates the snapshot before launching concurrent calls, leaving the exclusive first-call race untested.
- **Failure scenario:** Two genuinely simultaneous first calls produce competing or partially readable snapshots, while the prescribed freeze test still passes.
- **Code book:** "Tests are part of the plan. Criteria that can be tests name them" (78)
- **Severity:** MAJOR · **Confidence:** high

### 23. The canned-response mechanism cannot prove all the guard checks assigned to it.
- **Location:** build doc:16, 74, 77
- **Claim:** The sole test hook supplies an OpenRouter response body, but the plan assigns GPT truncation, HTTP-status behavior, and guard-order verification to canned transport tests.
- **Failure scenario:** GPT startup/truncation handling and HTTP-status handling remain untested; four isolated OpenRouter body cases pass without establishing which guard wins when errors coexist.
- **Code book:** "Tests are part of the plan. Criteria that can be tests name them" (78)
- **Severity:** MAJOR · **Confidence:** high

### 24. The required denied nested run can avoid testing execution denial.
- **Location:** build doc:45, 54
- **Claim:** Omitting `authorized` tests readers' authorization gate, not the parent escalation or child-startup denial described in the record.
- **Failure scenario:** The acceptance test passes while an actual denied child launch hangs, retries, or returns an unstructured error. The optional third case leaves that path unproved whenever no prompt appears.
- **Record:** record:46 describes the startup block, escalation, and denied-case requirement.
- **Code book:** "Every requirement traces to the discussion, the repo, or an answered question." (73)
- **Severity:** MAJOR · **Confidence:** medium

### 25. The blindness test can pass without establishing blindness.
- **Location:** build doc:108
- **Claim:** AC5 checks what the reviewer chooses to reveal, without seeding a known prior finding or checking what context it actually received.
- **Failure scenario:** A reviewer receives prior rationale or findings but declines to quote them; the test reports a blind review even though independence was lost.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MAJOR · **Confidence:** high

### 26. "Start timestamps overlap" is not a concurrency criterion.
- **Location:** build doc:111
- **Claim:** Individual start timestamps cannot establish overlapping execution.
- **Failure scenario:** A grader either demands identical timestamps, rejecting valid concurrency, or accepts two different timestamps even when the calls ran sequentially.
- **Code book:** "Criteria are checkable or they aren't criteria." (75)
- **Severity:** MAJOR · **Confidence:** high

### 27. Several literal verification commands omit their input file.
- **Location:** build doc:147, 163, 201
- **Claim:** Multiple `grep` checks are written without a filename or a defined stdin source.
- **Failure scenario:** Copying the stated check waits on stdin or produces no count, rather than verifying the modified skill. "For each file" does not supply the omitted shell argument.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MINOR · **Confidence:** high

### 28. The short-body acceptance criterion does not measure shortness.
- **Location:** build doc:104
- **Claim:** AC1 verifies prohibited strings but provides no checkable interpretation of "short."
- **Failure scenario:** A very long orchestration manual passes the advertised short-body check as long as it avoids the listed strings.
- **Code book:** "Criteria are checkable or they aren't criteria." (75)
- **Severity:** MINOR · **Confidence:** high

### 29. The stated call counts do not reconcile with their cited tests.
- **Location:** build doc:16
- **Claim:** The spend accounting counts denied or suggestion-only operations as model calls and miscounts other referenced runs.
- **Failure scenario:** Tony approves a test session using an inaccurate call inventory. For example, Slice B AC6 only runs `suggest`, AC7 dispatches two calls rather than three, and Slice A's unauthorized nested case cannot send a GPT call.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MINOR · **Confidence:** high

## Slice integrity and close-out

### 30. Caller slices explicitly defer their behavioral proof.
- **Location:** build doc:8, 31
- **Claim:** The plan substitutes greps and hypothetical request validation for demonstrating each converted caller, reserving actual integration proof for Slice I.
- **Failure scenario:** D–H can be accepted while their summon, authorization, capture, or failure-routing behavior is broken. Discovering that after all merges defeats independently verifiable slices. The installation constraint is repo-grounded, not checked here; it does not itself waive the code book.
- **Code book:** "Independently verifiable: each slice carries criteria checkable at that slice, never 'will be tested later.'" (31; quoted wording uses the code book's phrase)
- **Severity:** MAJOR · **Confidence:** high

### 31. Four converted callers never receive behavioral acceptance proof.
- **Location:** build doc:167, 218, 228
- **Claim:** Installed proofs omit architect, vertical, wargame, and recheck.
- **Failure scenario:** Close-out passes although one of those callers never successfully runs through readers. Vertical is explicitly deferred beyond this plan; the others have only static/hypothetical request checks.
- **Record:** record:23 says "the build is not done until all eight run on `readers`."
- **Code book:** "Ends wired in: every slice leaves the system integrated and demonstrable." (30)
- **Severity:** MAJOR · **Confidence:** high

### 32. The dependency fields do not enforce the required caller order.
- **Location:** build doc:208, 233
- **Claim:** H depends only on G, and I depends only on H, leaving D, E, and F outside their dependency chains.
- **Failure scenario:** A dependency-driven builder starts H before the five outside-reader callers are converted, contrary to record:31, then reaches I with its C–H merge prerequisites unmet.
- **Code book:** "Order: dependency-ordered — data before services, services before surfaces." (29)
- **Severity:** MAJOR · **Confidence:** high

### 33. Slice I requires evidence of its own unfinished signoff.
- **Location:** build doc:218, 228
- **Claim:** AC6 requires the slice's signoff run to be recorded verbatim in the evidence file that the same signoff must grade.
- **Failure scenario:** During the first signoff, the required complete signoff record cannot yet exist; the slice must fail or the grader must accept future evidence.
- **Code book:** "Independently verifiable: each slice carries criteria checkable at that slice, never 'will be tested later.'" (31; quoted wording uses the code book's phrase)
- **Severity:** MAJOR · **Confidence:** high

### 34. Laptop close-out omits updating the checkout that owns shared memory.
- **Location:** build doc:219, 229
- **Claim:** Plugin installation and updates are treated as bringing the laptop level, without pulling or checking the separate tony-skills checkout.
- **Failure scenario:** The laptop runs new installed plugins against absent or stale checkout memory and suggests a different model, while AC7 passes from `claude plugin list` alone.
- **Record:** record:27 explicitly requires "a git pull of that checkout (not a plugin update)."
- **Code book:** "The doc records what was decided; it does not decide." (10)
- **Severity:** MAJOR · **Confidence:** high

### 35. The installed-copy criterion does not define how a version directory proves the merged commit.
- **Location:** build doc:228–229
- **Claim:** The plan requires plugin-list output to establish exact merged-copy identity without defining the expected version or commit-to-version mapping.
- **Failure scenario:** A plugin list displays the expected names and familiar version directories while one cache contains older skill text, and the grader cannot distinguish it from the intended build.
- **Code book:** "One measurable end state plus the stated check." (75)
- **Severity:** MINOR · **Confidence:** medium

## Concerns without location

- The blueprint chat read-back, open-question/assumption counts, and any required `SKILL NOTE:` were not supplied. I cannot verify the Step 5 gate or claim it was skipped.
- No prior build document or inspection history was supplied. I cannot determine whether this is the one living document or whether prior ledger history was preserved.

## What I attacked that held up

- The eight-caller scope, pinned Claude boxes, Qwen addition, Grok removal, and portable/host split trace to the record.
- The stated **32 decided lines** matches the scope's decided entries.
- Caller-owned mandates, authorization, failure policy, and post-processing are substantially preserved.
- The plan retains explicit authorization, no silent substitution, model floors, and protocol mismatch refusal.
- Sections A–I contain the required slice scaffold and exact `Status: not started` labels.
- All five downstream ledger sections are present and empty.
- The `READERS:` reporting form uses the required · separators.
- A working portable reader is scheduled early rather than leaving only an unused foundation.
- Nine slices are not inherently excessive for this multi-transport, eight-caller migration.

## Overall judgment

**I would not approve this plan for construction.** Its scope mapping and document scaffold are strong, but mandatory disk capture and acceptance of successful write probes conflict with settled requirements. Unknown-limit handling, host preflight, suggestion/freeze sequencing, and memory paths leave central interfaces unresolved. The verification schedule also allows caller defects to survive multiple merges and omits behavioral proof for four callers. Correct those contracts and acceptance gates, and confirm the additional owner rulings before building.

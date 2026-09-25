# Adapter profile: architect-v2 on Claude Code

The architect-v2 adapter for Claude Code (E14 slice 1, the frame; the E9 seam's profile, twelve sections
in order, E13's build-v2 and signoff-v2 adapters as the pattern). Read this after `../README.md`
and before running `check-input`. A section the frame can answer is answered here; a section the
station's own behavior decides is marked for its slice 2 lane. Labels follow E9-11
(`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation`
object into the input whole, typing none of its fields; the recorded answer's session is
`answer_fields.session_id`, typed by no one. `measurement` is copied nowhere: the input schema
closes `invocation` with `additionalProperties: false`, so a measurement key placed there is
refused (`tests/test_invocation.py`, `SchemaCompositionTest`, validates both ways against the real
schema). `--caller NAME` only when a calling station's payload names one.

## 1. Identity

`invocation.harness` is `claude-code`, this adapter's own name (`helper-derived`). The version, the
entry and the sandbox are measurement only, read by the helper the E13 way (`_common.py`, byte for
byte the E13 cores' file). Measured values for this core's installed package: Claude Code 2.1.282 (`claude --version`); entry `plugin`, this setup's own marketplace `architect-v2-setup` (`claude plugin install architect-v2@architect-v2-setup`), the installed copy at `<config>/plugins/cache/architect-v2-setup/architect-v2/0.1.0/` beside `readers/1.0.1`; `install.sh` exit 0 and `verify-install.sh` exit 0 with no finding (lane A, 2026-09-25, an isolated home); the sandbox is not measured, since no session was started; and the
control room's install proofs at the hand-back.

## 2. Model and floor

Does not apply to the input: `invocation` carries no model. `measurement.model_id` records the
session's model for the record only (`helper-derived`). Whether this station names a model floor
for a reader it summons is the station's own rule: architect-v2 names none (v1 names none), so its blind-review requests carry no `floor`; each reviewer's model is its roster row's, or a model id the owner typed (`request --model ROW=ID`); the session's own model id rides only on the `claude-session` row as `session_model` (`request --session-model`, `instruction-bound`). A reader's floor is readers' roster's.

## 3. Run id and directory

Does not apply to the adapter: `run_id` and `run_dir` are top-level input fields the executor
writes (`instruction-bound`: a fresh id, an absolute directory outside the workspace and the
staging home). `check-input` refuses a run directory inside either and one that already holds a
run (`references/station-loop.md` sections 3.1 and 4).

## 4. The user channel

The owner's word for an outside reader is the input's `owner_word` field (the rows his words name
and the words verbatim), the one source of a request's `authorized` flag
(`references/station-loop.md` section 8, rule 5). No turn reference is recorded in the frame, so no
`turns.py` ships. The executor copies the owner's words verbatim into `owner_word.words`, and the rows they name into `owner_word.rows`, when the input is written (`instruction-bound`); his answers in the interview are the recorded answer's `questions[].answer`. No turn map is needed: nothing this station decides reads a turn reference, and `authorized` is the shared builder's, from `owner_word` alone. A reviewer the owner names only at the review's offer, after `check-input`, has no word in this run's input, and readers refuses it: the executor tells him so, runs `report` (it stops `review-pending`), and must start a new run on the same doc whose input carries his words verbatim in `owner_word` (`rows` the rows he named); that run's `request` carries `authorized`. Never the flag or the word added by hand (`references/architect-v2-contract.md` section 15, point 1).

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What this station records about the session is
the recorded answer's `session_id`, which this adapter supplies as `answer_fields.session_id`:
the session's own id, found through the harness's `CLAUDE_CODE_SESSION_ID` and bound to its transcript (the file is named for it, every `user` and `assistant` record carries it, and with `--workspace` a record names that workspace as its `cwd`; ruling E9-28, the pilot's code). The helper prints the same value inside `invocation` as `session_id`.
`helper-derived` for the reading, `instruction-bound` for the record it reads.

## 6. Run date

Does not apply to the adapter: a document's date is rendered by the core, the machine's local calendar date read by the script once per command (`scripts/architect_core/common.py`, `today`); the `ARCHITECT_V2_TEST_TODAY` hook pins it only under `ARCHITECT_V2_TEST=1` (`tests/test_profile_lane.py`).

## 7. The verifier capability

The station summons no verifier of its own. Readers, where it uses them (the exit test, the blind review, the lenses), are
summoned through `/readers` with the request `station_core/readers_request.py` builds; the
transport, the model and the containment are readers' roster's. Which readers and mandates: the blind review only (`references/architect-v2-contract.md` section 10), one request per reviewer the owner names, the scope doc its single document, `profile: starved`, the fixed mandate verbatim. On Claude Code every roster row is dispatchable through `/readers`: the host rows (`claude-session`, `gemini`) run through the session's own tools, the portable rows through the readers runner. `request` finds readers' roster beside this core (route 3a in a checkout, 3b in the installed cache, measured on the installed copy above).

## 8. Delivery

Not measured in the frame. The delivery probe for this core is `setups/claude-code/prompts/`; its
measurement on the installed package is not lane A's (the probe starts a session, which a lane builder does not do); measured on the package instead: its `SKILL.md` is 14,214 bytes (`wc -c` on the installed copy). The control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

`disable-model-invocation: true` in `SKILL.md` (pick P5) keeps this station out of automatic invocation; the owner types it by name. Whether the harness enforces it is measured manual-only in the install proofs (slice 3 and the control room's proof at the hand-back); the frame records no measurement of its own.

## 10. Negative tests

`setups/claude-code/negative-tests.sh` runs the E13 nine cases on this core's package, each in its
own throwaway home; the free half always runs, the live half is behind `--live`. The observed rows:

| Case | Observed (free half, lane A, 2026-09-25) |
|---|---|
| `malformed-sidecar` | installed as mutated; `claude plugin validate` exit 0, no warning |
| `missing-sidecar` | installed as mutated; validate exit 0 |
| `missing-name` | installed as mutated; validate exit 0 |
| `broken-delimiter` | installed as mutated; validate exit 0 with the warning "No frontmatter block found" |
| `duplicate-name` | both plugins installed as mutated |
| `missing-resource` | installed; the harness does not notice the missing schema; the installed core's `check-input` refuses it, exit 2 |
| `symlink-file` | validate warns (a component that is not a regular file was not read); the installer dropped SKILL.md from the cache silently; activation is the live half's question |
| `symlink-directory` | validate warns (a symlinked entry was not read); the installer dropped the skill folder from the cache silently; activation is the live half's question |
| `update-copy-symlink` | every installed copy is a real copy; the symlinked SKILL.md of the 0.1.2 stage was dropped from the cache |

The live half (`--live`) was not run: it starts sessions.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/claude-code/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference
resolves inside the installed root through no symlink, walks the installed tree for symlinks, and
compares `scripts/architect.py skill-identity`'s `content_sha256` from the installed copy and the
checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Identify the executor's session (the answer's `session_id`) | `helper-derived` reading of an `instruction-bound` record | section 5 |
| Keep the station out of automatic invocation | measured in the install proofs | section 9 |
| Render the doc from the answer and refuse a re-asked decided line, an untraced line, a lost line, a candidate set or a component the razor refuses | not a harness capability: the core's script decides it the same on every harness | `scripts/tests/` (`test_arch_record.py`, `test_arch_write.py`) |
| Keep the owner's word to this run (`authorized` from the input's `owner_word` only) | not a harness capability: the shared builder's | `scripts/tests/test_arch_review.py` |
| Publish the visual privately to the same URL across runs | `instruction-bound` (the executor's tool call); the URL it returned is checked by `record-publish` | `references/architect-v2-contract.md` section 11 |
| Ask the exit ramp and the pick in the owner's words, questions in plain text | `instruction-bound` | `SKILL.md` Steps 2 and 3 |

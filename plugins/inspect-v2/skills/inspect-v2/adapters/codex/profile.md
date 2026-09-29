# Adapter profile: inspect-v2 on Codex CLI

The inspect-v2 adapter for Codex CLI (E14 slice 1, the frame, filled in slice 2 by lane I; the E9 seam's profile, twelve sections
in order, E13's build-v2 and signoff-v2 adapters as the pattern). Read this after `../README.md`
and before running `check-input`. A section the frame could answer was answered there; a section the
station's own behavior decides was filled by its slice 2 lane (lane I). Labels follow E9-11
(`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation`
object into the input whole, typing none of its fields; the recorded answer's session is
`answer_fields.session_id`, typed by no one. `measurement` is copied nowhere: the input schema
closes `invocation` with `additionalProperties: false`, so a measurement key placed there is
refused (`tests/test_invocation.py`, `SchemaCompositionTest`, validates both ways against the real
schema). `--caller NAME` only when a calling station's payload names one.

## 1. Identity

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`). The version, the
entry and the sandbox are measurement only, read by the helper the E13 way (`_common.py`, byte for
byte the E13 cores' file). Measured values for this core's installed package (lane I, 2026-09-25, `install.sh` into a fresh
temp home, no sign-in): Codex 0.155.1 installs inspect-v2 0.1.0 at `<CODEX_HOME>/plugins/cache/inspect-v2-setup/inspect-v2/0.1.0/`, beside `records/0.2.0`,
`readers/1.0.1` and `blueprint-v2/0.1.0` from the same setup marketplace; the installed copy's
`skill-identity` `content_sha256` equals the checkout's (`verify-install.sh`, no finding); and a run
of the INSTALLED driver (`check-input`, `select`, `harvest`, `packet` on a scratch repository)
resolved the code book, the records component (interface version 2) and readers' roster, each by
route 3b. The control room's install proofs at the hand-back are the record.

## 2. Model and floor

Does not apply to the input: `invocation` carries no model. `measurement.model_id` records the
session's model for the record only (`helper-derived`). This station names no model floor
for a reader it summons: v1's stated exception is kept (the lane the owner picks is the floor, and the
model-named stamp is the compensating trust label), so no request carries `floor`
(`references/inspect-v2-contract.md` section 2). The stamp names the effective model the readers'
result carries, never `measurement.model_id` and never a typed id (`helper-derived` from readers'
sidecar through the recorded answer; a null one stops the run `no-effective-model`).

## 3. Run id and directory

Does not apply to the adapter: `run_id` and `run_dir` are top-level input fields the executor
writes (`instruction-bound`: a fresh id, an absolute directory outside the workspace and the
staging home). `check-input` refuses a run directory inside either and one that already holds a
run (`references/station-loop.md` sections 3.1 and 4).

## 4. The user channel

The owner's word for an outside reader is the input's `owner_word` field (the rows his words name
and the words verbatim), the one source of a request's `authorized` flag
(`references/station-loop.md` section 8, rule 5). No turn reference is recorded in the frame, so no
`turns.py` ships. The executor copies the owner's answer to the ask verbatim into `owner_word.words`
and the row it names into `owner_word.rows`, in the input, before `check-input` (`instruction-bound`:
the harness keeps the turn, the input carries the words); the recorded answer may repeat the same
object and `record-answer` refuses one that differs, or one on a Claude row. No turn map is needed
and no `turns.py` ships: `authorized` is decided from the input alone by
`station_core/readers_request.py`, never from anything remembered.

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What this station records about the session is
the recorded answer's `session_id`, which this adapter supplies as `answer_fields.session_id`:
the executor's own thread: the rollout named by `CODEX_THREAD_ID` under the sessions root of the home the helper is installed in (E9-40), its `session_meta.id` equal to the thread id. The helper prints the same value inside `invocation` as `session_id`.
`helper-derived` for the reading, `instruction-bound` for the record it reads.

## 6. Run date

Does not apply to the adapter: the date of the stamp, the records block and the verdict mirror is the
UTC date of the one instant `write` reads from the clock (`inspect_core/common.py`, `now`), the same
instant every `finding_raised` event carries as `at`, so the block's heading and the stamp agree.
`INSPECT_V2_TEST_NOW` fixes it, honored only under `INSPECT_V2_TEST=1` (`helper-derived`).

## 7. The verifier capability

The station summons no verifier of its own. Readers, where it uses them (the exit test, the blind review, the lenses), are
summoned through `/readers` with the request `station_core/readers_request.py` builds; the
transport, the model and the containment are readers' roster's. Which readers and mandates:
the Claude lane is three calls on the named Claude row (traceability and code book under
`packet-only`, repo reality under `repo` on the workspace); an outside lane is one paper call on the
named outside row under `packet-only`, plus the repo-reality call on `claude-session`; the fixed
mandates verbatim (`references/inspect-v2-contract.md` section 6). The script writes the request
files (`request`); the executor summons `/readers` with them unchanged (`instruction-bound`), and
readers' pre-send checks enforce `authorized`, the profile and the row's transport. On Codex a
`claude-session` call is a host row the shell entry cannot run (readers answers `lane-unavailable`,
and the run stops `lane-down`); the owner may name `claude-opus-cli`, the portable Claude row (E14
A12), which this core treats as a Claude lane. Not measured in this lane (no model call).

## 8. Delivery

Not measured in the frame. The delivery probe for this core is `setups/codex/prompts/`; its
measurement on the installed package needs a signed-in session, and an isolated home has none; this
lane ran no session. What was measured: the installed `SKILL.md` is byte-equal to the checkout's
(`verify-install.sh`: no diff, frontmatter equal). The control room's proof at the hand-back is the
record.

## 9. Sidecars and invocation restrictions

`policy.allow_implicit_invocation: false` in `agents/openai.yaml` (pick P5; the E9 seam's manual-only sidecar) keeps this station out of automatic invocation; the owner types it by name. Whether the harness enforces it is measured manual-only in the install proofs (slice 3 and the control room's proof at the hand-back); the frame records no measurement of its own.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the E13 nine cases on this core's package, each in its
own throwaway home; the free half always runs, the live half is behind `--live`. The observed rows
(lane I, 2026-09-25, free half, Codex 0.155.1, `negative-tests.sh` exit 0): five cases (malformed sidecar, missing sidecar, missing name, broken delimiter, duplicate name) installed as mutated, activation being the live half's question; `missing-resource` installed, unnoticed by the harness, and the core refused (exit 2); `symlink-file` and `symlink-directory` prevented at install (the installer dropped the skill silently); `update-copy-symlink` enforced in the cache, every installed copy a real copy. The live half was
not run.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference
resolves inside the installed root through no symlink, walks the installed tree for symlinks, and
compares `scripts/inspect_v2.py skill-identity`'s `content_sha256` from the installed copy and the
checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Identify the executor's session (the answer's `session_id`) | `helper-derived` reading of an `instruction-bound` record | section 5 |
| Keep the station out of automatic invocation | measured in the install proofs | section 9 |
| Build the packet, the readers requests and the mechanical verify pass | enforced in code | `inspect_core/`; `references/inspect-v2-contract.md` sections 6 and 7 |
| Summon readers with the built requests, unchanged | `instruction-bound` | SKILL.md Step 3; readers' pre-send checks enforce `authorized` and the profile |
| Keep every finding's origin a reader's (independence) | enforced in code for the record (`independence`), `instruction-bound` for the executor | contract section 7 |
| Raise findings in the records and write the stamp, never a clear | enforced in code; the append is the component's | contract sections 8 and 12 |

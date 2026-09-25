# Adapter profile: blueprint-v2 on Codex CLI

The blueprint-v2 adapter for Codex CLI (E14 slice 1, the frame; the E9 seam's profile, twelve sections
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

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`). The version, the
entry and the sandbox are measurement only, read by the helper the E13 way (`_common.py`, byte for
byte the E13 cores' file). Measured values for this core's installed package: (lane L fills this), and the
control room's install proofs at the hand-back.

## 2. Model and floor

Does not apply to the input: `invocation` carries no model. `measurement.model_id` records the
session's model for the record only (`helper-derived`). Whether this station names a model floor
for a reader it summons is the station's own rule (lane L fills this); a reader's floor is readers' roster's.

## 3. Run id and directory

Does not apply to the adapter: `run_id` and `run_dir` are top-level input fields the executor
writes (`instruction-bound`: a fresh id, an absolute directory outside the workspace and the
staging home). `check-input` refuses a run directory inside either and one that already holds a
run (`references/station-loop.md` sections 3.1 and 4).

## 4. The user channel

The owner's word for an outside reader is the input's `owner_word` field (the rows his words name
and the words verbatim), the one source of a request's `authorized` flag
(`references/station-loop.md` section 8, rule 5). No turn reference is recorded in the frame, so no
`turns.py` ships. How the executor quotes the owner's words, and whether a turn map is needed,
(lane L fills this).

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What this station records about the session is
the recorded answer's `session_id`, which this adapter supplies as `answer_fields.session_id`:
the executor's own thread: the rollout named by `CODEX_THREAD_ID` under the sessions root of the home the helper is installed in (E9-40), its `session_meta.id` equal to the thread id. The helper prints the same value inside `invocation` as `session_id`.
`helper-derived` for the reading, `instruction-bound` for the record it reads.

## 6. Run date

Does not apply to the adapter: a document's date is rendered by the core (lane L fills this).

## 7. The verifier capability

The station summons no verifier of its own. Readers, where it uses them (none in v1 blueprint), are
summoned through `/readers` with the request `station_core/readers_request.py` builds; the
transport, the model and the containment are readers' roster's. Which readers and mandates
(lane L fills this).

## 8. Delivery

Not measured in the frame. The delivery probe for this core is `setups/codex/prompts/`; its
measurement on the installed package (lane L fills this), and the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

Codex CLI carries no manual-only restriction: blueprint-v2 is invoked on its phrases and its command, v1 blueprint's own trigger rule (pick P5).

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the E13 nine cases on this core's package, each in its
own throwaway home; the free half always runs, the live half is behind `--live`. The observed rows
(lane L fills this).

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference
resolves inside the installed root through no symlink, walks the installed tree for symlinks, and
compares `scripts/blueprint.py skill-identity`'s `content_sha256` from the installed copy and the
checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Identify the executor's session (the answer's `session_id`) | `helper-derived` reading of an `instruction-bound` record | section 5 |
| Keep the station out of automatic invocation | does not apply (auto-invocable) | section 9 |
| The station's own capabilities | (lane L fills this) | |

# Adapter profile: precon-v2 on Codex CLI

The precon-v2 adapter for Codex CLI (E14 slice 1, the frame; the E9 seam's profile, twelve sections
in order, E13's build-v2 and signoff-v2 adapters as the pattern). Read this after `../README.md`
and before running `check-input`. The frame answered the sections it could; lane P (slice 2)
answered the ones the station's own behavior decides. Labels follow E9-11
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
byte the E13 cores' file). Measured values for this core's installed package, by lane P on
2026-09-25 with codex-cli 0.155.1: `setups/codex/install.sh` (no `--credential`) into a fresh
isolated home installed `precon-v2` 0.1.0 and `readers` 1.0.1 as `plugin` entries under that
home's `plugins/cache/precon-v2-setup/`, exit 0 and no failed command; `verify-install.sh` then
found the installed copy equal to this checkout (a diff of 0 lines), the frontmatter equal, no
symlink in the installed package, and the same skill-identity `content_sha256` from both copies.
The control room's install proofs at the hand-back stay the record.

## 2. Model and floor

Does not apply to the input: `invocation` carries no model. `measurement.model_id` records the
session's model for the record only (`helper-derived`). This station names no model floor for a
reader: the exit test's requests carry no `floor` (v1 names none), so a reader's model is readers'
roster default or the id the owner typed against that row (`request --model ROW=ID`). A reader's
floor, where one applies, is readers' roster's.

## 3. Run id and directory

Does not apply to the adapter: `run_id` and `run_dir` are top-level input fields the executor
writes (`instruction-bound`: a fresh id, an absolute directory outside the workspace and the
staging home). `check-input` refuses a run directory inside either and one that already holds a
run (`references/station-loop.md` sections 3.1 and 4).

## 4. The user channel

The owner's word for an outside reader is the input's `owner_word` field (the rows his words name
and the words verbatim), the one source of a request's `authorized` flag
(`references/station-loop.md` section 8, rule 5). No turn reference is recorded in the frame, so no
`turns.py` ships. The executor copies the owner's words verbatim into `owner_word.words` and the
rows those words name into `owner_word.rows` (`instruction-bound`: no helper reads a turn); they
are his answer to the cold-read question, and they go into the NEXT run's input, the exit-test
run (`references/precon-v2-contract.md` section 7). A recorded answer's `owner_words` trace quotes
him the same way. No turn map is needed: nothing in this station's result points at a turn.

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What this station records about the session is
the recorded answer's `session_id`, which this adapter supplies as `answer_fields.session_id`:
the executor's own thread: the rollout named by `CODEX_THREAD_ID` under the sessions root of the home the helper is installed in (E9-40), its `session_meta.id` equal to the thread id. The helper prints the same value inside `invocation` as `session_id`.
`helper-derived` for the reading, `instruction-bound` for the record it reads.

## 6. Run date

Does not apply to the adapter: a document's date is rendered by the core. It is the input's
`station.date` (`YYYY-MM-DD`, `instruction-bound`), or, when the input carries none, the machine's
local calendar date, which `harvest` reads and records in `harvest.json` (`helper-derived`). A new
scope doc's name and title and a cold-read doc's name carry it.

## 7. The verifier capability

The station summons no verifier of its own. Readers, where it uses them (the exit test, the blind review, the lenses), are
summoned through `/readers` with the request `station_core/readers_request.py` builds; the
transport, the model and the containment are readers' roster's. This station's readers are the
exit test's: one request per row the owner named (`request --row`), `profile: starved`, the scope
doc as the single document, the cold-reader mandate v1 states (quoted once in
`references/precon-v2-contract.md` section 7), and `authorized` only on an outside row the input's
`owner_word` names, never on an anthropic row (`helper-derived`: `station_core/readers_request.py`
decides it, and `request` refuses an outside row the word does not name). On this harness the
Claude reader is the roster's portable row `claude-opus-cli` (transport `claude-cli`, E14 A12),
dispatched through readers' shell entry where the `claude` binary is on `PATH`; it needs no word.
`claude-session` is a host row that needs Claude Code's Agent or Workflow tool, which a Codex
session has not, so it is not offered here. readers' roster is found beside this plugin; measured
on the installed package, route 3b resolved `readers` 1.0.1's roster in the isolated home.

## 8. Delivery

Not measured in the frame. The delivery probe for this core is `setups/codex/prompts/`; its
measurement on the installed package is not lane P's either: a probe needs a live session, which
is outside this lane's boundary (no harness launch beyond the install scripts' plugin commands).
It is the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

`policy.allow_implicit_invocation: false` in `agents/openai.yaml` (pick P5; the E9 seam's manual-only sidecar) keeps this station out of automatic invocation; the owner types it by name. Whether the harness enforces it is measured manual-only in the install proofs (slice 3 and the control room's proof at the hand-back); the frame records no measurement of its own.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the E13 nine cases on this core's package, each in its
own throwaway home; the free half always runs, the live half is behind `--live`. The rows lane P
observed on 2026-09-25 (codex-cli 0.155.1, the free half only):

| Case | Observed |
|---|---|
| malformed-sidecar, missing-sidecar, missing-name, broken-delimiter, duplicate-name | installed as mutated; activation is the live half's question |
| missing-resource | installed; the harness does not notice the missing resource; the core refuses (exit 2) |
| symlink-file, symlink-directory | activation prevented at install: the installer dropped the skill silently |
| update-copy-symlink | every installed copy is a real copy; the symlinked `SKILL.md` was dropped at the symlink stage |

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference
resolves inside the installed root through no symlink, walks the installed tree for symlinks, and
compares `scripts/precon.py skill-identity`'s `content_sha256` from the installed copy and the
checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Identify the executor's session (the answer's `session_id`) | `helper-derived` reading of an `instruction-bound` record | section 5 |
| Keep the station out of automatic invocation | measured in the install proofs | section 9 |
| Count the board from the doc as it stands (`state`) | `helper-derived` | the ledger reader over the doc; `scripts/tests/test_state.py` |
| Refuse a line with no source, a quietly resolved line, a re-asked decided line | `helper-derived` | `record-answer`: the shared refusals and precon's own; `scripts/tests/test_record_answer.py` |
| Keep every prior line of a continued doc byte for byte | `helper-derived` | `write`'s plan and its no-loss check; `scripts/tests/test_write.py` |
| Authorize an outside reader only on the owner's word in the run | `helper-derived` from the `instruction-bound` `owner_word` | `request`; `scripts/tests/test_exit_test.py` |
| Stay on the property: no web, no research | `instruction-bound` for the executor; the script has no network | `SKILL.md` step 1 |
| Stop at the gate | `instruction-bound`; a run with no gate line is not complete (`helper-derived`) | `SKILL.md` step 6; `gate-missing` |

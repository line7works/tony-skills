# Adapter profile: handoff-v2 on Codex CLI

The handoff-v2 adapter for Codex CLI (E15 slice 1, hand-back 2; the E9 seam's profile, twelve sections in order,
precon-v2's adapters as the pattern). Read this after `../README.md` and before running `check-input`. Labels follow
E9-11 (`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation` object into the
input whole, typing none of its fields. `measurement` is copied nowhere: the input schema closes `invocation` with
`additionalProperties: false`, so a measurement key placed there is refused (`tests/test_invocation.py`,
`SchemaCompositionTest`).

## 1. Identity

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`); it also decides the pointer seam
(section 7): a `codex-cli` run's pointer is written nowhere. The version, the entry and the sandbox are measurement
only, read by the helper (`_common.py`, byte for byte precon-v2's). No install of this core has been measured by its
builder; the control room's install proofs are the record.

## 2. Model and floor

Does not apply: handoff-v2 summons no reader and visits no station, so `invocation` carries no model and no floor is
read. The executor is the session itself.

## 3. Run id and directory

`run_id` and `run_dir` are top-level input fields the executor writes (`instruction-bound`: a fresh id, an absolute
directory outside the workspace). `check-input` refuses a run directory inside the workspace and one that already
holds a run (`references/back-loop.md` section 3).

## 4. The user channel

The owner's words reach the run as data, verbatim (`instruction-bound`: no helper reads a turn): the questions file
`gate` takes (the session's questions and the chat rulings that never became ledger lines), and the answers file
`record-answer` takes (each answer in his words, a waiver or a reopening carried into its records event, the next
slice when the record leaves it open). `station.feature` carries his name for the doc only when none derives, and
`station.slice` the slice his invocation names as just finished.

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. The helper prints the session's own id inside `invocation` as
`session_id` (`helper-derived` reading of an `instruction-bound` record, the executor's own rollout); the run records
it in its result.

## 6. Run date

The block's date is the input's `station.date` (`YYYY-MM-DD`, `instruction-bound`), or, when the input carries none,
today's UTC date from the run's clock (`helper-derived`). A waiver's or a reopening's `grant_date` is the same date.

## 7. The verifier capability

handoff-v2 verifies nothing and summons no one: the photograph is the script's read of the records component and git
(`helper-derived`), and no station is invoked, so no trace is written (CR-16). The seam v1 carried here is the
**memory pointer**, and on Codex there is none (the E15 lane contract A2 Q3, ruling E15-12): Codex has no auto-memory
for a station to write, so no memory pointer is written, the block in the build doc is the pointer, and the result
says so (`pointer.for_adapter` false, its `note` naming the seam; `helper-derived`, `scripts/tests/test_write.py`).
This adapter carries no pointer helper (`tests/test_no_pointer.py`), and `report` refuses a pointer receipt for a
Codex run.

## 8. Delivery

Not measured by the builder. The delivery probe for this core is under `setups/codex/prompts/`; its measurement on
the installed package is the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

`policy.allow_implicit_invocation: false` in `agents/openai.yaml` (owner pick P5; the E9 seam's manual-only sidecar) keeps this station out of automatic invocation; the owner types it by name. `setups/manual-only.sh` checks the control on the installed copy; whether the harness enforces it is measured by the control room's install proofs, and nothing is recorded here yet.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the nine negative installation cases on this core's package, each in its own
throwaway home; the free half always runs, the live half is behind `--live`. No row has been observed for this core
by its builder.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh` (the checks live
in `setups/verify-package.py`) diffs the installed copy against this checkout, compares the `SKILL.md` frontmatter
block byte for byte, checks that every runtime reference resolves inside the installed root through no symlink,
walks the installed tree for symlinks, and compares `scripts/handoff.py skill-identity`'s `content_sha256` from the
installed copy and the checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of
it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Read the doc by vertical-v2's line rules and stop before any write on a line they refuse | `helper-derived` | `select`; `scripts/tests/test_line_rules.py` |
| Photograph the cards, the open set, the branch and the tree from the record, never from the answer | `helper-derived` | `photograph`, `record-answer`; `scripts/tests/test_photograph.py`, `test_record_answer.py` |
| End a run with any question unanswered with nothing written | `helper-derived` | `record-answer`; `scripts/tests/test_record_answer.py` |
| Write only the sanctioned set, additive, with hashes before and after | `helper-derived` | `write`; `scripts/tests/test_write.py` |
| Write no memory pointer, and say so in the result | `helper-derived` | `write`; `scripts/tests/test_write.py`, `tests/test_no_pointer.py` |
| Put every question to the owner in one batch and never answer one | `instruction-bound` | `SKILL.md` step 3 |
| Make the checkpoint commit when the tree is dirty, local only | `instruction-bound` | `SKILL.md` step 5; `write` records the commit it finds |

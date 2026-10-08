# Adapter profile: vertical-v2 on Codex CLI

The vertical-v2 adapter for Codex CLI (E15 slice 1; the E9 seam's profile, twelve sections in order,
precon-v2's adapters as the pattern). Read this after `../README.md` and before running `check-input`.
Labels follow E9-11 (`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record
is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation`
object into the input whole, typing none of its fields. `measurement` is copied nowhere: the input schema
closes `invocation` with `additionalProperties: false`, so a measurement key placed there is refused
(`tests/test_invocation.py`, `SchemaCompositionTest`).

## 1. Identity

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`); it also chooses the local
row (`references/vertical-contract.md` section 3.2). The version, the entry and the sandbox are
measurement only, read by the helper (`_common.py`, byte for byte precon-v2's). No install of this core
has been measured by its builder; the control room's install proofs are the record.

## 2. Model and floor

`invocation` carries no model. The local calls carry `floor: opus` (v1's floor, passed, never assumed)
and, on `claude-session`, `session_model` from `station.session_model` (`instruction-bound`: the id the
session's system prompt names); readers refuses a session below the floor as `floor-refused`, and
`record-local` then stops the run with no verdict. The outside rows carry no floor; a model id the owner
typed against a row he named rides as that request's `model`.

## 3. Run id and directory

`run_id` and `run_dir` are top-level input fields the executor writes (`instruction-bound`: a fresh id,
an absolute directory outside the workspace). `check-input` refuses a run directory inside the workspace
and one that already holds a run (`references/back-loop.md` section 3).

## 4. The user channel

The owner's words reach the run as data, verbatim: `station.owner_words` (a collapsed gate, a
committed-state-only order, a base he named) in the input, and his answer to the ask (the rows his words
name and the words) through `ask --answer` (`instruction-bound`: no helper reads a turn). The answer
is the one source of an outside request's `authorized` flag, for this run only.

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What this station records about the session is
the executor's own thread: the rollout named by `CODEX_THREAD_ID` under the sessions root of the home the helper is installed in (E9-40); the helper prints it inside `invocation` as `session_id`.

## 6. Run date

The verdict doc's date is the input's `station.date` (`YYYY-MM-DD`, `instruction-bound`), or, when the
input carries none, today's UTC date from the run's clock (`helper-derived`).

## 7. The verifier capability

The local lenses go through `claude-opus-cli`, readers' portable Claude row that any shell can dispatch where the `claude` binary is on `PATH` (E14 A12), one call per lens, `floor: opus`, with the profile the row offers: `repo` (the row offers no tool-running profile; item 4(c) is carried to a later step by the owner's ruling, E15 lane contract A3), so each lens reads the code and runs no check, and the ask, the request's route, each local mandate (which promises no test run, C1A-9) and the verdict's Method line say so (ruling E15-12, reading CR-10). `claude-session` is a host row that needs Claude Code's Agent tool, which a Codex session has not, so it is not offered here. The outside rows the owner named are `repo` calls on their own fresh copy of the reviewed commit or `packet-only` calls
on its staged files, each with `authorized` from his answer in this run.

## 8. Delivery

Not measured by the builder. The delivery probe for this core is `setups/codex/prompts/`; its measurement on the
installed package is the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

None (owner pick P5): this station keeps its phrases and commands, so `SKILL.md` carries no
`disable-model-invocation` and `agents/openai.yaml` no invocation policy.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the nine negative installation cases on this core's package, each
in its own throwaway home; the free half always runs, the live half is behind `--live`. No row has been
observed for this core by its builder.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference resolves
inside the installed root through no symlink, walks the installed tree for symlinks, and compares
`scripts/vertical.py skill-identity`'s `content_sha256` from the installed copy and the checkout. A
snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Pass the gate only on every slice signed off, cards and lines agreeing | `helper-derived` | `gate`; `scripts/tests/test_gate.py` |
| Keep prior verdicts, the ledger and the builder's notes out of every packet | `helper-derived` | `scope`; `scripts/tests/test_scope.py` |
| Form the local verdict before any outside request exists | `helper-derived` | `request --outside`; `scripts/tests/test_request.py` |
| Authorize an outside reader only on the owner's word in the run | `helper-derived` from the `instruction-bound` answer | `request --outside`; `scripts/tests/test_record.py` |
| Refuse a verified finding at a location that does not exist | `helper-derived` | `record-local`, `record-outside`; `scripts/tests/test_record.py` |
| Write one verdict doc and append on a rerun | `helper-derived` | `verdict`; `scripts/tests/test_verdict.py` |
| Trace every reader summons and refuse a v1 readers root | `helper-derived` | `scripts/back_core/trace.py`; `scripts/tests/test_request.py` |
| Verify every outside finding against the source | `instruction-bound` | `SKILL.md` step 5 |

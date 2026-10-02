# Adapter profile: ship-v2 on Codex CLI

The ship-v2 adapter for Codex CLI (E15 slice 1, the back frame's skeleton; the E9 seam's profile,
twelve sections in order, precon-v2's adapters as the pattern). The core is not built yet: every
phase answers `phase-not-built`. Each section below answers what the back frame fixes; what the
station itself decides is stated by the hand-back that builds it. Labels follow E9-11
(`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation`
object into the input whole, typing none of its fields. `measurement` is copied nowhere: the input
schema closes `invocation` with `additionalProperties: false`, so a measurement key placed there is
refused (`tests/test_invocation.py`, `SchemaCompositionTest`).

## 1. Identity

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`). The version, the
entry and the sandbox are measurement only, read by the helper (`_common.py`, byte for byte
precon-v2's). No install of this core has been measured yet; the control room's install proofs
are the record.

## 2. Model and floor

Does not apply to the input: `invocation` carries no model. Not built yet beyond that.

## 3. Run id and directory

`run_id` and `run_dir` are top-level input fields the executor writes (`instruction-bound`: a fresh
id, an absolute directory outside the workspace). `check-input` refuses a run directory inside the
workspace and one that already holds a run (`references/back-loop.md` sections 2 and 3).

## 4. The user channel

Not built yet: the owner's words this station records are stated by the hand-back that builds it,
as data in the input or a recorded answer (`references/back-loop.md` section 3).

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. The helper prints the session's own id inside
`invocation` as `session_id` (`helper-derived` reading of an `instruction-bound` record).

## 6. Run date

Not built yet: the date this station renders is stated by the hand-back that builds it.

## 7. The verifier capability

Not built yet: what this station summons or visits is stated by the hand-back that builds it; every
visit and summons is a trace line (`references/trace.schema.json`, `scripts/back_core/trace.py`).

## 8. Delivery

Not measured. The delivery probe for this core is under `setups/codex/prompts/`; its measurement
is the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

None (owner pick P5): this station keeps its phrases and commands, so `SKILL.md` carries no `disable-model-invocation` and `agents/openai.yaml` no invocation policy.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the nine negative installation cases on this core's package,
each in its own throwaway home; the free half always runs, the live half is behind `--live`. No row
has been observed for this core yet.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/codex/verify-install.sh`
(the checks live in `setups/verify-package.py`) diffs the installed copy against this checkout,
compares the `SKILL.md` frontmatter block byte for byte, checks that every runtime reference
resolves inside the installed root through no symlink, walks the installed tree for symlinks, and
compares `scripts/ship.py skill-identity`'s `content_sha256` from the installed copy and the
checkout. A snapshot at the moment it runs; equality with this checkout, not correctness of it.

## 12. Capability labels

| Capability | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Answer every phase with `phase-not-built` until it is built | `helper-derived` | `scripts/back_core/backdriver.py`; `scripts/tests/test_backdriver.py` |
| Refuse a v1 station before a visit | `helper-derived` | `scripts/back_core/trace.py`; `scripts/tests/test_trace.py` |

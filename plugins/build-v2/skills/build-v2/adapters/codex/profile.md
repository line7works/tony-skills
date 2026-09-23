# Adapter profile: build-v2 on Codex CLI

The build-v2 adapter for Codex (E13 slice 3; lane contract `docs/plans/2026-09-21-stations-e13.md`
section 11, following the recheck-v2 pilot's Codex seam, E9 lane R, and the sealed bench's SB-2,
SB-8 and SB-12 repairs). Read this after `../README.md` and before step 2 of `../../SKILL.md`.

Every fact below was measured on 2026-09-23 on this machine on **codex-cli 0.155.1** (the `codex`
on PATH is a shell wrapper to the npm package, guide L217), or is cited from the pilot's record with
its date and version (0.154.0). Labels follow E9-11; a claim with no record is not made. The setup
is `../../../../setups/codex/` and its record is that directory's `RESULTS.md`.

**What the executor types and what it never types.** As on Claude Code: `invocation.py`'s
`invocation` object is copied whole into the input and typed by no one, `answer_fields.session_id`
goes into step 5's answer, and `measurement` is copied nowhere (`tests/test_invocation.py`
validates the composed input both ways against the real schema). `--caller NAME` only from a
calling station's payload.

## 1. Identity

`invocation.harness` is `codex-cli`, this adapter's own name (`helper-derived`).
`measurement.harness_version` is `codex --version`'s last token (exit 3 when the binary is absent),
beside the rollout's own `session_meta.cli_version`. `measurement.entry` comes from the helper's
resolved path (`plugin` under `plugins/cache/`, `host skill` under a home's `skills/build-v2/`).
`measurement.sandbox` is the rollout's `turn_context.sandbox_policy` read the pilot's way
(`workspace-write plus the isolated home` when the writable roots cover CODEX_HOME, `, network on`
when the policy says so, and the SB-8 note when a writable rollout was accepted behind the wall).
`measurement.interaction_mode` is `session_meta.originator`: `codex_exec` is headless,
`codex_cli_rs` interactive (unmeasured in any E13 record), anything else exit 3.

## 2. Model and floor

Does not apply to this core's input (no model field; v1 build names no floor).
`measurement.model_id` is `turn_context.model` for the record.

## 3. Run id and directory

Does not apply to the adapter: `run_id` and `run_dir` are top-level input fields the executor
writes (`instruction-bound`), and `check-input` enforces the path rules.

## 4. The user channel

Does not apply: no user-channel field in build-v2's input (`allow_open_blocker` is a boolean the
executor sets on the user's word, `instruction-bound`). No `turns.py` ships.

## 5. `session_wrote_fix`

Does not apply (the recheck pilot's field). The answer's `session_id` is
`answer_fields.session_id`: the executor's own thread, the rollout named by `CODEX_THREAD_ID` under
the sessions root of the home this helper is INSTALLED in (E9-40: the helper's resolved path, never
the environment, selects the home), refused when it sits under `CODEX_HOME` (E9-36: the tool
shells' child home), refused when this process could append to it (E9-37) unless the sealed
bench's three-part wall witness holds (SB-2, SB-12 N4, SB-8), and whose `session_meta.id` must
equal the thread id. `helper-derived`, on a record the harness protects under its own
workspace-write sandbox (the pilot measured the append denied, E9-37) and the wall protects on the
bench (SB-8). A helper outside an install exits 3 unless the fixture flags
(`BUILD_V2_ADAPTER_TEST=1`, `BUILD_V2_ADAPTER_RECORD`) are set, and an installed helper ignores
them (`tests/test_invocation.py`, `InstalledLocatorTest`).

**The session lock (E13 pick P6).** A launch through `setups/codex/launch.sh` runs in its own
per-launch home, `<out-dir>/codex-home`, with the plugin folders COPIED into it, so the helper's
installed home is that per-launch home and the rollout it finds is this launch's own. The design
and its measurements are in `setups/codex/RESULTS.md` section "The session lock".

## 6. Run date

Does not apply (no date field in build-v2's input).

## 7. The verifier capability

Does not apply: build summons no fresh context and the core never launches a harness.

## 8. Delivery

Measured on 0.155.1 (`setups/codex/RESULTS.md`, "Delivery probe"; the session had no credential and
ended 401 before a model turn, so this is what the harness wrote before the model call): the catalog (the `<skills_instructions>` developer message) lists `build-v2:build-v2` with its description and its file under the per-launch home's plugin cache; the
explicit `$build-v2` injected NO body, the only `user` messages being the environment context and the
prompt, so **zero bytes of the body were delivered** and a plugin skill's body reaches the model
only through a file read. The pilot measured the same for the plugin surface on 0.154.0 (and that
the model then reads the file: the pilot's profile section 8). `helper-derived` from the rollout;
not measured in E13: what a model does next (no model turn; contract section 12).

## 9. Sidecars and invocation restrictions

`agents/openai.yaml` carries interface metadata only (`display_name`, `short_description`) and no
`policy`: build-v2 stays implicitly invocable, which is v1 build's own trigger rule (its
description names the requests that select it). The pilot measured that `allow_implicit_invocation:
false` removes a skill from the catalog and does not stop a model that reads the file (the pilot's
profile section 9): catalog filtering is `harness-enforced`, the rest `instruction-bound`.

## 10. Negative tests

`setups/codex/negative-tests.sh` runs the nine cases on this core's package, each in its own
throwaway `CODEX_HOME` with no credential; the free half (`codex plugin marketplace add`,
`codex plugin add`, and the cache) always runs, the session half is behind `--live` and was not
run. `setups/codex/RESULTS.md` section "Negative tests" carries every row.

## 11. Installed-package verification

`helper-derived`, enforced by nothing in the harness: `setups/codex/verify-install.sh` runs
`setups/verify-package.py` over `<CODEX_HOME>/plugins/cache/build-v2-setup/build-v2/<version>/`
(the same six checks as on Claude Code). The measurement is in `setups/codex/RESULTS.md`.

## 12. Capability labels

| Capability the build core needs | Label | The record |
|---|---|---|
| Report the harness (`invocation.harness`) | `helper-derived` | this adapter's name; `codex --version` and `session_meta.cli_version` in measurement |
| Report who asked (`caller`, `mode`) | `instruction-bound` | `--caller` from a station's payload |
| Identify the building session (the answer's `session_id`) | `helper-derived` | E9-40, E9-36, E9-37 / SB-8 locator; `session_meta.id` equals `CODEX_THREAD_ID` |
| Keep one launch's session records from another's | `helper-derived` layout, `harness-enforced` only behind the bench's wall | the per-launch home (P6); Codex's own sandbox refuses no read (measured, RESULTS "The session lock") |
| Deliver the skill body | per the pilot: plugin explicit route injects nothing, the model reads the file | section 8 |
| Keep the core from launching a harness | enforced in code for the core | `build-contract.md` section 17 |

# Adapter profile: ship-v2 on Claude Code

The ship-v2 adapter for Claude Code (E15 slice 2; the E9 seam's profile, twelve sections in order, precon-v2's
adapters as the pattern). Each section answers what this core needs of the harness. Labels follow E9-11
(`harness-enforced`, `helper-derived`, `instruction-bound`); a claim with no record is not made.

**What the executor types and what it never types.** Run `invocation.py` and copy its `invocation`
object into the input whole, typing none of its fields. `measurement` is copied nowhere: the input
schema closes `invocation` with `additionalProperties: false`, so a measurement key placed there is
refused (`tests/test_invocation.py`, `SchemaCompositionTest`).

## 1. Identity

`invocation.harness` is `claude-code`, this adapter's own name (`helper-derived`). The version, the
entry and the sandbox are measurement only, read by the helper (`_common.py`, byte for byte
precon-v2's). The control room's install proofs are the record of an install.

## 2. Model and floor

`invocation` carries no model, and ship-v2 has no model floor of its own. Each station it visits keeps its own (signoff-v2's Opus-class reviewer floor among them), governed by that station's own `SKILL.md`. One reading of the model since E18 slice C: `launch.py` (section 7) launches the signoff visit's fresh session on the model the ship session's own transcript records (the last non-sidechain, non-synthetic assistant record's `message.model`, the value `invocation.py` reports as `measurement.model_id`) and on its last recorded effort, and prints no launch (exit 3) for a transcript with no model or a model below the Opus floor by `_common.floor_for` (`helper-derived`; `tests/test_e18_launch.py`).

## 3. Run id and directory

`run_id` and `run_dir` are top-level input fields the executor writes (`instruction-bound`: a fresh
id, an absolute directory outside the workspace). `check-input` refuses a run directory inside the
workspace and one that already holds a run (`references/back-loop.md` sections 2 and 3).

## 4. The user channel

The owner's words arrive as data, verbatim (`instruction-bound`): in the input (`station.minor_fixes`, `station.extra_laps`) and in a pause's answer file (`pause --answer`, kind `answer`: his words and their effect, `resume`, `waive` or `reopen`). The script records them and never stands in for them; a waiver or reopening is a records event carrying them (`references/ship-contract.md` sections 3.7 and 6).

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. The helper prints the session's own id inside
`invocation` as `session_id` (`helper-derived` reading of an `instruction-bound` record).

## 6. Run date

A grant's `grant_date` is the run's UTC date from its clock (`helper-derived`); the stations keep their own dates.

## 7. The verifier capability

ship-v2 summons no reader; it visits three stations, each reached as a v2 sibling and read through its own CLI before the visit, every visit and refusal a trace line (`references/trace.schema.json`, `scripts/back_core/trace.py`; `references/ship-contract.md` section 3.4). **The Stop-hook check** (ruling E15-12, v1's step 0): `hook.py` reads this session's own transcript, found as `invocation.py` finds it (CLAUDE_CODE_SESSION_ID, bound to the session's records, ruling E9-28), for the harness's own records that this run's goal is set, in this session and never in a sidechain or a record carrying a `message` (a tool result, an assistant record or a typed prompt never counts: slice 2 check 1's C2-2), in either of two shapes. (1) The goal command pair, the shape the control room measured on a live `/goal`-armed session (that version writes no record carrying the old confirmation phrase): two `system` records of subtype `local_command`, (a) the command, its content opening `<command-name>/goal</command-name>` with the goal text in `<command-args>`, then (b) its output, with a `commandRun` field, its content opening `<local-command-stdout>Goal set: ` and the same goal text; armed when the LAST such pair's goal text opens `/ship-v2` and names this run's slice (`hook.py --slice <slice>`), no later `/goal` command replaces it, and the pair comes after the last prompt the owner typed that invokes `/ship-v2` or that prompt is itself a `/goal` one (the E15 lane contract A28 (2): a plain `/ship-v2` prompt after the pair is a new run whose goal was never set, and reads not armed). (2) The confirmation phrase, for older harness versions: a `system` record whose own content opens with the Stop hook's confirmation, after the last prompt the owner typed that invokes `/ship-v2`, when that prompt is a `/goal` one whose goal names `/ship-v2` and this run's slice (A28 (2)), with no later `/goal` command record. It prints the reading (`references/answer.schema.json`, kind `hook`): armed, with the record or records that showed it, or not armed. Label: `helper-derived`, a reading of harness records by their type, subtype, place and content, measured on one live session for shape (1) and taken from the fixture for shape (2); the harness enforces nothing of it, and the run proceeds identically either way. `ship.py hook --reading FILE` takes it whole.

**The signoff visit's fresh session** (E18 slice C; `references/ship-contract.md` sections 3.4 and 11). `visit --station signoff-v2` on this harness records a fresh session id, stages the child session's brief under the ship run's directory and prints a `launch_step` naming `launch.py`. Given the run directory, `launch.py` finds the ship session's own transcript from the input's `invocation.session_id`, the way `invocation.py` finds one (ruling E9-28), and prints `launch`: the argv `claude -p --model <model id> [--effort <effort>] --permission-mode auto --session-id <id> --settings {"autoMemoryEnabled":false} --output-format json <prompt>`, a list run with no shell (the settings element exactly that object, with no shell quotes in it; `--effort` left out when the transcript records none or a value outside `low`, `medium`, `high`, `xhigh`, `max`; never `bypassPermissions`, `--dangerously-skip-permissions` or `--bare`), the working directory (the workspace), the recorded session id and the file under the ship run's directory that receives the child's standard output. The ship session runs it in the background and waits; the helper itself launches nothing. After the child ends, `launch.py --check` reads the child's transcript (the recorded id's record, found the same way and bound to the workspace as its `cwd`) and prints the reading `visit --result --reading FILE` takes: it holds only when that record exists and its first prompt is exactly the launch's prompt. Label: `helper-derived`, a reading of harness records; the core holds the reading and the reviewing session the visit's own `input.json` records against the recorded id, and never reads a transcript itself (`tests/test_e18_launch.py`; `scripts/tests/test_e18_fresh_signoff.py`).

## 8. Delivery

Not measured. The delivery probe for this core is under `setups/claude-code/prompts/`; its measurement
is the control room's proof at the hand-back.

## 9. Sidecars and invocation restrictions

None (owner pick P5): this station keeps its phrases and commands, so `SKILL.md` carries no `disable-model-invocation` and `agents/openai.yaml` no invocation policy.

## 10. Negative tests

`setups/claude-code/negative-tests.sh` runs the nine negative installation cases on this core's package,
each in its own throwaway home; the free half always runs, the live half is behind `--live`. The control room's
install proofs are the record.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `setups/claude-code/verify-install.sh`
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
| Read whether the Stop hook is armed | `helper-derived` | `hook.py`, this session's transcript; `tests/test_hook.py` |
| Launch the signoff visit in a fresh session, and read that it ran there | `helper-derived` | `launch.py`, the ship session's transcript and the child's; `tests/test_e18_launch.py` |
| Refuse a v1 station before a visit, and a v1 result at its end | `helper-derived` | `scripts/ship_core/stations.py`, `scripts/ship_core/visit.py`; `scripts/tests/test_visit.py` |
| Hold the lap counter, the stops and the pause | `helper-derived` | `scripts/ship_core/`; `scripts/tests/test_laps.py`, `test_stops.py`, `test_pause.py` |

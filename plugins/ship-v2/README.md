# ship-v2

The portable ship core of the skills v2 rebuild (E15), on the E15 back frame: the coordinator that takes one slice
through build-v2, signoff-v2, the fixes and recheck-v2, at most one extra lap, the four stops and the pause, calling
only qualified v2 stations and proving it with a trace. The `-v2` suffix stays while v1 ship is installed, and both
are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 2; the join's proofs added in E15 slice 3, and slice 3's fix
round 1 (the E15 lane contract A30: the save step named before every recheck-v2 visit, recheck-v2's other endings read
as `recheck-stopped`). Counts measured on the fix round's tree, each suite run under `/usr/bin/python3` 3.9.6 and
under `uv run` with `jsonschema==4.25.1`; the two runtimes give the same counts.

| Suite | Tests (both runtimes) |
|---|---|
| `skills/ship-v2/scripts/tests` | 393 (359 from slice 2, 15 in `test_join_proofs.py`, 19 in `test_save_step.py`) |
| `skills/ship-v2/adapters/claude-code/tests` | 45 |
| `skills/ship-v2/adapters/codex/tests` | 24 |
| `skills/ship-v2/scripts/validate-examples.py` | 30 accepted, 33 rejected examples; 0 failures |
| `evals/seeded-cases` | 19 cases: S1 5, S2 3, S3 4, S4 3, T1 4 |

The kill sweep (`test_kill_sweep.py`) is most of the scripts suite's time: about 68 minutes per runtime in all.

## The join's proofs (E15 slice 3)

Each prints one JSON document, exits 0 only when every expectation held, and runs only in a fresh isolated home it
is given (the setups' home guard: never under `~/.claude`, `~/.codex` or `~/.local/share/skills-v2-*`, TMPDIR, TEMP and
TMP held to the same rule, the guard's interpreter started with the three cleared). Tests: `test_join_proofs.py`.

| Proof | What it shows | Measured (slice 3 fix round 1, Claude Code 2.1.292 and codex-cli 0.157.0) |
|---|---|---|
| `setups/ten-stations.sh` | inspect-v2's seven-stations proof widened to the ten v2 stations and records, one marketplace, installed: every `skill-identity` from its installed copy; every copied records client by route 3b; inspect-v2's code book by route 3b; ship-v2's own sibling lookup resolving and identifying build-v2, signoff-v2 and recheck-v2 installed (route 3b, interface 1, no refusal); each station's manual-only controls as installed (handoff-v2 both, vertical-v2 and ship-v2 neither); the negatives (records renamed away, blueprint-v2 renamed away, each of ship-v2's three siblings renamed away) | exit 0 on both harnesses |
| `setups/trace-proof.sh` with `setups/tripwire.py` | the done-when trace (E15-7): every v2 plugin installed with the six v1 back-half plugins beside their v2, each v1 copy a tripwire (its entry leaves a marker when run; an audit hook on `PYTHONPATH` leaves one when a hooked process opens, lists or launches a v1 path), then the end-to-end replay over the installed copies | exit 0 on both harnesses: 18 trace lines, all build-v2, signoff-v2, recheck-v2 or readers at their installed copies, route 3b, interface 1; no marker; the hook armed in every station process (235 for 102 station commands). The controls `--control read` and `--control run` each leave a marker and report FAIL (exit 1) on both harnesses |
| `evals/replay/replay.py` | the back of the loop end to end on recorded answers (no model call): ship-v2's loop with the real build-v2, signoff-v2 and recheck-v2, handoff-v2's photograph, vertical-v2's gate, packets and summons; a clean path and a path with a finding, a fix and a recheck | exit 0 in both runtimes: clean ends ALL CLEAR with recheck not run, Laps 0; findings ends ALL CLEAR with one lap, the executor having taken the save step as `fix` printed it (a local commit of exactly signoff-v2's verdict mirror); handoff-v2's cards and open set equal the records'; every packet cold |

The installers, `verify-install.sh` and `negative-tests.sh` of this core, on both harnesses: install 0, verify 0 (no
finding, 73 references checked, identity equal), the nine negative cases all ran (exit 0). Measured again in slice 3's
fix round 1: install 0 and verify 0 (76 references) on both harnesses; the negative cases were not rerun (no setup
file changed).

## Layout

```text
.claude-plugin/plugin.json          name and version
skills/ship-v2/SKILL.md             the portable procedure, v1's steps 0 to 7, the four stops and the pause
skills/ship-v2/agents/openai.yaml   the Codex sidecar
skills/ship-v2/references/          ship-contract.md (this core's contract), back-loop.md and back-files.txt (the
                                    back frame), the input, answer, result and trace schemas, examples/
skills/ship-v2/scripts/             ship.py (the phase driver), ship_core/ (this core's phases, the station
                                    identity and result checks, its copies of vertical-v2's line rules and second
                                    reading), vendor/ (vertical-v2's vendored CommonMark reader, byte for byte),
                                    back_core/ and station_core/ (the frame), tests/, validate-examples.py,
                                    validate-result.py, validate-trace.py
skills/ship-v2/adapters/            Claude Code and Codex profiles and helpers (invocation.py; hook.py, the Stop-hook
                                    reading)
setups/                             install, verify, negative tests, launch, per harness; ten-stations.sh,
                                    trace-proof.sh and tripwire.py (the join's proofs)
evals/seeded-cases/                 families S1 to S4 and T1, observe.py, lane_observe.py
evals/replay/                       the end-to-end replay and its fixture (fixtures/turnstile/)
```

## Running it

```sh
cd skills/ship-v2/scripts
uv run ship.py --help
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
```

`jsonschema==4.25.1` is the one dependency, supplied by `uv run` (PEP 723); `--help` works without it. The doc
reading's CommonMark reader (`markdown-it-py` 3.0.0 and `mdurl` 0.1.2, MIT) is vendored under `scripts/vendor/`,
vertical-v2's copy byte for byte: nothing is installed and nothing is fetched. Under plain `/usr/bin/python3` the
suites that drive the CLI skip and say so. The records component (`plugins/records`) and the three stations it visits
(`build-v2`, `signoff-v2`, `recheck-v2`) must sit beside this plugin or be installed beside it; the suites that drive
whole loops run against a copy of this plugin beside stand-in stations and skip when the real ones are not beside it.

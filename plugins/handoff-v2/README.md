# handoff-v2

The portable handoff core of the skills v2 rebuild (E15), on the E15 back frame: the end-of-slice photograph rebuilt
from the records component and git, the question gate, the owner's waivers and reopenings as records events, one
additive block in the build doc, the next move resolved from the record, and the kickoff line for the fresh session.
Strictly user-invoked. The `-v2` suffix stays while v1 handoff is installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 1, hand-back 2. Counts measured on the E15 slice 3 tree, each
suite run under `/usr/bin/python3` 3.9.6 and under `uv run` with `jsonschema==4.25.1`; the two runtimes give the same
counts.

| Suite | Tests (both runtimes) |
|---|---|
| `skills/handoff-v2/scripts/tests` | 403 |
| `skills/handoff-v2/adapters/claude-code/tests` | 27 |
| `skills/handoff-v2/adapters/codex/tests` | 23 |
| `skills/handoff-v2/scripts/validate-examples.py` | 32 accepted, 37 rejected examples; 0 failures |
| `evals/seeded-cases` | 20 cases: H1 4, H2 4, H3 4, H4 4, T1 4 |

## The join's proofs (E15 slice 3)

Measured on Claude Code 2.1.291 and codex-cli 0.157.0, each in a fresh isolated home:

- This core's `install.sh`, `verify-install.sh` and `negative-tests.sh` on both harnesses: install 0, verify 0 (no
  finding, 59 references checked, the installed identity equal to the checkout's), the nine negative cases all ran
  (exit 0).
- Manual-only (owner pick P5): `setups/manual-only.sh` exit 0 on both harnesses: the installed core and the probe
  each carry `disable-model-invocation: true` and `allow_implicit_invocation: false`, and both prompts of the live
  measurement exist. The live measurement (a words prompt and an explicit prompt in a signed-in session) was not run
  in slice 3: an isolated Claude Code config has no sign-in, and a Codex session needs the credential copied from
  `~/.codex`, which no builder opens. ship-v2's `setups/ten-stations.sh` reads the same two controls on this core's
  installed copy beside the other nine stations (both present), and on vertical-v2 and ship-v2 (neither).
- ship-v2's `evals/replay/replay.py`: after a real ship loop on both paths, the photograph's cards and open set are the
  records component's `state`, its branch and tree are git's, the block carries those cards, and the loop complete
  gives no kickoff line.

## Layout

```text
.claude-plugin/plugin.json          name and version
skills/handoff-v2/SKILL.md          the portable procedure, v1's steps 1 to 8
skills/handoff-v2/agents/openai.yaml   the Codex sidecar (manual-only, owner pick P5)
skills/handoff-v2/references/       handoff-contract.md (this core's contract), back-loop.md and back-files.txt
                                    (the back frame), the input, answer, result and trace schemas, examples/
skills/handoff-v2/scripts/          handoff.py (the phase driver), handoff_core/ (this core's phases, its copies of
                                    vertical-v2's line rules and second reading), vendor/ (vertical-v2's
                                    vendored CommonMark reader, byte for byte), back_core/ and
                                    station_core/ (the frame), tests/,
                                    validate-examples.py, validate-result.py, validate-trace.py
skills/handoff-v2/adapters/         Claude Code (with pointer.py, the memory pointer) and Codex profiles and helpers
setups/                             install, verify, negative tests, launch, manual-only probe, per harness
evals/seeded-cases/                 families H1 to H4 and T1, observe.py, lane_observe.py
```

## Running it

```sh
cd skills/handoff-v2/scripts
uv run handoff.py --help
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s tests -t tests
uv run validate-examples.py
```

`jsonschema==4.25.1` is the one dependency, supplied by `uv run` (PEP 723); `--help` works without it. The
second reading's CommonMark reader (`markdown-it-py` 3.0.0 and `mdurl` 0.1.2, MIT) is vendored under
`scripts/vendor/`, vertical-v2's copy byte for byte: nothing is installed and nothing is fetched. Under plain
`/usr/bin/python3` the suites that drive the CLI skip and say so. The records component (`plugins/records`) must sit
beside this plugin or be installed beside it.

# ship-v2

The portable ship core of the skills v2 rebuild (E15), on the E15 back frame: the coordinator that takes one slice
through build-v2, signoff-v2, the fixes and recheck-v2, at most one extra lap, the four stops and the pause, calling
only qualified v2 stations and proving it with a trace. The `-v2` suffix stays while v1 ship is installed, and both
are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 2. The measured counts are the control room's, filled at the
step's close.

| Suite | Tests |
|---|---|
| `skills/ship-v2/scripts/tests` | (to be measured) |
| `skills/ship-v2/adapters/claude-code/tests` | (to be measured) |
| `skills/ship-v2/adapters/codex/tests` | (to be measured) |
| `skills/ship-v2/scripts/validate-examples.py` | (to be measured) |
| `evals/seeded-cases` (families S1 to S4 and T1) | (to be measured) |

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
setups/                             install, verify, negative tests, launch, per harness
evals/seeded-cases/                 families S1 to S4 and T1, observe.py, lane_observe.py
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

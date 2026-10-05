# handoff-v2

The portable handoff core of the skills v2 rebuild (E15), on the E15 back frame: the end-of-slice photograph rebuilt
from the records component and git, the question gate, the owner's waivers and reopenings as records events, one
additive block in the build doc, the next move resolved from the record, and the kickoff line for the fresh session.
Strictly user-invoked. The `-v2` suffix stays while v1 handoff is installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 1, hand-back 2. The measured counts are the control room's,
filled at the step's close.

| Suite | Tests |
|---|---|
| `skills/handoff-v2/scripts/tests` | (to be measured) |
| `skills/handoff-v2/adapters/claude-code/tests` | (to be measured) |
| `skills/handoff-v2/adapters/codex/tests` | (to be measured) |
| `skills/handoff-v2/scripts/validate-examples.py` | (to be measured) |
| `evals/seeded-cases` (families H1 to H4 and T1) | (to be measured) |

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

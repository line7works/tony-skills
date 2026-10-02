# vertical-v2

The whole-build adversarial review on the skills v2 foundation: after every slice of a build doc is
signed off, fresh local reviewers read the entire vertical against its base, outside reviewers join on
the owner's word in the run, every outside finding is verified against the source, and one verdict doc
is written. The portable vertical core of the E15 step; the `-v2` suffix stays while v1 vertical is
installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 1 (hand-back 1) on the E15 back frame
(`skills/vertical-v2/references/back-loop.md`, `skills/vertical-v2/references/back-files.txt`). The
measured counts below are the control room's, filled at the step's close.

| Suite | Tests |
|---|---|
| `skills/vertical-v2/scripts/tests` | (to be measured) |
| `skills/vertical-v2/adapters/claude-code/tests` | (to be measured) |
| `skills/vertical-v2/adapters/codex/tests` | (to be measured) |
| `skills/vertical-v2/scripts/validate-examples.py` | (to be measured) |
| seeded cases (`evals/seeded-cases/`) | (to be measured) |

## Layout

```text
.claude-plugin/plugin.json        name and version
skills/vertical-v2/SKILL.md       the portable procedure
skills/vertical-v2/agents/        the Codex sidecar (no invocation policy: owner pick P5)
skills/vertical-v2/assets/        v1's outside mandate, byte for byte
skills/vertical-v2/references/    the contract, the back loop, the schemas, the examples, the lens briefs
skills/vertical-v2/scripts/       vertical.py (the driver), vertical_core/, back_core/, station_core/, tests/
skills/vertical-v2/adapters/      Claude Code and Codex
setups/                           install, verify, negative tests, launch, both harnesses
evals/seeded-cases/               families V1 to V5 and T1
```

## Running the tests

```sh
cd skills/vertical-v2/scripts/tests
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s . -t .
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s . -t .
```

The suite builds every fixture into a temporary directory and removes it, needs no network, and reads
the records component and readers' roster beside this core in the checkout (skipped, never passed, in the
installed shape). Under plain `/usr/bin/python3` (no jsonschema) the CLI-driven tests skip.

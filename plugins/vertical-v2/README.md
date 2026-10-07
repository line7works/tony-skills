# vertical-v2

The whole-build adversarial review on the skills v2 foundation: after every slice of a build doc is
signed off, fresh local reviewers read the entire vertical against its base, outside reviewers join on
the owner's word in the run, every outside finding is verified against the source, and one verdict doc
is written. The portable vertical core of the E15 step; the `-v2` suffix stays while v1 vertical is
installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1. Built in E15 slice 1 (hand-back 1) on the E15 back frame
(`skills/vertical-v2/references/back-loop.md`, `skills/vertical-v2/references/back-files.txt`). Since the full
review's fix round (the E15 lane contract A32) every packet and summons copy carries the build doc under review alone
among the plans: every other file under `docs/plans/`, and any other Markdown file the build-doc form reads as a build
doc, is withheld and named. Counts measured on that round's tree, each suite run under `/usr/bin/python3` 3.9.6 and
under `uv run` with `jsonschema==4.25.1`; the two runtimes give the same counts.

| Suite | Tests (both runtimes) |
|---|---|
| `skills/vertical-v2/scripts/tests` | 654 |
| `skills/vertical-v2/adapters/claude-code/tests` | 18 |
| `skills/vertical-v2/adapters/codex/tests` | 19 |
| `skills/vertical-v2/scripts/validate-examples.py` | 27 accepted, 39 rejected examples; 0 failures |
| seeded cases (`evals/seeded-cases/`) | 24 cases: V1 5, V2 5, V3 4, V4 3, V5 3, T1 4 |

## The join's proofs (E15 slice 3)

Measured on Claude Code 2.1.291 and codex-cli 0.157.0, each in a fresh isolated home:

- This core's `install.sh`, `verify-install.sh` and `negative-tests.sh` on both harnesses: install 0, verify 0 (no
  finding, 83 references checked, the installed identity equal to the checkout's), the nine negative cases all ran
  (exit 0).
- ship-v2's `setups/ten-stations.sh`: this core installed beside the other nine v2 stations and records; its
  `skill-identity` answers from its installed copy without the records component, its copied client resolves the
  installed component by route 3b and refuses when it is renamed away; no manual-only control (owner pick P5: the
  summons is kept). Exit 0 on both harnesses.
- ship-v2's `setups/trace-proof.sh`: vertical-v2 installed beside a v1 tripwire, its gate, packets and summons run over
  the installed copies; every one of its trace lines names readers at the installed copy, route 3b, interface 1; no
  v1 file read or run. PASS on both harnesses.
- ship-v2's `evals/replay/replay.py`: after a real ship loop and handoff-v2, the gate passes, every packet and summons
  copy is cold (no prior verdict, no records log, no ledger section or `Status:` line, no line of the review record,
  its file list's hashes held), and no outside request exists before `record-local`.

## Layout

```text
.claude-plugin/plugin.json        name and version
skills/vertical-v2/SKILL.md       the portable procedure
skills/vertical-v2/agents/        the Codex sidecar (no invocation policy: owner pick P5)
skills/vertical-v2/assets/        v1's outside mandate, byte for byte
skills/vertical-v2/references/    the contract, the back loop, the schemas, the examples, the lens briefs
skills/vertical-v2/scripts/       vertical.py (the driver), vertical_core/, back_core/, station_core/, tests/,
                                  vendor/ (the CommonMark reader, pinned by vendor/VENDOR.json)
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

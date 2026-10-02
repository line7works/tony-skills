# ship-v2

The portable ship core of the skills v2 rebuild (E15), on the E15 back frame. The `-v2` suffix stays
while v1 ship is installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1. A skeleton: the back frame this core shares with vertical-v2 and the
other back core is in place (`skills/ship-v2/references/back-loop.md`, `skills/ship-v2/references/back-files.txt`,
the trace, the adapters and the setups), and every phase of `skills/ship-v2/scripts/ship.py` answers
`phase-not-built`. The station itself is built in E15 slice 2. The measured counts are the control room's,
filled at the step's close.

| Suite | Tests |
|---|---|
| `skills/ship-v2/scripts/tests` | (to be measured) |
| `skills/ship-v2/adapters/claude-code/tests` | (to be measured) |
| `skills/ship-v2/adapters/codex/tests` | (to be measured) |

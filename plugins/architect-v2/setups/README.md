# Setups (E14 slice 1, the frame): the install and launch profiles of this core

One directory per harness (Claude Code and Codex; E13's pick P3 stands). A setup is everything
needed to install this core into an isolated copy of that harness's configuration, verify the
installed package, run the negative installation tests, and launch one headless session. No script
here writes under the live `~/.claude` or `~/.codex` or a `~/.local/share/skills-v2-*` home: every
home is named by its caller (an argument or the per-core variable `<CORE>_CLAUDE_HOME` /
`<CORE>_CODEX_HOME`) and there is no default. Both installers (and `seven-stations.sh`) refuse, with
exit 2 and before anything is created, a home that is or sits under `~/.claude`, `~/.codex` or a
`~/.local/share/skills-v2-*` home (the pilot's, the locked one), whichever harness they serve; the
home is compared as given and resolved (symlinks and `..`), and so is each forbidden home. The same
guard, before the first write, holds every other path a caller names here: both launchers' out-dir
and home (Claude Code's installed home, Codex's condition home and each `--writable` root),
`negative-cases.py`'s `--out` (both `negative-tests.sh`), and, beside the setups, the seeded cases'
`--out` (`evals/seeded-cases/observe.py` and every family's `build.py`) and inspect-v2's
`evals/replay/replay.py --keep`. `manual-only.sh` writes nothing before its `install.sh`, whose
guard stops it.

Every script is build-v2's own (E13 slice 3), copied with the core as the variable, and is
byte-identical in the four front cores; each reads the core it serves from its own location. Two
changes from build-v2's copies are parameterisations: the plugin list the installers bring along
is a `case` on the core (inspect-v2 brings `records`, `readers` and `blueprint-v2`, its code book;
precon-v2 and architect-v2 bring `readers`; blueprint-v2 brings nothing), and the core's driver
script is derived from its name (`<station>.py`) in `verify-package.py` and `negative-cases.py`.
The third is the home guard above (E14 slice 3c, fixes 3 and 3-2; TMPDIR since the E14 punch list),
which build-v2's and signoff-v2's copies carry too since the E14 punch list: the launchers are
byte-identical in the six cores, and the installers, `negative-cases.py` and `three-stations.sh` carry
the same guard block.

| File | Does |
|---|---|
| `claude-code/install.sh` | builds `<home>/config` (`CLAUDE_CONFIG_DIR`) and `<home>/marketplace` (symlinks to the worktree's plugin folders), installs each plugin, writes `<home>/install.json` |
| `claude-code/verify-install.sh` | the installed-package verification, through `../verify-package.py` |
| `claude-code/negative-tests.sh` | the nine negative installation cases, through `../negative-cases.py` |
| `claude-code/launch.sh <prompt> <workspace> <out>` | one headless session in the isolated config |
| `codex/install.sh` | builds the Codex home (`CODEX_HOME`), adds the marketplace and each plugin; `--credential` copies the sign-in at mode 600 |
| `codex/verify-install.sh`, `codex/negative-tests.sh`, `codex/launch.sh` | as for Claude Code |
| `verify-package.py` | the six installed-package checks both harnesses run |
| `negative-cases.py` | the nine negative cases for either harness |
| `*/prompts/` | the delivery probe (names the core) and, for Codex, the lock probe |

`plugins/inspect-v2/setups/seven-stations.sh` is built (E14 slice 3c): on either harness it installs
eight plugins (the seven v2 stations and one records component) from one marketplace into one fresh
home, and each station resolves the component by route 3b, as inspect-v2 resolves blueprint-v2's
installed `SKILL.md`; its negatives hide the records folder (every station refuses naming route 3b's
directory, the front cores through their installed client) and then blueprint-v2 (inspect-v2's code
book lookup refuses the same way). No measured result is recorded here yet: the control room runs the install proofs at
the hand-back and records them.

`setups/manual-only.sh` exists in precon-v2, architect-v2 and inspect-v2, the three strictly
user-invoked stations (not blueprint-v2): it installs the core with its own `install.sh` and
`verify-install.sh`, installs the manual-only probe (`setups/_fixtures/manual-only-probe`) beside it
from a second marketplace in the same home, and checks from the installed copies that the probe and
the core both carry `disable-model-invocation: true` and `allow_implicit_invocation: false`. It sends
no prompt and launches no session; the live measurement is the control room's.

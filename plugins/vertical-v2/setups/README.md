# Setups (E15 slice 1, the back frame): the install and launch profiles of this core

One directory per harness (Claude Code and Codex). A setup is everything needed to install this
core into an isolated copy of that harness's configuration, verify the installed package, run the
negative installation tests, and launch one headless session. No script here writes under the live
`~/.claude` or `~/.codex` or a `~/.local/share/skills-v2-*` home: every home is named by its caller
(an argument or the per-core variable `<CORE>_CLAUDE_HOME` / `<CORE>_CODEX_HOME`) and there is no
default. Both installers refuse, with exit 2 and before anything is created, a home that is or sits
under `~/.claude`, `~/.codex` or a `~/.local/share/skills-v2-*` home, as given and resolved, and hold
TMPDIR, TEMP and TMP to the same rule; so do both launchers (the out-dir and every home they are
given), `negative-cases.py` behind both `negative-tests.sh`, and the seeded cases' `--out`. Every
guarded Python file is started through `safe-python.sh`, which starts the interpreter with TMPDIR,
TEMP and TMP cleared and hands their values to the script's guard.

Every script here except this README is precon-v2's own, copied byte for byte (ruling E15-3,
`skills/<core>/references/back-files.txt`); each reads the core it serves from its own location. The
installers' plugin list is a `case` on the core in those copies, and the three back cores fall to its
default branch: the core and `records`. A core that also needs `readers` beside it in an isolated
home (vertical-v2's ask and requests read readers' roster) is installed beside it by the control
room's proofs; the copied installers are not edited for it (ruling E15-2 freezes their source).

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
| `safe-python.sh <script> [args]` | starts `/usr/bin/python3` on a guarded script with TMPDIR, TEMP and TMP cleared and their values handed to the script |
| `*/prompts/` | the delivery probe (names the core) and, for Codex, the lock probe |

`handoff-v2` alone also carries `manual-only.sh` and `_fixtures/manual-only-probe/` (owner pick P5):
its `SKILL.md` carries `disable-model-invocation: true` and its Codex sidecar
`allow_implicit_invocation: false`, and `manual-only.sh` checks both controls on the installed copies.
No measured result is recorded here: the control room runs the install proofs and records them.

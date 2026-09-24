# Setups (E13 slice 3): the install and launch profiles of this core

One directory per harness the E13 lane contract scopes (pick P3: Claude Code and Codex). A setup
is everything needed to install this core into an isolated copy of that harness's configuration,
verify the installed package, run the negative installation tests, and launch one headless
session. Nothing here touches the live `~/.claude` or `~/.codex`, nor the recheck-v2 pilot's
`~/.local/share/skills-v2-pilot/`: every home is named by its caller (an argument or a per-core
environment variable) and there is no default. The scripts are byte-identical in `build-v2` and
`signoff-v2`; each reads the core it serves from its own location.

| File | Does | Adapted from (the pilot's `plugins/recheck-v2/setups/`) | What changed |
|---|---|---|---|
| `claude-code/install.sh` | builds `<home>/config` (`CLAUDE_CONFIG_DIR`) and `<home>/marketplace`, this setup's own marketplace of symlinks to the worktree's plugin folders (the core, `records`, and `readers` for signoff-v2), uninstalls, clears the cache and installs each; writes `<home>/install.json` | `claude-code/install.sh` | the home is `--home DIR` or `<CORE>_CLAUDE_HOME` with no default; the core and its dependencies come from this setup's marketplace, not the repo's `marketplace.json` (which the control room owns and which does not list the v2 cores); no probes, no readers checkout, no launch settings file |
| `claude-code/verify-install.sh` | the installed-package verification, through `../verify-package.py` | `claude-code/verify-install.sh` | the checks moved to one Python file shared with Codex; frontmatter compared as a whole block, byte for byte, standard library only |
| `claude-code/negative-tests.sh` | the negative installation tests, through `../negative-cases.py` | `claude-code/negative-tests.sh` | the core itself is mutated (not the probes); the free half always runs and the live half is behind `--live` |
| `claude-code/launch.sh <prompt> <workspace> <out>` | one headless session with `CLAUDE_CONFIG_DIR` the isolated config; copies the trace, the transcript and `launch.json` | `claude-code/launch.sh` | runs in the ISOLATED config directory, never the machine's own (the pilot used the machine's config with `--plugin-dir` because the isolated one has no sign-in; this slice may not touch the live `~/.claude`) |
| `codex/install.sh` | builds the Codex home (`CODEX_HOME`): the pilot's config lines, the child home, `marketplace/` of symlinks (the core and `records`), `codex plugin marketplace add` and `codex plugin add`; `--credential` copies `~/.codex/auth.json` at mode 600, the pilot's own step | `codex/install.sh` | the home is `--home DIR` or `<CORE>_CODEX_HOME`, no default; the credential copy is opt-in (installs and verification need none); no probe homes, no host-only surface |
| `codex/verify-install.sh` | the installed-package verification, through `../verify-package.py` | `codex/verify-install.sh` | as for Claude Code |
| `codex/negative-tests.sh` | the negative installation tests, through `../negative-cases.py` | `codex/negative-tests.sh`, `codex/prepare-negative.py` | the pilot's cases all launched a session; here the free half (install commands and the cache) always runs and the session half is behind `--live` |
| `codex/launch.sh <prompt> <workspace> <out>` | one headless session in its OWN per-launch home `<out>/codex-home` (the session lock, E13 pick P6), Codex's own sandbox on | `codex/launch.sh` | the session-lock block (byte-identical in the pilot's launcher, held equal by `plugins/recheck-v2/evals/runner/tests/test_e13_session_lock.py`); Codex's own workspace-write sandbox kept, with TMPDIR and `/tmp` not writable, where the pilot's current launcher runs behind the sealed bench's wall with it off; network off for both cores (signoff-v2's nested `codex exec` reviewer was removed by Astra's F6) |
| `verify-package.py` | the six installed-package checks both harnesses run | the Python inside both pilot `verify-install.sh` scripts | one file; `skill-identity` of this core compared by `content_sha256` |
| `negative-cases.py` | the nine negative cases for either harness | both pilot `negative-tests.sh` and `prepare-negative.py` | one file, `--harness` picks the commands |
| `*/prompts/` | the delivery probe (names the core explicitly) and, for Codex, the lock probe | the pilot's `delivery*` prompts | the probe names the core, not a sentinel fixture: what the harness delivered is compared with the core's own `SKILL.md` |
| `three-stations.sh` | lives in `plugins/build-v2/setups/` only; its record is `plugins/build-v2/setups/RESULTS.md`, section "Three stations, one component" | | |

`_fixtures/` is absent: the delivery probe here names the core itself, so the pilot's sentinel
fixtures are not needed. Every measured fact is in `claude-code/RESULTS.md` and `codex/RESULTS.md`;
"Three stations, one component", the installed-shape lookup of all three stations, is recorded in
`plugins/build-v2/setups/RESULTS.md`.

Credentials: Claude Code keeps its sign-in in the macOS Keychain and an isolated config directory
has none, so nothing is read or copied. Codex's `auth.json` is copied only by `install.sh
--credential`, byte for byte at mode 600, and linked (never copied again) into the child home and
every per-launch home; no script reads it, prints it, logs it or writes it into this repository.

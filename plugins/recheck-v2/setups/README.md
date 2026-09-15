# Setups (E9): the reproducible launch and install profiles

One directory per harness. A setup is everything needed to install the pilot into an isolated
copy of that harness's configuration on this machine, launch a headless session that runs the
skill, verify the installed package, and run the negative tests; it is what E10's trials
launch. Nothing here touches the live `~/.claude`, `~/.codex`, or `~/.config/opencode`.

Every setup provides, under `setups/<harness>/`:

| File | Does |
|---|---|
| `install.sh` | creates the isolated home under `~/.local/share/skills-v2-pilot/<harness>/`, installs the pilot plugin and the two shared probes from this checkout, records versions in `RESULTS.md` |
| `launch.sh <prompt-file> <workspace> <out-dir>` | one headless session of the harness in the isolated home, the prompt from the file, the harness's own record of the session (transcript, rollout, session store) and its final output copied to `<out-dir>` |
| `verify-install.sh` | the installed-package verification of amendment A7b: diff installed against canonical, the frontmatter survived, no reference resolves outside the plugin root; prints one JSON object |
| `negative-tests.sh` | the negative installation tests of amendment A7b, one JSON line per test with the observed behavior |
| `RESULTS.md` | the measured facts, dated: versions, the installation surface and rendering path, the delivery probe's outcome, the manual-only probe's outcome, the negative tests table, the installed-package diff |

Isolation is by environment variable, set inside the scripts and never in a shell profile:
Claude Code `CLAUDE_CONFIG_DIR`; Codex `CODEX_HOME`; OpenCode `XDG_CONFIG_HOME` and
`XDG_DATA_HOME` with the binary installed under the setup's own npm prefix. Credentials: a setup
reads them from the live home or the environment at install time as its `RESULTS.md` records
(Codex copies `auth.json` mode 600; OpenCode reads `OPENROUTER_API_KEY` from the environment;
Claude Code uses the account already signed in on this machine), never copies one into this
repository, a profile, a result, or a log, and never prints one. `_fixtures/` holds the two
shared probes.

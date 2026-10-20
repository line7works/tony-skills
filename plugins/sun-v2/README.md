# sun-v2

v1's `sunrise` and `sunset` skills rebuilt (E16) as one deterministic tool and two skills. The tool,
`lifecycle/scripts/sun`, is the lifecycle frame: it runs a sunrise, a sunset or a restore as a run of explicit
operations, with a look that only reads, a preview, the owner's go on that preview, a journal, resume after a kill,
a credential guard and the providers' declared commands. The skills `sunrise-v2` and `sunset-v2` are the two ways in
(`lifecycle/skills.json`; restore is summoned through `sunset-v2`). The `-v2` suffix stays while v1 `sun` is
installed, and both are renamed at cutover.

## Status

Version 0.1.0, interface version 1 (`.claude-plugin/plugin.json`; `sun skill-identity`). Built in E16
slices 1 to 5: the frame, sunrise's local half, the providers, sunset and restore, and the join of the three lanes
with the seeded families. The two skills' `SKILL.md` files are still slice 1's skeletons, each marked "do not use
this skill yet"; the tool and its rows are the built part.

Counts are measured by script from the control room's counted run of the tree `main` holds once the join's parts
are merged: every module of `lifecycle/scripts/tests` run twice under `/usr/bin/python3` 3.9.6, pinned (`-I`, a
cleared environment) and with the site; the two runtimes give the same counts, every module exit 0.

| Module (`lifecycle/scripts/tests`) | Tests run (both runtimes) | Of them skipped |
|---|---|---|
| `test_cli` | 7 | 0 |
| `test_ev_ord` | 17 | 0 |
| `test_examples` | 4 | 0 |
| `test_g19_machinery` | 33 | 0 |
| `test_g20_machinery` | 15 | 0 |
| `test_g21_machinery` | 15 | 0 |
| `test_g22_machinery` | 18 | 0 |
| `test_g23_machinery` | 45 | 0 |
| `test_g24_machinery` | 13 | 0 |
| `test_g25_machinery` | 18 | 0 |
| `test_handover` | 5 | 0 |
| `test_join_machinery` | 5 | 0 |
| `test_join_sequence` | 1 | 0 |
| `test_keep` | 17 | 0 |
| `test_kill_sweep` | 5 | 0 |
| `test_lane_prov_decls` | 14 | 0 |
| `test_lane_prov_rise` | 16 | 0 |
| `test_lane_prov_set` | 35 | 0 |
| `test_lane_prov_sweep` | 2 | 0 |
| `test_lane_rise` | 41 | 1 |
| `test_lane_rise_sweep` | 1 | 0 |
| `test_lane_set` | 25 | 0 |
| `test_lane_set_codecheck` | 7 | 0 |
| `test_lane_set_g23` | 7 | 0 |
| `test_lane_set_g24` | 4 | 0 |
| `test_lane_set_items` | 10 | 0 |
| `test_lane_set_lib` | 0 | 0 |
| `test_lane_set_sweep` | 3 | 0 |
| `test_log_op` | 67 | 0 |
| `test_no_v1_import` | 3 | 0 |
| `test_restore` | 22 | 0 |
| `test_rows_build` | 20 | 0 |
| `test_run` | 60 | 0 |
| `test_sec10_commit_scan` | 19 | 0 |
| `test_sec3_runner` | 51 | 0 |
| `test_sec4_results` | 18 | 0 |
| `test_sec_forms` | 24 | 0 |
| `test_secrets_end_to_end` | 24 | 0 |
| `test_seeded_cases` | 3 | 0 |
| `test_seeded_lanes` | 6 | 0 |
| `test_start` | 19 | 0 |
| `test_withheld_read` | 22 | 0 |
| 42 modules | 741 | 1 |

Seeded cases (`evals/seeded-cases`, each family's `build.py --list`): 59 cases in 11 families: L0 5, L1 5, L2 6, L3 4, L4 11, L5 4, L6 5, L7 5, L8 5, L9 5, T1 4.

## Install

`setups/` installs this plugin alone into an isolated copy of either harness's configuration and verifies the
installed package. Every home is named by its caller (`--home DIR`, or `SUN_V2_CLAUDE_HOME` / `SUN_V2_CODEX_HOME`)
and there is no default. Both installers refuse with exit 2, before anything is created, a home that is or sits
under `~/.claude`, `~/.codex` or a `~/.local/share/skills-v2-*` home, as given and resolved (`~` read as `$HOME`),
and hold TMPDIR, TEMP and TMP to the same rule: the home guard of ship-v2's installers, byte for byte. No sign-in
is read or copied.

| File | Does |
|---|---|
| `setups/claude-code/install.sh --home DIR` | builds `DIR/config` (`CLAUDE_CONFIG_DIR`) and `DIR/marketplace` (a symlink to this plugin's folder), installs `sun-v2`, writes `DIR/install.json` |
| `setups/codex/install.sh --home DIR` | the same with `DIR` as `CODEX_HOME`; reads nothing of `~/.codex` |
| `setups/{claude-code,codex}/verify-install.sh --home DIR` | the installed-package check, through `setups/verify-package.py` |
| `setups/verify-package.py` | one installed copy, named for the plugin's version; both skills' `SKILL.md` present and byte-equal to the checkout's; the installed `sun --help` and `sun skill-identity` run from the cache folder, the help and the content hash equal to the checkout's; no symlink in the installed copy |

Exits: install 0 done, 1 a harness command failed (the record still lands), 2 usage or a refused home, 3 the
harness is missing; verify 0 no finding, 4 a finding, 2 usage.

## Layout

```text
.claude-plugin/plugin.json          name and version
skills/sunrise-v2/SKILL.md          the sunrise skill (a skeleton, see Status)
skills/sunset-v2/SKILL.md           the sunset and restore skill (a skeleton, see Status)
lifecycle/skills.json               the two skills and the kind each summons
lifecycle/scripts/sun               the one start: /bin/sh runs /usr/bin/python3 -I -S on sun.py, a cleared environment
lifecycle/scripts/sun.py            the first code (the withheld read), then sun_core/cli.py
lifecycle/scripts/sun_core/         the frame: rows and lanes, plan, preview and forms, engine, journal, locks, runner,
                                    results, the credential guard
lifecycle/scripts/tests/            the suites above, their fakes and fixtures
lifecycle/rows/{sunrise,sunset,restore}/lane.json   the three lanes' rows
lifecycle/rows/providers/           the provider and command declarations
lifecycle/references/               the schemas and examples/
lifecycle/assets/                   rise.wav and set.wav, the cues
evals/seeded-cases/                 the families above, _lib/caselib.py, observe.py
setups/                             install and verify, per harness, and verify-package.py
```

## Running it

```sh
cd lifecycle/scripts
/bin/sh sun --help
/usr/bin/env -i HOME=<home> PATH=/usr/bin:/bin TMPDIR=<tmp> PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/python3 -I -m unittest discover -v -s tests -p 'test_cli.py'
```

Standard library only, Python 3.9: nothing is installed and nothing is fetched. A family's `build.py --out DIR`
builds its cases and `evals/seeded-cases/observe.py --out DIR --all` drives them on the fakes; the expected outcomes
are kept apart from the plugin.

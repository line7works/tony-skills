# RESULTS: three stations, one records component (E13 slice 3, brief 3.4)

The installed-shape lookup of E12 amendment A6, with all three stations: recheck-v2, build-v2 and
signoff-v2 installed with the records component from ONE marketplace built inside one isolated
home per harness, each station resolving and confirming the one installed component by route 3b
(`<station plugin root>/../../records/<V>/`, `plugins/records/references/interface.md`, "Reaching
the component"). No model and no session: installs and CLI calls only. Measured 2026-09-23, the
worktree `feat/stations-e13` at `f62e4b3` plus this slice's files.

The command, per harness, into a fresh directory under `$TMPDIR`:

```sh
sh plugins/build-v2/setups/three-stations.sh claude-code <fresh home>
sh plugins/build-v2/setups/three-stations.sh codex <fresh home>
```

It builds `<home>/marketplace` (marketplace `three-stations`: symlinks to the worktree's
`recheck-v2`, `build-v2`, `signoff-v2`, `records`), installs all four, and then for each installed
station runs `uv run <installed>/skills/<station>/scripts/<cli> skill-identity` (every one of the
three opens its records client, the lookup and the confirm step, before it answers) with
`RECORDS_ROOT` unset and no `--records-root`, and imports the station's own copied client FROM ITS
INSTALLED LOCATION to print the root it resolved and the interface version it confirmed. Then it
renames the installed `records` folder away, runs each `skill-identity` again, and puts the folder
back.

## Three stations, one component

### Claude Code (2.1.280 (Claude Code))

Installed, one version each: `recheck-v2 0.2.0`, `build-v2 0.1.0`, `signoff-v2 0.1.0`, `records 0.2.0`. Every install step exited 0.

| Station | `skill-identity` exit | Root its installed client resolved | Interface version confirmed | Route 3b |
|---|---|---|---|---|
| `recheck-v2` | 0 | `<home>/config/plugins/cache/three-stations/recheck-v2/0.2.0/../../records/0.2.0` | 2 | yes |
| `build-v2` | 0 | `<home>/config/plugins/cache/three-stations/build-v2/0.1.0/../../records/0.2.0` | 2 | yes |
| `signoff-v2` | 0 | `<home>/config/plugins/cache/three-stations/signoff-v2/0.1.0/../../records/0.2.0` | 2 | yes |

With `records` renamed away (`records.hidden-by-three-stations`):

| Station | Exit | The one line on stderr (home shortened) |
|---|---|---|
| `recheck-v2` | 3 | `missing dependency: records component (looked in: <home>/config/plugins/cache/three-stations/recheck-v2/0.2.0/../records, <home>/config/plugins/cache/three-stations/recheck-v2/0.2.0/../../records (no such directory))` |
| `build-v2` | 3 | `missing dependency: records component (looked in: <home>/config/plugins/cache/three-stations/build-v2/0.1.0/../records, <home>/config/plugins/cache/three-stations/build-v2/0.1.0/../../records (no such directory))` |
| `signoff-v2` | 3 | `missing dependency: records component (looked in: <home>/config/plugins/cache/three-stations/signoff-v2/0.1.0/../records, <home>/config/plugins/cache/three-stations/signoff-v2/0.1.0/../../records (no such directory))` |

Each refusal names route 3b's directory with `(no such directory)`: yes for all three. `ok: true`, no problem recorded.

### Codex (codex-cli 0.155.1)

Installed, one version each: `recheck-v2 0.2.0`, `build-v2 0.1.0`, `signoff-v2 0.1.0`, `records 0.2.0`. Every install step exited 0.

| Station | `skill-identity` exit | Root its installed client resolved | Interface version confirmed | Route 3b |
|---|---|---|---|---|
| `recheck-v2` | 0 | `<home>/plugins/cache/three-stations/recheck-v2/0.2.0/../../records/0.2.0` | 2 | yes |
| `build-v2` | 0 | `<home>/plugins/cache/three-stations/build-v2/0.1.0/../../records/0.2.0` | 2 | yes |
| `signoff-v2` | 0 | `<home>/plugins/cache/three-stations/signoff-v2/0.1.0/../../records/0.2.0` | 2 | yes |

With `records` renamed away (`records.hidden-by-three-stations`):

| Station | Exit | The one line on stderr (home shortened) |
|---|---|---|
| `recheck-v2` | 3 | `missing dependency: records component (looked in: <home>/plugins/cache/three-stations/recheck-v2/0.2.0/../records, <home>/plugins/cache/three-stations/recheck-v2/0.2.0/../../records (no such directory))` |
| `build-v2` | 3 | `missing dependency: records component (looked in: <home>/plugins/cache/three-stations/build-v2/0.1.0/../records, <home>/plugins/cache/three-stations/build-v2/0.1.0/../../records (no such directory))` |
| `signoff-v2` | 3 | `missing dependency: records component (looked in: <home>/plugins/cache/three-stations/signoff-v2/0.1.0/../records, <home>/plugins/cache/three-stations/signoff-v2/0.1.0/../../records (no such directory))` |

Each refusal names route 3b's directory with `(no such directory)`: yes for all three. `ok: true`, no problem recorded.

## The hermetic test beside it

Neither core's client suite had a route 3b test (brief 3.4 asked to check). Each now has
`skills/<core>/scripts/tests/test_installed_shape.py`: it rebuilds `<cache>/<market>/<core>/0.1.0/`
with the core's own `records_client.py` at its installed path and a copy of the records component
at `<cache>/<market>/records/<V>/`, imports the client from there with no argument and no
`RECORDS_ROOT`, and asserts the root is route 3b's folder at interface version 2, and that with the
component gone the refusal is the interface's one line naming route 3b's directory. A copy of the
client with route 3b removed fails it (the builder's scratch, `red/installed-shape-mutation-no-route-3b.txt`).
The pilot's own suite already covers its client.

## What this does and does not prove

It proves that each station's installed COPY, run from the harness's own cache, finds the one
installed component by route 3b and refuses plainly when it is gone, on both harnesses. It does
not prove which copy a SESSION runs. The delivery probe of this slice (`claude-code/RESULTS.md`,
"Delivery probe") found that Claude Code 2.1.280 loads a plugin installed from a DIRECTORY
marketplace from the marketplace's source path (here a symlink to the worktree), not from the
cache; a station run from there resolves the worktree's `plugins/records` by route 3a, not the
installed one. On Codex 0.155.1 the catalog names the cache copy (`codex/RESULTS.md`, "Delivery
probe"), so a session's station is the cached one measured above. A marketplace fetched from git
or a URL was not measured.

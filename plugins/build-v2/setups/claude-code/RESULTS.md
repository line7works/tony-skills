# RESULTS: build-v2 on Claude Code (E13 slice 3)

Measured on 2026-09-23 on this machine: Claude Code 2.1.280, the worktree `feat/stations-e13` at HEAD
`f62e4b3` plus this slice's uncommitted files. Every home was a fresh directory under the user's
temporary directory (`$TMPDIR`), never the live `~/.claude` and never the pilot's
`~/.local/share/skills-v2-pilot/`. No model call was made by any command in this file except the
sessions named under "Delivery probe", each of which ended before a model turn (below).
The raw records sit in the builder's scratch (`~/.cache/e13-builder/scratch/s3/out/`), which the
control room files in the audit packet.

## Install

`BUILD_V2_CLAUDE_HOME=<fresh dir> install.sh` (the home is required; there is no default):

```text
claude plugin marketplace add <home>/marketplace      -> exit 0, marketplace build-v2-setup
claude plugin install build-v2@build-v2-setup --json -y -> exit 0, ok
claude plugin install records@build-v2-setup --json -y -> exit 0, ok
```

`install.json`: `ok: true`, installed `build-v2/0.1.0`, `records/0.2.0`. The marketplace entries are symlinks to the worktree's plugin folders; the installer wrote real copies into the cache (no symlink in any installed copy, section "Installed-package verification").

## Delivery probe

One headless session, `launch.sh prompts/delivery-probe.txt <throwaway git workspace> <out>`, in the ISOLATED config directory (the explicit slash route, `/build-v2` plus the probe's instructions as arguments). The session ended `Not logged in · Please run /login`, `is_error: true`, `total_cost_usd: 0`, session `74f9b75d-5996-4961-ab05-a840d3aa9c98`: the isolated config directory has no sign-in (the pilot's finding on 2.1.270 holds on 2.1.280). It was not retried and never moved to the machine's own config directory.

What the harness recorded BEFORE the sign-in refusal, from the session's own `transcript.jsonl` (19 records):

- the init event's catalog lists `build-v2:build-v2`; `plugins[].path` for the core is `<home>/marketplace/build-v2`, the marketplace's SYMLINK to the worktree, not the cache copy under `<home>/config/plugins/cache/`;
- record 3, a `user` record carrying `isMeta` and `turnCompanion` (no `sourceToolUseID`: no Skill call was made, the explicit route), is the base-directory line `Base directory for this skill: <home>/marketplace/build-v2/skills/build-v2` and a blank line (149 bytes), then the whole procedure body of `skills/build-v2/SKILL.md` after its frontmatter and blank line, **byte-identical to the file (17,104 bytes)**, then `\n\nARGUMENTS: <the probe's instructions>`; the whole record is 18,631 bytes;
- record 15, the `assistant` record, is the harness's `Not logged in · Please run /login`: no model ran, so the probe's three quoted lines were never produced and nothing is claimed about what a model would do with the body.

**Finding (2.1.280): a plugin from a DIRECTORY marketplace is loaded from its source path.** The pilot measured on 2.1.270/2.1.271 that the installed cache copy is what `--plugin-dir` loads; here, with the plugin installed and enabled from a directory marketplace, both the init event and the delivered base-directory line name the marketplace entry, which is a symlink to the worktree. Consequences recorded, not repaired: the installed-package verification below proves the cache copy equals the checkout, which on this route is not the copy a session reads; the adapter helpers resolve their own path to the worktree, so `measurement.entry` reads `explicit path` for such a session; and the cache-level negative observations below do not predict activation.

## Sidecar and invocation restriction

`skills/build-v2/agents/openai.yaml` carries `interface` only; build-v2 is implicitly invocable on both harnesses, which is v1 build's own trigger rule. Claude Code reads the frontmatter, not the sidecar (the pilot's measurement); the init catalog above lists the skill.

## Negative tests

`negative-tests.sh <fresh dir>` ran the free half of the pilot's nine cases on this core's own
package (each case: a throwaway copy of the plugin, mutated, a one-plugin marketplace linking it,
its own `CLAUDE_CONFIG_DIR`). No session was started: the live half (`--live`, a session reading the
catalog the harness built) was NOT run in this slice, so every row below says what the harness's
`claude plugin validate`, `marketplace add` and `install` and its installer's cache did, and nothing about what a session would activate.

| Case | Observed (the harness's own commands, then the cache) | Classification | Half |
|---|---|---|---|
| `malformed-sidecar` | install exits 0,0; validate exit 0, no finding; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-sidecar` | install exits 0,0; validate exit 0, no finding; cache: SKILL.md present, sidecar absent | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-name` | install exits 0,0; validate exit 0, no finding; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `broken-delimiter` | install exits 0,0; validate exit 0: warning frontmatter: No frontmatter block found. Add YAML frontmatter between --- delimiters at the top of the file to set description and other metadata.; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `duplicate-name` | install exits 0,0,0; validate exit 0, no finding; cache: SKILL.md present, sidecar present; the duplicate plugin installed beside it (SKILL.md present) | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-resource` | install exits 0,0; validate exit 0, no finding; cache: SKILL.md present, sidecar present; the installed core `check-input`: exit 2, `reference unavailable: references/input.schema.json` | installed; the harness does not notice the missing resource; the core refuses (exit 2) | free half run; live half not run |
| `symlink-file` | install exits 0,0; validate exit 0: warning directory: 1 component here was not read — the path is not a regular file (a symlink, a FIFO, a directory). A session loading this plugin does follow them, so validate the real paths separately.; cache: SKILL.md ABSENT, sidecar present | the installer dropped the skill from the cache silently, but a session loads this marketplace's plugin from its source path: activation is the live half's question | free half run; live half not run |
| `symlink-directory` | install exits 0,0; validate exit 0: warning directory: 1 entry here is a symlink and was not read — components are read without following symlinks. A session loading this plugin does follow them, so validate the real paths separately.; cache: SKILL.md ABSENT, sidecar absent | the installer dropped the skill from the cache silently, but a session loads this marketplace's plugin from its source path: activation is the live half's question | free half run; live half not run |
| `update-copy-symlink` | install exits 0,0,0,0; validate exit None, no finding; stages copy 0.1.1 exit 0 cache 0.1.1:SKILL.md; symlink 0.1.2 exit 0 cache 0.1.1:SKILL.md, 0.1.2:no SKILL.md; copy-again 0.1.3 exit 0 cache 0.1.1:SKILL.md, 0.1.2:no SKILL.md, 0.1.3:SKILL.md | enforced in the cache: every installed copy is a real copy; the symlinked SKILL.md was DROPPED at the symlink stage (a session loads the source path, not the cache) | free half run; live half not run |

Every Claude Code row is qualified by the finding above: the session loads a directory-marketplace plugin from its source path, so a skill the installer dropped from the CACHE may still activate from the source. `claude plugin validate` says as much in its own words for the two symlink cases ("A session loading this plugin does follow them").


## Installed-package verification

A fresh home, `install.sh` (`ok: true`), then `verify-install.sh`: exit 0, `ok: true`, findings none.

- the one installed copy: `<home>/config/plugins/cache/build-v2-setup/build-v2/0.1.0` (versions present: 0.1.0);
- `diff -r -x __pycache__` against the checkout's `plugins/build-v2`: exit 0, 0 diff lines;
- the `SKILL.md` frontmatter block byte-equal to the canonical: true;
- runtime references checked: 40 (Markdown links and backticked paths whose first segment is one of
  the skill's own folders, in `SKILL.md`, `adapters/README.md`, `references/*.md` and every adapter
  `profile.md`), none unresolved, outside the root or through a symlink; paths listed as prose,
  never gating: `build_core/inputs.py`, `build_core/records_client.py`, `docs/plans/2026-09-13-recheck-v2-e8-core.md`, `docs/plans/2026-09-14-recheck-v2-e9-adapters.md`, `docs/plans/2026-09-21-stations-e13.md`, `feat/stations-e13`, `plugins/build/skills/build/SKILL.md`, `recheck_core/ledger.py`, `scripts/records.py (the records component's path)`, `setups/codex/RESULTS.md`, `setups/codex/launch.sh`, `setups/codex/negative-tests.sh`, `setups/codex/verify-install.sh`, `setups/verify-package.py`, `src/a`, `src/a.py`, `tests/test_invocation.py`;
- symlinks in the installed package: 0;
- `build.py skill-identity` from the checkout: exit 0, `content_sha256` `bda6ee388b5841f36f2c2a15e01dfa9b36744a60e0c1e33d0626765c0ef45157`; from the installed copy: exit 0, the same
  hash: true (version and commit recorded, never compared, the pilot's E9-16).

This file was written after that verification ran, so the package now differs from the verified
one by this section; `verify-install.sh` re-verifies it in one command.

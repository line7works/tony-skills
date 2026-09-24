# RESULTS: build-v2 on Codex CLI (E13 slice 3)

Measured on 2026-09-23 on this machine: codex-cli 0.155.1, the worktree `feat/stations-e13` at HEAD
`f62e4b3` plus this slice's uncommitted files. Every home was a fresh directory under the user's
temporary directory (`$TMPDIR`), never the live `~/.codex` and never the pilot's
`~/.local/share/skills-v2-pilot/`. No model call was made by any command in this file except the
sessions named under "Delivery probe" and "The session lock", each of which ended before a model turn (below).
The raw records sit in the builder's scratch (`~/.cache/e13-builder/scratch/s3/out/`), which the
control room files in the audit packet.

## Install

`BUILD_V2_CODEX_HOME=<fresh dir> install.sh` (no `--credential`: the pilot's credential copy was refused by the builder session's permission layer, see below; installs need none):

```text
codex plugin marketplace add <home>/marketplace --json -> exit 0, marketplace build-v2-setup
codex plugin add build-v2@build-v2-setup --json -> exit 0
codex plugin add records@build-v2-setup --json -> exit 0
```

`install.json`: `ok: true`, installed `build-v2/0.1.0`, `records/0.2.0`. The marketplace entries are symlinks to the worktree's plugin folders; the installer wrote real copies into the cache (no symlink in any installed copy, section "Installed-package verification").

**The credential step.** The pilot's `install.sh` copies `~/.codex/auth.json` byte for byte at mode 600. `install.sh --credential` keeps that step; in this slice it was NOT run: the builder session's permission layer refused the copy ("Credential Leakage") when the builder first tried it for the lock measurement, and the builder did not work around it. Every Codex session below therefore ran without a credential and ended `401 Unauthorized` before a model turn, which is why each measures what the harness wrote BEFORE the model call and nothing after it.

## Delivery probe

One headless session, `launch.sh prompts/delivery-probe.md <throwaway git workspace> <out>` (the explicit `$build-v2` form), in its own per-launch home. No credential: exit 1, `401 Unauthorized` on every reconnect, thread `01a0cdf8-fd96-7063-b769-de96ac63d8b8`, no model turn. What the rollout recorded before the model call:

- the skills catalog (`<skills_instructions>` developer message) lists `build-v2:build-v2` with its description and the file `r1/build-v2/0.1.0/skills/build-v2/SKILL.md`, `r1` being `<out>/codex-home/plugins/cache/build-v2-setup`;
- the explicit `$build-v2` injected NO body: the only `user` messages are the environment context and the prompt itself (its native `UserMessage` item), so **zero bytes of the skill body were delivered** before the model call, as the pilot measured for the plugin surface on 0.154.0 (a plugin skill's body reaches the model only through a file read, which a credential-free session never gets to);
- `turn_context.sandbox_policy`: `workspace-write`, `writable_roots` `[<out>/codex-home/child]`, `exclude_tmpdir_env_var: true`, `exclude_slash_tmp: true`, network off.

Not measured: what a model does with the catalog entry or the explicit mention (no model turn ran). Real-body runs of the core are not part of E13 (contract section 12).

## Sidecar and invocation restriction

`skills/build-v2/agents/openai.yaml` carries `interface` only; build-v2 is implicitly invocable on both harnesses, which is v1 build's own trigger rule. The Codex catalog above lists it.

## Negative tests

`negative-tests.sh <fresh dir>` ran the free half of the pilot's nine cases on this core's own
package (each case: a throwaway copy of the plugin, mutated, a one-plugin marketplace linking it,
its own `CODEX_HOME` with no credential). No session was started: the live half (`--live`, a session reading the
catalog the harness built) was NOT run in this slice, so every row below says what the harness's
`codex plugin marketplace add` and `plugin add` and its installer's cache did, and nothing about what a session would activate.

| Case | Observed (the harness's own commands, then the cache) | Classification | Half |
|---|---|---|---|
| `malformed-sidecar` | install exits 0,0; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-sidecar` | install exits 0,0; cache: SKILL.md present, sidecar absent | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-name` | install exits 0,0; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `broken-delimiter` | install exits 0,0; cache: SKILL.md present, sidecar present | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `duplicate-name` | install exits 0,0,0; cache: SKILL.md present, sidecar present; the duplicate plugin installed beside it (SKILL.md present) | installed as mutated (activation is the live half's question) | free half run; live half not run |
| `missing-resource` | install exits 0,0; cache: SKILL.md present, sidecar present; the installed core `check-input`: exit 2, `reference unavailable: references/input.schema.json` | installed; the harness does not notice the missing resource; the core refuses (exit 2) | free half run; live half not run |
| `symlink-file` | install exits 0,0; cache: SKILL.md ABSENT, sidecar present | prevented activation at install (the installer dropped the skill silently) | free half run; live half not run |
| `symlink-directory` | install exits 0,0; cache: SKILL.md ABSENT, sidecar absent | prevented activation at install (the installer dropped the skill silently) | free half run; live half not run |
| `update-copy-symlink` | install exits 0,0,0,0; stages copy 0.1.1 exit 0 cache 0.1.1:SKILL.md; symlink 0.1.2 exit 0 cache 0.1.2:no SKILL.md; copy-again 0.1.3 exit 0 cache 0.1.3:SKILL.md | enforced in the cache: every installed copy is a real copy; the symlinked SKILL.md was DROPPED at the symlink stage | free half run; live half not run |

On Codex the catalog names the cache copy (the delivery probe above), so a skill the installer dropped from the cache is not offered by the catalog; whether a model then finds the file anyway is the live half's question, and the pilot measured that catalog absence never prevents a direct file read.

## The session lock (E13 pick P6, SB-14)

**The finding it answers** (the sealed bench's SB-14, 2026-09-20): every Codex launch in a
condition home could read the whole home, which keeps every earlier session's rollout under
`$CODEX_HOME/sessions/`, so two stations sharing one home shared their session records, and the
read-boundary preflight never tested that target.

**Measured first** (codex-cli 0.155.1, 2026-09-23; the brief allowed two Codex sessions for it and
both ran without a credential, ending 401 before a model turn):

- *No model, `codex sandbox`* (Codex's own seatbelt, the one a launch's tool shells run under),
  `CODEX_HOME=<isolated home>`, `-c sandbox_mode=workspace-write`: `/bin/cat <sibling folder>/sentinel.txt`
  printed the sentinel, exit 0; `/bin/ls` of the sibling listed it; a write into it succeeded
  (the folder sat under `$TMPDIR`, which workspace-write makes writable). **Codex's own sandbox
  gives no read separation**, so the separation has to be the bench's wall.
- *Launch 1* (`codex exec`, `CODEX_HOME=<T>/home` with `sessions` a SYMLINK to `<T>/folderA`,
  `CODEX_SQLITE_HOME=<T>/sqliteA`): the rollout landed at
  `folderA/2026/09/23/rollout-<timestamp>-<thread>.jsonl` (the symlink was followed and kept); every
  state database (`state_5`, `thread_history_1`, `logs_2`, `goals_1`, `memories_1`, `queue_1`) went
  to `sqliteA`; and Codex REWROTE `$CODEX_HOME/config.toml` (it added a
  `[projects."<workspace>"] trust_level = "trusted"` table and set mode 600), so a config file shared
  between launches is written by every launch.
- *The binary's own strings* name the config keys `sqlite_home`, `log_dir` and
  `experimental_thread_store` and the variables `CODEX_HOME`, `CODEX_SQLITE_HOME` and
  `CODEX_THREAD_ID`; `codex exec --ephemeral` "Run[s] without persisting session files to disk".
  **Nothing names a rollout folder but `$CODEX_HOME/sessions`**, and `--ephemeral` keeps no rollout,
  which the adapters (E9-31, E9-40) and the runner's compaction witness read.

**The design, therefore: a per-launch home.** `launch.sh` derives `<out-dir>/codex-home` from the
condition home before every launch (the lines between `# >>> session lock` and
`# <<< session lock <<<`, byte-identical in this file's `launch.sh`, signoff-v2's and the pilot's
`plugins/recheck-v2/setups/codex/launch.sh`; `plugins/recheck-v2/evals/runner/tests/test_e13_session_lock.py`
holds the three equal):

- `config.toml` and `child/config.toml` COPIED, the `[shell_environment_policy.set] CODEX_HOME`
  pointer rewritten to the per-launch child, `UV_CACHE_DIR` left at the condition's warmed cache (a
  build cache, not a session record);
- `auth.json` and `child/auth.json` LINKED to the condition home's (the credential stays one file,
  the pilot's E9-26(c));
- `plugins/` and `skills/` COPIED, not linked: E9-40 derives the executor's sessions root from the
  helper's RESOLVED path, so a link would send every adapter helper back to the shared home's
  `sessions/`; absolute paths in the copied plugin JSON rewritten, the way the pilot's install.sh
  derives its `homes/plugin-only`;
- a private `child/` for the tool shells and the reviewer or verifier children;
- a spent `<out-dir>/codex-home` is never reused.

*Launch 2* measured the lock itself (build-v2's `launch.sh`, prompt `prompts/lock-probe.md`, no
credential, thread `01a0cdf8-8a14-75e0-9dcd-3d55953fd903`): the rollout AND every state database
landed in `<out>/codex-home/`; the condition home held no `sessions/` folder afterwards; the rollout's
catalog names the core at `<out>/codex-home/plugins/cache/build-v2-setup/...`; `launch.json` records
`codex_home`, `condition_home` and `session_lock`.

**What separates a sibling launch's folder is the bench's wall**, and the runner now proves it:
`plugins/recheck-v2/evals/runner/runner.py` names the targets (`session_lock_targets`: a sibling
trial's `<record>/harness/codex-home/sessions`, and the condition home's shared `sessions/` and
`child/sessions/`), refuses the two shared folders in every Codex launch's profile (they sit inside
the condition home, a write root, so they are refused after the allows), plants a sentinel in each
target in the read-boundary preflight and passes the preflight only when every one was planted and
refused. The continuation trial's resume now runs in the first half's own per-launch home
(`cut.session_home`, from its `launch.json`). Tests, red first
(`~/.cache/e13-builder/scratch/s3/red/runner-session-lock.txt`), in
`test_e13_session_lock.py`: the launcher with a stub `codex` writes its session into
`<out>/codex-home` and nothing into the condition home; the targets; the separated rule (a readable
sibling fails, an unplanted sentinel fails); the plain unwalled child reads the sibling (the
filesystem allows it); and on a SEALED plan, behind a real `sandbox-exec` profile, the child is
refused every lock target while the unwalled fact still reads them. No bench was rerun and no trial
ran (brief 3.5).

Not measured: a live locked launch with a credential (the credential copy was refused), and a live
walled bench launch.

## Installed-package verification

A fresh home, `install.sh` (`ok: true`), then `verify-install.sh`: exit 0, `ok: true`, findings none.

- the one installed copy: `<home>/plugins/cache/build-v2-setup/build-v2/0.1.0` (versions present: 0.1.0);
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

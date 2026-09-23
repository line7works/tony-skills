# RESULTS: signoff-v2 on Codex CLI (E13 slice 3)

Measured on 2026-09-23 on this machine: codex-cli 0.155.1, the worktree `feat/stations-e13` at HEAD
`f62e4b3` plus this slice's uncommitted files. Every home was a fresh directory under the user's
temporary directory (`$TMPDIR`), never the live `~/.codex` and never the pilot's
`~/.local/share/skills-v2-pilot/`. No model call was made by any command in this file except the
sessions named under "Delivery probe" and "The session lock", each of which ended before a model turn (below).
The raw records sit in the builder's scratch (`~/.cache/e13-builder/scratch/s3/out/`), which the
control room files in the audit packet.

## Install

`SIGNOFF_V2_CODEX_HOME=<fresh dir> install.sh` (no `--credential`: the pilot's credential copy was refused by the builder session's permission layer, see below; installs need none):

```text
codex plugin marketplace add <home>/marketplace --json -> exit 0, marketplace signoff-v2-setup
codex plugin add signoff-v2@signoff-v2-setup --json -> exit 0
codex plugin add records@signoff-v2-setup --json -> exit 0
```

`install.json`: `ok: true`, installed `records/0.2.0`, `signoff-v2/0.1.0`. The marketplace entries are symlinks to the worktree's plugin folders; the installer wrote real copies into the cache (no symlink in any installed copy, section "Installed-package verification").

**The credential step.** The pilot's `install.sh` copies `~/.codex/auth.json` byte for byte at mode 600. `install.sh --credential` keeps that step; in this slice it was NOT run: the builder session's permission layer refused the copy ("Credential Leakage") when the builder first tried it for the lock measurement, and the builder did not work around it. Every Codex session below therefore ran without a credential and ended `401 Unauthorized` before a model turn, which is why each measures what the harness wrote BEFORE the model call and nothing after it.

## Delivery probe

One headless session, `launch.sh prompts/delivery-probe.md <throwaway git workspace> <out>` (the explicit `$signoff-v2` form), in its own per-launch home. No credential: exit 1, `401 Unauthorized` on every reconnect, thread `01a0cdf9-3751-7713-abcb-138ef0191629`, no model turn. What the rollout recorded before the model call:

- the skills catalog does NOT list `signoff-v2`: the sidecar's `policy: allow_implicit_invocation: false` removed it (catalog filtering, `harness-enforced`; the pilot measured the same on 0.154.0);
- the explicit `$signoff-v2` injected NO body: the only `user` messages are the environment context and the prompt itself (its native `UserMessage` item), so **zero bytes of the skill body were delivered** before the model call, as the pilot measured for the plugin surface on 0.154.0 (a plugin skill's body reaches the model only through a file read, which a credential-free session never gets to);
- `turn_context.sandbox_policy`: `workspace-write`, `writable_roots` `[<out>/codex-home/child]`, `exclude_tmpdir_env_var: true`, `exclude_slash_tmp: true`, network on (signoff-v2 turns it on for its nested reviewer).

Not measured: what a model does with the catalog entry or the explicit mention (no model turn ran). Real-body runs of the core are not part of E13 (contract section 12).

## Sidecar and invocation restriction

`skills/signoff-v2/agents/openai.yaml` carries `policy: allow_implicit_invocation: false`. On Codex the catalog above omits it: the restriction is enforced at the catalog and, per the pilot, does not stop a model that reads the file.

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
| `missing-resource` | install exits 0,0; cache: SKILL.md present, sidecar present; the installed core `check-input`: exit 10, `stopped: reference unavailable: references/input.schema.json` | installed; the harness does not notice the missing resource; the core refuses (exit 10) | free half run; live half not run |
| `symlink-file` | install exits 0,0; cache: SKILL.md ABSENT, sidecar present | prevented activation at install (the installer dropped the skill silently) | free half run; live half not run |
| `symlink-directory` | install exits 0,0; cache: SKILL.md ABSENT, sidecar absent | prevented activation at install (the installer dropped the skill silently) | free half run; live half not run |
| `update-copy-symlink` | install exits 0,0,0,0; stages copy 0.1.1 exit 0 cache 0.1.1:SKILL.md; symlink 0.1.2 exit 0 cache 0.1.2:no SKILL.md; copy-again 0.1.3 exit 0 cache 0.1.3:SKILL.md | enforced in the cache: every installed copy is a real copy; the symlinked SKILL.md was DROPPED at the symlink stage | free half run; live half not run |

On Codex the catalog names the cache copy (the delivery probe above), so a skill the installer dropped from the cache is not offered by the catalog; whether a model then finds the file anyway is the live half's question, and the pilot measured that catalog absence never prevents a direct file read.

## The session lock (E13 pick P6, SB-14)

This setup's `launch.sh` carries the session-lock block byte for byte (held equal to the pilot's
and build-v2's by `plugins/recheck-v2/evals/runner/tests/test_e13_session_lock.py`): every launch
runs in its own `<out-dir>/codex-home`, and the reviewer children `reviewer.py` starts write their
rollouts under that home's own `child/`. The measurements, the design and the runner's preflight
target are recorded once, in `plugins/build-v2/setups/codex/RESULTS.md`, "The session lock".

## Installed-package verification

A fresh home, `install.sh` (`ok: true`), then `verify-install.sh`: exit 0, `ok: true`, findings none.

- the one installed copy: `<home>/plugins/cache/signoff-v2-setup/signoff-v2/0.1.0` (versions present: 0.1.0);
- `diff -r -x __pycache__` against the checkout's `plugins/signoff-v2`: exit 0, 0 diff lines;
- the `SKILL.md` frontmatter block byte-equal to the canonical: true;
- runtime references checked: 32 (Markdown links and backticked paths whose first segment is one of
  the skill's own folders, in `SKILL.md`, `adapters/README.md`, `references/*.md` and every adapter
  `profile.md`), none unresolved, outside the root or through a symlink; paths listed as prose,
  never gating: `CODEX_HOME/sessions`, `D/readers/mandate.md`, `D/request.json`, `docs/plans/2026-09-14-recheck-v2-e9-adapters.md`, `docs/plans/2026-09-21-stations-e13.md`, `readers/mandate.md`, `recheck_core/ledger.py`, `setups/codex/RESULTS.md`, `setups/codex/launch.sh`, `setups/codex/negative-tests.sh`, `setups/codex/verify-install.sh`, `setups/verify-package.py`, `tests/test_invocation.py`, `tests/test_reviewer.py`;
- symlinks in the installed package: 0;
- `signoff.py skill-identity` from the checkout: exit 0, `content_sha256` `930a8db5f03d324f07ad8acaf0d1ae58ec66b97df3dc27380c204777f20280b1`; from the installed copy: exit 0, the same
  hash: true (version and commit recorded, never compared, the pilot's E9-16).

This file was written after that verification ran, so the package now differs from the verified
one by this section; `verify-install.sh` re-verifies it in one command.

# The E10 trial runner (lane S)

`runner.py` drives the recheck-v2 pilot campaign: it stages the checkout, installs and
verifies the three harness setups in their three homes each, probes the environment a launched
session actually carries, plans a campaign, runs one trial end to end, grades it against the
answer key, runs the routing and continuation trials, scans every record for credential
shapes, and reports. It sits beside the E7 check runner under `evals/checks/`.

Built at step E10 of the skills v2 execution plan under the lane contract
`docs/plans/2026-09-14-recheck-v2-e10-runner.md`. The pilot contract
(`skills/recheck-v2/references/pilot-contract.md`, revision 5) outranks that document, and
that document outranks the E9 lane contract at E10.

- Python 3.9 syntax, standard library only. The grading step calls the core's
  `validate-result.py` through `uv run`, the way the E7 runner calls things, and imports
  `evals/checks/match.py` from its path.
- One JSON document on stdout and nothing else; every diagnostic on stderr.
- Exit **0** success · **2** a usage slip · **3** a missing binary, setup or record ·
  **1** anything else (ruling A7a, E10-9).
- Every subcommand runs from any working directory and refuses to overwrite a record.

## Contents

1. [The wall](#1-the-wall) · 2. [Subcommands](#2-subcommands) ·
3. [The trial record](#3-the-trial-record) · 4. [plan.json](#4-planjson) ·
5. [The environment allowlist](#5-the-environment-allowlist) ·
6. [The fake harness and `check`](#6-the-fake-harness-and-check) ·
7. [Where each ruling is implemented](#7-where-each-ruling-is-implemented) ·
8. [Codex quirks](#8-codex-quirks) · 9. [Tests](#9-tests) ·
10. [What the harnesses cannot do](#10-what-the-harnesses-cannot-do)

## 1. The wall

`evals/answer-key/` and `evals/trigger-set/held-out/` are opened by exactly three code paths,
all of them below the `the wall` marker in `runner.py`:

| path | what it opens | why |
|---|---|---|
| `grade` (`key_entry`) | the lane's key file, for the case being graded | E10-11 |
| `routing-score` (`expectation_of`) | both files, for the expected target per entry | E10-13 |
| `routing` (`request_text`) | the tuning file directly; a **held-out** entry's text through a subprocess that prints that one entry's text and nothing else | E10-13 |

`plan` reaches the held-out **ids** the same way (a subprocess that prints ids only), so the
sealed text never enters the runner's own process. No launch path imports or opens either
directory; `tests/test_wall.py` proves it two ways — by walking `runner.py`'s AST and naming
every function that can reach a reader, and by running every launch path (`run`, `routing`,
`continuation`) against a copy of the plugin whose `answer-key/` and `held-out/` are mode
`0o000`.

`grade` writes `grade.json` into the trial record and `grade --summary` prints counts only. A
`grade.json` carries expected values as reasons: read the summary, never the file.

**The test-only stand-in (E10-21).** `RECHECK_RUNNER_KEY_DIR=<dir>` and
`RECHECK_RUNNER_HELDOUT=<file>` point `grade` and `routing-score` at stand-ins a test wrote
itself, and are honoured **only** with `RECHECK_RUNNER_TEST=1`; set without it, the runner
exits 2 with `key stand-in outside test`. A grade of a real dry-run trial never uses them.

## 2. Subcommands

Every subcommand takes `--campaign <dir>`, the campaign directory under
`~/.local/share/skills-v2-pilot/e10/`. `check` accepts it and ignores it.

### `stage [--refresh]`

A copy of the checkout at the campaign commit under `<campaign>/stage/`, with
`plugins/recheck-v2/evals/` and `__pycache__` excluded (E10-6). Writes `stage.json`: the
commit, the staged tree's `plugin_tree_sha256` (every file under the staged
`plugins/recheck-v2/`, sorted relative paths, `<path>\0<sha256>\n` concatenated, as
`fixturelib` hashes), the file count, the canonical `content_sha256` from a fresh
`recheck.py skill-identity`, and the proof that no `answer-key`, `held-out` or `evals`
directory survived the copy. Refuses to replace an existing stage without `--refresh`
(exit 2). Exit 1 when the stage still holds any of the three.

### `install [--setup NAME]... [--home available|absent|routing]`

Runs the **staged copy's** own `setups/<harness>/install.sh` so every marketplace and copy
source points at the stage. Per harness, measured, not assumed:

| harness | available | absent | routing |
|---|---|---|---|
| `claude-code` | `install.sh --pilot-home <home>` | the same install, then `claude plugin uninstall recheck-v2@tony-skills` under that home's `CLAUDE_CONFIG_DIR` | the same install, then `claude plugin install <name>@tony-skills` for every marketplace plugin except the five blocked |
| `codex` | `install.sh` (it takes no arguments and derives `$HOME/.local/share/skills-v2-pilot/codex/home`) | a copy of the available home with its absolute paths rewritten (the way `install.sh` makes its own `homes/plugin-only`), then `codex plugin remove recheck-v2` and the host-skill folder gone | the same copy, then `codex plugin add <name>@tony-skills` per plugin |
| `opencode` | `install.sh --setup <home> --model <model>` | the same install, then the `recheck-v2` folder removed from `<home>/xdg-config/opencode/skill/` | the same install, then every unblocked plugin's skill folders copied into that directory |

**Labelled honestly.** The Claude Code and OpenCode installs target a second home directly;
the Codex `install.sh` cannot, so its `absent` and `routing` homes are recorded
`derived_from_available: true`. And in every case `absent` is *the installed home with the
skill removed by the harness's own mechanism*, not a home that never held it: `install.sh`
installs recheck-v2 unconditionally and takes no flag to skip it. The record names what was
removed (`uninstalled_after_install`, `removed`). E10-3's words are "never held recheck-v2 on
any surface"; the runner cannot reach that without editing a setup, so it is a finding.

Every install record carries `home_leak_scan`: the walk that proves no `answer-key`,
`held-out` or `evals` name exists anywhere under the home (E10-6). A non-empty scan is exit 1.

E10-20: this is the only path that passes `OPENROUTER_API_KEY`, and only to the OpenCode
install script. Existence is checked, the value is never printed, logged or copied.

### `verify [--setup NAME]... [--home ...]`

Runs each setup's `verify-install.sh` and compares the installed `content_sha256` with a fresh
`uv run skills/recheck-v2/scripts/recheck.py skill-identity` of the checkout — compared, never
typed. Also re-runs `home_leak_scan` per home. Exit 3 for a home that is not installed.

### `probe-env [--setup NAME]... [--home ...] [--timeout N] [--refresh]`

A trial-shaped session per setup and home whose whole prompt is `env | cut -d= -f1 | sort`.
The record's `names_seen` is every environment-variable-shaped name the session's own record
printed; `banned_names_seen` is those matching the banned pattern of E10-7. `campaign start`
is expected to be gated on this being empty. Refuses to replace a probe record (exit 2).

### `plan [--plan FILE] [--refresh]`

Writes `campaign.json` from a `plan.json` (section 4), or from the full E10 default plan when
`--plan` is omitted. Adds: `planned_at`, the stage record, the measured `path_entries`, the
allowlisted names, `case_lanes`, the fixed order per setup (E10-5), the routing and
continuation orders, and the trial counts. Exit 2 for a missing field, a case no generator
lists, a condition outside `available|absent`, or an existing `campaign.json` without
`--refresh`.

### `run <trial-id> [--plugins NAME]... [--fake-launcher PATH]`

One comparison trial end to end, in this order:

1. a fresh opaque fixture build into `<record>/fixture` (`build.py --out … --case … --opaque
   --json`, E10-5 and E7-18), so the path the model sees names neither the lane nor the case;
2. a fresh run directory under the trial's own `TMPDIR`, with the canonical
   `result.schema.json` copied in (never edited, E10-4);
3. the prompt from the E10-4 template, identical bytes in both conditions;
4. the launch through the staged copy's `setups/<harness>/launch.sh` under the allowlist, with
   `TMPDIR` fixed to `<campaign>/tmp/`;
5. the collection (section 3), `validate-result.py --strict` against the **live** run
   directory, and the credential scan;
6. one line in `trials.jsonl`.

It never grades. A used trial directory is exit 2 (E9-34). `--fake-launcher` is for the tests
and `check`.

### `campaign start|status|stop [--foreground]`

`start` runs the whole plan as a detached process writing `runner.log`, `trials.jsonl` and
`campaign.pid`; `--foreground` runs it in this process (what the tests use). Resumable from
disk: a restart **skips** every trial whose `command.json` says `complete`, and **reruns
nothing on its own** — an incomplete record is skipped and named in `interruptions.jsonl`
(E10-9; `rerun` is the operator's call, E10-15). `status` prints the planned count, the
complete count, the incomplete records, the next trial, and whether the pid is alive. `stop`
terminates the campaign's own process group.

### `rerun <trial-id>`

A new attempt directory `attempts/<n>/` beside the failed one. The failed attempt stays on
disk and stays counted in `trials.jsonl`; the rerun is a line of its own with `attempt: n`,
and `interruptions.jsonl` records it.

### `grade <trial-id> | --all [--summary]`

`validate-result.py --strict` (a skip under `--strict` is a failed grade naming the skip),
then `match()` from `evals/checks/match.py` against the key entry's `expected`, then every
metric of E10-11. Refuses while a harness process for that trial is alive (exit 1). Exit 3 for
a record that is not there. Fields of `grade.json`:

| field | what it holds |
|---|---|
| `key_runs_at`, `key_runs_at_includes_E10` | the key entry's `runs_at`, and whether E10 is in it |
| `key_stand_in` | whether an E10-21 stand-in supplied the entry |
| `validator` | the exit, `ok`, the schema and semantic errors, the skips, `failed_for_a_skip` |
| `match` | `match()`'s verdict and its reasons |
| `dispositions` | per item: expected, observed, match |
| `false_fixed` | the items the key pins as not fixed that the result reports `fixed`, and the count |
| `evidence_sufficient` | per item: the evidence count, the method, the static reason, and `commands_run` / `observed` as E8-A43 names them (`unchecked` when the result carries neither) |
| `scope_violations` | the result's own `boundary_violations` plus the grader's scan of the trace for writes outside the workspace, the run directory and `TMPDIR` |
| `unauthorized` | git commands that change branches, index or history; web tools; writes to a pilot home — from the trace |
| `interop` | the chat block's `RECHECK:`, `Result:` and `Source:` lines, its byte count, and one line per item |
| `time`, `cost`, `model` | copied from `command.json`, `cost.json`, `model.json` |
| `floor_met` | the result's `run.model` block beside `model.json`'s id, so E9-3 re-grades from the record without a rerun (E10-16) |
| `run_dir_used`, `run_dir_is_the_retained_copy` | which run directory the validator saw |

A trial with no `result.json` grades every metric as `no_result` and counts as a failure of the
condition, never as excluded.

`grade --summary` prints the counts **and** a `per_trial` block whose fields are listed in
`SUMMARY_SAFE_FIELDS`: every one is the runner's or the harness's own (the validator's exit and
source, the scope and unauthorized lists, the model, the effort, the wall, the cost, and
`match_ok` / `false_fixed_count` as verdicts and counts). `match`'s *reasons* are never in it,
because they quote the expected values the wall keeps from a builder. The block exists so
nobody has to open a `grade.json` to see what the run recorded.

### `routing <trial-id>`

One routing trial: the request as the opening line of a fresh session in an empty
git-initialized workspace with no build doc, the plan's 300-second timeout, and the harness's
own turn limit where it has one — **on this machine none of the three has one**, recorded per
trial in `command.json.turn_limit` with the measurement (`claude --help` on 2.1.272 prints no
`--max-turns`). Records the observed target from the harness's own record, never by asking the
model:

| harness | the record the observed target comes from |
|---|---|
| `claude-code` | the `Skill` tool call in the session's own trace |
| `codex` | the skill's own `SKILL.md` read in the rollout (implicit selection), else an injected `<skill …>` message |
| `opencode` | the first `skill` tool call in the session store |

A catalog holding a blocked name is `profile_breach`: the trial is recorded and the lane stops
(exit 1).

### `routing-score [--revision REV]`

Behind the wall. Writes `<campaign>/routing/trigger-set-<setup>-<revision>.json` per setup in
the trigger README's shape: one row per entry with `observed_target`, `activated` and
`matches_expected`, the tuning and held-out rates kept separate, the manual-only row, and the
blocked-station leak rows.

### `continuation <trial-id> [--compact-tokens N]`

`cont-<setup>-<case>-<handoff|compaction>-r<n>`. Launches the trial, polls
`run/checkpoint.json` and `run/checkpoint.log` every second, and cuts at the first checkpoint
showing one item `done` and one `pending` in phase `adjudicating` or `verifying` — SIGTERM to
the harness's own process group, SIGKILL after five seconds — recording the checkpoint's `seq`
and the log's line count at the cut, and copying the checkpoint, its log and the receipt
before the resume touches them. Then, per kind:

- `handoff`: a fresh session, never having seen the run, with the resume prompt.
- `compaction`: the same session continued by the harness's own resume mechanism with its
  compaction setting, and `compaction_witness` set only when the harness's own record shows a
  compaction or summary event before the resumed turn.

`--poll-interval` defaults to E10-12's 1.0 second and was measured too coarse (finding 13); at
0.1 s the dry run cut all four continuation trials at seq 3, phase `adjudicating`, one item done
and one pending. What the two mechanisms did:

| setup | resume command | witness | verdict |
|---|---|---|---|
| claude-code | `claude -p --resume <id> --autocompact 100000 …` | `trace.jsonl:7` matching `"subtype": "compact` | compaction observed; the resumed run reached `continuations: 1`, `done: 2`, phase `committed`, and its result validates |
| opencode | `opencode run --session <id> --format json --model …` | none | `compaction unavailable headlessly`; the resume ran and was graded, and the run reached `continuations: 1`, phase `committed` |
| codex | `codex exec resume <thread> -c model_auto_compact_token_limit=<n>` | not reached | blocked by finding 17 |

### `scan [PATH...]`

The credential scan over every record: the OpenCode scanner's shapes plus JWT and `sk-`
shapes. Overlapping shapes count once (the most specific claims the span). The only exemption
is the setups' own auth stores by resolved path. A hit names the file, the shape, the offset
and the length — never a value. Exit 1 on a hit.

### `report`

`table.md`, `table.json` and a `report.md` skeleton. Every number is computed from
`trials.jsonl` and the grade files, and every row names the records it came from. Available
trials are split by `activated` (E10-4).

### `check [--tests-only] [--scratch DIR]`

The runner's self-test: the whole test suite, plus one dry trial against the fake harness with
no model. Exit 1 when either fails.

## 3. The trial record

`trials/<trial-id>/`, with `<trial-id>` = `<setup>-<case>-<available|absent>-r<n>`. The record
is behind the wall from every model; the fixture path the model sees is opaque.

| file | what it holds |
|---|---|
| `command.json` | the fields below |
| `prompt.txt` | the prompt bytes, exactly as the harness received them |
| `harness/` | everything the setup's `launch.sh` wrote: the trace, the transcript or rollout or session-store dump, `launch.json`, stderr, and the catalog capture |
| `model.json` | `id`, `effort` and the **record they were read from** (a missing value is `null`, never a label, E10-19) |
| `cost.json` | `total_cost_usd`, token counts, and the record; `null` when the harness printed nothing |
| `run/` | the run directory copied whole after the harness ended and after the validation, verifier captures included |
| `input.json`, `result.json` | copies from the run directory, or absent with `absent: true` in `command.json` |
| `chat.md` | the session's final text |
| `validate.txt` | the exact output of `uv run validate-result.py <result> --input <input> --run-dir <run> --workspace <ws> --strict`, with the exit status on the last line |
| `scan.json` | the credential scan of this record |
| `grade.json` | written by `grade`, never by `run` |
| `attempts/<n>/` | a rerun's own record, with the same layout |
| `fixture/` | this trial's opaque fixture build |

`command.json`: `argv`, `cwd`, `allowlisted_env_names` (names, never values),
`launcher_env_names`, `started_at`, `ended_at`, `wall_seconds`, `launch_wall_seconds`, `exit`,
`timeout_verdict`, `condition_witness`, `catalog`, `activated`, `setup_home`, `setup`,
`harness`, `condition`, `case`, `staged_commit`, `plugin_tree_sha256`, `setup_tree_sha256`,
`fixture` (the build's `--json` summary with its `tree_sha256`), `run_dir`, `run_root`,
`run_root_note`, `workspace`, `result_absent`, `absent`, `status`, `validate_exit`,
`scan_hits`, and on OpenCode `store_separation_witness` (E10-17).

`model.json` per harness, measured (see section 10 for the effort gap):

| harness | model | effort | cost |
|---|---|---|---|
| `claude-code` | the last non-sidechain `assistant` record's `message.model` in the transcript; the init event's `model` as `init_model` | that record's top-level `effort` | the `result` event's `total_cost_usd` |
| `codex` | `turn_context.model` in the rollout (`session_meta` as the fallback) | `turn_context.effort` | no dollar figure; the events stream's token counts |
| `opencode` | `providerID/modelID` from the session store's assistant rows | **none exists on 1.18.31 → `null`** | the assistant rows' `cost` summed, with the token totals |

`trials.jsonl`, one line per trial attempt: `id`, `attempt`, `status` (`complete`, `no_result`,
`timed_out`, `launch_failed`, `profile_breach`), `exit`, `wall`, `cost`, `model`, `effort`,
`activated`, `record`. `interruptions.jsonl` carries every timeout, launch failure, rerun,
wall-clock gap and skipped incomplete record with what the runner observed and what it did
(E10-14).

## 4. `plan.json`

```json
{
  "plan_version": 1,
  "campaign_id": "e10-2026-09-20",
  "run_date": "2026-09-20",
  "setups": [
    {"name": "claude-code", "harness": "claude-code"},
    {"name": "codex", "harness": "codex"},
    {"name": "opencode", "harness": "opencode", "model": "qwen"}
  ],
  "cases": ["F1-01-fixed-clean", "F2-01-reproduces", "F3-01-missed-case",
            "F4-01-missing-fixture-file", "F5-01-outbound-required", "F6-04-verifier-override"],
  "conditions": ["available", "absent"],
  "repetitions": 2,
  "continuation": {"case": "F3-02-mixed-two-items", "condition": "available", "repetitions": 1},
  "routing": {"entries": "all", "repetitions": 3},
  "timeouts": {"comparison": 1800, "continuation": 1800, "routing": 300},
  "run_root_name": "runs"
}
```

That is the full E10 campaign and the default when `--plan` is omitted: the six comparison
fixtures of E10-1 (one case per semantic family, `F6-04` over `F6-01`), the three setups of
E10-2, the two conditions of E10-3, two repetitions — **6 × 3 × 2 × 2 = 72 comparison
trials** — plus the continuation set on `F3-02-mixed-two-items` (two checklist items, so an
interruption between item results exists), one `handoff` and one `compaction` trial per setup,
**6 continuation trials**; plus the routing set, all twenty trigger-set entries (12 tuning, 8
held-out) at three repetitions per setup, **180 routing trials**; plus the `probe-env` sessions,
three setups × three homes. The timeouts are E10-14's. The allowlist is E10-7's, with the
measured `PATH` written into `campaign.json` as `path_entries`; on this machine that is
`/Users/tonycoon/.local/bin` (claude, codex, uv), `/usr/local/bin` (node), `/usr/bin` (git,
python3), then `/usr/bin:/bin:/usr/sbin:/sbin`.

Optional keys: `entries` may be `"tuning"`, `"all"`, or an explicit list of ids; a setup entry
`{"name": "opencode-deepseek", "harness": "opencode", "model": "deepseek"}` adds the DeepSeek
setup in one line (E10-2: the runner takes its setup list from the plan, never from code);
`run_root_name` sets the run root's segment under `TMPDIR` (see section 10).

The order (E10-5) is written into `campaign.json` before the first launch: per setup, case by
catalog order, then repetition 1 available, 1 absent, 2 available, 2 absent. The three setups
are three lanes; each lane is strictly sequential.

## 5. The environment allowlist

Every process the runner starts — an install, a verify, a launch, a probe, a grade — starts
from a complete environment built from nothing with exactly: `PATH` (the fixed list above),
`HOME`, `TMPDIR` (`<campaign>/tmp/`, the same for the installs and the trials because
OpenCode's `external_directory` rule is written from it, E9-27 — proved: the three installs
wrote `"<campaign>/tmp/recheck-v2/**": "allow"` into each home's `opencode.json`),
`LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `TERM=dumb`, `SHELL=/bin/zsh`, **`USER`**, plus the one
variable the setup's own launcher needs for itself: `SKILLS_V2_PILOT_HOME`, `RECHECK_CODEX_HOME`, or `RECHECK_OPENCODE_SETUP`
(and `RECHECK_OPENCODE_TIMEOUT`). Nothing named `CLAUDE_CODE_*`, `CLAUDECODE`, `CODEX_*`,
`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `*_TOKEN`, `*_SECRET`, `*_KEY`,
`AWS_*`, `GH_*`, `GITHUB_*`, `NOTION_*`, `SLACK_*` or `SSH_*` passes; `command.json` records
the names, never the values.

**`USER` is the one name E10-7's measure-and-add clause added.** Measured 2026-09-15 on Claude
Code 2.1.272 with four short sessions from `env -i`:

| environment | outcome | cost |
|---|---|---|
| the seven names of E10-7 | `"Not logged in · Please run /login"`, `is_error: true` | 0 |
| the seven plus `USER` and `LOGNAME` | answered | 0.7100425 (a cold prompt cache) |
| the seven plus `USER` | answered `ok` | 0.011564 |
| the seven plus `LOGNAME` | `"Not logged in · Please run /login"` | 0 |

The sign-in lives in the macOS Keychain (`security find-generic-password -s
"Claude Code-credentials"`, class `genp`), not in a variable, and the harness reaches it only
when `USER` is set. `USER` names the process's own identity, carries no credential, and matches
no banned shape. Nothing was widened to inheritance.

**What the nine probe sessions found in a launched session.** No banned name the runner passed,
on any setup. But the harness sets its own: Claude Code puts `CLAUDECODE`,
`CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_EXECPATH`,
`CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_SESSION_ATTENDED`, `CLAUDE_CODE_MESSAGING_SOCKET` and
`CLAUDE_CODE_MESSAGING_TOKEN` in every tool shell, and Codex puts `CODEX_HOME` there (E9-25 by
design). OpenCode's tool shell carried no banned name at all, which is E9-38 holding. So
E10-7's "the runner fails the campaign start if any banned name appears in the record" can only
be a gate on **what the runner passed**: a gate on the raw record would fail every Claude Code
campaign. `probe-env` therefore records `banned_the_runner_passed` (the gate, empty in all nine
probes) beside `banned_the_harness_set_for_its_own_tool_shells`.

**Measured, and not something the parent can prevent**: four names appear in a launched child
below that boundary. `/bin/sh` adds `PWD` and `SHLVL`; CoreFoundation adds
`__CF_USER_TEXT_ENCODING`; and the `/usr/bin/python3` xcrun shim adds `SDKROOT`, `CPATH`,
`LIBRARY_PATH` and `MANPATH` when it re-execs the Xcode interpreter. None matches a banned
shape and none carries a credential. `tests/test_env_allowlist.py` asserts the child's
environment is the allowlist plus the one pointer plus exactly that named set, and that no
planted `CLAUDE_CODE_X`, `CODEX_X`, `OPENROUTER_API_KEY` or `FOO_TOKEN` survives.

## 6. The fake harness and `check`

`tests/fake/` holds a stub launcher per setup with the real launcher's own arguments, and
`fakelib.py` behind them. A stub does what a real session does, minus the model:

1. reads the run directory, the workspace, the slice and the build doc out of the prompt;
2. builds the input document from the fixture's own seeded `input.json`, replacing only the
   `invocation` object (a headless run, the harness and model the fake reports, the pinned run
   date);
3. drives `scripts/recheck.py` through `start`, `record-call`, `adjudicate` and `record`, with
   a canned verifier report in the shape `references/verifier.md` fixes — the fake's own
   dispositions, never a key value;
4. writes the harness's own record in that harness's shape (a stream-json trace plus a
   transcript; a rollout plus an events stream; a session-store dump plus a JSONL trace), so
   the model, cost, condition-witness and activation readers have a real record to read;
5. records the names its own environment carried, in `env-names.json`.

The result it produces validates: `schema ok; semantic: 0 finding(s), 0 check(s) skipped`,
exit 0. So `check` exercises `run`, `grade`, `routing`, `routing-score`, `continuation`,
`campaign`, `rerun`, `scan` and `report` end to end with no model, and grading runs against
the stand-in key of E10-21. Hooks: `RECHECK_FAKE_SLEEP` (the timeout path),
`RECHECK_FAKE_NO_CORE` (the record without the core), `RECHECK_FAKE_TARGET` (the routing
target, for the leak rows).

## 7. Where each ruling is implemented

| ruling | where |
|---|---|
| E10-1, the six fixtures | `DEFAULT_CASES`, `default_plan` |
| E10-2, the three setups; the setup list from the plan | `SETUP_CLASSES`, `make_setup`, `_selected_setups` |
| E10-3, the two conditions; the condition witness; `skill_file_reached` | `pilot_home`, `Setup.install`, `condition_witness` per setup, `_unauthorized` / `_scope_violations` (the trace scan for pilot-home paths) |
| E10-4, the comparison prompt; the schema copy; activation measured, not rerun | `PROMPT_TEMPLATE`, `prepare_run_dir`, `activation` per setup |
| E10-5, repetitions and order | `order_of`, `build_fixture` (`--opaque`, one case, fresh per trial) |
| E10-6, the staged copy | `do_stage`, `home_leak_scan`, `do_verify` |
| E10-7, the allowlist | `ALLOWED_ENV`, `path_entries`, `allowlist_env`, `Campaign.env`, `do_probe_env` |
| E10-8, nested launches | the runner is what the operator invokes; `rmtree` instead of `rm -rf`; see section 8 |
| E10-9, the shape and the subcommands | `build_parser`, `main`, `Usage`/`Missing`/`Failure` |
| E10-10, the trial record | `collect_trial` |
| E10-11, grading and the metrics | `grade_one` and the `_dispositions`, `_false_fixed`, `_evidence`, `_scope_violations`, `_unauthorized`, `_interop` helpers |
| E10-12, the continuation trials | `do_continuation`, `_launch_and_cut`, `cut_point_reached`, `_compaction_resume`, `compaction_witness`, `COMPACTION` |
| E10-13, the routing trials | `do_routing`, `observed_target`, `_profile_breach`, `_turn_limit`, `do_routing_score`, `_rates`, `_manual_only_row` |
| E10-14, timeouts and interruptions | `run_cmd`'s timeout, `_terminate_group`, `Campaign.interruption`, `interruptions.jsonl` |
| E10-15, the operator's rules | `campaign status`, `rerun` (one attempt directory per call), `grade --summary` |
| E10-16, floors and provisional maps | `grade.floor_met` |
| E10-17, the OpenCode store separation | `OpenCodeSetup.store_separation_witness` |
| E10-19, the effort witness | `model.json`'s `effort` and `source`; never a label |
| E10-20, the one install-time credential | `OpenCodeSetup.install` (the only place `INSTALL_CREDENTIAL` is read) |
| E10-21, the test-only stand-in | `_stand_in`, `key_dir`, `heldout_file` |
| E9-34, a record is never overwritten | `do_run`, `do_routing`, `do_continuation`, `do_stage`, `do_probe_env`, `do_plan` |
| E9-41, the timeout verdict | `run_cmd` collects the child's status before any verdict; a child that finished first keeps its own exit |
| E7-18, the opaque mount and the run date | `build_fixture`, `default_plan` (from `trial-defaults.json`) |
| E8-A43, `commands_run` and `observed` | `_evidence` (`unchecked` per item when the result carries neither) |

## 8. Codex quirks

The runner is launched from inside a `codex exec` (E10-8), so:

- **No `rm -rf`.** The Codex approval review rejects a command containing `rm -rf` even under
  `approval_policy=never`, so every removal in the runner goes through `rmtree()`
  (`shutil.rmtree`), never a shell command.
- **`</dev/null`.** A `codex exec` launched from a script needs its stdin closed; `run_cmd`
  gives every child `subprocess.DEVNULL` unless it is handing one a prompt on stdin.
- **A hard-link probe is declined by the model**, so the runner never asks for one; containment
  is proved by the allowlist and the walk of each home.
- **The nested verifier needs `-s danger-full-access`** (E9-21): under the outer seatbelt a
  nested `codex exec` at `read-only` or `workspace-write` initializes but every shell command
  it runs fails at `sandbox-exec: sandbox_apply: Operation not permitted`. That is the
  adapter's business, not the runner's, but it is why the operator's own `codex exec` runs at
  `danger-full-access` with the allowlist as the containment.

## 9. Tests

`tests/`, unittest, standard library, run from any directory:

```
python3 -m unittest discover -s plugins/recheck-v2/evals/runner/tests
uv run python3 -m unittest discover -s plugins/recheck-v2/evals/runner/tests
```

`RECHECK_RUNNER_TEST_SCRATCH=<dir>` puts every test's scratch under one directory.

| file | covers |
|---|---|
| `test_cli.py` | `--help` on every subcommand, the JSON-on-stdout rule, and every usage exit code (2 for a bad id, a missing flag, a used record, a plan with a bad field; 3 for a missing campaign, stage, record or plan file) |
| `test_env_allowlist.py` | the allowlist's shape, the banned pattern over every shape E10-7 names, a real launched child's own environment, and that only the OpenCode install ever sees the credential name |
| `test_wall.py` | the AST proof of which functions can reach a reader, every launch path run against unreadable stand-ins, the E10-21 refusal, and the grade path refusing while a harness pid is alive |
| `test_records.py` | the record layout and every `command.json` field, the opaque fixture path, the refusal to overwrite, `rerun`'s attempt directories, the timeout path (E9-41), the credential scan, the report's counts from a hand-written `trials.jsonl`, and campaign resume from disk |
| `test_fake_end_to_end.py` | one trial per setup validating end to end, the model/cost/activation/condition-witness readers per harness, the grade paths (matching, false-fixed, no-result), the routing and routing-score paths, and the continuation cut |

## 10. What the harnesses cannot do

Measured on this machine, 2026-09-14/15 (Claude Code 2.1.272, codex-cli 0.154.0,
opencode-ai 1.18.31):

1. **No turn limit.** E10-13 asks for `--max-turns 3` on Claude Code. `claude --help` on
   2.1.272 prints no `--max-turns` at all, and neither `codex exec` nor `opencode run` offers
   one. The routing trials are bounded by the 300-second timeout alone, recorded per trial.
2. **OpenCode has no headless compaction.** `opencode run` offers `--session`, `--continue` and
   `--fork` and no compaction flag, and the config exposes no compaction key; the binary
   carries a `session.compact` command and `session.compaction.{started,ended}` events, so the
   product compacts, but nothing on the CLI forces it. Those trials are recorded
   `compaction unavailable headlessly` with the resume still run and graded (E10-12).
3. **Claude Code's smallest compaction window is 100k tokens.** `--autocompact` is documented
   as `auto, or 100k–1M tokens`, so "small enough that the harness compacts before the next
   turn" is not reachable for a short trial.
4. **OpenCode records no reasoning effort.** The session store's message rows carry `modelID`,
   `providerID`, `cost` and `tokens` and no effort field, so `model.json.effort` is `null` for
   every OpenCode trial. `--variant` sets it per run but is not read back.
5. **OpenCode writes no init event.** The session store carries no catalog, so the condition
   witness for an OpenCode trial is `opencode debug skill` under that home (the loader's own
   catalog record, captured with no model call) rather than the session's own record.
6. **The prompt names the skill through the run-directory path.** The adapter's run root is
   `${TMPDIR}/recheck-v2` (pilot contract section 2, every profile's section 3), and three
   installed things are written for exactly that path: the Claude launcher's `--add-dir`, the
   OpenCode `external_directory` allow rule the install writes from its own `TMPDIR`, and the
   helpers' own default. E10-4 also says the prompt "never names recheck-v2", and the prompt
   must name the run directory. The runner keeps the working path, records the breach in
   `command.json.run_root_note`, and takes `run_root_name` in the plan so the control room can
   flip it once the setups accept a neutral segment.
7. **`absent` is a removal, not a never-install.** See `install` above.
8. **`claude plugin uninstall` leaves the cache copy on disk.** Measured on 2.1.272: the
   uninstall prints `✔ Successfully uninstalled plugin: recheck-v2` and drops it from
   `claude plugin list`, and `config/plugins/cache/tony-skills/recheck-v2/0.1.0/skills/recheck-v2/`
   is still there afterwards — so the absent home would hold the very files E10-3 forbids. The
   runner removes the leftover with its own `rmtree` and names it in the install record. Codex's
   `codex plugin remove` cleans its cache; only Claude Code's does not.
9. **`codex plugin remove` needs the qualified name.** A bare `recheck-v2` is refused with
   `plugin requires --marketplace unless passed as <plugin>@<marketplace>`.
10. **`opencode debug skill` truncates into a pipe.** Exactly 65,536 bytes through a pipe,
    67,934 into a file, on the same command. The catalog capture goes to a file
    (`run_cmd(..., stdout_path=…)`), or the condition witness is unparseable JSON.
11. **A cut session writes no `launch.json`.** The cut kills the launcher's process group before
    its own post-step, so the session id comes from the harness's own stream (the trace's init
    event, the events stream's `thread.started`, the trace's `sessionID`) and `launch.json` is
    only the fallback. Without this the compaction resume has nothing to resume.
12. **A cut session's cost is never recorded.** The harness writes its cost in the `result`
    event, which never lands in a session that was killed, so the six continuation trials' first
    sessions have no cost figure at all.
13. **E10-12's one-second poll is too coarse to catch the cut.** On `F3-02-mixed-two-items` a
    one-second poll never saw a mixed state: the earliest checkpoint it read was already
    `done, done` at seq 9, because the core's two `adjudicate` commands land inside one second.
    At `--poll-interval 0.1` the cut landed at seq 3, phase `adjudicating`, one item done and
    one pending, with four lines in `checkpoint.log`. Every record says which interval it used.
14. **Two trials on one case would collide.** The run id is fixed at `<case id>-run` (E7), so
    two trials of the same case mint the same absolute run directory and the second destroys the
    first — found when a grade validated against a later trial's rebuild and reported 23
    semantic errors. The run root now carries an opaque per-trial segment (a digest of the trial
    id), and `grade` compares the run directory's `input.json` with the record's copy before
    trusting it, falling back to the trial's own `validate.txt` when the directory is no longer
    that trial's.
15. **A raw-trace scan reads prose as commands.** Scanning the whole trace for git commands
    found `git add`, `git commit`, `git rebase` and `git reset` — all of them inside the
    delivered skill body's own sentence forbidding them. The grader scans only the commands the
    session's own record shows it ran (`tool_commands`).
16. **`scan` skips binaries and vendored trees, with reasons.** A whole-pilot-root scan hit three
    identical `sk-`-shaped byte runs inside Codex's own dropped helper binaries and six JWT
    literals inside `node_modules/zod/**/tests/string.test.ts` (two in each of the three
    OpenCode homes). No campaign record lives in either, so a file with a NUL in its first 8 KiB
    and the directories in `SCAN_SKIP_DIRS` are skipped and counted. After that: 31,222 text
    files, 0 hits, across the campaign, the builder's scratch, this directory and the whole pilot
    root.
17. **Codex cannot reach its model.** `The 'gpt-6-astra' model is not supported when using Codex
    with a ChatGPT account` (HTTP 400) on every Codex session, so no Codex trial can produce a
    result and the operator's own `codex exec -m gpt-6-astra` shape is blocked too. The runner's
    Codex paths are otherwise exercised: install, verify, the leak scan, the launch, the rollout
    capture, and the `turn_context` reader, which read `gpt-6-astra` and effort `high` off the
    failed turn.
18. **`codex sandbox` cannot be driven on 0.154.0.** It requires `--permission-profile` naming a
    profile in an undocumented `[permissions]` table; fourteen shapes were tried, and the one
    the deserializer accepts aborts with signal 6 (exit 134) and no output. The no-model half of
    E10-8 is therefore not performed.

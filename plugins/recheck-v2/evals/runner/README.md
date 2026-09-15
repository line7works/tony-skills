# The E10 trial runner (lane S)

`runner.py` drives the recheck-v2 pilot campaign: it stages the checkout, installs and
verifies the three harness setups in their three homes each, probes the environment a launched
session actually carries, plans a campaign, runs one trial end to end, grades it against the
answer key, runs the routing and continuation trials, scans every record for credential
shapes, and reports. It sits beside the E7 check runner under `evals/checks/`.

Built at step E10 of the skills v2 execution plan under the lane contract
`docs/plans/2026-09-14-recheck-v2-e10-runner.md`. The pilot contract
(`skills/recheck-v2/references/pilot-contract.md`, revision 5) outranks that document, and
that document outranks the E9 lane contract at E10. Astra's review of the first build
(RUNNER REJECTED, 20 BLOCKER, 6 MAJOR, 1 MINOR) and the control room's rulings E10-40 to
E10-53 are the predicate for everything marked **fix round** below; section 11 is the history
of what the first build claimed and what replaced it.

- Python 3.9 syntax, standard library only. The grading step calls the core's
  `validate-result.py` through `uv run`, the way the E7 runner calls things, and imports
  `evals/checks/match.py` from its path.
- One JSON document on stdout and nothing else; every diagnostic on stderr. **`--help` text on
  stdout is the documented A7a exception** (E10-52): `argparse` prints usage to stdout and
  every E9 helper answers `--help` the same way, so the fifteen `--help` exits of 0 with human
  text are deliberate and are the only non-JSON stdout the runner produces. An unknown
  argument is still exit 2 with empty stdout.
- Exit **0** success · **2** a usage slip · **3** a missing binary, setup or record ·
  **1** anything else (ruling A7a, E10-9).
- Every subcommand runs from any working directory and refuses to overwrite a record.

## Contents

1. [The wall and the key lock](#1-the-wall-and-the-key-lock) · 2. [Subcommands](#2-subcommands) ·
3. [The trial record](#3-the-trial-record) · 4. [plan.json](#4-planjson) ·
5. [The environment allowlist](#5-the-environment-allowlist) ·
6. [The fake harness and `check`](#6-the-fake-harness-and-check) ·
7. [Where each ruling is implemented](#7-where-each-ruling-is-implemented) ·
8. [Codex quirks](#8-codex-quirks) · 9. [Tests](#9-tests) ·
10. [What the harnesses cannot do](#10-what-the-harnesses-cannot-do) ·
11. [History: what the first build claimed](#11-history-what-the-first-build-claimed)

## 1. The wall and the key lock

`evals/answer-key/` and `evals/trigger-set/held-out/` are opened by exactly three code paths,
all of them below the `the wall` marker in `runner.py`:

| path | what it opens | why |
|---|---|---|
| `grade` (`key_entry`) | the lane's key file, for the case being graded | E10-11 |
| `routing-score` (`expectation_of`) | both files, for the expected target per entry | E10-13 |
| `routing` (`request_text`) | the tuning file directly; a **held-out** entry's text through a subprocess that prints that one entry's text and nothing else | E10-13 |

`plan` reaches the held-out **ids** the same way (a subprocess that prints ids only), so the
sealed text never enters the runner's own process.

**The boundary is `instruction-bound + measured`, not enforced (E10-40).** The three harnesses
run every trial as the same user with no read sandbox — the E9 profiles record unrestricted
file reads on all three, and Codex confines writes only — so no process boundary the runner
can build keeps a model under trial from a readable file. Astra's prescription ("place keys and
grading records outside the launch process's enforced read access") is not reachable on these
setups and E10-40 records it as such. What the runner does instead, all of it mechanical:

1. **The key lock.** Every launch path (`run`, `routing`, `continuation`, `probe-env`) calls
   `close_key()` before it launches: both directories go to mode `000` and stay there. `grade`
   and `routing-score` reopen them inside a `with key_open(...)` block, after the barrier
   below, and close them again on the way out. A crash therefore leaves them closed, and
   `campaign start` refuses until `campaign start --reopen-key` (or `key-state --reopen`) is
   run by hand and logged.
2. **The grading barrier.** Neither grading path opens a key while any process of the attempt
   is alive. Three sources are checked, not one filename: the campaign's own
   `processes.jsonl` (written before each launch and bound to `(trial, attempt)`), every
   `child.pid` under every capture directory of the record (`harness/`, `harness-first/`,
   `harness-second/`), and the pid fields a launcher writes into `launch.json` or
   `pointer.json`.
3. **Measurement.** The grader scans every trial's native tool records for reads of a campaign
   record outside the trial's own opaque tree (`records_reached`) and for reads of the skill
   files under the absent condition (`skill_file_reached`, E10-3).
4. **Links.** `stage` copies no symlink at all and refuses a stage holding one; `install` and
   `verify` survey every home and fail on a link whose resolved target lands in the place the
   rule protects — the answer key, the held-out set, or one of the campaign's own record trees.
   Every other escaping link is recorded with its target, because `uv` fills each home's virtual
   environment with interpreter symlinks and the Claude Code install builds its local
   marketplace out of links into the stage; refusing "any link" refuses every install.
5. **The sentinel.** `check` plants a file inside a trial's opaque tree and another outside it
   under the campaign root, runs a trial, and records what a child could and could not read
   while the key was closed. The record carries the label `instruction-bound + measured`.

`grade` writes `grade.json` into the trial record and `grade --summary` prints counts only. A
`grade.json` carries expected values as reasons: read the summary, never the file.

**The test-only stand-in (E10-21, narrowed by E10-45).** `RECHECK_RUNNER_KEY_DIR=<dir>` and
`RECHECK_RUNNER_HELDOUT=<file>` point `grade` and `routing-score` at stand-ins a test wrote
itself. They are honoured only with `RECHECK_RUNNER_TEST=1` **and** only for a campaign the
runner itself marked synthetic — `plan --synthetic`, or any launch that ran a
`--fake-launcher`, which writes a `SYNTHETIC` marker into the campaign. Set without the flag,
the runner exits 2 with `key stand-in outside test`; set on an ordinary campaign, it exits 2
with `key stand-in outside a synthetic campaign`. A grade of a real trial can never use one.

## 2. Subcommands

Every subcommand takes `--campaign <dir>`, the campaign directory under
`~/.local/share/skills-v2-pilot/e10/`. `check` and `key-state` accept it and ignore it.

### `stage [--refresh]`

A copy of the checkout at the campaign commit under `<campaign>/stage/`, with
`plugins/recheck-v2/evals/` and `__pycache__` excluded (E10-6). Writes `stage.json`: the
commit, the staged tree's `plugin_tree_sha256` (every file under the staged
`plugins/recheck-v2/`, sorted relative paths, `<path>\0<sha256>\n` concatenated, as
`fixturelib` hashes), the file count, the canonical `content_sha256` from a fresh
`recheck.py skill-identity`, the proof that no `answer-key`, `held-out` or `evals` directory
survived the copy, the link survey, and the path of a **file manifest** record listing every
staged file with its sha256 and size (E10-53(3), so a tree hash can be recomputed later).

Refuses to replace an existing stage without `--refresh` (exit 2). **Fails** (exit 1) when the
stage still holds any of the three names, when the fresh `skill-identity` did not produce a
64-character digest (E10-52: a `null` digest is not a successful identity), or when the stage
holds any link at all.

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
skill removed by the harness's own mechanism*, not a home that never held it. The record names
what was removed (`uninstalled_after_install`, `removed`). E10-3's words are "never held
recheck-v2 on any surface"; the runner cannot reach that without editing a setup, so it is a
finding.

Every install record carries `home_leak_scan` (the walk that proves no `answer-key`,
`held-out` or `evals` name exists anywhere under the home, E10-6), a `link_survey`, and the
path of a **full home inventory** record: every file under the home with its sha256 and size,
plus the home's tree hash (E10-53(3), so a later reader can prove what was and was not there).
A non-empty leak scan, a failed step, or a link leaving the pilot root is exit 1.

E10-20: this is the only path that passes `OPENROUTER_API_KEY`, and only to the OpenCode
install script. Existence is checked, the value is never printed, logged or copied.

### `verify [--setup NAME]... [--home ...]`

Runs each setup's `verify-install.sh` and compares the installed `content_sha256` with a fresh
`uv run skills/recheck-v2/scripts/recheck.py skill-identity` of the checkout — compared, never
typed. Also re-runs `home_leak_scan` and the link survey per home.

**Exit 3** when the fresh identity did not compute, and **exit 3** for a home that is not
installed: "no skill in a home that does not exist" proves nothing, so an absent home is a
missing prerequisite, never an `ok: true` row (E10-52). **Exit 1** when any required row
failed — every failed row fails the command.

### `probe-env [--setup NAME]... [--home ...] [--timeout N] [--refresh]`

A trial-shaped session per setup and home whose whole prompt is `env | cut -d= -f1 | sort`.
Each probe writes its own **immutable** record, `<campaign>/probes/<setup>-<home>/probe-<stamp>.json`;
`--refresh` runs another probe **beside** the old one and never replaces it (E10-43,
E10-53(5)). The aggregate index takes a reserved name of its own under `records/`.

A probe **fails** when the session exited non-zero, when it printed nothing, when the runner
passed a banned name, or when a banned name appears that is not on that harness's measured
own-tool-shell list (`HARNESS_CREATED_ENV`). `campaign start` refuses to start without one
current successful probe per setup and home — nine for the full plan — where "current" means
bound to this campaign's staged commit and `plugin_tree_sha256` (E10-42).

### `plan [--plan FILE] [--refresh] [--synthetic]`

Writes `campaign.json` from a `plan.json` (section 4), or from the full E10 default plan when
`--plan` is omitted. **The whole plan is validated before any write** (E10-43): unique setup
names that are identifiers with no separator and no dot segment, a supported harness per
setup, comparison cases inside E10-1's six with no duplicate, the continuation set on
`F3-02-mixed-two-items` in the available condition, conditions inside `available|absent`,
positive repetitions and timeouts, a well-formed routing set, and no duplicate among every
trial id the plan mints. Adds: `planned_at`, the stage record, the measured `path_entries`,
the allowlisted names, `case_lanes`, the fixed order per setup (E10-5), the routing,
manual-only and continuation orders, and the trial counts.

`--synthetic` marks the campaign synthetic so an E10-21 stand-in is honoured (tests and
`check` only).

### `run <trial-id> [--plugins NAME]... [--fake-launcher PATH]`

One comparison trial end to end, in this order:

1. a fresh opaque fixture build into `<campaign>/tmp/<digest>/fixture` — the digest is over the
   campaign id, the full trial id and the attempt number (E10-41), so the workspace path the
   model sees names no setup, case, condition, repetition or attempt, and two attempts never
   mint the same path;
2. a fresh run directory at `<campaign>/tmp/<digest>/runs/<case id>-run`, with the canonical
   `result.schema.json` copied in (never edited, E10-4). An existing run directory is
   **refused**, never removed (E10-43);
3. the prompt from the E10-4 template, identical bytes in both conditions after each trial's
   own paths are normalised;
4. the launch through the staged copy's `setups/<harness>/launch.sh` under the allowlist, with
   `TMPDIR` fixed to `<campaign>/tmp/`, the key closed, and the process registered in
   `processes.jsonl` before it starts;
5. the collection (section 3), `validate-result.py --strict` against the **live** run
   directory with its verdict bound to the hashes of what it validated, and the credential
   scan — a hit, or an unreadable mandatory capture, fails the launch (E10-52);
6. one line in `trials.jsonl`, and an interruption line for any outcome that is not `complete`.

The status comes from the **process outcome**, not from what happened to be on disk:
`timed_out` if the limit was reached, `launch_failed` on a non-zero exit, `no_result` when a
clean exit wrote no `result.json`, else `complete` — and `command.json` and the ledger carry
the same one (E10-43).

It never grades. A used trial directory is exit 2 (E9-34). `--fake-launcher` is for the tests
and `check`, and marks the campaign synthetic.

### `campaign start|status|stop [--foreground] [--lanes N] [--reopen-key] [--skip-probe-gate]`

`start` runs the whole plan as a detached process writing `runner.log`, `trials.jsonl`,
`attempts.jsonl`, `processes.jsonl` and `campaign.pid`; `--foreground` runs it in this process.

**One atomic ownership handshake (E10-51).** The parent claims `campaign.pid` with
`O_CREAT|O_EXCL` and writes a token; the detached child is given that token, verifies it, and
rewrites the file with its own pid; the parent waits for that handshake and reports the pid
that actually owns the campaign. **The launch options are preserved** into the detached
process (`--fake-launcher`, `--compact-tokens`, `--poll-interval`, `--lanes`).

**One sequential worker per setup, the lanes concurrent (E10-5, E10-51).** Each lane runs its
own queue strictly in order, so Claude Code and Codex never overlap with themselves; the three
lanes run at the same time and every record's own `started_at`/`ended_at` proves it.

Resumable from disk: a restart **skips** every trial whose record carries a terminal status and
**reruns nothing on its own** (E10-9; `rerun` is the operator's call, E10-15). A directory
without a `command.json` is a **partial** attempt: skipped, named in `status`, and retained by
`report` (E10-43).

`status` prints the planned count, the complete and recorded counts, the failed outcomes, the
partial records with their reasons, the live registered processes, the lane stops, the key
state, the per-lane counts and the next trial. `stop` terminates the campaign's own process
group **and every registered trial process group**, collects each one's status, writes an
interruption line per process, and leaves the key closed.

### `rerun <trial-id>`

A new attempt directory `attempts/<n>/` beside the failed one, **dispatched by kind**:
comparison, continuation or routing (E10-44 — the first build parsed every id as a comparison
id, so a failed routing or continuation trial could not be retried at all). The failed attempt
stays on disk and stays counted in `trials.jsonl`; the rerun is a line of its own with
`attempt: n`, `attempts.jsonl` journals it, and `interruptions.jsonl` records it against that
attempt number.

### `grade <trial-id> [--attempt N] | --all [--summary]`

`validate-result.py --strict`, then `match()` from `evals/checks/match.py` against the key
entry's `expected`, then every metric of E10-11. `--all` covers **every comparison and
continuation attempt**, `attempts/<n>/` included (E10-44). Refuses while any process of the
attempt is alive (exit 1). Exit 3 for a record that is not there. **Refuses a key whose
`runs_at` does not include E10, before matching** (exit 1, E10-45).

Fields of `grade.json`:

| field | what it holds |
|---|---|
| `trial`, `attempt`, `grade_path` | the identity of what was graded and where the file was written |
| `inputs_bound_to` | the staged commit, the plugin tree hash, the case, the fixture tree hash, and the sha256 of the result, the input, the reply and the key file (E10-45) |
| `key_runs_at`, `key_runs_at_includes_E10` | the key entry's `runs_at` (always true: a non-E10 key is refused) |
| `key_stand_in` | whether an E10-21 stand-in supplied the entry |
| `validator` | the exit, `ok`, the schema and semantic errors, the skips, `skip_count`, `failed_for_a_skip`, `binding_ok` |
| `match` | `match()`'s verdict and its reasons |
| `dispositions` | the matcher form, per item: expected, observed, match and how the pair was made; plus `unmatched_expected` and `all_matched` |
| `false_fixed` | the items the key pins as not fixed or broke that the result reports `fixed`, and the count |
| `evidence_sufficient` | per item: the evidence count, the method, the static reason, and `commands_run` / `observed` as E8-A43 names them |
| `trace_witnesses` | every native action scanned, the captures they came from, the refused actions, the writes outside, the git rows with their options, the web tools |
| `scope_violations` | the result's own `boundary_violations` plus the grader's own scan |
| `unauthorized` | git commands that change branches, index or history; web tools; writes to a pilot home |
| `interop` | the session's **actual final reply** against the Output block's required lines and one line per item, by the item's own location |
| `skill_file_reached`, `records_reached` | E10-3 and E10-40's measurements |
| `time`, `cost`, `model` | copied from `command.json`, `cost.json`, `model.json` |
| `floor_met` | the result's `run.model` block beside `model.json`'s id (E10-16) |
| `continuation_invariants` | on a continuation trial: `continuations == 1`, done items and prior verifier calls unchanged, start identity preserved (E10-47) |
| `checks`, `ok`, `ok_because` | every mandatory metric, the verdict, and the names of the ones that failed |

`ok` is the conjunction of **every** check: the match, the validator's `ok` and exit 0, zero
skips, the validation binding, no false-fixed item, sufficient evidence, interop, no scope
violation, no unauthorized action, every disposition matched, and — on a continuation trial —
the three invariants (E10-45).

A trial with no `result.json` grades every metric as `no_result` and counts as a failure of the
condition, never as excluded.

`grade --summary` prints the counts **and** a `per_trial` block whose fields are listed in
`SUMMARY_SAFE_FIELDS`. `match`'s *reasons* are never in it, because they quote the expected
values the wall keeps from a builder.

### `routing <trial-id>`

One routing trial: the request as the opening line of a fresh session in an empty
git-initialized workspace inside the trial's own opaque tree, with no build doc, the plan's
300-second timeout, and the harness's own turn limit where it has one — **on this machine none
of the three has one**, recorded per trial in `command.json.turn_limit` with the measurement.

The observed target comes from the harness's own record, never by asking the model:

| harness | the record the observed target comes from |
|---|---|
| `claude-code` | the `Skill` tool call in the session's own trace, with its line and tool-use id |
| `codex` | E10-33 as E10-46 corrects it: the **last `SKILL.md` read before the first non-read action**, or an injected `<skill …>` message. The developer `<skills_instructions>` catalog message is **not** a read; every candidate read is listed and a browse of several files is its own row |
| `opencode` | the first `skill` tool call in the session store that **completed with a delivered body** |

The catalog is parsed in each harness's **native** format — Claude Code's init-event JSON,
Codex's textual `codex plugin list` (enabled rows only), OpenCode's `debug skill` JSON — and
the full required set is verified. A catalog holding a blocked name, a missing catalog, or a
missing required name is a `profile_breach`: the trial is recorded, a **lane stop** is
persisted under `<campaign>/lane-stops/<setup>.json`, and no later launch of any kind on that
setup can pass (exit 1, E10-46).

The required set is written in **each catalog's own vocabulary**: Claude Code's and Codex's
catalogs name plugins, OpenCode's `debug skill` names skills, so `sun` is required of the first
two and `sunrise`/`sunset` of the third. `manual-only-probe` is required of all three: measured
2026-09-15 from the three live routing catalogs, every setup installs it — Claude Code through
its own local marketplace, Codex through the `recheck-probes` marketplace its `install.sh`
builds, OpenCode through the skill-folder copy.

A lane stop is a record. `lane-stop --campaign C` shows the standing stops;
`lane-stop --setup S --clear --why "…"` clears one, moving the stop file into
`lane-stops/cleared/` with the reason beside it and writing an interruption line. Nothing is
deleted and no later reader loses the fact that the lane stopped.

### `routing-score [--revision REV]`

Behind the wall, and behind the same grading barrier as `grade`. Writes
`<campaign>/routing/trigger-set-<setup>-<revision>.json` per setup in the trigger README's
shape: one row per entry with `observed_target`, `activated` and `matches_expected`, the tuning
and held-out rates kept separate, the blocked-station leak rows, and the **manual-only row**.
A rescore takes the next free name; a score file is never replaced (E10-43).

The manual-only measurement is one dedicated request outside both evaluation sets, added by the
runner to every routing lane, in words rather than the explicit `/manual-only-probe` form, and
counted apart from `routing` in the plan's counts — so neither the tuning nor the held-out
denominator changes (E10-53(4)).

### `continuation <trial-id> [--compact-tokens N] [--poll-interval S]`

`cont-<setup>-<case>-<handoff|compaction>-r<n>`. Launches the trial and polls
`run/checkpoint.json` and `run/checkpoint.log` **at least ten times a second** — E10-47 fixes
both the default and the maximum at 0.1 s, and a coarser `--poll-interval` is refused.

**The cut is what was retained (E10-47).** The poller notices the first checkpoint showing one
item `done` and one `pending` in phase `adjudicating` or `verifying`; the runner then stops the
process group (SIGTERM, SIGKILL after five seconds) and waits for it to be gone; only then does
it read the checkpoint and its log off disk, copy that exact pair into the record as
`at-cut-*` with their hashes, and check that the **retained** pair shows the state the cut
claims. Every figure in `cut` — `seq`, `phase`, `done`, `pending`, `checkpoint_log_lines`,
`start_identity` — comes from the retained pair. A pair that disagrees is an **invalid cut**:
`valid: false`, `invalid_because` naming both states, an interruption line, and the resume
still run so the record carries what the harness did.

Then, per kind:

- `handoff`: a fresh session, never having seen the run, with the resume prompt.
- `compaction`: the same session continued by the harness's own resume mechanism with its
  compaction setting. `compaction_witness` is a **native compaction event in the resumed
  session's own record, before the resumed work** — prose is never a witness (E10-47), and the
  witness carries the file, the event type, its line, the line at which the resumed work
  starts, and whether the ordering holds.

Both are graded like a comparison trial, plus the three continuation invariants of E10-12.

### `scan [PATH...]`

The credential scan over every record: the OpenCode scanner's shapes plus JWT and `sk-`
shapes. **Every retained capture is scanned whatever its extension and whatever its first
bytes hold** — a NUL no longer buys a free pass (E10-52) — and an assignment delimiter (`=`,
`"`, `:`) is a boundary, so `OPENROUTER_API_KEY=<key>` is a hit while a `sk-` run inside a
longer base64 blob is not. Overlapping shapes count once (the most specific claims the span).

The only exemption is each setup's **actual configured** credential store by resolved path:
Codex's `auth.json` and its child's, and OpenCode's `xdg-data/opencode/auth.json`. **Claude
Code has none** — its sign-in is the macOS Keychain — so a file of that name under its pilot
home is scanned like any other capture. A hit names the file, the shape, the offset and the
length, never a value. A hit, or an unreadable mandatory capture, is exit 1.

### `report`

`tables/table.md`, `tables/table.json` and `tables/report-skeleton.md`. Every number is
computed from `trials.jsonl` and the grade files **joined by (trial id, attempt)**, and every
row names the attempts, the records and the grade files it came from. Available trials are
split by `activated` (E10-4). Partial attempts are retained and listed. Launches
(`processes.jsonl`) are counted apart from trials, and journalled attempts apart from ledger
lines.

**`report` never writes `report.md`** — that is the operator's own file (E10-43). Corrected
measurements (below) are applied only where their hash binding still holds; a stale one is
listed and not applied. A credential shape anywhere in the records fails the report gate.

### `measure --trial T [--attempt N] --field cost|wall --corrects PATH --raw-value V --corrected-value V --why TEXT [--evidence PATH]...`

A hash-bound corrected measurement record under `<campaign>/measurements/` (E10-48). Raw
history is never edited: the correction names the record it corrects, that record's sha256 at
the time of writing, the field, the raw value, the corrected value, why, and the files the
corrected value was read from. `report` consumes it only while the binding holds.

### `lane-stop [--setup S --clear --why TEXT]`

Show the standing lane stops, or clear one with a reason (E10-46). A cleared stop moves to
`lane-stops/cleared/` with `cleared_at` and `cleared_because`; the log and
`interruptions.jsonl` both record it.

### `key-state [--reopen]`

The mode of the two key directories, and the one hand-run reopening E10-40 allows, logged.

### `check [--tests-only] [--scratch DIR]`

The runner's self-test, with no model and every harness boundary substituted:

1. the whole test suite;
2. one dry trial against the fake harness, whose result the **real** `validate-result.py
   --strict` passes with zero schema errors, zero semantic errors and zero skips, and which
   grades `ok` against a stand-in key `check` wrote itself;
3. the **negative metric cases** — `missing-evidence`, `missing-chat`, `skip`, `false-fixed`
   and `wrong-key-phase` — each of which must fail its grade, naming the metric that failed;
4. the **read-boundary sentinel** of E10-40, with the interpreter's own version recorded.

Exit 1 when any of them fails. `check` never leaves the key closed behind it.

## 3. The trial record

`trials/<trial-id>/`, with `<trial-id>` = `<setup>-<case>-<available|absent>-r<n>`. The record
is behind the wall from every model; the fixture and run paths the model saw live under the
campaign's own `tmp/<digest>/` and are copied into the record afterwards.

| file | what it holds |
|---|---|
| `command.json` | the fields below |
| `prompt.txt` | the prompt bytes, exactly as the harness received them |
| `harness/` | everything the setup's `launch.sh` wrote: the trace, the transcript or rollout or session-store dump, `launch.json`, stderr, and the catalog capture |
| `harness-first/`, `harness-second/` | a continuation trial's two sessions, with `at-cut-*` beside the first |
| `model.json` | `id`, `effort`, the **record they were read from**, the session binding, the native init event, and `configured` (what the launcher was told) kept apart (E10-50) |
| `cost.json` | `total_cost_usd`, token counts, and the record; `null` when the harness printed nothing |
| `run/` | the run directory copied whole after the harness ended and after the validation, verifier captures included |
| `fixture/` | this trial's opaque fixture build, copied in after the trial |
| `input.json`, `result.json` | copies from the run directory, or absent with `absent: true` in `command.json` |
| `chat.md` | what the core wrote into the run directory |
| `reply.md` | the **session's own final reply** (`result.txt`, `final.md`, or the store's last text part) — what `interop` grades |
| `validate.txt` | the exact output of `uv run validate-result.py … --strict`, with the exit status on the last line |
| `validate.json` | the hashes that verdict was bound to (E10-45) |
| `scan.json` | the credential scan of this record |
| `grade.json` | written by `grade`, never by `run` — the one replaceable file |
| `attempts/<n>/` | a rerun's own record, with the same layout |

`command.json`: `trial`, `attempt`, `kind`, `argv`, `cwd`, `allowlisted_env_names` (names,
never values), `launcher_env_names`, `started_at`, `ended_at`, `wall_seconds`,
`launch_wall_seconds`, `exit`, `timeout_verdict`, `condition_witness`, `catalog`, `activated`,
`setup_home`, `setup`, `harness`, `condition`, `case`, `staged_commit`, `plugin_tree_sha256`,
`setup_tree_sha256`, `fixture`, `opaque_tree` and `opaque_tree_mapping`, `run_dir`, `run_root`,
`run_root_note`, `workspace`, `reply_source`, `result_absent`, `absent`, `status`,
`validate_exit`, `validation_binding`, `key_boundary`, `scan_hits`, and on OpenCode
`store_separation_witness` (E10-49). A continuation trial adds `cut`, `compaction`,
`compaction_witness`, `checkpoint_after`, `continuations_equals_1`, `resume_prompt` and
`continuation_invariants`.

`model.json` per harness, measured (see section 10 for the effort gap):

| harness | model | effort | cost |
|---|---|---|---|
| `claude-code` | the native `system/init` event, and the last non-sidechain `assistant` record bound to that session | that record's top-level `effort` | the `result` event's `total_cost_usd` |
| `codex` | `turn_context.model` in the rollout, bound to the `session_meta` id | `turn_context.effort` | no dollar figure; the events stream's token counts |
| `opencode` | `providerID/modelID` from the session store's assistant rows, bound to the store's session id | **none exists on 1.18.31 → `null`** | the assistant rows' `cost` summed, with the token totals |

In every case the id is `null` when the harness wrote no native record, and the launcher's own
label lives in `configured` and never becomes an observation (E10-50).

`trials.jsonl`, one line per trial **attempt**: `id`, `attempt`, `kind`, `status` (`complete`,
`no_result`, `timed_out`, `launch_failed`, `profile_breach`), `exit`, `wall`, `cost`, `model`,
`effort`, `activated`, `record`. `interruptions.jsonl` carries every timeout, launch failure,
rerun, stop, wall-clock gap, invalid cut, credential hit and skipped record, each against its
own `(trial, attempt)`. `attempts.jsonl` journals every attempt's creation before it runs.
`processes.jsonl` journals every launch process: reserved before the spawn, started with its
pid and pgid, ended with its status.

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
fixtures of E10-1, the three setups of E10-2, the two conditions of E10-3, two repetitions —
**6 × 3 × 2 × 2 = 72 comparison trials** — plus the continuation set on
`F3-02-mixed-two-items`, one `handoff` and one `compaction` trial per setup, **6 continuation
trials**; plus the routing set, all twenty trigger-set entries (12 tuning, 8 held-out) at three
repetitions per setup, **180 routing trials**; plus **3 manual-only trials**, one per lane,
counted apart (E10-53(4)); plus the `probe-env` sessions, three setups × three homes. The
timeouts are E10-14's.

Optional keys: `entries` may be `"tuning"`, `"all"`, or an explicit list of ids; a setup entry
`{"name": "opencode-deepseek", "harness": "opencode", "model": "deepseek"}` adds the DeepSeek
setup in one line (E10-2: the runner takes its setup list from the plan, never from code);
`run_root_name` sets the run root's segment inside the trial's opaque tree.

The order (E10-5) is written into `campaign.json` before the first launch: per setup, case by
catalog order, then repetition 1 available, 1 absent, 2 available, 2 absent. The three setups
are three lanes; each lane is strictly sequential and the lanes run concurrently.

## 5. The environment allowlist

Every process the runner starts — an install, a verify, a launch, a probe, a grade, a fixture
listing, the held-out one-entry lookup, the self-test, and the detached campaign process itself
— is built by **one function** (E10-42). `run_cmd` refuses a child with no environment, so a
new call site cannot inherit the session's environment by omission, and it refuses any
environment carrying a banned name.

The environment is built from nothing with exactly: `PATH` (the fixed list of E10-7), `HOME`,
`TMPDIR` (`<campaign>/tmp/`, the same for the installs and the trials because OpenCode's
`external_directory` rule is written from it, E9-27), `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`,
`TERM=dumb`, `SHELL=/bin/zsh`, **`USER`**, plus the one variable the setup's own launcher needs
for itself: `SKILLS_V2_PILOT_HOME`, `RECHECK_CODEX_HOME`, or `RECHECK_OPENCODE_SETUP` (and
`RECHECK_OPENCODE_TIMEOUT`).

Exactly two names matching a banned shape may ever reach a child, each with the measurement
that put it there (`DECLARED_ENV`): `CODEX_HOME`, the Codex home pointer the harness's own
launcher sets for itself (E9-25, E10-7), passed directly only for the no-model `codex plugin
list` catalog capture and the `codex exec resume` of a compaction trial; and
`OPENROUTER_API_KEY`, the one install-time credential of E10-20. Every other banned name is a
hard failure at the boundary.

**`USER` is the one name E10-7's measure-and-add clause added.** The four sessions that
measured it were run by the first builder and **not retained as records**; E10-53(1) struck
their quoted costs from the estimate and required the measurement to be re-made as retained
probe records, which the fix round did. The finding itself stands: the sign-in lives in the
macOS Keychain (`security find-generic-password -s "Claude Code-credentials"`, class `genp`),
not in a variable, and the harness reaches it only when `USER` is set. `USER` names the
process's own identity, carries no credential, and matches no banned shape.

**What a launched session's own tool shells carry.** No banned name the runner passed, on any
setup. The harness sets its own: Claude Code puts `CLAUDECODE` and eight `CLAUDE_CODE_*` names
in every tool shell, and Codex puts `CODEX_HOME` and `GH_PAGER` there (E9-25 and E10-30 by
design). OpenCode's tool shell carries no banned name at all, which is E9-38 holding. So
E10-7's "the runner fails the campaign start if any banned name appears in the record" is a
gate on **what the runner passed**, plus a per-harness measured list: a banned name that is on
neither fails the probe outright (E10-42).

**Measured, and not something the parent can prevent**: `/bin/sh` adds `PWD` and `SHLVL`;
CoreFoundation adds `__CF_USER_TEXT_ENCODING`; the `/usr/bin/python3` xcrun shim adds
`SDKROOT`, `CPATH`, `LIBRARY_PATH` and `MANPATH`. None matches a banned shape and none carries
a credential.

## 6. The fake harness and `check`

`tests/fake/` holds a stub launcher per setup with the real launcher's own arguments, and
`fakelib.py` behind them. A stub does what a real session does, minus the model:

1. reads the run directory, the workspace, the slice and the build doc out of the prompt;
2. builds the input document from the fixture's own seeded `input.json`, replacing only the
   `invocation` object;
3. drives `scripts/recheck.py` through `start`, `record-call`, `adjudicate` and `record`, with
   a canned verifier report in the shape `references/verifier.md` fixes — the fake's own
   dispositions, never a key value;
4. writes the harness's own record in that harness's shape, including the delivery events the
   activation readers need (a `tool_result` for the Skill call, the developer catalog message
   for Codex, the textual `codex plugin list` capture, the OpenCode catalog JSON);
5. records the names its own environment carried, in `env-names.json`.

**Behaviour travels in a stub the test writes, not in the environment** (E10-52, finding 25):
`testlib.stub_launcher(...)` writes a one-line shell stub that exports what it needs and execs
`fakelib.py`, and `testlib.cut_stub(...)` writes a stub that plants a checkpoint/log pair and
waits to be cut (optionally advancing it on SIGTERM, which is the invalid-cut race made
deterministic). The old `RECHECK_FAKE_SLEEP` hook was handed to the runner, which stripped it
at its own allowlist before the launcher ever ran.

## 7. Where each ruling is implemented

| ruling | where |
|---|---|
| E10-1, the six fixtures | `DEFAULT_CASES`, `default_plan`, `validate_plan` |
| E10-2, the three setups; the setup list from the plan | `SETUP_CLASSES`, `make_setup`, `_selected_setups` |
| E10-3, the two conditions; the condition witness; `skill_file_reached` | `pilot_home`, `Setup.install`, `condition_witness` per setup, `trace_witnesses` |
| E10-4, the comparison prompt; the schema copy | `PROMPT_TEMPLATE`, `prepare_run_dir`, `activation` per setup |
| E10-5, repetitions and order | `order_of`, `build_fixture`, `_campaign_loop`'s lanes |
| E10-6, the staged copy | `do_stage`, `file_manifest`, `home_leak_scan`, `do_verify` |
| E10-7, the allowlist | `ALLOWED_ENV`, `path_entries`, `allowlist_env`, `Campaign.env`, `tool_env`, `DECLARED_ENV` |
| E10-9, the shape and the subcommands | `build_parser`, `main`, `Usage`/`Missing`/`Failure` |
| E10-10, the trial record | `collect_trial` |
| E10-11, grading and the metrics | `grade_one` and its helpers |
| E10-12, the continuation trials | `do_continuation`, `_launch_and_cut`, `_compaction_resume`, `compaction_witness` |
| E10-13, the routing trials | `do_routing`, `observed_target`, `catalog_names`, `_profile_breach`, `do_routing_score` |
| E10-14, timeouts and interruptions | `run_cmd`'s timeout, `_terminate_group`, `Campaign.interruption` |
| E10-15, the operator's rules | `campaign status`, `rerun`, `grade --summary` |
| E10-16, floors and provisional maps | `grade.floor_met` |
| E10-19, the effort witness | `model.json`'s `effort` and `source`; never a label |
| E10-20, the one install-time credential | `OpenCodeSetup.install`, `DECLARED_ENV` |
| E10-21, the test-only stand-in | `_stand_in`, `key_dir`, `heldout_file`, `Campaign.synthetic` |
| E10-40, the wall as a measured boundary | `close_key`/`open_key`/`key_open`, `link_survey`, `records_reached`, `sentinel_probe` |
| E10-41, the opaque tree | `Campaign.opaque_tree`, `run_root_of`, `run_root_note` |
| E10-42, one environment boundary | `tool_env`, `run_cmd`'s refusal, `do_probe_env`, `current_probes` |
| E10-43, identities, records and outcomes | `check_identifier`, `contained`, `validate_plan`, `reserve_record`, `outcome_status`, `Campaign.journal_attempt`, `campaign stop` |
| E10-44, attempts and grading | `graded_attempts`, `do_rerun`, `_dispositions`, `grade_path` |
| E10-45, the grading barrier and the grade | `harness_alive_for`, `refuse_while_alive`, `grade_one`'s `checks`, `_recorded_validation` |
| E10-46, witnesses from native records | `native_actions`, `trace_witnesses`, `catalog_names`, `_codex_reads`, `observed_target`, `stop_lane` |
| E10-47, the cut is what was retained | `_launch_and_cut`, `state_of_checkpoint`, `continuation_invariants`, `compaction_witness` |
| E10-48, measurements | `do_measure`, `measurement_records`, `do_report` |
| E10-49, OpenCode store separation | `OpenCodeSetup.store_separation_witness` |
| E10-50, model provenance | `model_record` per setup |
| E10-51, the campaign process | `claim_campaign`, `do_campaign`, `_campaign_loop` |
| E10-52, the scanner, the tests, the stage, the docs | `scan_paths`, `auth_store_exemptions`, `tests/`, `do_stage`, `do_verify`, this file |
| E10-53, Astra's five questions | `do_probe_env` (1), `file_manifest` (3), `MANUAL_ONLY_ENTRY` (4), immutable probe records (5) |
| E9-34, a record is never overwritten | every subcommand's refusal, `reserve_record` |
| E9-41, the timeout verdict | `run_cmd` collects the child's status before any verdict |
| E7-18, the opaque mount and the run date | `build_fixture`, `Campaign.opaque_tree`, `default_plan` |
| E8-A43, `commands_run` and `observed` | `_evidence` |

## 8. Codex quirks

The runner is launched from inside a `codex exec` (E10-8), so:

- **No `rm -rf`.** The Codex approval review rejects a command containing `rm -rf` even under
  `approval_policy=never`, so every removal in the runner goes through `rmtree()`
  (`shutil.rmtree`), never a shell command.
- **`</dev/null`.** A `codex exec` launched from a script needs its stdin closed; `run_cmd`
  gives every child `subprocess.DEVNULL` unless it is handing one a prompt on stdin.
- **A hard-link probe is declined by the model**, so the runner never asks for one; containment
  is proved by the allowlist, the walk of each home, and the link survey.
- **The nested verifier needs `-s danger-full-access`** (E9-21): under the outer seatbelt a
  nested `codex exec` at `read-only` or `workspace-write` initializes but every shell command
  it runs fails at `sandbox-exec: sandbox_apply: Operation not permitted`.
- **`codex exec resume` takes only its own options** (E10-35): `-C`, `--add-dir` and the
  sandbox line come **before** the `resume` subcommand.
- **The compaction witness is in the thread's rollout, not the exec event stream** (E10-36).

## 9. Tests

`tests/`, unittest, standard library, run from any directory:

```
RECHECK_RUNNER_TEST_SCRATCH=<dir> /usr/bin/python3 -m unittest discover -s plugins/recheck-v2/evals/runner/tests
RECHECK_RUNNER_TEST_SCRATCH=<dir> uv run python3 -m unittest discover -s plugins/recheck-v2/evals/runner/tests
```

No test touches a real pilot home: `testlib` relocates `PILOT_ROOT` before importing the runner
and hands the same two names to every child, and the runner honours the relocation only when
both are set. Every test restores the two key directories on the way out, whatever it did.

| file | covers |
|---|---|
| `test_cli.py` | `--help` on every subcommand (the documented A7a exception), the JSON-on-stdout rule, and every usage exit code |
| `test_env_allowlist.py` | the allowlist's shape, the banned pattern over every shape E10-7 names, a real launched child's own environment, and that only the OpenCode install ever sees the credential name |
| `test_wall.py` | the key lock closing on every launch path and a real child failing to read them, `grade` reopening and re-closing, `campaign start --reopen-key`, `records_reached` / `skill_file_reached`, the AST proof of which functions can reach a reader, the E10-21 and E10-45 refusals, the grading barrier from all three pid sources, and the link survey |
| `test_records.py` | the record layout and every `command.json` field, the opaque fixture path, the refusal to overwrite, `rerun`'s attempt directories, the timeout path driven by a sleeping **stub launcher**, the credential scan including a NUL capture and an assignment delimiter, the report's counts, and campaign resume from disk |
| `test_fake_end_to_end.py` | one trial per setup validating end to end, the model/cost/activation/condition-witness readers per harness, the grade paths, the routing and routing-score paths, the valid and invalid cut, the poll-interval refusal, and the compaction witness's ordering |
| `test_findings.py` | one test per finding of the review verdict, exercising the real path the finding names |

## 10. What the harnesses cannot do

Measured on this machine, 2026-09-14/15 (Claude Code 2.1.272, codex-cli 0.154.0,
opencode-ai 1.18.31):

1. **No read sandbox on any of the three.** The wall is `instruction-bound + measured`
   (E10-40), and section 1 says exactly what is mechanical and what is not.
2. **No turn limit.** E10-13 asks for `--max-turns 3` on Claude Code. `claude --help` on
   2.1.272 prints no `--max-turns` at all, and neither `codex exec` nor `opencode run` offers
   one. The routing trials are bounded by the 300-second timeout alone, recorded per trial.
3. **OpenCode has no headless compaction.** Those trials are recorded `compaction unavailable
   headlessly` with the resume still run and graded (E10-12, E10-26).
4. **Claude Code's smallest compaction window is 100k tokens.**
5. **OpenCode records no reasoning effort**, so `model.json.effort` is `null` for every
   OpenCode trial (E10-26).
6. **OpenCode writes no init event**, so its condition witness is `opencode debug skill` under
   that home (E10-26).
7. **`absent` is a removal, not a never-install.** See `install` above.
8. **`claude plugin uninstall` leaves the cache copy on disk** (measured on 2.1.272). The
   runner removes the leftover with its own `rmtree` and names it in the install record.
9. **`codex plugin remove` needs the qualified name.**
10. **`opencode debug skill` truncates into a pipe**: exactly 65,536 bytes through a pipe,
    67,934 into a file. The catalog capture goes to a file.
11. **A cut session writes no `launch.json`**, so the session id comes from the harness's own
    stream and `launch.json` is only the fallback.
12. **A cut session's cost is recorded only when the harness had already written its result
    event** (E10-48 correcting E10-27): the Claude hand-off's first session recorded
    $2.906325 at trace line 224 and was not cut; only a session killed before its result event
    has none.
13. **`codex plugin list` says `not installed`, never `disabled`.** An entry is active only
    when its STATUS column reads `enabled`; a parser that skipped only `disabled` counted the
    five blocked stations as present and stopped a correct lane (measured 2026-09-15 on the fix
    round's own live campaign).
14. **A session may ignore the run directory the prompt names.** Measured 2026-09-15: one
    Claude Code continuation session ran the whole recheck in the adapters' default run root
    `${TMPDIR}/recheck-v2/<minted run id>/` and wrote only `result.json` and `chat.md` into the
    named directory, so the cut poller — watching the named directory — never saw a checkpoint
    and the validator reported `the write list names checkpoint.json but the run directory holds
    none`. The runner records it; making the helpers refuse to mint a directory when one was
    named is a core change.
15. **A cut can be raced.** E10-47 orders stop-then-capture-then-verify, and on two of six live
    continuation trials the core advanced from `seq 3, one done one pending` to `seq 4, both
    done` between the poll and the process group dying. Those cuts are recorded **invalid** with
    both states named. Freezing the group with `SIGSTOP` before capturing would remove the race
    and is a ruling, not a builder's call.
16. **`codex sandbox` cannot be driven on 0.154.0.** It requires `--permission-profile` naming
    a profile in an undocumented `[permissions]` table; fourteen shapes were tried, and the one
    the deserializer accepts aborts with signal 6. The no-model half of E10-8 is not performed.
17. **The Codex account must be the Pro one** (E10-29). `The 'gpt-6-astra' model is not
    supported when using Codex with a ChatGPT account` (HTTP 400) on every Codex session while
    the free account is signed in.

## 11. History: what the first build claimed

Every statement below was true of the first build and is **no longer current**. It is kept so a
reader of the E10 records can tell a superseded claim from a live one.

| the first build said | what replaced it |
|---|---|
| "`--poll-interval` defaults to E10-12's 1.0 second"; the README's `continuation` section said the runner "polls every second" | E10-47: 0.1 s is both the default and the maximum, and a coarser interval is refused |
| "the run root carries an opaque per-trial segment (a digest of the trial id)" under `<campaign>/tmp/runs/` | E10-41: the whole tree is opaque — `<campaign>/tmp/<digest of campaign, trial id and attempt>/{fixture,runs}` — because the fixture used to be built under the **named** record directory and every prompt carried `/trials/<setup>-<case>-<condition>-r<n>/fixture/...` |
| "the run root is `${TMPDIR}/recheck-v2` … the runner keeps the working path and records the breach" | E10-22 renamed it to `${TMPDIR}/runs` in the setups; the note now records the name and the one documented exception (the run id's case name, E7 gap 13) |
| `grade --summary`'s `run_dir_is_the_retained_copy` field | replaced by `run_dir_is_this_trial_s` and by the hash-bound `validation_binding` |
| "`report` writes `table.md`, `table.json` and a `report.md` skeleton" | E10-43: the generated tables live under `tables/` and `report.md` is the operator's, never written by `report` |
| "the scan skips binaries and vendored trees, with reasons … 31,222 text files, 0 hits" | E10-52: every retained capture is scanned whatever its first bytes hold; the count is superseded by each campaign's own scan record |
| the four `USER` sign-in sessions quoted with their costs | E10-53(1): those sessions were not retained as records, their costs are struck, and the measurement was re-made as retained probe records |
| "the exemption list is the setups' own auth stores" including a Claude Code `auth.json` | E10-52: Claude Code has no configured store; its sign-in is the Keychain |
| E10-37's false hit described as `internal_chat_message_metadata_passthrough` | E10-52 corrects the citation: the 307-character match sat in `/payload/encrypted_content` at verifier rollout line 26. The classification is unchanged: a real key never sits mid-token in a base64 run |
| "23,332" in E9-34's parenthetical, and lane R's two MINORs | E10-17: still carried, listed in the README build record at the close, E11 named |

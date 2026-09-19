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
E10-53 are the predicate for everything marked **fix round** below. The control room then read
the twelve grades of that round's verification campaign and issued **E10-54 to E10-57**: the
run directory, the run id, the trial-conditioned expected document, the frozen cut and the
`--without recheck-v2` flag. Lane S then closed at E10-61, and **E10-62** ordered one scoped
pass on top of it: Tony's four pinned lanes, each with its own model and, where the harness
takes one, its own effort, honoured to each launcher and recorded in every trial's
`model.json`. The campaign then ran on the night of 2026-09-15 with all four lanes concurrent
for the first time and surfaced three runner defects no single-lane proof could reach;
**E10-68** is that fix round (the held-out barrier and concurrency, a string `message`, a dead
lane thread, and the OpenCode homes' prior-campaign state). Section 11 is the history of what
each round claimed and what replaced it.

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
11. [History: superseded claims](#11-history-superseded-claims)

## 1. The wall and the key lock

`evals/answer-key/` and `evals/trigger-set/held-out/` are opened by exactly three code paths,
all of them below the `the wall` marker in `runner.py`:

| path | what it opens | why |
|---|---|---|
| `grade` (`key_entry`) | the lane's key file, for the case being graded | E10-11 |
| `routing-score` (`expectation_of`) | both files, for the expected target per entry | E10-13 |
| `routing` (`request_text`) | the tuning file directly; a **held-out** entry's text through a subprocess that prints that one entry's text and nothing else — the FALLBACK since E10-68, used only outside a campaign start | E10-13 |
| `campaign start` (`cache_routing_requests`) | every PLANNED held-out entry's text, once, before the first launch, through a subprocess that writes the file itself | E10-68 (1) |

`plan` reaches the held-out **ids** the same way (a subprocess that prints ids only), so the
sealed text never enters the runner's own process.

**How a held-out request reaches a launch, and why the invariant still holds (E10-68 (1)).**
The lock below holds the held-out directory at mode 000 for the whole of every launch and
while any registered launch is alive. `routing` used to read the entry's text at LAUNCH time,
so with more than one lane alive a launch was nearly always alive, the read failed with
`PermissionError`, and the trial was recorded as raised with no process started — 72 of them
on the night of 2026-09-15. `campaign start` now writes every planned held-out request into
`<campaign>/routing-requests/<entry id>.txt` **before the first launch, while the keys are
open**, and a launch copies its own entry's file into `prompt.txt` with `/bin/cp`. The
subprocess writes the file itself and prints its digest and size; the digest of a file cached
by an earlier run comes from a digest subprocess too (E10-70, Astra's recheck5 item 1: the
first version hashed the cached file in the runner process, which read the text to do it).
So no held-out text enters the runner process at all, not even to hash or copy it — strictly
less than E10-13 allowed, which was one entry at a time; `tests/test_e10_68.py` checks by AST
that neither the cache nor the launch-time copy names a reader or a copier, and live that the
subprocess digests match the files. `routing-requests/index.json` records each file, its
sha256, its size and the key state at cache time, and never any text.
The two invariants E10-40 and E10-45 name are unchanged and are re-proved by
`tests/test_e10_68.py`: the sealed set never enters the runner process as a whole, and the
directory is at mode 000 at every launch (the test's stub records the mode it met, at every
launch of both lanes). The alternative shape — reopen the directory under the lock for the read
— is NOT taken, because reopening it while another lane's harness is alive is exactly what the
barrier forbids, and serialising every lane's launch against every other to avoid that would
remove the concurrency the campaign exists to have. The prompt text of a held-out routing
trial is a campaign record either way: once a trial runs, its `prompt.txt` holds it.

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
| `claude-code` | `install.sh --pilot-home <home>` | **`install.sh --pilot-home <home> --without recheck-v2`**: the skill is never installed | the same install, then `claude plugin install <name>@tony-skills` for every marketplace plugin except the five blocked |
| `codex` | `install.sh` (the home is `$RECHECK_CODEX_HOME` when set, else `$HOME/.local/share/skills-v2-pilot/codex/home`) | **`RECHECK_CODEX_HOME=<home> install.sh --without recheck-v2`**: the script's own run into that home, the skill never installed, then `auth.json` linked to the available home's store | a copy of the available home with its absolute paths rewritten (the way `install.sh` makes its own `homes/plugin-only`), then `codex plugin add <name>@tony-skills` per plugin |
| `opencode` | `install.sh --setup <home> --model <model>` (the plan's full `openrouter/...` id, or the short `qwen` / `deepseek` name resolved to it) | **`install.sh --setup <home> --model <model> --without recheck-v2`**: the skill folder is never copied in | the same install, then every unblocked plugin's skill folders copied into that directory |

**The absent home, and where the flag reaches (E10-56(1)).** All three `install.sh` scripts
take `--without recheck-v2`, which skips the one step that installs the skill and records
`without` in their own install report. On Claude Code and OpenCode the runner passes it for the
absent home, so that home **never held recheck-v2 on any surface** (E10-3) and the runner's own
second-guard removal is gone with it — no `claude plugin uninstall`, no cache removal (E10-24),
no skill-folder `rmtree`.

**Codex too, since E10-58(2).** `setups/codex/install.sh` honours `RECHECK_CODEX_HOME` (the
name `verify-install.sh` and `launch.sh` already read) and defaults to the pilot home as before,
so the runner points the script at the `absent` home and passes the flag. That home therefore
**never held recheck-v2 on any surface**: no plugin registry entry, no cache copy, no host-skill
folder, and a catalog without it; `derived_from_available` is `false` and nothing is removed
afterwards. Its `auth.json` and its child's are then linked to the available home's store, so
the credential stays one file (E9-26(c)). The **routing** home is still the copy of the
available one.

`recheck_v2_installation` in the install record says what happened: `how` is `never installed`
on every `absent` home, with the flag that did it and, on Codex, the name the home was pointed
by. The home inventory carries that same field beside every path under the home whose name holds
`recheck-v2` (empty on all three absent homes).

**The OpenCode home's prior-campaign state (E10-68, item (e) of the close hand-off).** Before
it runs the script, `OpenCodeSetup.install` clears everything under the home's
`xdg-data/opencode/` and `xdg-state/opencode/` except the harness's own auth store — the log,
the snapshot tree, `opencode.db` and its `-shm`/`-wal` siblings, `tool-output/`, `repos/` and
the lock directory. The 2026-09-15 campaign found that state still in place from earlier
campaigns, and in the absent trials the model reached prior campaign roots' paths through the
harness. `prior_state_cleared` in the install record names every path removed with its size in
bytes, every path kept with why, and the rule. **`xdg-cache/` is deliberately NOT cleared and
the record says so**: `xdg-cache/uv` is the uv wheel, sdist and interpreter cache that every
`uv run` of a trial and of `verify-install.sh` resolves against, and `xdg-cache/opencode/bin`
is the harness's own downloaded binary, which E10-68 names as off limits; clearing either
turns every install and every verifier call into a fresh network fetch immediately before a
campaign, and neither holds a session, a transcript or an earlier campaign root's path. The
`npm/` tree (the binary and its modules) and the auth store are untouched, so the one
install-time credential of E10-20 survives a reinstall.

Every install record carries `home_leak_scan` (the walk that proves no `answer-key`,
`held-out` or `evals` name exists anywhere under the home, E10-6), a `link_survey`, and the
path of a **full home inventory** record: every file under the home with its sha256 and size,
plus the home's tree hash (E10-53(3), so a later reader can prove what was and was not there).
A non-empty leak scan, a failed step, or a link leaving the pilot root is exit 1.

**The Codex home's model and effort lines (E10-62 item 2).** `setups/codex/install.sh` copies
exactly three lines out of the machine's own `~/.codex/config.toml` — `model`,
`model_reasoning_effort` and `sandbox_mode` — and fails if it does not find exactly three.
`CodexSetup.install` then replaces the first two, from the plan, **in the pilot home and its
child home only** (`_write_model_lines`, recorded as `model_lines` in the install record); the
`routing` home is the copy of the `available` one and is rewritten again for the record.
`~/.codex/config.toml` and `~/.codex/auth.json` are never written by any path here, and
`sandbox_mode` keeps coming from the real config because the plan says nothing about it. A
config with no line to replace is exit 1, never a silent no-op. `codex exec` takes no `-m` in
`setups/codex/launch.sh`, so the pilot home's config is what the session runs on.

**The Claude Code launcher's two flags (E10-62 item 2).** `setups/claude-code/launch.sh` takes
`--model M` and `--effort E` and puts each, when given, on the `claude` argv; neither is
defaulted, so an E9-shaped call runs exactly the command E9 measured. It records what it was
told as `configured_model` and `configured_effort` in `launch.json`, apart from `model`, which
is and stays the session's own init event.

E10-20: `install` is the only path that passes `OPENROUTER_API_KEY`, and only to the OpenCode
install script. Existence is checked, the value is never printed, logged or copied.

### `verify [--setup NAME]... [--home ...]`

Runs each setup's `verify-install.sh` and compares the installed `content_sha256` with a fresh
`uv run skills/recheck-v2/scripts/recheck.py skill-identity` of the checkout — compared, never
typed. Also re-runs `home_leak_scan` and the link survey per home.

**Exit 3** when the fresh identity did not compute, and **exit 3** for a home that is not
installed: "no skill in a home that does not exist" proves nothing, so an absent home is a
missing prerequisite, never an `ok: true` row (E10-52). **Exit 1** when any required row
failed — every failed row fails the command.

**The verifier subprocess's own exit is part of the success condition (E10-59 (26)).** It was
recorded and then ignored, so a `verify-install.sh` that crashed after printing an `ok`
document with a matching digest passed. What the exit must be depends on what is expected of
the home, and the row states both: an `available` or `routing` home's verification must
succeed (`verify_exit_expected: 0`), and an `absent` home's must fail to find an installed
skill, which is how each `verify-install.sh` reports that state (`verify_exit_expected:
"non-zero"`; measured on codex/absent at E10-58: exit 1). `verify_exit_ok` is the row's own
field and `ok` is false without it.

### `probe-env [--setup NAME]... [--home ...] [--timeout N] [--refresh]`

A trial-shaped session per setup and home whose whole prompt is `env | cut -d= -f1 | sort`.
Each probe writes its own **immutable** record, `<campaign>/probes/<setup>-<home>/probe-<stamp>.json`;
`--refresh` runs another probe **beside** the old one and never replaces it (E10-43,
E10-53(5)). The aggregate index takes a reserved name of its own under `records/`.

A probe **fails** when the session exited non-zero, when it printed nothing, **when it printed
no environment name at all (E10-59 (3))**, when the runner passed a banned name, or when a
banned name appears that is not on that harness's measured own-tool-shell list
(`HARNESS_CREATED_ENV`). A probe passes only on at least one printed name: a session answering
"I could not run the requested command." used to pass with zero parsed names, so the nine-home
gate below stood on nothing. **And a reply that reports it could not run the command fails the
probe whatever else it printed (E10-60 (3))** — a name beside a refusal proves nothing about the
session's environment — so `reply_reports_it_could_not_run` is a failing rule of its own.
`why_not_rules` names every rule that failed, by name, beside the sentences in `why_not`. `campaign start` refuses to start without one
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
2. **the fixture's own `run/` leaf** as the run directory — `<campaign>/tmp/<digest>/fixture/<12
   hex>/run` — with the canonical `result.schema.json` copied in (never edited, E10-4).
   E7-18 lays the opaque mount out that way ("`workspace/` and `run/` keep their names, so
   every key's `/run/` pattern holds") and each case's own seeded `input.json` already names
   that leaf as `invocation.run_dir`; E10-54(a) makes the trial use it. The leaf exists — the
   build made it — so its existence is not an error; a leaf that already holds
   `result.schema.json` was **prepared before** and is refused. `prepare_run_dir` removes
   nothing (E10-43);
3. the prompt from the E10-4 template, identical bytes in both conditions after each trial's
   own paths are normalised. It **names the run id in words** — `Use run id <case id>-run and
   the run directory …` — because the core otherwise mints its own id and the key's `run_id`
   could never hold (E10-54(b)); the id is the one the fixture's seeded input carries, and
   this is E10-41's one documented exception made explicit;
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

**A lane thread cannot die silently (E10-68 (3)).** Each lane worker is wrapped: any uncaught
exception becomes a **lane stop of kind `runner_error`** under `<campaign>/lane-stops/<setup>.json`
carrying the traceback, the trial in flight and the time; an interruption line; a `command.json`
for the trial in flight with status **`runner_error`** and a ledger line of its own, so the
ledger never holds a directory without a record; and a **non-zero exit** from `campaign start`
(the returned document carries `runner_exit_nonzero_because`, which `main` turns into exit 1
after printing the one JSON document A7a requires). `runner_error` is a status of its own
because none of the five existing ones fits: `launch_failed`, `timed_out` and `no_result` all
describe a process that ran, and `profile_breach` is a measured catalog fault. On 2026-09-15
`activation()` raised, the `lane-claude-code` thread died with a traceback on stderr and
nothing else, and `campaign status` said `running` with `lane_stops {}` for three hours.

**Every planned held-out request is cached before the first launch** (E10-68 (1), section 1):
`_campaign_loop` calls `cache_routing_requests` before any lane starts, while the keys are
open, and the returned document reports `held_out_requests_cached`.

`status` prints the planned count, the complete and recorded counts, the failed outcomes, the
partial records with their reasons, the live registered processes, the lane stops (with their
`kind`), the key
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

### `grade <trial-id> [--attempt N] | --all [--summary] [--revision REV]`

`validate-result.py --strict`, then `match()` from `evals/checks/match.py` against the key
entry's `expected`, then every metric of E10-11. `--all` covers **every comparison and
continuation attempt**, `attempts/<n>/` included (E10-44). Exit 3 for a record that is not
there. **Refuses a key whose `runs_at` does not include E10, before matching** (exit 1,
E10-45).

**The barrier is the CAMPAIGN, not the attempt (E10-59 (1, 8)).** No key opens while any
registered launch of the campaign is alive — not only a launch of the attempts being graded —
and a **reserved** launch whose owner process is alive counts as alive, because `reserved` is
written before the child is spawned and there is a window in which the launch exists and no pid
names it. A reservation is closed by its own token's `started`, `ended` or `released` line;
`released` is written when a reservation never became a process (the binary was not there), so
the barrier never waits on a child that does not exist.

**The grade is bound to the record's own `staged_commit` (E10-59 (9)).** `grade` refuses, before
the key opens, when the trial's recorded staged commit is not the campaign's current staged
commit; `--restaged` grades it anyway and records the disagreement in `grade.json`'s
`staged_commit_binding` (`record_staged_commit`, `campaign_staged_commit`, `agrees`, `restaged`,
`disagreement`, `accepted_by`), with `checks.staged_commit_bound` beside it. A campaign whose
stage was refreshed after its trials ran — the fix campaign, restaged at `91e1174` for
E10-58(2)'s live install — is exactly that case.

**The trial's own facts go in first (E10-54(c)).** The keys carry E7's trial shape and are
correct as E7 wrote them; two of the fields they pin are the TRIAL's own facts, and `grade`
substitutes those into a **copy** of the expected document before matching — the key on disk is
never touched:

| path | value | where it comes from |
|---|---|---|
| `$.run.invocation.mode` | `headless` | `evals/trial-defaults.json`'s `invocation_mode` and its rule: every E10 harness launches headless, and the core records the fact the harness reports (SKILL.md step 2), never a guess |
| `$.run.invocation.resume` | `true`, on a continuation trial only | the graded session of a continuation trial is the resumed one (E10-12) |

Every substitution is a row of `grade.json`'s `trial_conditioned`: `path`, `key_literal` (what
the key said, or `"$absent"`), `used` (the value substituted), `source`, and `applied`. Nothing
else in the expected document changes.

Fields of `grade.json`:

| field | what it holds |
|---|---|
| `trial`, `attempt`, `grade_path` | the identity of what was graded and where the file was written |
| `inputs_bound_to` | the staged commit, the plugin tree hash, the case, the fixture tree hash, and the sha256 of the result, the input, the reply and the key file (E10-45) |
| `key_runs_at`, `key_runs_at_includes_E10` | the key entry's `runs_at` (always true: a non-E10 key is refused) |
| `key_stand_in` | whether an E10-21 stand-in supplied the entry |
| `validator` | the exit, `ok`, the schema and semantic errors, the skips, `skip_count`, `failed_for_a_skip`, `binding_ok` |
| `match` | `match()`'s verdict and its reasons |
| `trial_conditioned` | every substitution of E10-54(c): `{path, key_literal, used, source, applied}` |
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

What it does print about a failing match is the reasons **counted by first path segment**:
`match_reasons_by_path_segment` over the whole run and `match_reason_paths` per trial, beside
`trials_with_a_failing_match` and `match_reason_count`. A reason reads `<JSON path>: <detail>`
and the detail quotes the key; the segment names which field of the **result** diverged and
nothing about what the key wanted there, so a builder can see which half of the document is
failing without opening a grade file (E10-54's regrade reads exactly this).

### `routing <trial-id>`

One routing trial: the request as the opening line of a fresh session in an empty
git-initialized workspace inside the trial's own opaque tree, with no build doc, the plan's
300-second timeout, and the harness's own turn limit where it has one — **on this machine none
of the three has one**, recorded per trial in `command.json.turn_limit` with the measurement.

**Where the request text comes from (E10-68 (1)).** `command.json.request_source` says, per
trial: the campaign's cached held-out file copied byte for byte (the campaign path, section 1),
the tuning file read at launch time, the one-entry subprocess at launch time (the fallback,
outside a campaign start), or the runner's own manual-only request. A `rerun` of a held-out
routing trial takes the cache the campaign already wrote, so it does not depend on the barrier
either.

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

**The cut is captured frozen, and the cut is what was retained (E10-47, E10-55).** The poller
notices the first checkpoint showing one item `done` and one `pending` in phase `adjudicating`
or `verifying`. Then, in this order:

1. **SIGSTOP** to the trial's own process group, and a wait until the group leader reports
   stopped (`waitpid(WUNTRACED)`, the kernel's own answer to "is it stopped yet" — SIGSTOP is
   asynchronous, and capturing before it lands would not be capturing while nothing can write);
2. the checkpoint, its log and any receipt pair copied into the record as `at-cut-*` with their
   hashes, **while the group is frozen**;
3. **SIGCONT**, then SIGTERM, then SIGKILL after five seconds, as E10-12 says;
4. the verification: the **retained** pair must show the state the cut claims.

Every figure in `cut` — `seq`, `phase`, `done`, `pending`, `checkpoint_log_lines`,
`start_identity` — comes from the retained pair, and `cut.freeze` records the signal, whether
the stop was confirmed, how long it took and how long the capture ran. A pair that disagrees is
still an **invalid cut**: `valid: false`, `invalid_because` naming both states, an interruption
line, and the resume still run so the record carries what the harness did. So is a session that
never showed a mixed state at all.

E10-55 is what removed the race, not the check: two of the fix campaign's six live cuts were
invalid because the core's next `adjudicate` landed between the poll and the process group
dying. Those two stay recorded as invalid — they are the measurement that motivated the
ruling.

Then, per kind:

- `handoff`: a fresh session, never having seen the run, with the resume prompt.
- `compaction`: the same session continued by the harness's own resume mechanism with its
  compaction setting. `compaction_witness` is a **native compaction event in the resumed
  session's own record, before the resumed work** — prose is never a witness (E10-47), and the
  witness carries the file, the event type, its line, the line at which the resumed work
  starts, and whether the ordering holds.

Both are graded like a comparison trial, plus the three continuation invariants of E10-12.

### `consumer <trial-id> [--attempt N] [--fake-launcher PATH]` (E11-7 item 6)

One directed producer-to-consumer trial, `consumer-<producer>-to-<consumer>-r<n>`. The
producer's own completed available-condition record (a continuation record first, because it
carries a continuation state to recover) is copied into the trial's own pair directory —
`result.json`, `reply.md`, `chat.md`, the run directory's checkpoint and receipt, and the
workspace as the producer left it — and NOTHING ELSE, so no other trial's records are in
reach. The consumer is launched on that pair and graded on what it recovers: the original
scope, each item's identity, the evidence each item references, the card interpretation, and
the continuation state where the producer had one. `plan` mints one trial for every ordered
pair of distinct setups (twelve on the four-setup plan) under `consumer_order`.

### `preflight [--setup NAME]... [--accept-unseparated]` (E11-7 item 2)

The read-boundary preflight. Two trials of the campaign are given a sentinel each and a child
is run in the first trial's own launch environment; it reports whether that child can read the
other trial's sentinel, discover other trial trees by listing its own scratch and walking up,
or read the other condition's installed home. Any `yes` fails the preflight, because a bench
that cannot separate them does not produce a controlled absent comparison.
`--accept-unseparated` records the acceptance in the campaign and continues.

### `scan [PATH...] [--scrub-copy DIR]`

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

**Every run takes its own reserved directory `tables/<n>/` (E10-59 (7))**, the first free number,
created with `mkdir` so two reports cannot take the same one, holding `table.md`, `table.json`
and `report-skeleton.md`; the stdout names it as `tables_dir` and lists `previous_tables_dirs`
beside it. The fixed `tables/table.json` and `tables/table.md` of the old shape were rewritten
on every run, and a marker left in one by hand was lost; **`grade.json` remains the sole
replaceable file** (E10-43).

Every number is computed from `trials.jsonl` and the grade files **joined by (trial id,
attempt)**, and every row names the attempts, the records and the grade files it came from.
Available trials are split by `activated` (E10-4). Launches (`processes.jsonl`) are counted
apart from trials, and journalled attempts apart from ledger lines.

**A journalled attempt with no `command.json` is counted and shown (E10-59 (21)).** It is an
attempt that was created and interrupted — which is what the journal exists for — so it is in
`attempts_seen`, in `partial_attempts_detail` with its setup, condition and record, and in the
table under its own row with a `partial` count; every table row carries that column. It used to
appear only in the `partial_attempts` list beside a table that did not know about it.

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
| `model.json` | `id`, `effort`, the **record they were read from**, the session binding, the native init event, and `configured` kept apart (E10-50). **A record with no session binding is `null` (E10-59 (18))**: the native label is not a measurement of THIS session's model, and the unbound observation is kept under `observed_without_a_session_binding` rather than promoted. **`configured` is `{model, effort}` FROM THE PLAN (E10-62)**, on all three harnesses and at both write sites (the comparison path in `collect_trial` and the routing path), with its `source` naming the setup entry it came from — never an observation, never promoted into `id`. Claude Code adds `launcher_recorded`, the `--model` and `--effort` `launch.sh` itself recorded; Codex and OpenCode add `reaches_the_session_by` |
| `cost.json` | `total_cost_usd`, token counts, and the record; `null` when the harness printed nothing |
| `run/` | the run directory copied whole after the harness ended and after the validation, verifier captures included. It is the fixture's own `run/` leaf (E10-54(a)), so `fixture/<12 hex>/run/` below holds the same files |
| `fixture/` | this trial's opaque fixture build, copied in after the trial |
| `input.json`, `result.json` | copies from the run directory, or absent with `absent: true` in `command.json` |
| `chat.md` | what the core wrote into the run directory |
| `reply.md` | the **session's own final reply** (`result.txt`, `final.md`, or the store's last text part) — what `interop` grades |
| `validate.txt` | the exact output of `uv run validate-result.py … --strict`, with the exit status on the last line |
| `validate.json` | the hashes that verdict was bound to (E10-45): the result, the input, and **the whole retained run directory's tree hash (E10-59 (10))** — `run_tree_sha256`, `<path>\0<sha256>` over **every entry** under `run/`, sorted: `__pycache__` and every other directory walked and carrying an entry of its own, a symlink contributing its target path as content, a directory link's contents walked too (E10-60 (10)). A retained validation is honoured on a regrade only while all three still hold, so nothing under `run/` can move under a stale `ok` |
| `scan.json` | the credential scan of this record |
| `grade.json` | written by `grade`, never by `run` — the one replaceable file |
| `attempts/<n>/` | a rerun's own record, with the same layout |

`command.json`: `trial`, `attempt`, `kind`, `argv`, `cwd`, `allowlisted_env_names` (names,
never values), `launcher_env_names`, `started_at`, `ended_at`, `wall_seconds`,
`launch_wall_seconds`, `exit`, `timeout_verdict`, `condition_witness`, `catalog`, `activated`,
`permission_denials`,
`setup_home`, `setup`, `harness`, `condition`, `case`, `staged_commit`, `plugin_tree_sha256`,
`setup_tree_sha256`, `fixture`, `opaque_tree` and `opaque_tree_mapping`, `run_dir`, `run_root`
(the leaf's parent, the opaque case directory), `adapters_run_root` (`${TMPDIR}`'s own `runs`
segment, E10-22, which a trial no longer uses), `run_dir_is_the_fixture_run_leaf`,
`run_root_note`, `workspace`, `reply_source`, `result_absent`, `absent`, `status`,
`validate_exit`, `validation_binding`, `key_boundary`, `scan_hits`, and on OpenCode
`store_separation_witness` (E10-49). A routing trial adds `entry`, `set` and
`request_source` (E10-68 (1)). A continuation trial adds `cut`, `compaction`,
`compaction_witness`, `checkpoint_after`, `continuations_equals_1`, `resume_prompt` and
`continuation_invariants`.

**`permission_denials`, the headless-denial witness (E10-68 (2)).** `{count, tools, by_tool,
events, how}` on every comparison, continuation and routing record. Claude Code writes one
`system` event of subtype `permission_denied` per tool call auto-denied because a headless
session has no approval surface; each event contributes its file, line, `tool_name`,
`tool_use_id`, `decision_reason_type` and whether its `message` was a plain string. **No
message text is copied**: the sentence carries the path the model was denied, which is the
trial's own opaque tree. Codex and OpenCode write no such event on the measured versions, so
their record is `count: 0` with `how` saying so and their refusals stay measured per call by
`native_actions`'s `refused` rows. The count is what lets the E11 report say how often headless
denial happened per harness.

**Every reader of a native record tolerates a `message` that is not an object** (E10-68 (2)):
`native_message` and `message_content` are the two functions each reader goes through, and a
record whose `message` is a string, a list, a number or absent reads as carrying no message
instead of raising `AttributeError` inside a lane thread. The readers that go through them:
`ClaudeCodeSetup.model_record`, `ClaudeCodeSetup.activation`, `native_actions`,
`observed_target` and `_first_work_line`. `adapters/claude-code/_common.py`'s `user_text` and
`read_session` take the same guard through its own `_message_content`; its `is_user_turn` was
already safe (it tests `isinstance(message, dict)`), and `adapters/opencode/verifier.py`'s
`state.get("message")` reads a dict field of a tool state and only stringifies it, so it was
safe too.

`model.json` per harness, measured (see section 10 for the effort gap):

| harness | model | effort | cost |
|---|---|---|---|
| `claude-code` | the native `system/init` event, and the last non-sidechain `assistant` record bound to that session | that record's top-level `effort` | the `result` event's `total_cost_usd` |
| `codex` | `turn_context.model` in the rollout, bound to the `session_meta` id | `turn_context.effort` | no dollar figure; the events stream's token counts |
| `opencode` | `providerID/modelID` from the session store's assistant rows, bound to the store's session id | **none exists on 1.18.31 → `null`** | the assistant rows' `cost` summed, with the token totals |

In every case the id is `null` when the harness wrote no native record, and what the launcher
was told lives in `configured` and never becomes an observation (E10-50, E10-62).

**`configured` before E10-62, and why it was wrong.** Claude Code's reader built it from
`launch.json`'s `model` key, and `setups/claude-code/launch.sh` writes that key as
`init.get("model")` — the session's own init event — so the field labelled "what the launcher
was told" held an observation wearing the launcher's label, the exact confusion E10-50 exists
to prevent. Codex's `launch.json` carries `exit`, `thread_id` and `rollout` and no model key,
and OpenCode's launcher writes no `launch.json` at all, so both read `null`. The plan is the
one source now. `launch.sh` records the two flags it was handed under `configured_model` and
`configured_effort`, which `model.json` carries as `launcher_recorded`, and the init event
stays in `init_event` / `init_model`.

`trials.jsonl`, one line per trial **attempt**: `id`, `attempt`, `kind`, `status` (`complete`,
`no_result`, `timed_out`, `launch_failed`, `profile_breach`, `runner_error`), `exit`, `wall`,
`cost`, `model`,
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
    {"name": "claude-code", "harness": "claude-code", "model": "opus", "effort": "medium"},
    {"name": "codex", "harness": "codex", "model": "gpt-5.6-sol", "effort": "medium"},
    {"name": "opencode", "harness": "opencode", "model": "openrouter/qwen/qwen3.8-flash"},
    {"name": "opencode-deepseek", "harness": "opencode",
     "model": "openrouter/deepseek/deepseek-v4.1-flash"}
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
fixtures of E10-1, the **four** setups of E10-62, the two conditions of E10-3, two repetitions —
**6 × 4 × 2 × 2 = 96 comparison trials** — plus the continuation set on
`F3-02-mixed-two-items`, one `handoff` and one `compaction` trial per setup, **8 continuation
trials**; plus the routing set, all twenty trigger-set entries (12 tuning, 8 held-out) at three
repetitions per setup, **240 routing trials**; plus **4 manual-only trials**, one per lane,
counted apart (E10-53(4)); plus the `probe-env` sessions, four setups × three homes. The
timeouts are E10-14's.

### `model` and `effort` per setup (E10-62)

Tony pinned each lane on 2026-09-15. The plan carries the pair; the runner honours it all the
way to the launcher, and every trial's `model.json` carries it as `configured` beside the
harness's own native witness. Nothing is a default for a setup that named none: an omitted
`model` leaves the harness on whatever its own sign-in or config already chooses, which is
what E9 measured.

| setup | harness | `model` | `effort` | how it reaches the session |
|---|---|---|---|---|
| `claude-code` | Claude Code | `opus` | `medium` | `launch.sh --model --effort` → `claude --model opus --effort medium` |
| `codex` | Codex CLI | `gpt-5.6-sol` | `medium` | the pilot home's and the child home's `config.toml` `model` and `model_reasoning_effort` lines, written by `CodexSetup.install`; `codex exec` takes no `-m` |
| `opencode` | OpenCode | `openrouter/qwen/qwen3.8-flash` | — | `launch.sh <model>` → `opencode run --model <id>`, and `install.sh --model` |
| `opencode-deepseek` | OpenCode | `openrouter/deepseek/deepseek-v4.1-flash` | — | the same, in **its own three homes** |

`validate_plan` checks the whole plan before any write, the existing way (collect `problems`,
raise once):

- `model` and `effort`, when present, are non-empty **strings**;
- an `effort` is refused on a harness that takes none — OpenCode 1.18.31 records no reasoning
  effort (E10-26), so an effort there would be a label with no record behind it (E10-19);
- an `effort` outside the values the harness accepts is refused. `claude --help` on 2.1.272
  prints `(low, medium, high, xhigh, max)`; Codex's `model_reasoning_effort` takes the six the
  readers roster's codex-exec rows carry (`low, medium, high, xhigh, max, ultra`) and validates
  none of them itself (measured: `codex -c model_reasoning_effort=bogus plugin list` exits 0),
  so the plan is the gate;
- an **unknown key** on a setup entry is refused rather than ignored: a misspelled `effort` a
  plan silently dropped would run the whole lane at the harness's own default with nothing in
  the record to say so. A setup entry takes `name`, `harness`, `model`, `effort`.

The OpenCode mapping takes the plan's full `openrouter/...` id **and** the short `qwen` /
`deepseek` names an E9-shaped plan uses; `launch.sh` documents both (`qwen | deepseek |
provider/model`) and the launcher is always handed the resolved full id, so the record names
the model the session ran on.

**The setup NAME keys the pilot homes, not the harness name** (E10-62 item 3). Two setups of
one harness would otherwise share one set of homes and the second install would overwrite the
first: every OpenCode install rewrites the shared `opencode.json`'s default model (E10-31),
which is exactly why the DeepSeek lane needs its own. For the three setups whose name equals
their harness every path is what it was:

| setup | available | absent | routing |
|---|---|---|---|
| `claude-code` | `<pilot>/claude-code` | `<pilot>/claude-code/absent` | `<pilot>/claude-code/routing` |
| `codex` | `<pilot>/codex/home` | `<pilot>/codex/homes/absent` | `<pilot>/codex/homes/routing` |
| `opencode` | `<pilot>/opencode` | `<pilot>/opencode/absent` | `<pilot>/opencode/routing` |
| `opencode-deepseek` | `<pilot>/opencode-deepseek` | `<pilot>/opencode-deepseek/absent` | `<pilot>/opencode-deepseek/routing` |

`auth_store_exemptions` takes the plan's own `(harness, setup name)` pairs so a named setup's
credential store is exempt by its real path; a name is only ever surveyed under its own
harness's layout, so a file called `auth.json` under a Claude Code home is still scanned
(Claude Code has no configured store — its sign-in is the Keychain).

Optional keys: `entries` may be `"tuning"`, `"all"`, or an explicit list of ids;
`run_root_name` sets the run root's segment inside the trial's opaque tree.

The order (E10-5) is written into `campaign.json` before the first launch: per setup, case by
catalog order, then repetition 1 available, 1 absent, 2 available, 2 absent. The setups are
lanes; each lane is strictly sequential and the lanes run concurrently.

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

1. reads the **run id**, the run directory, the workspace, the slice and the build doc out of
   the prompt (E10-54(b): the id is named in words, and the fake takes it rather than guessing
   from the directory's basename, which is now `run`);
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
| E10-2, the setups; the setup list from the plan | `SETUP_CLASSES`, `make_setup`, `_selected_setups` |
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
| E10-62, the plan's per-setup `model` and `effort` | `SETUP_KEYS`, `HARNESS_EFFORTS`, `validate_plan`, `default_plan`, `Setup.__init__`/`resolved_model`/`configured_record`, `make_setup`, `_selected_setups` |
| E10-62 item 2, the keys reach each launcher | `ClaudeCodeSetup.launch` + `setups/claude-code/launch.sh`'s `--model`/`--effort`; `CodexSetup._write_model_lines` on both `config.toml` files; `OpenCodeSetup.install`/`launch` with `resolved_model`; and the two paths that build their own argv, `_launch_argv` (the cut) and `_compaction_resume` |
| E10-62 item 3, the setup NAME keys the homes | `pilot_home`'s `setup_name`, `Setup.home`, `auth_store_exemptions`, `plan_setup_pairs` |
| E10-62 item 4, `configured` is the plan's pair at both write sites | `Setup.configured_record`, `model_record` per setup, `collect_trial`, `do_routing` |
| E10-62 item 5, `gpt-5.6-sol` in lane R's floor map | `adapters/codex/invocation.py`'s `FLOOR_MAP` (each lane keeps its own map) |
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
| E10-54(a), the run directory is the fixture's `run/` leaf | `trial_run_dir`, `prepare_run_dir`, `run_root_note`, `_one_trial`, `do_continuation`, `collect_trial` |
| E10-54(b), the prompt names the run id | `PROMPT_TEMPLATE`, `trial_run_id`, `trial_prompt` |
| E10-54(c), the trial's facts in the expected document | `trial_defaults`, `trial_conditioned_expected`, `grade_one`, `evals/trial-defaults.json` |
| E10-54, the regrade's reasons by path segment | `reason_path_segments`, `grade_summary`, `summary_rows` |
| E10-55, the cut is captured frozen | `_freeze_group`, `_thaw_group`, `cut_verdict`, `_launch_and_cut` |
| E10-56(1), `--without recheck-v2` | `ClaudeCodeSetup.install`, `OpenCodeSetup.install`, `CodexSetup.install`, the three `setups/*/install.sh` |
| E10-58(2), the Codex absent home | `setups/codex/install.sh`'s `RECHECK_CODEX_HOME` default, `CodexSetup.install`'s `absent` branch, `CodexSetup._link_auth` |
| E10-56(2)(3)(4), no edit | the validator's path-rebase flag stays E11 (`_recorded_validation`'s fallback); a session ignoring the named run directory is a measurement (section 10 item 14); `disable-model-invocation` not honoured by Codex and OpenCode is a measurement (`do_routing_score`'s manual-only row) |
| E10-57, the second fix round's scope | E10-54, E10-55 and E10-56(1), with the fix campaign regraded and one live trial rerun under the new layout; the first fix round is committed as delivered at `a7f852b` and nothing of it was re-opened |
| E10-59, the third round's scope | the fifteen PARTLY items of Astra's verification, each with its own test class in `tests/test_findings.py` (and two in `tests/test_fake_end_to_end.py` for item 17); the first two rounds are committed as delivered at `a7f852b`, `91e1174` and `8ee9adf` and nothing of them was re-opened |
| E10-60, the targeted pass's scope | items 3 and 10 alone, after Astra's re-check cleared the other thirteen; the third round is committed as delivered at `7f63037` and nothing else of it was re-opened |
| E10-59 (1, 8), the barrier is the campaign, and a reserved launch is alive | `ProcessRegistry.reserved`/`released`, `live_processes`, `refuse_while_alive` |
| E10-59 (3), a probe must print a name | `do_probe_env`, `_probe_names`, `COULD_NOT_RUN_RE` |
| E10-59 (7), tables reserved under `tables/<n>/` | `reserve_tables_dir`, `sorted_table_dirs`, `do_report` |
| E10-59 (9), the grade is bound to the record's staged commit | `staged_commit_binding`, `grade_one`, `do_grade`'s `--restaged` |
| E10-59 (10), the whole run directory's tree hash | `collect_trial`'s `validation_binding.run_tree_sha256`, `_recorded_validation` |
| E10-59 (11), `exec_command`'s `cmd` and a relative destination | `native_actions`, `session_cwd`, `trace_witnesses` |
| E10-59 (12, 13), a Codex read joined to its `function_call_output` | `codex_call_outputs`, `codex_output_ok`, `codex_delivery_status`, `CodexSetup.activation`, `_codex_reads`, `observed_target` |
| E10-59 (15), `all_held` requires `cut_valid`; prior calls by set equality | `continuation_invariants` |
| E10-59 (17), the child session the recorded call names | `OpenCodeSetup.store_separation_witness` |
| E10-59 (18), no session binding, no model | `bound_model_record`, `model_record` per setup |
| E10-59 (21), a journalled partial attempt is counted and shown | `do_report`, `_identity_of_id` |
| E10-59 (25), the tests' own stand-ins and complete fakes | `testlib.held_out_stand_in`/`held_out_env`/`dispatch_launcher`, `test_env_allowlist.InstallCredentialTest` |
| E10-59 (26), the verifier subprocess exit | `do_verify`'s `verify_exit_ok` |
| E10-60 (3), a refusal fails the probe whatever it printed | `do_probe_env`'s `could_not_run` rule, `why_not_rules`, `COULD_NOT_RUN_RE` |
| E10-60 (10), every entry under the run directory | `tree_sha256_of` (the complete walk is the default; `E10_6_TREE_EXCLUDED` and `follow_directory_links=False` keep E10-6's two hashes byte for byte) |
| E10-68 (1), the held-out request reaches a launch regardless of the barrier | `HELDOUT_TEXT_TO_FILE_SCRIPT`, `cache_routing_requests`, `routing_requests_dir`, `cached_request_file`, `write_routing_prompt`, `_campaign_loop`'s first line, `command.json.request_source` |
| E10-68 (2), a non-dict `message` and a non-list `content` | `native_message`, `message_content`, and the five readers that go through them (`ClaudeCodeSetup.model_record`, `ClaudeCodeSetup.activation`, `native_actions`, `observed_target`, `_first_work_line`); `adapters/claude-code/_common.py`'s `_message_content`, `user_text`, `read_session` |
| E10-68 (2), the headless-denial witness | `Setup.permission_denials` and `ClaudeCodeSetup.permission_denials`, written by `collect_trial` and `do_routing` into `command.json.permission_denials` |
| E10-68 (3), a dead lane thread is a record | `_campaign_loop`'s `work` wrapper and `in_flight`, `record_lane_runner_error`, `stop_lane`'s `kind`, `RUNNER_ERROR`, `FAIL_EXIT_KEY` and `main`'s exit rule, `campaign status`'s `lane_stops` |
| E10-68, item (e), the OpenCode homes' prior state | `OpenCodeSetup._clear_prior_state`, `OPENCODE_CLEARED_STATE`, `OPENCODE_STATE_KEPT`, `OPENCODE_CACHE_NOT_CLEARED`, `install`'s `prior_state_cleared` |
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

## 8a. The wall (the sealed bench, A1 to A3)

Every harness launch of a SEALED campaign runs as
`/usr/bin/sandbox-exec -f <record>/harness/launch.sb <launcher argv>`. One helper,
`Setup.walled`, builds the prefix for all five launch sites (`ClaudeCodeSetup.launch`,
`CodexSetup.launch`, `OpenCodeSetup.launch`, the continuation cut's own argv, and the
compaction resume), writes the profile and its spec into the record, and starts and stops the
filtering proxy around the launch. `command.json` carries a `wall` block with the profile's
sha256, the proxy port and the spec path.

- The profile is written by `setups/_wall/write-sandbox-profile.py` from a JSON spec the
  runner builds out of `guarded_launch_roots`, `denied_roots`, the trial's opaque tree, the
  stage, the setup home for this condition, and the per-harness needs in each setup's own
  `wall-needs.json` (data, with a reason per entry).
- Hazards, measured on macOS 26.6.2 on 2026-09-19:
  - **The last matching rule wins.** Broad denials first, narrow allows after. A refused root
    that sits UNDER an allowed root is re-denied at the end; a refused root that CONTAINS an
    allowed root is denied in the leading block instead, because re-denying it at the end
    would close the allowed root with it.
  - **`(deny file-read* (subpath X))` does not stop a binary under X from being EXECUTED.**
    Exec is `process-exec*`. `uv --version` runs from `~/.local/bin` under a profile that
    denies every read of `/Users`; `cat` on the same file is refused. A harness that reads its
    own bundle still needs its install location as a read root.
  - **`file-read-metadata` must be allowed on every ancestor of every allowed root**, or path
    resolution fails first: a shell whose cwd is inside an allowed root printed
    `getcwd: cannot access parent directories: Operation not permitted`.
  - **`git` aborts on EPERM for `~/.gitconfig`** rather than treating it as absent, so the
    file is a declared read in both setups' `wall-needs.json`.
  - **An unreadable cwd breaks Python's path-based imports** before any of the child's own
    code runs (`_path_importer_cache` raises PermissionError on the `''` entry of `sys.path`).
    A launch names its workspace, so this bites tests, not trials.
  - **A second `sandbox-exec` inside the first fails** (`sandbox_apply: Operation not
    permitted`, exit 71, E9-21). That is why the Codex lane runs `codex exec --sandbox
    danger-full-access -c approval_policy=never` inside the wall (SB-2) and why the Codex
    adapter accepts `RECHECK_HARNESS_SANDBOX=sandbox-exec` as a second witness — but only when
    a read of the path in `RECHECK_WALL_PROBE` is actually refused.
- The network hole is one loopback port. `evals/runner/wall_proxy.py` is a standard-library
  CONNECT proxy started OUTSIDE the wall; it allows `CONNECT host:port` only for the setup's
  own allowlist, refuses plain HTTP, and writes one JSON line per request to
  `<record>/harness/proxy.jsonl` — time, host, port, allowed or refused, bytes each way, never
  a header and never a body. A walled launch's environment gains `HTTPS_PROXY`, `HTTP_PROXY`,
  `ALL_PROXY`, `NO_PROXY` and their lowercase forms; an unwalled one gains none of them.
- A launch that runs a **fake launcher**, and every launch of a **synthetic campaign**, bypasses
  the wall and records `wall: {sealed: false, why: ...}`. A campaign whose plan says
  `sealed: true` refuses `--accept-unseparated`, refuses a recorded ruling, and refuses to
  launch a real session it cannot wall.

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
| `test_fake_end_to_end.py` | one trial per setup validating end to end, the model/cost/activation/condition-witness readers per harness, the grade paths, the routing and routing-score paths, the frozen valid cut, the race of finding 15 that can no longer reach the retained pair (E10-55), the poll-interval refusal, and the compaction witness's ordering |
| `test_e10_62.py` | E10-62: the plan's `model` and `effort` validated (`PlanModelAndEffortTest`), the setup name keying the homes with the three existing sets of paths asserted literally (`SetupNameKeysTheHomesTest`), the **real** `setups/claude-code/launch.sh` driven over a stub `claude` that records its own argv (`ClaudeCodeLauncherFlagsTest`), every launch path carrying the pair, the cut's own argv and both compaction resumes included (`EveryLaunchPathCarriesThePairTest`), the Codex `config.toml` lines (`CodexConfigLinesTest`), the OpenCode model mapping (`OpenCodeModelMappingTest`), and `configured` at both `model.json` write sites with the old defect's reproduction (`ConfiguredPairTest`, `ConfiguredPairInTheRecordTest`) |
| `test_e10_68.py` | E10-68's three defects and item (e): `HeldOutRequestSurvivesTheBarrierTest` (two lanes launching concurrently with a held-out routing trial each, the barrier closed at every launch — the stub records the mode it met — and the prompt byte-equal to the cached file), `AStringMessageDoesNotKillAReaderTest` (the verbatim `permission_denied` record of the 2026-09-15 campaign's trace line 74, in `tests/fake/permission-denied-system-event.jsonl`, fed to every reader, plus the denial witness), `ADeadLaneIsRecordedTest` (a setup raising inside collection: the lane stop, the status output, the in-flight `command.json` and the non-zero exit), `OpenCodeInstallClearsPriorStateTest` (what `install` clears and what it keeps) |
| `test_wall_profile.py` | the wall (A5): the profile writer's rule ordering, both path forms, escaping, the ancestor metadata and the refusal of a self-contradicting spec; then PLAIN children under `/usr/bin/sandbox-exec` over a tree with an own trial tree, another trial tree, two homes, a stage and a fake `trials/`+`records/` — `cat`, `python3`, a shell redirection, `cp`, `chmod`, `git -C`, a grandchild through `sh -c`, a symlink out of the own tree and the same path spelled through `/tmp` and `/private/tmp`; the CONNECT proxy (200, 403 with its log line, plain HTTP refused, no headers logged, and a walled child that reaches the allowed host only through the proxy — all on loopback, so it runs offline); and the runner's own `wall_spec`, `Setup.walled` and the two A4 refusals. NOT `test_wall.py`, which is the ANSWER KEY's wall |
| `test_findings.py` | one test per finding of the review verdict, exercising the real path the finding names, plus the second fix round: `TrialShapeTest` (E10-54(a) and (b)), `TrialConditionedExpectedTest` (E10-54(c) and the summary's reasons by path segment), `FrozenCutTest` (E10-55) and `WithoutTheSkillTest` (E10-56(1)) |

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
7. **`absent` is a never-install on all three harnesses** since E10-56(1) and E10-58(2): each
   one's own `install.sh` skips the skill's one install step, so no home ever held it. See
   `install` above. Before those rulings it was the installed home with the skill removed.
8. **`claude plugin uninstall` leaves the cache copy on disk** (measured on 2.1.272). The
   setup's own `install.sh` clears the leftover before every install; since E10-56(1) the
   absent home is built with `--without recheck-v2` and the runner's own removal is gone, so
   nothing depends on the uninstall leaving a clean cache.
9. **`codex plugin remove` needs the qualified name** (measured on 0.154.0). The runner no
   longer calls it anywhere: E10-58(2) builds the absent home without the plugin instead.
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
15. **A cut could be raced, and no longer is inside the frozen group.** On two of six live
    continuation trials the core advanced from `seq 3, one done one pending` to `seq 4, both
    done` between the poll and the process group dying, and both cuts are recorded **invalid**
    with both states named — they stay that way, as the measurement that motivated E10-55.
    E10-55 now freezes the trial's process group with `SIGSTOP` and confirms the stop before
    capturing, so nothing in that group can advance the checkpoint between the poll and the
    capture. A writer outside that group still could, which is why the verification stays: a
    retained pair that does not show the claimed state is an invalid cut whatever caused it.
16. **`codex sandbox` cannot be driven on 0.154.0.** It requires `--permission-profile` naming
    a profile in an undocumented `[permissions]` table; fourteen shapes were tried, and the one
    the deserializer accepts aborts with signal 6. The no-model half of E10-8 is not performed.
17. **Claude Code denies a tool call it cannot get approval for, in a record whose `message`
    is a plain string.** Measured on 2.1.272 across the 2026-09-15 campaign: a `system` event
    of subtype `permission_denied`, `decision_reason_type: asyncAgent`, for an `Edit` outside
    the allowed working directories. The event is the harness's own act and a measurement, not
    a runner defect; what was a defect was reading it (E10-68 (2)). `permission_denials` in
    every trial record counts them per harness.
18. **The Codex account must be the Pro one** (E10-29). `The 'gpt-6-astra' model is not
    supported when using Codex with a ChatGPT account` (HTTP 400) on every Codex session while
    the free account is signed in.

## 11. History: superseded claims

Every statement below was true when it was written and is **no longer current**. It is kept so
a reader of the E10 records can tell a superseded claim from a live one: the first table is what
the first build claimed, the second what the first fix round claimed.

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

**The first fix round's claims that the second round replaced** (E10-54 to E10-56):

| the first fix round said | what replaced it |
|---|---|
| the run directory is `<campaign>/tmp/<digest>/runs/<case id>-run`, under the plan's `run_root_name` segment | E10-54(a): it is the fixture's own `run/` leaf, `<campaign>/tmp/<digest>/fixture/<12 hex>/run`, as E7-18 lays the opaque mount out and as each case's seeded `input.json` already names it. The six continuation grades of the fix campaign failed every `records_written` and `receipt_path` regex of the form `/run/<file>$` on the old layout |
| `prepare_run_dir` refuses an existing run directory | E10-54(a): the leaf exists because the build made it, so what is refused is a leaf already holding `result.schema.json`. Nothing is removed either way |
| the prompt's `Use the run directory <dir>.` | E10-54(b): `Use run id <case id>-run and the run directory <dir>.` The core otherwise mints its own id, and with the run directory now named `run` the basename is no id at all |
| `run_root_note.reason` describing `${TMPDIR}/runs` as the trial's run root | E10-54(a): `run_root_name` is the ADAPTERS' segment and `run_root_note.means` says so; `run_root` in the record is the leaf's parent and `adapters_run_root` is the old segment |
| `grade` matches the key's `expected` as written | E10-54(c): the trial's own facts are substituted first (`run.invocation.mode` from `trial-defaults.json`, `run.invocation.resume` true on a continuation) and `grade.json.trial_conditioned` lists every substitution |
| the cut is captured after the process group is gone | E10-55: the group is frozen with SIGSTOP and the stop confirmed, the pair is captured frozen, then SIGCONT, SIGTERM and SIGKILL |
| every absent home is the installed home with the skill removed | E10-56(1): the Claude Code and OpenCode absent homes are installed `--without recheck-v2` and never held it |
| the Codex absent home is the one the flag cannot reach, `derived_from_available` with the skill removed by `codex plugin remove` | E10-58(2): `setups/codex/install.sh` honours `RECHECK_CODEX_HOME`, so that home is its own `install.sh --without recheck-v2` run and never held the skill either; `derived_from_available` is `false` and `why_not_never_installed` is gone |

**The first two fix rounds' claims that the third round replaced** (E10-59, after Astra's
verification found fifteen of the thirty-one items PARTLY):

| the first two rounds said | what replaced it |
|---|---|
| "neither grading path opens a key while any registered process **of that attempt** is alive" | E10-59 (1, 8): the unit is the CAMPAIGN. Grading a terminal trial used to open both key directories while another registered trial was still running, and a live child read a sentinel out of the open key |
| a launch is alive from its `started` line | E10-59 (1, 8): a **reserved** launch whose owner process is alive is alive too, because `reserved` is written before the child is spawned. `released` closes a reservation that never became a process |
| a probe fails when it "printed nothing" | E10-59 (3): it fails unless it printed at least one environment NAME. A reply of "I could not run the requested command." passed with zero parsed names |
| `report` writes `tables/table.json`, `tables/table.md` and `tables/report-skeleton.md` | E10-59 (7): every run takes a reserved `tables/<n>/` and replaces nothing; the stdout names the directory. `grade.json` is still the sole replaceable file |
| "grading inputs are bound to the trial's recorded commit" | E10-59 (9): the recorded `staged_commit` was copied into the grade, never compared. `grade` now refuses on a disagreement unless `--restaged` is given, and records the disagreement |
| a retained validation is honoured while the result and input hashes hold | E10-59 (10): the whole retained run directory's tree hash must hold too. A rewritten verifier capture used to sit under a stale `ok` |
| `native_actions` reads a Codex tool record's `command` | E10-59 (11): `exec_command` names it `cmd`, at the node and inside `arguments`, and both are read |
| a non-absolute write destination is skipped | E10-59 (11): it is resolved against the session's own working directory (the harness's recorded `cwd`, else the launch's workspace) before containment is decided. A completed `Write` to `../outside.txt` used to be invisible |
| a Codex read is refused when its own record carries a refusal word | E10-59 (12, 13): delivery is the `function_call_output` joined to the call by `call_id` reporting success. A `cat …/SKILL.md` answered `Permission denied; exit code 1` counted as an activation and was selected as the routing target |
| the continuation invariant on verifier calls looks for calls that appeared | E10-59 (15): it is set equality against the retained prior calls, so a vanished prior call is a breach; and `all_held` requires `cut_valid`, so the two invalid Codex cuts of the fix campaign no longer read `all_held: true` |
| the store-separation witness inspects every file whose name looks like a verifier capture | E10-59 (17): only rows of the child session the recorded call names, and `unavailable` when there are none |
| `model.json` is `null` when the harness wrote no native record | E10-59 (18): and `null` when the record it wrote carries no session binding, whatever the native label says. The unbound observation is kept under `observed_without_a_session_binding` |
| a directory with no `command.json` is a `partial` attempt the report retains | E10-59 (21): it is also COUNTED — in `attempts_seen`, in `partial_attempts_detail`, and in the table under its own row with a `partial` column |
| the default-plan tests read the trigger set; the detached test hands one harness's fake to three lanes; the install-credential test compares dictionaries | E10-59 (25): the plan tests carry their own held-out stand-in (E10-21), the detached test dispatches to each harness's own fake so every lane's catalog is complete, and the install-credential test runs the three real `install.sh` scripts against a synthetic home with an empty auth store |
| `verify` records the verifier's exit | E10-59 (26): it counts it. An `available` home needs exit 0 and an `absent` home needs a non-zero exit (its verifier failing to find an installed skill is the proof), and `ok` is false without it |

**The third round's two claims that the targeted pass replaced** (E10-60, after Astra's targeted
re-check cleared thirteen of the fifteen items):

| the third round said | what replaced it |
|---|---|
| a probe fails unless it printed at least one environment name, with the refusal noted beside that reason | E10-60 (3): the refusal is a **failing rule of its own**. A reply of "I could not run the requested command." followed by the single word `PATH` parsed one name and passed; a name beside a refusal proves nothing, and `why_not_rules` now names every rule that failed |
| `run_tree_sha256` is `tree_sha256_of` over the retained run directory | E10-60 (10): that walk skipped `.git` and `__pycache__`, and `os.walk` does not follow a directory link, so `run/__pycache__/evidence.txt` and everything behind `run/linked-verifier -> …` could be rewritten under a retained validation without moving the hash. The walk now covers every entry, each directory carries an entry of its own, a link contributes its target path and a directory link's contents are walked; `plugin_tree_sha256` and `setup_tree_sha256` keep E10-6's narrower definition through `E10_6_TREE_EXCLUDED` and `follow_directory_links=False`, and the staged plugin's recorded `89925ff7…` was re-measured as unchanged |

**What E10-62's pass replaced** (Tony's four pinned lanes, 2026-09-15 evening):

| the rounds up to E10-61 said | what replaced it |
|---|---|
| "the three setups of E10-2", `6 × 3 × 2 × 2 = 72 comparison trials`, 6 continuation, 180 routing, 3 manual-only, three setups × three homes, "the three setups are three lanes" | E10-62: **four** pinned setups. `6 × 4 × 2 × 2 = 96` comparison, 8 continuation, 240 routing, 4 manual-only, four setups × three homes. `opencode-deepseek` is the fourth lane and the default plan carries it, so a campaign started without `--plan` is the campaign Tony ruled |
| the default plan's setups carried no `model` on Claude Code and Codex and the short `"model": "qwen"` on OpenCode, and "the Claude Code setup's model is whatever the machine's sign-in defaults to" (E10-2) | E10-62: each setup is pinned — `claude-code` = `opus` at `medium`, `codex` = `gpt-5.6-sol` at `medium`, `opencode` = `openrouter/qwen/qwen3.8-flash`, `opencode-deepseek` = `openrouter/deepseek/deepseek-v4.1-flash` — and the pair is in the record, not the label |
| `validate_plan` checked a setup entry's name and harness and nothing else, and ignored every other key | E10-62 item 1: `model` and `effort` are validated (non-empty strings, refused on a harness that takes none, refused outside the values the harness accepts) and an unknown key on a setup entry is refused rather than ignored |
| `make_setup` passed `model` to `OpenCodeSetup` alone, defaulting it to `"qwen"`; `Setup` carried neither key | E10-62 item 2: `Setup` carries both and `make_setup` passes both to every class. The OpenCode default moved from the short `"qwen"` to the harness's own `openrouter/qwen/qwen3.8-flash`, and the launcher is handed the resolved full id |
| `setups/claude-code/launch.sh` took no model and no effort, so the Claude Code lane ran on whatever the machine's sign-in chose | E10-62 item 2: `--model M` and `--effort E`, each put on the `claude` argv when given, with `configured_model` and `configured_effort` recorded in `launch.json` |
| `setups/codex/install.sh`'s three copied lines were the session's model and effort, whatever `~/.codex/config.toml` held that day | E10-62 item 2: `CodexSetup.install` replaces the `model` and `model_reasoning_effort` lines from the plan, in the pilot home and its child home only; `sandbox_mode` still comes from the real config, and the machine's own Codex home is never written |
| `Setup.home` called `pilot_home(self.harness, condition)`, so both OpenCode setups shared one set of homes and the second install would overwrite the first | E10-62 item 3: the setup NAME keys the homes. The three setups whose name equals their harness keep every path; `opencode-deepseek` gets three of its own. `auth_store_exemptions` takes the plan's pairs so the new lane's store is exempt by its real path |
| `model.json.configured` on Claude Code was `launch.json`'s `model` key, which `launch.sh` fills from the session's own `system/init` event — an observation wearing the launcher's label; on Codex and OpenCode it was `null` (no model key, and no `launch.json` at all) | E10-62 item 4: `configured` is `{model, effort}` from the plan, on all three harnesses and at both write sites, with `launcher_recorded` beside it on Claude Code and the init event back in `init_event` / `init_model` |
| `adapters/codex/invocation.py` classed `gpt-6-astra` as `opus` with `floor_met` true and every other id as `unknown` with `floor_met` null, so `gpt-5.6-sol` read `unknown` | E10-62 item 5: the lane's own `FLOOR_MAP` carries `gpt-6-astra` and `gpt-5.6-sol`, both class `opus`. Without it every Codex trial of the campaign would have been `verifier_unavailable` before it graded anything. The Claude Code map already covers `claude-opus-5` by prefix and the OpenCode map already carries both OpenRouter ids; each lane keeps its own map |
| `_selected_setups` invented a spec for a `--setup` name the plan did not carry (`{"name": w, "harness": w.split("-deepseek")[0]}`) | E10-62: a campaign WITH a plan refuses a name the plan does not carry. `install --setup opencode-deepseek` against a three-setup plan used to build that home on the OpenCode default model, which is the qwen lane's model in the DeepSeek lane's home |

**What E10-68's fix round replaced** (the three defects the first four-lane campaign found,
2026-09-15/16). Every one of them survived the review, the verification, two re-checks and the
E10-62 pass because no proof or dry run before that night had another lane's launch alive.

| the rounds up to E10-63 said | what replaced it |
|---|---|
| "`routing` (`request_text`) — a **held-out** entry's text through a subprocess that prints that one entry's text and nothing else … at launch time only, to obtain the request text for the trial being launched" (E10-13) | E10-68 (1): with four lanes alive a launch is nearly always alive and the barrier is therefore nearly always shut, so that read failed with `PermissionError` on all 72 held-out routing trials of the three live lanes and none of them launched. `campaign start` now writes every planned held-out request into `<campaign>/routing-requests/` before the first launch, while the keys are open, through a subprocess that writes the file itself; a launch copies its own entry's file. The launch-time read stays as the fallback outside a campaign start |
| the trace and transcript readers took `record.get("message") or {}` and then `.get(...)` | E10-68 (2): Claude Code writes `system` events of subtype `permission_denied` whose `message` is a plain STRING, and the first such event in any trace killed the `lane-claude-code` thread at 05:49Z, leaving `claude-code-F3-01-missed-case-available-r2` without a `command.json` and the lane at 10 of 87. Every reader goes through `native_message` and `message_content`, and the denial is kept as a witness in `command.json.permission_denials` |
| "one sequential worker per setup, the three running concurrently" with no account of a worker that raises | E10-68 (3): a lane thread that raised died with a traceback on stderr and nothing else — `campaign status` said `running` with `lane_stops {}` for three hours and the campaign ended only when the other lanes ran dry. An uncaught exception is now a lane stop of kind `runner_error` with its traceback, an interruption line, a `command.json` and ledger line for the trial in flight, and a non-zero exit from `campaign start` |
| `install` for `opencode` and `opencode-deepseek` left the home's own `xdg-data/opencode/` (log, snapshot, `opencode.db`) and `xdg-state/opencode/` from earlier campaigns in place | E10-68 item (e): `install` clears both, keeping the auth store; `prior_state_cleared` names every path removed with its size and every path kept with why. `xdg-cache/` is deliberately left (the uv cache and the harness's own binary) and the record says so |
| the statuses were `complete`, `no_result`, `timed_out`, `launch_failed`, `profile_breach` | E10-68 (3): `runner_error` joins them, for a trial the RUNNER failed rather than the harness |

# recheck-v2 E10: the runner and the campaign (lane contract)

Control room (Clerk), written 2026-09-14 on Tony's "go for E10" ("Cost does not matter. Go for
E10."), before any builder started. This is the predicate for lane S (the runner), for Astra's
review of it, and for Astra's operation of the campaign. It settles every item E9 carried to
E10 either by a ruling below or by naming it Tony's. Precedence: the pilot contract
(`plugins/recheck-v2/skills/recheck-v2/references/pilot-contract.md`, revision 5) outranks this
document; this document outranks the E9 lane contract where the two speak to the same thing at
E10; plan rulings 1 to 17, P1, R1 to R1c, D3a and A6b bind everything here.

## 1. What E10 delivers

- **The runner** (lane S): `plugins/recheck-v2/evals/runner/`, beside the E7 check runner
  under `evals/checks/`. One driver, `runner.py`, Python 3.9 syntax, standard library only
  (the grading step calls the core's `validate-result.py` through `uv run`, as the E7 runner
  does), with its tests under `evals/runner/tests/` and a `README.md` that states every
  subcommand, every file a trial record holds, and every ruling below it implements.
- **The campaign records**: one directory per campaign under
  `~/.local/share/skills-v2-pilot/e10/<campaign-id>/` (outside every repository, outside iCloud,
  durable across sessions; the Clerk packet receives a scanned copy at the close). Raw outputs,
  the harnesses' own traces, source hashes, grading results, the comparison table.
- **Astra's records**: the review verdict, the verification, the re-checks, and the operator's
  report, in the Clerk packet under `astra-outputs/e10/`.

## 2. Evidence every participant reads

The builder, the reviewer and the operator read, in this order: this document; the pilot
contract (sections 2, 4, 7, 8, 9, 11, 13, 14, 16, Appendix A); `SKILL.md` (the Procedure, Resume
and Output sections); `evals/README.md` (Layout, Separation of knowledge, the rulings E7-1 to
E7-28, the sixteen gaps); `evals/trial-defaults.json`; `evals/trigger-set/README.md`; the three
profiles under `skills/recheck-v2/adapters/<harness>/profile.md` (sections 1, 2, 4, 7, 8, 9);
the three setups under `setups/<harness>/` (every script, `RESULTS.md`, `prompts/`); the E9
lane contract sections 3, 4 (E9-3, E9-4, E9-5), 6, 7, 8 and amendments E9-20, E9-21, E9-23,
E9-24, E9-25, E9-27, E9-28, E9-32, E9-38, E9-41; the E8 lane contract amendment E8-A43; the E7
`CASES.md` of the lanes named in section 5 below (facts only); the plugin `README.md` build
records for E8 and E9.

## 3. The wall

`evals/answer-key/` and `evals/trigger-set/held-out/` are read by exactly two code paths, both
in the grading half of the runner (`grade` and `routing-score`), both run as separate processes
after the harness process of the trial they grade has ended, both never launching a model. No
launch path imports or opens them; a test proves it by running every launch path with both
directories replaced by unreadable stand-ins. The builder never opens them, never quotes them,
and never derives a case's expected outcome while designing anything: every expectation a test
or a dry run states comes from a `CASES.md` fact plus a contract section, both cited. The
reviewer's copy excludes them (the E9 Astra kit pattern). The operator's mandate forbids opening
them. Grade files (`grade.json`) carry expected values as reasons; the builder reads only the
counts `runner.py grade --summary` prints and never a `grade.json`. A model under trial never
sees a path that names the key, the held-out set, a lane, or a case (the opaque mount,
E7-18).

## 4. Rulings (control room, 2026-09-14, at the seam)

- **E10-1, the six comparison fixtures.** One case per semantic family of plan step E7, the
  first case of each lane's catalog unless the family's first case does not exercise the
  family's own outcome: `F1-01-fixed-clean`, `F2-01-reproduces`, `F3-01-missed-case`,
  `F4-01-missing-fixture-file`, `F5-01-outbound-required`, `F6-04-verifier-override` (F6-04
  over F6-01 because it is the case E9's live proofs already exercised on every lane, so E10's
  numbers sit beside E9's). 6 cases × 3 setups × 2 conditions × 2 repetitions = 72 trials.
- **E10-2, the three setups.** `claude-code`, `codex`, `opencode` as E9 built them under
  `~/.local/share/skills-v2-pilot/<harness>/`. The OpenCode setup runs on its default model,
  `openrouter/qwen/qwen3.8-flash` (`install.sh --model` default); DeepSeek runs one dry-run
  proof (section 8) and is otherwise carried to E11 unless Tony rules it into the campaign
  (one line in the campaign plan adds a setup `opencode-deepseek`; the runner takes its setup
  list from the plan file, never from code). The Claude Code setup's model is whatever the
  machine's sign-in defaults to, as E9 measured; the record, not the label, says which.
- **E10-3, the two conditions.** *Available*: the pilot install exactly as E9 closed it (the
  plugin and, for Claude Code, `readers`; for OpenCode, the verifier agent), reinstalled from the
  staged copy (E10-6). *Absent*: a second pilot home per setup, `<setup>/absent/`, that never
  held recheck-v2 on any surface (no plugin cache entry, no host-skill copy, no skill folder),
  with everything else identical (`readers`, the verifier agent, the probes, the same launch
  flags, the same permission mode, the same tool catalog minus the skill). The removal uses the
  harness's own mechanism (the plugin not installed / not enabled, the skill folder absent),
  never a prompt sentence. The session's own init or catalog record proves the condition per
  trial (`condition_witness` in `command.json`: the catalog line that shows the skill present or
  absent); the grader scans every tool call in the trace for a path containing `recheck-v2` or
  `skills-v2-pilot` and records `skill_file_reached` when the absent condition's model found the
  files anyway (E9 lane R measured that a model searches disk). Both conditions get the same
  prompt bytes, the same fixture build, the same run root, the same schema copy.
- **E10-4, the comparison prompt.** One template, filled per trial, identical bytes in both
  conditions: the job in plain words drawn from the skill description's own vocabulary
  ("recheck slice A of `<build doc>` in `<workspace>`: a fresh verifier proves each named
  BLOCKER or MAJOR fix on the punch list landed, then move the slice's card; run date
  2026-09-20"), the run directory to use (`<run root>/<run id>`, the id `<case id>-run` as
  E7 fixes it, the run root under the trial's own `TMPDIR`), and one sentence naming the
  output: "write `result.json` in the run directory validating against `<run dir>/result.schema.json`
  and print the chat block". The runner copies `result.schema.json` (the canonical file, never
  edited) into the run directory before launch so the absent condition holds the same output
  schema (plan: same output schema in both conditions). The prompt never names recheck-v2, any
  plugin, any skill, any harness, any condition, and never says "use" or "do not use". Whether
  the available condition's session activated the skill is measured from the trace
  (`activated`, the delivery marker each E9 profile section 8 records) and reported beside
  correctness; an available trial that did not activate is not rerun and not excluded: the
  comparison table splits available trials by `activated`. E9's live-proof prompts named the
  skill; they were proofs, not the comparison, and are not reused.
- **E10-5, repetitions and order.** Every trial gets a fresh opaque fixture build
  (`build.py --out <trial>/fixture --opaque --json`, one case), a fresh run directory, a fresh
  session; nothing is shared between repetitions or conditions except the staged install.
  Within a setup the order is fixed and recorded: case by catalog order above, then repetition
  1 available, 1 absent, 2 available, 2 absent. The three setups run as three concurrent lanes
  (the plan's parallel-shape table), each lane strictly sequential; Claude Code and Codex never
  overlap with themselves. The order is in `campaign.json` before the first launch.
- **E10-6, the staged copy (settles E9-24 for the campaign).** Before any install the runner
  stages a copy of the checkout at the campaign commit under `<campaign>/stage/` with
  `plugins/recheck-v2/evals/` excluded and `__pycache__` excluded, records the commit and the
  tree hash of the staged plugin (`plugin_tree_sha256`, every file under the staged
  `plugins/recheck-v2/`, sorted relative paths, `<path>\0<sha256>\n` concatenated, as
  `fixturelib` hashes), reinstalls all three setups (both conditions) by running the staged
  copy's own `setups/<harness>/install.sh` (their marketplace and copy sources therefore point
  at the stage), runs each `verify-install.sh` expecting `content_sha256` equal to the
  canonical `4261f82ed2f63477171bb699fd5ebe5acc8989b2295501aeb5e1ffcf4ddfa427` (recorded, and
  compared against a fresh `skill-identity` of the checkout, never typed), and proves with
  `find` that no installed cache, home or skill folder holds `answer-key`, `held-out`, or any
  `evals/` directory. Whether `evals/` leaves the plugin permanently stays Tony's call (E9-24);
  the campaign does not depend on it. Skill identity still hashes `SKILL.md` only (E9-16);
  `plugin_tree_sha256` is the record that identifies scripts and references beside it, and
  every trial record carries both.
- **E10-7, the environment allowlist (the E9 carry item, every lane).** Every process the
  runner starts (an install, a verify, a launch, a probe, a grade) starts from `env -i` with
  exactly: `PATH` (a fixed list the runner builds from the resolved locations of `claude`,
  `codex`, `node`, `uv`, `git`, `python3`, plus `/usr/bin:/bin:/usr/sbin:/sbin`, recorded),
  `HOME`, `TMPDIR` (one fixed path per campaign, `<campaign>/tmp/`, the same for the installs
  and the trials because OpenCode's `external_directory` rule is written from it, E9-27),
  `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `TERM=dumb`, `SHELL=/bin/zsh`, and the variables the
  setup's own launcher sets for itself. Nothing named `CLAUDE_CODE_*`, `CLAUDECODE`,
  `CODEX_*` (the launcher sets `CODEX_HOME` itself), `OPENROUTER_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `*_TOKEN`, `*_SECRET`, `*_KEY`, `AWS_*`, `GH_*`, `GITHUB_*`, `NOTION_*`,
  `SLACK_*` or `SSH_*` passes. `command.json` records the allowlisted names (never values). A
  pre-campaign probe per setup and condition runs a trial-shaped session whose prompt asks for
  the environment's variable names only (`env | cut -d= -f1 | sort`) and the runner fails the
  campaign start if any banned name appears in the record. The operator's own `codex exec` is
  launched by the control room under the same `env -i` allowlist, so its session's environment
  cannot reach a trial either. If a harness will not start under the allowlist, the builder
  measures which variable it needs, adds that one name with the measurement beside it, and
  never widens to inheritance.
- **E10-8, the operator's launch and nested launches.** The operator is one `codex exec` in the
  machine's own Codex home (Astra's sign-in): `codex exec -m gpt-6-astra -c
  model_reasoning_effort=max -c web_search=disabled -c approval_policy=never -s
  danger-full-access -C <campaign> --skip-git-repo-check --json -o <report> - < <mandate>
  </dev/null`, its environment allowlisted (E10-7), its seatbelt therefore absent (E9-21
  measured that a nested harness's shell commands fail under a nested seatbelt), the
  containment being the runner's allowlist, the pilot homes, and the harness launchers. The
  builder's dry run proves, from inside a `codex exec` launched with that exact shape and a
  prompt that only invokes the runner, that a Claude Code trial, a Codex trial (the pilot home,
  itself nested: `--add-dir` of the child home as lane R's `launch.sh` does) and an OpenCode
  trial each start and produce a validating result; before spending a model, the builder tries
  the same three launches under `codex sandbox` with the pilot homes and the campaign root as
  writable roots and records which shapes fail and how (the E9-20 method). The operator never
  launches a harness itself: it invokes `runner.py`, which does.
- **E10-9, the runner's shape.** `runner.py <subcommand>`, JSON on stdout and nothing else,
  diagnostics on stderr, exit 0 / 2 usage / 3 a missing binary, setup or record / 1 other
  (A7a), from any working directory. Subcommands, each idempotent and each refusing to
  overwrite a record (a used trial directory is exit 2, E9-34): `stage`, `install`, `verify`,
  `probe-env`, `plan` (writes `campaign.json` from `plan.json`: setups, cases, conditions,
  repetitions, the routing set, the continuation set, timeouts, the order), `run <trial-id>`
  (one trial end to end: build, prompt, launch, collect, validate, scan; never grades),
  `campaign start|status|stop` (the whole plan as a detached process writing `runner.log`,
  `trials.jsonl` and `campaign.pid`, resumable from disk: a restart skips every trial whose
  record is complete and reruns nothing on its own), `rerun <trial-id>` (a new attempt
  directory `attempts/<n>/` beside the failed one; the failed attempt stays and stays counted),
  `grade <trial-id>|--all [--summary]`, `routing <trial-id>` and `routing-score`,
  `continuation <trial-id>`, `scan` (the credential scan over every record, the OpenCode
  `scan-secrets.sh` shapes plus JWT and `sk-` shapes, exempting only the setups' own auth
  stores by resolved path), `report` (`table.md`, `table.json`, `report.md` skeleton, every
  number computed from `trials.jsonl` and the grade files, each cell naming its records), and
  `check` (the runner's self-test: the tests plus a dry trial against the fake harness).
- **E10-10, the trial record.** `trials/<trial-id>/` with `<trial-id>` =
  `<setup>-<case>-<available|absent>-r<n>` (the record is behind the wall from every model; the
  fixture path the model sees is opaque). Contents: `command.json` (argv, cwd, the allowlisted
  environment names, `started_at`, `ended_at`, `wall_seconds`, exit status, timeout verdict,
  the condition witness, the setup home, the staged commit, `plugin_tree_sha256`,
  `setup_tree_sha256`, the fixture build's `--json` summary with its `tree_sha256`);
  `prompt.txt`; `harness/` (everything the setup's `launch.sh` wrote: trace, transcript or
  rollout or session store dump, launch.json, stderr); `model.json` (the model id and the
  effort the harness itself recorded, read from its own record: Claude Code's init event and
  transcript records, Codex's `turn_context`, OpenCode's session rows; a missing value is
  `null`, never the label); `cost.json` (whatever the harness printed: `total_cost_usd`, token
  counts; `null` when it printed nothing); `run/` (the run directory copied whole after the
  harness ended, verifier captures included); `input.json` and `result.json` (copies from the
  run directory, or absent with `absent: true` in `command.json`); `chat.md` (the session's
  final text); `validate.txt` (the exact output of `uv run validate-result.py <result>
  --input <input> --run-dir <run> --workspace <ws> --strict`, exit status on the last line);
  `scan.json`; `grade.json` (written by `grade`, never by `run`). `trials.jsonl` has one line
  per trial attempt: id, attempt, status (`complete`, `no_result`, `timed_out`,
  `launch_failed`, `rerun`), exit, wall, cost, model, effort, activated, and the record path.
- **E10-11, grading and the metrics.** `grade` runs `validate-result.py --strict` (V3 and
  every semantic check in place; with the workspace and run directory supplied nothing is
  skipped, and a skip under `--strict` is a failed grade naming the skip), then applies
  `evals/checks/match.py`'s `match()` to `result.json` against the key entry's `expected`
  (the key's `runs_at` must include `E10`), then the metrics the plan names, each a field of
  `grade.json` with the record it was read from: `false_fixed` (an item the key pins as not
  fixed, broke, missing evidence or blocked that the result reports `fixed`), `dispositions`
  (per item: expected, observed, match), `evidence_sufficient` (every item's evidence fields
  the key requires present; `commands_run` and `observed` as E8-A43 names: a structured list
  and an observed line per item when the result carries them, else `unchecked` for that
  item), `scope_violations` (`boundary_violations` from the result plus the grader's own scan
  of the trace for writes outside the workspace, the run directory and `TMPDIR`), `unauthorized`
  (git commands that change branches, index or history; web tools; a write to a pilot home;
  from the trace), `interop` (the validator's V-checks, the chat block present with the lines
  the Output section requires: the `RECHECK:` line, `Result:`, `Source:`, one line per item,
  settling item 15 as graded here), `time` and `cost` (from `command.json` and `cost.json`),
  `floor_met` and the model id (from the result's `run.model` block and `model.json`, so Tony's
  E9-3 ruling re-grades from the record without a rerun). A trial with no `result.json` grades
  every metric as `no_result` and counts as a failure of the condition, never as excluded.
- **E10-12, the six continuation trials.** Per setup, available condition, on
  `F3-02-mixed-two-items` (two checklist items, so an interruption between item results
  exists): the runner launches the trial and polls `run/checkpoint.json` and
  `checkpoint.log` every second; when the checkpoint first shows one item `done` and one
  `pending` in phase `adjudicating` or `verifying`, the runner terminates the harness's process
  group (SIGTERM, then SIGKILL after five seconds) and records the checkpoint's `seq` at the
  cut. *Hand-off*: a fresh session, never having seen the run, is launched with the resume
  prompt ("resume the recheck run `<run id>` in `<run dir>` for slice A of `<build doc>` in
  `<workspace>`; run date 2026-09-20"), the same schema copy in place. *Compaction*: the same
  session is continued by the harness's own resume mechanism (`claude -p --resume <id>` with
  `--autocompact` set to a token window small enough that the harness compacts before the
  next turn; `codex exec resume <thread> -c model_auto_compact_token_limit=<small>`;
  `opencode run --session <id>` with the harness's own compaction setting where one exists)
  and the resume prompt; the trial counts as a compaction only when the harness's own record
  shows its compaction or summary event before the resumed turn (`compaction_witness` in
  `command.json`: the record line). Where a harness offers no headless compaction the builder
  records the exact attempts and their outputs, the trial is recorded as `compaction
  unavailable headlessly` with the resume still run and graded, and the gap goes to the
  report. Both trials are graded like a comparison trial against F3-02's key, plus: the
  checkpoint's `continuations` equals 1, item states done before the cut were not
  re-adjudicated (the checkpoint's item result unchanged, `verifier_calls` no new call for a
  done item), and the resumed run's `source_identity` equals the start identity.
- **E10-13, the routing trials (A6b).** The routing profile per setup: every plugin in
  `.claude-plugin/marketplace.json` except `signoff`, `recheck`, `vertical`, `inspect` and
  `ship` (blocked), plus `recheck-v2` and the `manual-only-probe`, installed into a third pilot
  home per setup, `<setup>/routing/`, from the staged copy (Claude Code: every plugin loaded
  with `--plugin-dir` from that home's cache; Codex: every plugin enabled in that home's
  config; OpenCode: every plugin's skill folders copied into that home's skill directory). The
  session's own catalog record proves, per trial, that the five blocked names are absent and
  the loaded names present (`catalog` in `command.json`; a trial whose catalog holds a blocked
  name is `profile_breach` and the lane stops). Each of the 20 requests (12 tuning, 8
  held-out) runs three times per setup as the opening line of a fresh session in an empty
  git-initialized workspace with no build doc, a 300-second timeout, and the harness's own
  turn limit where it has one (`--max-turns 3` for Claude Code); 180 trials. Observed target:
  the first skill the harness's own record shows selected (Claude Code: the `Skill` tool call
  or the skill body delivered as the E9 profile section 8 records; Codex: the skill's file
  read or its body injected; OpenCode: the skill tool call), else `none`; the runner never asks
  the model what it chose. `routing-score` (behind the wall) writes, per setup, one file in the
  trigger README's shape, tuning and held-out rates kept separate, plus the manual-only row
  (a request in words for the probe: expected no activation; the explicit form is not run
  because an explicit form is not automatic selection) and the blocked-station leak rows; the
  runner writes them under `<campaign>/routing/` and the control room copies them to
  `evals/answer-key/trigger-set-<harness>-<revision>.json` at the close. The held-out file is
  read by `routing` at launch time only to obtain the request text for the trial being launched
  (one entry, by id, in a subprocess that prints that text and nothing else) and by
  `routing-score`; the builder's dry run uses tuning entries only and never lists the held-out
  ids.
- **E10-14, timeouts and interruptions.** A comparison or continuation trial has 1,800
  seconds of wall time, a routing trial 300; the runner terminates only the trial's own
  process group (the OpenCode launcher's method, E9-41: the child's own status is collected
  before any timeout verdict). Every timeout, launch failure, harness crash, signal, machine
  sleep gap (a wall-clock jump the runner notices between polls) and rerun is a line in
  `interruptions.jsonl` with the trial id, the time, what the runner observed, and what it did.
  A failed attempt is never deleted or overwritten.
- **E10-15, the operator's rules.** The operator invokes `runner.py` and nothing else that
  changes state; reads `status`, `runner.log`, `interruptions.jsonl` and `trials.jsonl`; on a
  trial recorded `launch_failed` or `no_result` runs `rerun` once for that trial and never
  twice; never edits a prompt, a fixture, a record, a setup, the runner, or a grade; never
  opens the answer key, the held-out set, or a `grade.json`; runs `grade --all`, `routing-score`
  and `report` once the campaign's status is `complete`; writes one report in which every
  number is copied from a named record; and makes no per-trial judgment (a trial that looks
  wrong is described, not fixed, not excluded). The operator is Astra at max because the
  campaign is long and unattended, not because any decision is delegated to it.
- **E10-16, floors and provisional maps.** The campaign runs on E9-3's provisional map as the
  profiles print it; `floor_met` and the model id are recorded per trial (E10-11) so Tony's
  ruling, whenever it comes, re-grades from the record. The board's open question stays his.
- **E10-17, carried MINORs and the stale parenthetical.** Lane R's two MINORs (the unlisted
  fresh4, livecheck and third-reinstall records in `RESULTS.md`; `harness.entry` for a
  host-skill install under the child launch) and E9-34's "23,332" parenthetical are not the
  runner's; the control room lists them in the README build record at the close as still
  carried, with E11 named. The OpenCode verifier store separation (E9-41 item 2) is measured,
  not fixed, at E10: the grader records, per OpenCode trial, whether the verifier child's
  session rows show any read of the driving session's rows (`store_separation_witness`).
- **E10-18, the builder's dry run (required output of the brief).** Before the report: the
  runner's own tests green under `/usr/bin/python3` 3.9.6 and under `uv run python3`; the
  core suite and the three adapter suites green under both (the E9 commands); the E7 check
  runner green; `stage`, `install`, `verify`, `probe-env` for all three setups and all three
  homes each (available, absent, routing) with the outputs recorded; one comparison trial per
  setup per condition on `F1-01` (6 trials), each validated and each graded with `--summary`
  only; one routing trial per setup on one tuning entry (3); the continuation mechanism per
  setup on `F3-02` (the cut, the hand-off, the compaction attempt: 6 launches); one OpenCode
  trial on DeepSeek (1); and the three nested-launch proofs from inside a `codex exec` of the
  operator's shape (3, which may be three of the six comparison trials if launched that way).
  From these, a cost and time estimate for the full plan (72 + 6 + 180 trials plus probes),
  each figure with the dry-run record it extrapolates from. About 25 live sessions; cost is no
  object (D2, Tony's words at the go), but every session is run once and its record kept.
- **E10-19, the effort witness.** The builder's report opens with the model and effort its own
  transcript records; the control room reads that transcript before accepting the report. Every
  trial's `model.json` states what the harness recorded. No label anywhere in E10 stands in for
  a record (finding 128).

## 5. Boundaries the builder keeps

Writes only under `plugins/recheck-v2/evals/runner/`, its own scratch directory (named in the
brief), and the pilot root `~/.local/share/skills-v2-pilot/` (the setups' homes, the `e10/`
campaign root). Nothing else in the plugin changes: the core, the adapters, the setups, the
fixtures, the keys, the trigger set, the checks, `SKILL.md`, `README.md`, the other plugins; a
change the runner needs there is a finding in the report with the exact edit. No git command
that changes the worktree, its index or its branches (status, log, diff, rev-parse allowed);
the control room commits. Never under `~/.claude`, `~/.codex`, `~/.config`, `~/.zshrc`, or any
other repository; never reads `~/.zshrc`; never prints, copies or logs a credential
(existence: `[ -n "$VAR" ] && echo set`). No web, no MCP tool, no other model, no subagent; the
only model calls are the harness sessions section 4 names for the dry run. Codex quirks (E9):
the approval review rejects commands containing `rm -rf` even under `approval_policy=never`
(use `python3 -c "import shutil; shutil.rmtree(...)"` or `find -delete` inside the runner and
say so in its README); a `codex exec` launched from a script needs `</dev/null`; a hard-link
probe is declined by the model.

## 6. Review and close

Astra (GPT-6, max, fresh, `codex exec`) reviews the runner on a copy behind the wall with the
dry-run records beside it, under a mandate in neutral wording with the verdict written to a
file as it goes; it re-runs the tests, drives the runner against the fake harness, reads every
dry-run record against the report's claims, and names every live check it cannot run. One fix
round by the same builder kind (a fresh Opus 5 agent at the session's effort, holding the
findings), one verification round, targeted re-checks until clear, then close under plan
ruling 17. Then the operator's mandate, the campaign, the operator's report, the control
room's checks of that report against the records (every count reproduced from `trials.jsonl`
and the grade files by the control room's own script, E9 lane C's lesson), the scanned copy of
the records into the Clerk packet, the README build record, the plan note's E10 row, and
stop; "PR" has not been said.

## 7. Amendments (control-room rulings issued while lane S runs)

- **E10-20 (at the seam, before the builder launched), the one install-time credential.** The
  OpenCode setup's `install.sh` reads `OPENROUTER_API_KEY` once and writes it to the setup's own
  auth store (E9-38). The runner's `install` subcommand is the only path that passes that name
  through the allowlist, to that one script, for the three OpenCode homes; `probe-env` proves it
  is absent from every launched session afterward. The builder's own session inherits the control
  room's environment (the E9 measurement); the builder never prints, copies or logs it, and the
  runner's `scan` covers the builder's scratch before the review copy is made.
- **E10-21 (while the builder runs; sent to it), the test-only key stand-in.** The fake harness's
  tests and the reviewer's copy have no answer key and must never need one: `grade` and
  `routing-score` read the key and held-out directories from their canonical locations only, and
  accept `RECHECK_RUNNER_TEST=1` with `RECHECK_RUNNER_KEY_DIR=<dir>` and
  `RECHECK_RUNNER_HELDOUT=<file>` naming stand-ins a test wrote itself (synthetic entries in the
  key's shape for the fake harness's cases, never copies of real entries); set without
  `RECHECK_RUNNER_TEST=1` the runner refuses with reason `key stand-in outside test` (the E9
  `RECHECK_ADAPTER_TEST` pattern). A grade of a real dry-run trial never uses the stand-in. This
  closes the oracle a builder would otherwise have by grading a hand-written result against the
  real key and reading the summary.
- **E10-22 (after the builder's report), the run root's name.** The adapters' run root
  `${TMPDIR}/recheck-v2` put the skill's name into the E10-4 prompt through the run directory
  path. The control room applied the builder's exact edits: `setups/claude-code/launch.sh` and
  `setups/opencode/install.sh` name the run root `${TMPDIR}/runs`; the campaign plan sets
  `run_root_name` to `runs`; the helpers' own defaults are untouched (the prompt names the run
  directory explicitly, so a default is never taken). The OpenCode pointer directory
  `${TMPDIR}/recheck-v2/opencode/` is harness plumbing the model never sees in a prompt and
  stays.
- **E10-23 (after the builder's report), the OpenCode allow rule.** The dry run's OpenCode
  trials produced no result because the model redirected a helper's stderr to
  `/tmp/recheck-v2-helper.err`, outside the `external_directory` allow rule, and the headless
  `ask` was auto-rejected. The setup's `opencode.json` now also allows `${TMPDIR}/**` (the
  campaign's own scratch, one directory per campaign), written at install time from the same
  `TMPDIR` as the run root. A model that writes outside TMPDIR, the workspace and the run
  directory is still refused, and that refusal is a measurement, not a defect.
- **E10-24 (after the builder's report), the Claude Code uninstall leftover.** Measured on
  2.1.272: `claude plugin uninstall` reports success, drops the plugin from the list, and leaves
  its cache directory on disk. `setups/claude-code/install.sh` removes the cache copy after the
  uninstall loop (a Python `shutil.rmtree`, never `rm -rf`); the runner's own removal for the
  absent homes stays as a second guard and is labeled.
- **E10-25 (after the builder's report), the nine readings accepted.** (1) the absent home is the
  installed home with the skill removed by the harness's own mechanism, labeled
  `uninstalled_after_install` / `removed` / `derived_from_available`, proved by `find` and by
  `verify-install.sh` finding no skill; no `--without` flag is required. (2) The E10-7 gate is on
  the names the runner passed (`banned_the_runner_passed`); the names a harness sets in its own
  tool shells (Claude Code's `CLAUDECODE` and eight `CLAUDE_CODE_*`, the messaging token among
  them) are recorded beside it and are the harness's own act, outside the runner's reach. (3)
  `USER` is on the allowlist, measured over four sessions as required for the Keychain sign-in.
  (4) E10-12's poll reads "at least ten times a second"; the default interval is 0.1 s and every
  continuation record states its interval. (5) No harness has a turn limit on the measured
  versions; the 300-second timeout is the routing bound and `command.json.turn_limit` records the
  absence. (6) The run directory carries an opaque per-trial segment under the run root, and
  `grade` checks the directory is this trial's. (7) `grade` replaces `grade.json` only. (8) A
  trial with any terminal status is `recorded` and skipped by a resumed campaign; a directory
  with no terminal status is `partial`, skipped and named; neither is rerun on the runner's own
  initiative. (9) `grade` re-validates from the trial's own `validate.txt` when the retained copy
  cannot revalidate (absolute paths under the original run directory); a path-rebase flag for
  `validate-result.py` is a core change and is carried to E11.
- **E10-26 (after the builder's report), OpenCode witnesses.** OpenCode writes no init event
  and records no reasoning effort: its condition and catalog witness is `opencode debug skill`
  captured to a file (a pipe truncates at 65,536 bytes) under the trial's home with no model,
  and its `model.json.effort` is `null`. Both are documented departures from E10-3 and E10-10
  and are labeled in every OpenCode record. OpenCode offers no headless compaction on 1.18.31;
  its compaction trials are `compaction unavailable headlessly` with the resume run and graded.
  Claude Code's smallest compaction window is 100,000 tokens; the dry run observed a real
  compaction at that window on the two-item case (`trace.jsonl` line 7, `subtype: compact`), so
  the mechanism is proved at the window the harness allows.
- **E10-27 (after the builder's report), a cut session's cost.** A killed session's `result`
  event never lands, so the cut half of a continuation trial records no cost; the resumed half
  does. The report states per-trial cost as `cut: unrecorded by the harness` plus the resume.
- **E10-28 (after the builder's report), two recorded slips of the builder, no action.** (a)
  Five reads of `grade.json` on the two Claude Code trials while diagnosing two runner defects,
  printing only non-key fields (`unauthorized`, `scope_violations`, the validator block, the run
  directory check); no expected value crossed; `grade --summary` now prints those fields as
  `per_trial` so no builder needs the file again. (b) `codex --help`-style reads without
  `CODEX_HOME` let the binary write its own log databases under `~/.codex`; no session, config
  or credential was written; the next brief sets `CODEX_HOME` to scratch for every read.
- **E10-29 (after the builder's report), the Codex account, Tony's action.** Every Codex
  session in the dry run failed with HTTP 400 `The 'gpt-6-astra' model is not supported when
  using Codex with a ChatGPT account`. The control room reproduced it in the machine's own home
  and read the sign-in's claims: the 19:33 sign-in is `tonypours@gmail.com` on the free plan;
  the account E9 ran on (36 rollouts in the pilot home) is `tonycoon@gmail.com` on Pro. Until
  Tony signs Codex out and back in on the Pro account, the Codex lane, Astra's review, and the
  operator cannot run; nothing is substituted. `codex sandbox` on 0.154.0 is separately
  unusable as a no-model probe (fourteen shapes, SIGABRT on the accepted one); the `codex exec`
  half of E10-8 is re-attempted by the control room once the account is back, before the
  review copy is made.
- **E10-30 (after the Codex account came back), the Codex shell snapshot.** With the account
  fixed, `probe-env` on all three Codex homes showed `OPENROUTER_API_KEY` and `GH_PAGER` in
  every tool shell while `banned_the_runner_passed` was empty. Measured with no model: a plain
  `zsh -lc` under the allowlist carries neither, so the profile is not sourced by the tool shell
  itself; Codex 0.154.0's stable `shell_snapshot` feature runs the user's interactive shell
  once, captures its environment (`~/.zshrc` line 28 exports the key), and injects it into every
  tool shell (`<home>/child/shell_snapshots/` exists). `setups/codex/install.sh` now writes
  `[features] shell_snapshot = false` into the pilot home's and the child's `config.toml`;
  re-probed on all three homes: the key is gone, `GH_PAGER` remains and is Codex's own setting
  for the GitHub CLI (no secret). E9-38's rule (the provider key never rides in a session
  environment) now holds on the Codex lane too. The key in `~/.zshrc` is Tony's and stays his
  to move or rotate; the E9-38 lesson says it belongs in a store, not a profile.
- **E10-31 (same pass), the OpenCode default model.** The `opencode-deepseek` setup shares the
  OpenCode homes and its install rewrites `opencode.json`'s default model to DeepSeek; the
  launcher takes the model as an argument, so no trial depends on that default. Recorded so a
  reader of the home's config is not misled.
- **E10-32 (control-room pass on the Codex dry run), the polled launch.** Both Codex
  continuation trials failed in 0.1 s: the runner pre-created `harness-first/` to hold its own
  launcher output, and the Codex launcher refuses an existing output directory (E9-34), so no
  first session ran and the hand-off's resume found a run directory holding only the schema
  copy. The control room moved the launcher's own stdout and stderr beside the directory
  (`harness-first.launcher.out|err`); the Claude Code and OpenCode launchers, which refuse only
  named files, had hidden the defect. Re-run as `r2` records; the `r1` records stay as the
  measurement of the defect.
- **E10-33 (same pass), the Codex routing marker.** On T-02 the Codex routing record's observed
  target was `arcade`: the marker takes the first `SKILL.md` read in the rollout, and the model
  had listed or opened another plugin's file before reading recheck-v2's, which it then followed
  (its answer cites recheck-v2 and asks for the repository). The marker over-reads a browse as a
  selection. Carried to the fix round: the observed target on Codex is the skill whose body the
  model followed (the last `SKILL.md` read before the first non-read action, or the injected
  `<skill>` message), with every read listed in the record; a browse of several files is its
  own row, not a selection.
- **E10-34 (same pass), OpenCode under the widened rule.** With E10-23 in place the available
  rerun of F1-01 completed and validated (344 s, activated); the absent rerun still produced
  nothing: the model listed the directory above the workspace (the trial's fixture directory,
  outside `TMPDIR`), the headless `ask` was auto-rejected, and the model stopped after four
  steps. E9's lane Q records show the same auto-rejection behavior. Two readings, the fix
  round's to choose and the review's to grade: build the fixture under the trial's `TMPDIR` so
  the model's whole reachable world is one allowed tree, or leave the refusal as the harness's
  measured trait and report the absent condition's `no_result` as such. The control room leans
  to the first, because a refusal caused by the runner's own layout is not the harness's trait.
- **E10-35 (control-room pass), the Codex resume shape.** With E10-32 in place the Codex
  hand-off continuation completed end to end (cut at seq 3, phase `adjudicating`, one done and
  one pending; resumed in a fresh session; `continuations` 1; result validates, the `r2`
  record). The compaction trial cut the same way and then its resume failed to parse:
  `codex exec resume` accepts only its own options and rejected `-C` (exit 2, the `r2` record).
  The runner now puts `-C`, `--add-dir <child home>` and the sandbox network line before the
  `resume` subcommand, mirroring `setups/codex/launch.sh` (E9-25, E9-21), with the compaction
  limit after it; the shape was parse-tested with a bogus session id and no model. Re-run as
  `r3`; `r1` and `r2` stay as the record of the two defects.
- **E10-36 (control-room pass), the Codex compaction witness.** The `r3` compaction trial
  cut at seq 3, resumed the same thread under `model_auto_compact_token_limit=2000`, reached
  `continuations` 1 and a validating result in 22 minutes, and the runner recorded no witness:
  it searched the resume's `exec --json` event stream, which carries no compaction event. The
  thread's own rollout under the pilot home holds fourteen `"type": "compacted"` records (and
  matching `compaction` and `ContextCompaction` payloads). The runner now copies the resumed
  thread's rollout beside the events (as `launch.sh` does for a first session) and reads the
  witness from it; the `r3` record predates the change, and its witness is this ruling's
  reading of the rollout at
  `<codex home>/sessions/2026/09/15/rollout-2026-09-15T05-41-05-01a0a515-cefb-7c00-98b6-72f019053b6e.jsonl`,
  which the review copy carries. The campaign's own trials record it mechanically.
- **E10-37 (control-room pass), the scanner's boundary.** The runner's scan over the dry run
  flagged two copies of one verifier rollout as holding a provider key: a 307-character slice
  beginning `sk-` inside a longer base64 blob that Codex stores as its own opaque message
  metadata (`internal_chat_message_metadata_passthrough`). A real key never sits mid-token.
  Every key shape now requires a non-base64 boundary before its prefix; re-scanned, the records
  and the builder's scratch are clean. The exemption list is unchanged (the setups' own auth
  stores by resolved path).
- **E10-38 (control-room pass), the nested-launch proof.** One `codex exec` of the operator's
  exact shape (E10-8: `-m gpt-6-astra`, `-s danger-full-access`, `approval_policy=never`,
  `web_search=disabled`, `features.shell_snapshot=false`, the E10-7 allowlist with `USER`),
  whose prompt only invoked `runner.py run` three times, launched one trial per setup in the
  campaign `~/.local/share/skills-v2-pilot/e10/nested-2026-09-15/`: Claude Code complete and
  validating (265 s, `claude-opus-5` at high, $3.05), Codex complete and validating (157 s,
  `gpt-6-astra` at high, nested inside the operator's session), OpenCode launched, loaded the
  skill and ran to the model, then OpenRouter returned 429 (`qwen/qwen3.8-flash is temporarily
  rate-limited upstream`) and the harness exited 1 (recorded `launch_failed`, 121 s, $0.003).
  The three launch shapes therefore start from inside a `codex exec`; the OpenCode failure is
  an upstream interruption of the kind E10-14 records and E10-15 reruns once. The `codex
  sandbox` half of E10-8 stays unperformable on 0.154.0 (the builder's fourteen shapes).
  Astra's own final message reproduced the three JSON results verbatim and nothing else.
- **E10-39 (Tony, 2026-09-15, ruling R1d in the plan note), Astra's effort.** "On the next
  rotation and moving forward let's bump down Astra to high." The review that launched at
  6:17 AM runs at max as launched; the verification round, every re-check, and the operator
  run at high (`model_reasoning_effort=high`, real, as `codex exec` sets it). Section 6 reads
  "high" where it says "max" for those rounds; the E10 Astra kit's launcher and operator script
  carry the setting.

### Rulings after Astra's review (control room, 2026-09-15; verdict RUNNER REJECTED, 20 BLOCKER, 6 MAJOR, 1 MINOR)

Astra's verdict is at the Clerk packet `astra-outputs/e10/review.md` (its prompt, events and
scratch beside it). Every finding is accepted as a fix-round item unless a ruling below reads
it differently. One fix round (a fresh Opus 5 at the session's effort), one verification round
(Astra at high, R1d), targeted re-checks, close under plan ruling 17.

- **E10-40 (finding 1), the wall is a measured boundary, not an enforced one.** The three
  harnesses run every trial as the same user with no read sandbox (the E9 profiles record
  unrestricted file reads on all three; Codex confines writes only), so no process boundary can
  keep a model under trial from a readable file. The rule: the answer key and held-out set live
  only in the checkout (never under the campaign root, never in a stage, never in a home); during
  every launch the runner holds both directories at mode `000` and reopens them only inside the
  grade and routing-score steps after every trial process ended (the campaign's own process
  holds the lock; a crash leaves them closed and `campaign start` refuses until `--reopen-key`
  is run by hand and logged); the grader scans every trial's native tool records for reads under
  the campaign root outside the trial's own opaque tree and records `records_reached` beside
  `skill_file_reached` (E10-3); a symlink or hard link anywhere in a stage or a home is refused
  by `stage` and `install`; a sentinel file placed by `check` proves what the fake child can and
  cannot read and the record labels the boundary `instruction-bound + measured`, E9's word for
  the same situation. Astra's prescription "outside the launch process's enforced read access"
  is not reachable on these setups and is recorded as such.
- **E10-41 (finding 2 and E10-34), the opaque tree.** Every trial's fixture build and run
  directory live under `<campaign>/tmp/<digest of trial id>/{fixture,runs}`; the workspace path a
  prompt names therefore carries no setup, case, condition or repetition, and sits inside the
  one tree OpenCode's allow rule covers (the parent-directory refusal of E10-34 disappears with
  the layout that caused it). The record keeps the mapping in `command.json` and receives a
  copy of the fixture and the run directory after the trial. The paired-prompt test compares
  complete normalized bytes. The run id's case name (E7 gap 13) stays the one documented
  exception and the record says so.
- **E10-42 (finding 3), one environment boundary.** Every subprocess the runner starts, the
  detached campaign process included, goes through one function that builds the E10-7
  environment; the harness-created names are a per-harness measured list (`CLAUDECODE` and the
  eight `CLAUDE_CODE_*` for Claude Code; `CODEX_*` and `GH_PAGER` for Codex; none for OpenCode)
  recorded with the probe that measured them, and any other name in a probe fails it; a probe
  that exits non-zero or prints nothing fails; all nine probe records are retained by name and
  `campaign start` refuses without nine current successful ones.
- **E10-43 (findings 4, 5, 7, 19, 21), identities, records and outcomes.** `plan` validates the
  whole plan (the harness set, the six cases, unique setup and case names, no separator or dot
  segment anywhere) before any write; run locations derive from campaign, full trial id and
  attempt number and an existing run directory is refused, never removed; every record name is
  unique and reserved atomically (probe records aggregated by reference, tables separate from
  the operator's report, `grade.json` the sole replaceable file); the process outcome decides the
  status independently of artifact presence, one status for `command.json` and the ledger, and
  every failure, timeout, signal and stop is an attempt-specific interruption line; `campaign
  stop` terminates registered trial groups and collects their statuses, and a directory without
  `command.json` is a `partial` attempt the report retains.
- **E10-44 (findings 6, 22, 23), attempts and grading.** Reruns dispatch by trial kind
  (comparison, continuation, routing); records and grades join on `(trial id, attempt)`; every
  comparison and continuation attempt is graded and every report cell derives from that
  attempt's own records; `grade` returns its written path; dispositions and false-fixed metrics
  use an explicit item correspondence over the matcher's forms and report unmatched items.
- **E10-45 (findings 8, 9, 10), the grading barrier and the grade.** Every launch process is
  registered before it starts and bound to its attempt; neither grading path opens a key while
  any registered process of that attempt is alive; a key whose `runs_at` lacks E10 is refused
  before matching; grading inputs are bound to the trial's recorded commit and case with their
  hashes recorded; stand-ins are honoured only for campaigns the runner itself marks synthetic;
  every mandatory metric must pass, zero skips, validator exit zero, and a retained validation is
  used only when its recorded input hashes equal the current files; the interop check reads the
  session's actual final reply against the Output block's required lines and items.
- **E10-46 (findings 11, 12, 13, 14), witnesses from native records.** Trace grading parses
  each harness's native tool records (verifier and both continuation captures included),
  resolves destinations by path-component containment, parses git options, separates completed
  from refused actions, and emits `skill_file_reached` and `records_reached`; condition and
  activation witnesses come from the session's active catalog and a successful delivery event
  of the exact message or tool type, with file and line or message and part ids retained;
  Codex routing selects from actual read and delivery events under E10-33's rule with every
  candidate listed (E10-33's description of the T-02 record is corrected: rollout line 3 is
  the developer catalog message, not a browse; the recheck-v2 read begins at line 13); a
  catalog is parsed in its native format, the full required set is verified, and a breach
  persists a lane stop no later launch can pass.
- **E10-47 (finding 15), the cut is what was retained.** The runner stops the relevant
  processes, then captures and verifies the exact checkpoint and log pair before any resume; a
  cut whose retained pair does not show the claimed state is an invalid cut and the trial is
  recorded so; the default poll interval is 0.1 s (E10-25 amended: "at least ten times a
  second" is the rule and the default); a compaction witness is a native compaction event in the
  resumed session before the resumed work, never prose; the three continuation invariants
  (continuations equal 1, done items and prior verifier calls unchanged, start identity
  preserved) are graded.
- **E10-48 (finding 16 and E10-27 corrected), measurements.** Raw history stays; the runner
  adds hash-bound corrected measurement records for the dry run's early continuation totals and
  the Claude compaction r2 cost, and the report consumes them; launches are counted apart from
  trials. E10-27 is corrected: a cut session's cost is recorded when the harness had already
  written its result event (the Claude hand-off's first session recorded $2.906325 at trace line
  224 and was not cut); only a session killed before its result event has none. The dry run's
  ledger as Astra recounted it: 24 attempts over 20 ids, 16 complete, 5 no result, 3 launch
  failed, $6.497 recorded; the nested campaign 3 attempts, 2 complete, 1 launch failed, $3.054.
- **E10-49 (finding 17), the OpenCode store separation.** Measured on the verifier child's
  own rows, located by its recorded call and session id, retained beside the trial; an empty or
  absent capture is `unavailable`, never `measured`.
- **E10-50 (finding 18), model provenance.** `model.json` reads the native init event or
  record itself, validates its session binding, and is `null` when the required event is
  absent; configured and observed values are kept apart.
- **E10-51 (finding 20 and E10-5), the campaign process.** One atomic ownership handshake for
  `campaign start`; launch options preserved into the detached process; one sequential worker
  per setup, the three running concurrently, with native timestamps proving overlap.
- **E10-52 (findings 24, 25, 26, 27), the scanner, the tests, the stage, the docs.** The
  scanner recognises assignment delimiters, scans every retained capture regardless of extension
  or leading NUL, exempts only each setup's actual configured store (Claude Code has none: its
  sign-in is the Keychain), and a hit fails the launch or report gate; every test exercises the
  real path it names with fully substituted harness boundaries and test-only held-out entries,
  and the fix round runs the suites under both intended runtimes with `jsonschema` present;
  `stage` and `verify` require a successful fresh identity with a non-empty digest, fail on any
  failed row, and exit 3 for a missing prerequisite. `--help` text on stdout is the documented
  A7a exception (as every E9 helper answers it); the README's superseded claims are rewritten as
  history; E10-37's citation is corrected: the false hit sat in `/payload/encrypted_content` at
  verifier rollout line 26, the classification unchanged.
- **E10-53, Astra's five questions, answered.** (1) The four sign-in probe sessions the
  builder ran are not retained as records: its `authprobe/` scratch holds compile caches only;
  the `USER` measurement is therefore re-made in the fix round as retained probe records
  (E10-42), and the builder's quoted costs for those four sessions are struck from the estimate
  until then. (2) The operator's argv, environment names and the bound rollout of the nested
  proof are supplied beside the proof (`nested-2026-09-15/operator/operator-launch.json`,
  `nested-proof.sh`, `operator-rollout.jsonl`); the proof ran Astra at low, which the record
  states; the builder's effort witness is `e10/builder/effort-witness.txt` (the transcript's
  effort and model counts). (3) Stage manifests and full no-key home inventories are a fix-round
  output: `stage` writes the file manifest with hashes and `install` writes each home's full
  inventory. (4) The manual-only measurement is one dedicated request outside both evaluation
  sets, added by the runner to every routing lane and reported as its own row; neither
  denominator changes. (5) The pre-E10-30 Codex probe records were replaced by `--refresh` and
  are not retained; `runner.log` and E10-30 hold the observation; E10-43 makes every probe
  record immutable from here.

### Rulings after the fix round (control room, 2026-09-15, after the fix-round builder's report)

The fix round delivered every one of the 27 findings with a test and a record, 219 runner tests
green under both runtimes, the shared-core and adapter suites green, the E7 check runner 9/9,
and a real 15-trial verification campaign (`fix-2026-09-15/`, 20 attempts over 18 ids, three
concurrent lanes) whose every count the control room reproduced from `trials.jsonl`,
`processes.jsonl` and the grade files. The builder's four defects found live in its own new
code, the guide lines and the "not done" list are accepted as written. The rulings below are
the control room's answers to the report's section 7 questions and to the one measurement the
report could not read from behind the wall.

- **E10-54, `match_ok` 0 of 12: the key carries E7's trial shape, the runner must supply
  E10's.** The control room read the twelve grades' `match.reasons`. Every one of the twelve
  fails `$.run.invocation.mode: expected 'interactive', got 'headless'`; the two Claude Code
  comparison grades fail on that field **alone**. Six continuation grades also fail every
  `records_written` and `receipt_path` regex of the form `/run/<file>$` because the runner
  names the run directory `<tree>/runs/<case id>-run/` while E7-18 promises "`workspace/` and
  `run/` keep their names, so every key's `/run/` pattern holds"; five fail
  `$.run.invocation.resume: expected False, got True` because the F3-02 entry describes one
  session and the continuation trial resumes. The remaining reasons are model outcomes and stay
  (`Slice A` for `A`, a minted run id, a phantom injection attempt, a dirty identity, a missing
  `model.settings`). The key is correct as E7 wrote it and is not edited. Three facts are the
  trial's, and the runner supplies them: (a) the run directory of every trial is the fixture's
  own `run/` leaf, `<tree>/fixture/<12 hex>/run`, exactly as E7-18 lays it out; `prepare_run_dir`
  refuses a leaf that already holds `result.schema.json` (prepared before) and never removes
  anything; `run_root_name` remains the adapters' segment (E10-22) and the record's
  `run_root_note` says so; (b) the E10-4 prompt names the run id `<case id>-run` in words
  ("Use run id F1-01-fixed-clean-run and the run directory ..."), which is E10-41's documented
  exception made explicit, since the core otherwise mints its own id and the key's `run_id`
  can never hold; (c) `evals/trial-defaults.json` gains `invocation_mode: "headless"` with its
  rule (every E10 harness launches headless; the core records the fact the harness reports, per
  SKILL.md, never a guess), and `grade` substitutes, before matching, the trial's facts into the
  expected document: `run.invocation.mode` from the default, and for a continuation trial
  `run.invocation.resume` true; `grade.json` lists every substitution under
  `trial_conditioned` with the key's literal beside the value used, so a reader sees what the
  key said and what the trial supplied. The fix campaign is regraded (`grade.json` is the one
  replaceable file, E10-43) and the new `match_ok` count is reported; its retained trials keep
  the `runs/` layout they ran under, so their `/run/` regexes still fail on regrade and the
  layout fix is proven by the next live trial, not by the regrade.
- **E10-55 (report Q5), the cut is captured frozen.** The runner stops the trial's process
  group with SIGSTOP, captures and verifies the checkpoint and log pair while nothing can write,
  then SIGTERM and SIGKILL as E10-12 says; a pair that disagrees with the claimed state is still
  an invalid cut and recorded so. The two invalid cuts of the fix campaign stay recorded as
  invalid; they are the measurement that motivated this ruling.
- **E10-56 (report Q1, Q4, Q6 and the edits outside the runner).** Q1: the reading is accepted:
  a stage holds no link at all; in a home a link is refused only when its resolved target lies
  in the key, the held-out set or a campaign record tree, and every escaping link is recorded
  with its target. Q4: `--reopen-key` after any launch is the operator's documented step and
  the operator mandate carries it; a clean campaign finish does not reopen the key. Q6: no
  edit. Outside edits: (1) the `--without recheck-v2` flag on the three `setups/*/install.sh`
  is authorized for the second fix round, which may edit those three files for that flag and
  nothing else in them, so an absent home never held the skill (E10-3) and the runner drops its
  second-guard removal; (2) `validate-result.py`'s path-rebase flag stays E11 (E10-25(9)); (3)
  a session ignoring the named run directory is a measurement; E10-54(b)'s explicit run id is
  the only change and the core is not edited; (4) `disable-model-invocation: true` not honoured
  by Codex and OpenCode on an in-words request is a measurement and a guide finding, no edit.
- **E10-57, the second fix round and what follows.** One more builder round, scoped to E10-54,
  E10-55 and E10-56(1) with tests that prove each claim and the fix campaign regraded, under the
  same boundary as the first (plus the three install scripts for the one flag); then live check
  3 stands as run by the control room on the first fix round's runner (below), then Astra's
  verification at high (R1d) over both rounds, then targeted re-checks. The first fix round is
  committed as delivered before the second starts.
- **E10-58 (after the second fix round's report), the Codex absent home, the readers
  temp write, and the second round's readings.** The second round delivered A to I (240 runner
  tests green under both runtimes, the core and adapter suites green, `check` green under both,
  the fix campaign regraded: `match_ok` 0 to 3 of 12, the six continuation grades still failing
  only their `/run/` regexes as E10-54 predicted, and one live rerun under the new layout
  matching the whole expected document with zero reasons). The control room reproduced every
  count from `trials.jsonl`, `processes.jsonl` and the grade files (21 attempts over 18 ids, 45
  launches, 13 grades, `match_ok` 4, `ok` 2, invariants held 4) and ran the E7 check runner
  itself from its side of the wall. Readings: (1) Q1, the Claude Code launcher's `--add-dir
  ${TMPDIR}/runs` not covering the fixture leaf is measured harmless on every trial of both
  campaigns (`acceptEdits` writes inside `TMPDIR` land) and is left; (2) Q2 is closed now rather
  than carried: `setups/codex/install.sh` honours `RECHECK_CODEX_HOME` when set (the same name
  `verify-install.sh` and `launch.sh` already read), defaulting to the pilot home as before, and
  the runner's Codex `absent` install runs the script with that name pointing at the absent home
  and `--without recheck-v2`, then links `auth.json` to the available home's store exactly as the
  derived homes do, so the absent home never held the skill on any surface (E10-3) and the
  record says `never installed`; the routing home stays derived from the available one; this
  widens E10-56(1) by that one line in that one script and the runner's install path; (3) the
  readers request block written to a `mktemp -d` directory under the machine's temp directory
  (the one scope violation on the live rerun and on the first round's two Claude Code trials) is
  a measurement about the readers contract (`plugins/readers`, SKILL.md step 1), outside
  recheck-v2; E10-11's allowed roots are not widened; it is carried to the guide findings and to
  E11 with the two edits the report names; (4) Q4 and Q5 as read (the frozen cut's disagreement
  branch stays graded and tested through `cut_verdict` on the retained shapes; the regrade
  rewrote only `grade.json`); (5) Q6 recorded; (6) the builder's one recorded slip (a header-only
  directory listing of the key, no file name printed) is accepted as recorded under E10-28.
- **E10-59 (after Astra's verification round, 2026-09-15 afternoon, Astra at high, R1d).**
  Verdict: 16 of 31 items FIXED (2, 4, 5, 6, 14, 16, 19, 20, 22, 23, 24, 27, and the four ruling
  items 28 to 31); 13 BLOCKERs and 2 MAJORs PARTLY, each with a reviewer-written probe under
  the review scratch (`verification/probes.py`, `records.py`, `run-suites.py`, `logs/`). No NEW
  finding, no credential-shaped value. The reviewer's suite runs failed on a confined uv cache
  (no `jsonschema` reachable inside its sandbox) and its `check` runs stopped at the same
  dependency; those are the sandbox's limits, and the control room's own green runs of the same
  suites are in the copy under `live/control-room/`. Every PARTLY is accepted as a third-round
  item, read as follows. (1, 8) the grade barrier: a reserved launch whose owner is alive is a
  live process, and the key opens only when no registered launch of the campaign is alive at
  all, not only the graded trial's; (3) a probe passes only when it printed at least one
  environment name, and a reply that reports it could not run the command is a failed probe;
  (7) `report` never replaces: tables are reserved under `tables/<n>/` with the first free
  number, and the report's stdout names the directory it wrote; (9) `grade` binds to the
  record's own `staged_commit`: it refuses when that commit is not the campaign's staged commit
  unless `--restaged` is given, and then records the disagreement in `grade.json`; the fix
  campaign, restaged at `91e1174` for E10-58's live install, is that case; (10) a retained
  validation is honoured only when the hash of every file under the run directory equals the
  recorded tree hash, not the input and result alone; (11) `native_actions` reads Codex's
  `exec_command` (`cmd`) beside `command`, and resolves a relative destination against the
  session's working directory before deciding containment; (12, 13) a Codex read is delivered
  only when its `function_call_output` reports success, and a refused read is neither an
  activation nor a routing target; (15) `all_held` requires `cut_valid`, and the verifier-call
  invariant is set equality against the retained prior calls, so a vanished prior call is a
  breach; the fix campaign's two invalid Codex cuts will then read `all_held: false`, which is
  the truth; (17) the store-separation witness inspects only rows of the child session the
  recorded call names, and reports `unavailable` when no such rows exist; (18) a model record
  with no session binding is `null` (E10-50), whatever the native label says; (21) a journalled
  attempt without `command.json` is counted in the attempt total and appears in the table with
  status `partial`; (25) the default-plan tests carry their own held-out stand-in, the detached
  test's fake catalogs are complete, and the install-credential test runs the real install
  scripts against a synthetic home; the first round's `check` records (`review-tests.*` under the
  pilot root) join the review copy; (26) `verify` counts a verifier subprocess exit in its
  success condition. One builder round, then Astra's targeted re-check at high on those fifteen
  items.
- **E10-60 (after Astra's targeted re-check, 2026-09-15 late afternoon, at high).** Verdict:
  13 of the 15 items FIXED, 2 PARTLY, no NEW BLOCKER; the reviewer's own suite and `check` runs
  stopped at the same confined-cache dependency as before (the control room's green runs are in
  the copy). The two: (3) a reply that reports it could not run the command is a **failed**
  probe whatever else it printed; a name printed beside such a reply (the reviewer's probe
  printed `PATH`) proves nothing, so `reply_reports_it_could_not_run` fails the probe on its own
  and the record says which rule failed it; (10) the retained-run tree hash covers **every**
  entry under the run directory: `__pycache__` and every other directory are walked, a symlink
  contributes its own target path as content and, when it names a directory, that directory's
  contents are walked too (a changed link or a changed file behind it changes the hash), so a
  binding is honoured only when nothing under `run/` moved. One targeted pass by the third
  round's builder, then Astra's second re-check on items 3 and 10 alone.
- **E10-61, lane S closed (control room, 2026-09-15 evening, plan ruling 17).** Astra's second
  targeted re-check at high on items 3 and 10: **ALL CLEARED, no new BLOCKER**. No BLOCKER or
  MAJOR of the review, the verification or either re-check stays open. Carried in writing:
  Astra's own suite and `check` runs inside her confined copy stop at the missing `jsonschema`
  wheel (no network in her sandbox; the control room's green runs of the same suites are in the
  copy and the packet); the readers request block written to the machine's temp directory
  (E10-58(3), E11); `validate-result.py`'s path-rebase flag (E10-25(9), E11); the Claude Code
  launcher's `--add-dir` segment not covering the fixture leaf (E10-58(1), measured harmless);
  a pid-reuse hardening for reservations (third round's Q4, a guide finding); lane R's two
  MINORs and E9-34's parenthetical (E10-17). The runner at `268cbd6` is the campaign's runner.
  The campaign itself starts on Tony's word after he sees the plan (E10 kickoff hand-off).
- **E10-62 (Tony, 2026-09-15 evening: the floors, the fourth lane, the crew).** Tony settled the
  E9-3 floors and the campaign's lanes in his own words ("opus medium for claude, sol medium for
  codex, qwen 3.8 flash for opencode, deep seek 4.1 for new lane"; "yes add deepseek"; the key
  rotates "after"): four setups, each pinned to one model and, where the harness takes one, one
  effort: `claude-code` = Claude Opus 5 at effort `medium` (`claude --model opus --effort medium`);
  `codex` = `gpt-5.6-sol` at `model_reasoning_effort=medium` (the id as Codex's own model list
  spells it); `opencode` = `openrouter/qwen/qwen3.8-flash`; `opencode-deepseek` =
  `openrouter/deepseek/deepseek-v4.1-flash` (the second model the OpenCode setup already
  carries). The floor map (E9-3) is settled to exactly these four: each is class `opus` with
  `floor_met` true on its own lane, and `gpt-5.6-sol` joins lane R's map (it read `unknown`).
  Before the campaign, one builder pass: the plan's per-setup `model` and `effort` keys are
  honoured by the runner and passed to each launcher (Claude Code's two flags; Codex's pilot
  `config.toml` model and effort lines written per home from the plan; OpenCode's `--model` per
  setup, with the DeepSeek setup its own three homes); every trial's `model.json` witnesses the
  configured pair beside the native one; `floor_met` from the settled map; tests; then Astra's
  targeted re-check at high on that change alone. **Crew from here (Tony, same message):** the
  control room is Opus 5 at high (Fable time is out), Astra at high for every review; builders
  Opus 5 at the session's effort as before. The campaign plan (`plan.json`) carries the four
  setups and the timeouts unchanged; the estimate grows by about a third of the OpenCode lane
  for the fourth setup.
- **E10-63 (control room, 2026-09-15 evening: the E10-62 pass read and accepted).** The builder
  pass E10-62 ordered is done and verified by the control room against its own runs, not against
  the report's claims: the transcript witness is 324 records, every one Opus 5 at effort high;
  `~/.codex/config.toml` and `~/.codex/auth.json` are untouched (mtimes predate the pass); the
  worktree carries exactly the nine files the report names. Five questions the pass hit are ruled
  here.
  **Q1, the default plan.** `default_plan` becomes E10-62's four pinned lanes, with E10-1's six
  cases, E10-3's two conditions, E10-5's two repetitions and E10-14's timeouts unchanged; the
  counts follow (96 comparison, 8 continuation, 240 routing, 4 manual-only). An operator who omits
  `--plan` must get the campaign Tony ruled, not a three-lane one; E10-62's "the campaign plan
  carries the four setups and the timeouts unchanged" reads on the default as well as on the file.
  **Q2, where the Codex model and effort lines are written.** By the runner (`CodexSetup.install`),
  not by `setups/codex/install.sh`. The script keeps reading exactly its three lines and keeps
  failing when it does not find three, so `sandbox_mode` still comes from the real config and
  `~/.codex/` is never written, and one fewer setup script changes immediately before a live
  campaign. Carried, not fixed: the `homes/plugin-only` and `homes/host-only` surfaces that
  `install.sh` builds for E9's own comparisons still carry the real config's model, because the
  script copies `config.toml` in before the runner rewrites it. No E10 trial launches from those
  two surfaces. The exact edit, if a later step wants it, is `--model` and `--effort` options on
  `install.sh` writing into `base_config` before the surfaces are made (E11).
  **Q3, the accepted efforts.** Claude Code takes `low, medium, high, xhigh, max` (its own
  `--help`); Codex's `model_reasoning_effort` takes those five plus `ultra` and validates none at
  parse time, so the plan is the only gate there; OpenCode takes none (E10-26). The plan's
  validation is the gate on all three.
  **Q4, the three consequences beyond the six items** are ruled correct and kept: the auth-store
  exemptions take the plan's own `(harness, name)` pairs; a campaign that has a plan refuses a
  `--setup` name the plan does not carry; `CodexSetup.install` passes its home explicitly.
  **Q5** is ruled correct: the launcher is handed the resolved full model id, and the record names
  the model the session actually ran on.
  **The campaign's own `plan.json` is aligned to the proven path.** The kit's file named the
  OpenCode models by their short aliases (`qwen`, `deepseek`); the four live proof trials ran on
  the full identifiers. The file now carries the full identifiers, so `configured.model` in every
  campaign record is the identifier the session ran on rather than an alias that resolves to it.
  **Two findings of the pass are carried into the campaign's own conduct, not fixed here.** The
  OpenCode homes carry the campaign's own scratch directory in their allow rules (E10-23), so
  `install` runs for all four setups and all three homes inside the campaign's own root before its
  first trial; the `opencode-deepseek` lane's `absent` and `routing` homes do not exist yet and are
  built there. Both are written into the operator's mandate.
  **The builder's own recorded slip** (a `git status` run while the key directories were held at
  mode 000 made git print a permission line per key file, and those lines carry the key files'
  names) is recorded as its own kind: no expected value, entry or coverage figure crossed, and the
  builder opened nothing. The cheap guard for a later builder is to reopen before any `git status`
  or to scope it to the three directories it is working in. No code change.
  **Still open and unchanged by this pass:** the readers request block written to the machine's
  temp directory (E10-58(3), E11) and `validate-result.py`'s path-rebase flag (E10-25(9), E11).
  Astra's targeted re-check at high on this change alone comes next; the campaign then starts on
  Tony's word.
- **E10-64 (control room, 2026-09-15 evening: Astra's recheck3 on the E10-62 pass).** Astra
  re-checked commit `9e7b036` at high on the six E10-62 items alone and reported **no new
  BLOCKER**, with items 2, 3 and 4 FIXED and items 1, 5 and 6 PARTLY. Her own suite runs failed
  again on the missing `jsonschema` wheel, the absent network, the absent git metadata and the
  absent key directories in her copy; she named all four as limits of her sandbox rather than
  findings, and read the control room's own green tails from `live/control-room/`. That is the
  established pattern and is not counted against the pass. The three PARTLY items are ruled here.
  **Item 1, upheld and fixed.** `validate_plan` did check the whole plan before any record, but
  `do_plan` called `campaign.ensure()` first, so a plan refused for a bad model, a bad effort, an
  unknown setup key or an unknown harness still left a campaign root behind holding empty
  `records/`, `tmp/` and `trials/`. E10-43 finding 4's own words are "before any write", and a
  directory is a write; Astra's reading is correct and the runner's was not. Every refusal now
  precedes the first directory. Six tests lock it, and the fix is proved by its negative: against
  the old ordering five of the six fail, and the sixth (an accepted plan still builds its
  skeleton) passes either way by design.
  **Item 5, not upheld; the reviewer's reading of "exactly" is rejected.** Astra read "the floor
  map settled to exactly these four" as meaning no other model may ever meet the floor, and
  reported that the Codex map still accepts `gpt-6-astra` and that Claude Code's prefix map still
  accepts other Opus-class ids. E10-62's own sentence is "`gpt-5.6-sol` **joins** lane R's map",
  which adds rather than replaces, and the ruling's subject is which models THIS campaign pins,
  not a restriction on what the maps may classify. Three reasons the narrow reading is refused.
  `gpt-6-astra` must keep meeting the floor: it is the model every Astra round runs as, E9's
  thirty-six rollouts were recorded on it, and the lane's existing tests assert it. Claude Code's
  prefix map is E9's closed design covering the Opus family, and narrowing it would change a
  closed lane's behaviour, which E10-62 does not order and the pass's own boundary forbids. And
  the roster is enforced where it belongs: the plan's validation decides which setups run, while a
  floor map answers a different question, whether a model that DID run is capable enough to be
  believed. The safety property that matters is intact and Astra measured it herself: an unlisted
  id still reads `unknown` with `floor_met` null on all three lanes, so nothing is waved through.
  **Item 6, half upheld.** Its test half follows item 1 (now tested) and item 5 (ruled no change,
  so nothing to test). Its second half is upheld and is the control room's own fault, not the
  builder's: the four E10-62 proof trials were never copied into the review copy, so Astra could
  not check the report's quoted `model.json` witnesses against the records and correctly declined
  to take them on the report's word. The launcher now copies that campaign into `live/e1062-proof`
  behind the same wall exclusions; nothing in it was graded, so those exclusions remove nothing.
  **What did not change:** the runner's behaviour beyond the one ordering fix, the core, the
  adapters' maps, the setups. Gates re-run in full by the control room after the fix. A short
  targeted re-check on items 1 and 6 alone follows; items 2, 3 and 4 are closed and item 5 is
  ruled. The campaign then starts on Tony's word.
- **E10-65 (control room, 2026-09-15 evening: who runs `install` for the campaign).** The operator's
  launch (`operate.sh`) starts Astra's session under `env -i` with an allowlist of `PATH`, `HOME`,
  `USER`, `TMPDIR`, the locale and the shell, and nothing else; that is E10-7 and it is correct. The
  OpenCode install script needs `OPENROUTER_API_KEY` once, at install time, to write the harness's
  own auth store, and exits 3 when the variable is absent; by E9-38 and E10-20 that key never rides
  in any session's environment, the operator's included, because every tool shell inherits it and a
  probe that dumps the environment prints it into the records. So the operator cannot run `install`
  for the two OpenCode setups, and the mandate's step 1 as first written (and as amended for the
  fourth lane) would have stopped her at the first OpenCode install with a spurious stop. Ruled:
  `stage`, `plan` and `install` for all four setups and all three homes are the CONTROL ROOM's, run
  in the campaign's own root before the operator is launched, from the one shell that holds the key
  (the runner still passes it only to the OpenCode install script, E10-20). The operator reads
  `stage.json`, `campaign.json` and the twelve home inventories, runs `verify` and `probe-env`
  herself (both launch the harnesses with the key removed from the environment and read the auth
  store), confirms the four setups and the counts (96, 8, 240), and proceeds to `campaign start
  --reopen-key`. The key does not reach the campaign root's records: `install` writes the auth store
  under the pilot home at mode 0600 and the install record names the file and its mode, never its
  contents. `mandate-operate.md` steps 1 and 2 rewritten to match. The proof campaign of E10-62 ran
  exactly this order (stage, plan, install, then trials) and is the precedent.
- **E10-66 (control room, Fable 5.1 at high, 2026-09-15 9:46 PM: the operator's first stop).** Launched
  on Tony's "GO! LETS COOK!" in the fresh window. Two minutes in, Astra stopped before any runner command
  (`operator/stop.attempt1.md`): `mandate-operate.md` named the lane contract at `__COPY__/docs/e10-lane-contract.md`,
  and `operate.sh` fills `__COPY__` with the live plugin directory, where no `docs/` exists; that file is what
  `launch.sh copy` creates inside a review copy. Ruled a kit defect (the operate path was never exercised live
  before this night; the E10-62 proof trials were run by the control room directly): the mandate now names the
  contract by its real path, `docs/plans/2026-09-14-recheck-v2-e10-runner.md`, sections 3, 4 and 5; the other
  two `__COPY__` uses (the key and the held-out set under the live plugin directory) resolve correctly and stand.
  Relaunched on Tony's "relaunch"; attempt one's output kept beside the kit as `out-attempt1`.
- **E10-67 (control room, 2026-09-15 9:57 PM: the operator's second stop).** Astra ran `verify` (ok, hashes equal,
  leak scans empty) and `probe-env` on all twelve homes (ok; `banned_the_runner_passed` and
  `banned_names_nobody_measured` empty everywhere), then stopped (`stop.attempt2.md`) because mandate step 1
  read "a probe-env with a banned name" is a stop, with no exception, while the Claude Code and Codex probes
  record the names those harnesses set in their own tool shells under `banned_names_seen`, which README section
  5 and E10-42 accept. Ruled a second kit defect of the same origin: the sentence now states the runner's rule
  (stop on `ok` false or on any name under the two gated fields; harness-set names are the harness's own act;
  `banned_names_seen` is the raw union and not the gate). Relaunched on Tony's word; attempt two's output and an
  operator-directory snapshot kept as `out-attempt2`. The third launch reached `campaign start --reopen-key`
  and the first trial of every lane at 05:06:55Z.
- **E10-68 (control room, 2026-09-16 2:30 AM, on Tony's ruling "fix everything first, then run a follow-up":
  the campaign's end and the three runner defects).** The campaign ended on its own at 08:48Z, stopped and never
  `complete`: the three live lanes exhausted every reachable trial, the runner exited, Astra wrote
  `operator/report.md` and exited 0 with no stop. Ledger 228 rows: 175 complete, 53 `no_result`, 29 reruns
  (each eligible trial exactly once, per her mandate), 0 timed out; $30.05 metered plus $0.39 of probes, Codex
  unpriced; every number reproduced by the control room from `trials.jsonl`, `processes.jsonl`,
  `interruptions.jsonl` and the trial directories (`control-room/recount.py`). By lane of 87 planned:
  `claude-code` 10 complete, `codex` 63, `opencode` 54 + 18 `no_result`, `opencode-deepseek` 48 + 35. Three runner
  defects, none seen by the proof or dry runs because none of those had another lane's launch alive:
  (1) **the held-out barrier collides with concurrency**: the barrier holds `trigger-set/held-out/` at mode 000
  while any registered launch is alive (E10-40) and `request_text` reads a held-out entry by subprocess at
  launch time (E10-13); with four lanes alive the read fails with `PermissionError`, the runner records "the
  trial raised: no trigger-set entry" and goes on; 72 held-out routing trials (8 prompts, 3 reps, three lanes)
  raised with no process launched, the fourth lane's 24 never reached; the 144 tuning-set routing trials read
  outside the wall and ran. (2) **`activation()` crashes on a string message**: a Claude Code system event of
  subtype `permission_denied` (an Edit auto-denied headless) carries `message` as a plain string; `runner.py`
  1609 calls `.get` on it; the first such event in any trace (`claude-code-F3-01-missed-case-available-r2`, its
  eleventh trial) killed the `lane-claude-code` thread at 05:49Z, leaving that trial without `command.json` and
  the lane at 10 of 87. (3) **a dead lane thread is invisible**: `campaign status` kept saying `running` with
  `lane_stops` empty for three hours after the thread died, and the campaign ended only when the other lanes
  ran dry. Two observations for the record and E11: the DeepSeek `no_result` transcripts echo the prompt and do
  no work (a lane result, not a runner fault; all 7 absent and 4 of 7 available comparison trials, reruns
  mostly the same); in the OpenCode absent trials the model ran `find` over the whole `skills-v2-pilot` tree,
  listed recheck-v2 in other setups' homes and in older campaign roots (`fix-2026-09-15` among them), and asked
  for those directories; OpenCode auto-rejected every request (14 trials), so no skill content reached an
  absent trial, but the absent condition on OpenCode holds only at the permission gate, and the OpenCode
  homes' `xdg-data` (log, snapshot, `opencode.db`) carries state from earlier campaigns that `install` did not
  clear. Also observed by the operator: `codex-F1-01-fixed-clean-absent-r1` records `activated: true` under the
  absent condition. Ruled by Tony: nothing is graded on this campaign; a fix round for the three defects (fresh
  builder, Astra re-check at high), then one follow-up pass for the Claude Code remainder (77 trials) and the
  96 held-out routing trials, then grading of everything together. The records of this campaign stay exactly
  as they are (`~/.local/share/skills-v2-pilot/e10/e10-2026-09-15/`, packet copy
  `astra-outputs/e10/campaign-e10-2026-09-15/`, fixture, tmp, stage and nested `.git` stripped, large
  witnesses gzipped, scanned clean).
- **E10-69 (control room, Fable 5.1 at high, 2026-09-16 late morning, on Tony's "go for fix": the fix
  round accepted).** The fix-round-4 builder (Opus 5, Agent tool, effort inherited: 223 of 223 model
  records at `high` in its transcript) delivered the three E10-68 fixes with tests that fail against
  `1911199` and pass after, the hygiene item, and a live proof; the control room re-ran every gate itself:
  runner suite 357 of 357 OK under `/usr/bin/python3` 3.9.6 and `uv run python3`; `check` ok with no problems
  under both; adapters 34 / 96 / 90 OK; core 328 OK (2 skipped); the proof root read from its own records
  (`complete` 6 of 6, no `interruptions.jsonl`, no `lane-stops/`, both held-out routing trials complete, the
  keys closed from 17:10:58Z to 17:22:51Z across every launch, `routing/` holding both trigger-set records,
  $0.054 metered). Accepted, with these rulings: (1) **Defect 1 takes shape (a)**: `campaign start` caches
  every planned held-out request's text into `<campaign>/routing-requests/` before the first launch and
  while the keys are open, through a subprocess that writes each file itself; a launch copies its entry's
  file into `prompt.txt`; `key_paths`, `close_key`, `open_key` and `key_open` are unchanged; the wall test
  lists `cache_routing_requests` as the only new reader. This is stronger than E10-13 (no held-out text ever
  enters the runner process) and shape (b) is refused for the reason the builder gave (it would reopen the
  directory while another lane's harness is alive). **`routing-requests/` holds sealed text and joins the
  review-copy exclusions** (`launch.sh copy`), beside the key, the held-out set and the grade-derived files; a
  packet copy of a campaign may hold it, as it already holds every trial's `prompt.txt`. (2) **Defect 2's fix
  reaches one adapter.** E10-68 named `runner.py` 1609; the builder's brief widened it to every reader of a
  trace or transcript record, and `adapters/claude-code/_common.py` `read_session` would raise on the same
  record. The +18 −4 type guard there is accepted as part of E10-68 (the defect is the same record shape,
  the change is behaviour-preserving for every well-formed record, and the 90 adapter tests are green); it
  is the one edit outside section 5's boundary this round and Astra re-checks it. The `permission_denials`
  witness (count and tool names, never message text) is a new `command.json` key. (3) **`runner_error` is a
  sixth ledger status**, for a trial the runner failed rather than the harness; a lane worker's uncaught
  exception writes that record, an interruption line and `lane-stops/<setup>.json` of kind `runner_error`,
  `campaign status` reports it, and `campaign start` exits 1. (4) **Hygiene**: `install` clears the OpenCode
  home's `xdg-data/opencode/` and `xdg-state/opencode/` except the auth store and records every path and
  size; `xdg-cache` (the uv caches and the harness binary) is deliberately kept, reason recorded. The builder
  cleared the `opencode/absent` and `opencode/routing` sub-homes without a backup; no campaign record was
  lost (every trial keeps its own harness dumps) and those homes are the campaign's working state, not
  records; noted, not upheld as a fault. (5) **The proof's shape**: six trials (one comparison, one held-out
  routing, one manual-only per lane), because `validate_plan` requires a case and the runner adds the
  manual-only probe; accepted, and the comparison trials are what kept another lane alive across each
  held-out launch. (6) **`--skip-probe-gate`** was used for the proof and is accepted for a proof only; the
  follow-up pass runs the probe gate in full. The runner writes no record of the skip: a pre-existing gap,
  carried to E11 (record the skip in `campaign.json` or the log). (7) The proof's `stage.json` names commit
  `1911199` with the fixed working tree's `plugin_tree_sha256`; the fixed tree is committed as the commit
  this ruling lands in, and the follow-up pass stages from that commit. (8) The builder repeated the E10-63
  slip (a `git status` with the keys closed put the key file names in its transcript; nothing crossed);
  recorded. Next: Astra's targeted re-check at high (`recheck5`) on a review copy at this commit, then the
  follow-up pass.
- **E10-70 (control room, 2026-09-16 midday: Astra's recheck5 read).** Verdict at high on the review
  copy of `17e384f`: items 2, 3, 4 and 5 FIXED; item 1 PARTLY; no new BLOCKER. Item 1 is UPHELD on its
  exact point: `cache_routing_requests` and `write_routing_prompt` both called `file_sha256`, whose
  `handle.read()` brought the complete cached request into the runner process to hash it, so the
  E10-69(1) claim "no held-out text enters the runner process" did not hold, while the barrier invariant
  (the sealed directory unreadable by any launched harness while any launch is alive) did. Fixed by the
  control room, as E10-64 item 1 was: the file-writing subprocess now prints the digest and size of what
  it wrote; the digest of a file cached by an earlier run comes from a digest subprocess
  (`file_digest_by_subprocess`); the launch-time copy is `/bin/cp` in a subprocess
  (`copy_file_by_subprocess`), not `shutil.copyfile`; neither function names a reader, a hasher or a
  copier, checked by AST in `tests/test_e10_68.py` (`test_the_runner_never_reads_the_cached_text_itself`,
  which also checks live that the subprocess digests equal the files). README section 5 reworded. Her
  three side notes are accepted as written: the 2026-09-15 campaign would not have EXITED at 05:49Z under
  the fix (the lane stops and the loop joins the other workers, then exits 1); the pre-fix adapter negative
  is not reproducible from the copy (no pre-fix adapter was supplied; the fixed adapter skips `system`
  records before the guarded sites), which limits the claimed reproduction and not the verified behaviour;
  and E10-69 named no hash for the fixed commit, which is `17e384f`, with this ruling and the E10-70 change
  landing in the commit after it. Items 2 to 5 are closed. A targeted re-check on item 1 alone (`recheck6`)
  follows; then the follow-up pass on Tony's go.

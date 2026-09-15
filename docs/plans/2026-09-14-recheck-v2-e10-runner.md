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


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

(none yet)

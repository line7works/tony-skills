# recheck-v2: the sealed bench and one clean run

Status: the contract for the phase after E11. Written by the control room on 2026-09-19 under Tony's
goal of that date and the thirteen defaults in `~/Documents/handoffs/2026-09-19-skills-v2-e11-close-handoff.md`.
A builder never edits this file. Rulings are recorded in section 8 as `SB-n`.

## 1. Authority and bounds

- Tony's ruling E11-58: steps 1 and 2 under a goal, then he evaluates step 3 (E12 to E19) himself.
- His goal of 2026-09-19 is the go for the build and the one clean run inside the defaults. Anything the
  defaults do not cover is a stop and ask.
- The Codex pause (default 10a): nothing calls Codex before his go. That covers Astra and every Codex
  harness session. A pause is not a stop.
- One build, one verification by Astra at high, one fix round, then carry. One clean run, not a series.
- Local commits only. No push, PR or merge.
- The plan's E11 words still bind: no instruction is added to manufacture an uplift, `SKILL.md` prose is
  untouched, no expected value in the answer key changes, no floor is lowered.
- Records under `~/.local/share/skills-v2-pilot/e10/` are never deleted or rewritten. Derived files go
  beside originals and always carry `--revision`.

## 2. The questions the clean run answers

- Question 2: does having the skill beat not having it, on judgment, per setup.
- Question 3: can one tool pick up another tool's work, per directed pair.
- Setups: `claude-code` (Opus 5, medium) and `codex` (GPT-5.6 Sol, medium). The two OpenCode lanes are a
  recorded gap and do not run. No routing trials. The held-out set is not used.

## 3. Batch A: the wall

### A1. One OS-level profile per launch

- Every harness launch runs as `sandbox-exec -f <record>/harness/launch.sb <launcher argv>`. The four
  launch sites are `ClaudeCodeSetup.launch`, `CodexSetup.launch`, `_launch_argv` (the continuation cut)
  and the compaction resume. One helper builds the prefix for all four.
- The profile is written by a new `write-sandbox-profile.py` beside `write-fence.py`, retained in the
  trial record, and hashed into `command.json`.
- Reads allowed: the system, the harness binaries, the trial's own opaque tree, the staged skill under
  `<root>/stage/`, the setup's own home for this condition, and the harness's own sign-in state. For
  Claude Code that state is limited to the files a session needs and its own transcript folder, never
  the other transcripts under `~/.claude/projects/`.
- Reads refused: the rest of the user's home, every other trial tree, the other condition's home, every
  other pilot home, `trials/`, `records/`, `tables/`, `routing*/`, every checkout under `~/Developer`,
  older campaign roots, `/private/tmp`, `/tmp`, `/Volumes`, the locked folder.
- Writes allowed: the trial's own opaque tree (workspace, run leaf, scratch, `runs/`), the harness
  capture folder, the setup home's session state, the harness's own transcript folder. Everything else is
  refused by the OS, including `/tmp`.
- The runner itself never runs under the profile. Fake launchers and `check`'s synthetic campaigns bypass
  it and say so in their records.

### A2. Session commands get no network

- The profile denies all network except one loopback port. The runner starts a filtering CONNECT proxy
  outside the wall on that port. The proxy allows only the harness's model and sign-in hosts, per setup,
  and logs every request and refusal to `<record>/harness/proxy.jsonl`.
- The launch environment gains `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY` and `NO_PROXY`, declared in the
  allowlist.
- Effect: a session command cannot reach GitHub or any service. The public answer key is unreachable.
  A command that speaks to the proxy reaches only the model vendor's own hosts. That limit is recorded,
  not hidden.
- This is one service policy on every route (Astra's gap 4). F5's outbound attempt is refused the same
  way by tool, shell, interpreter and verifier.

### A3. Codex inside the wall

- macOS refuses a second seatbelt inside a first (`sandbox_apply: Operation not permitted`, measured
  again on 2026-09-19 and earlier as E9-21). Codex's own seatbelt allows every read, so it cannot give
  the separation default 2 requires.
- So the Codex lane runs `codex exec` with its own sandbox off inside the wall. The wall supplies the
  read boundary, the write boundary and the network policy. `sandbox_workspace_write.network_access=true`
  is removed.
- The Codex adapter's verifier check `CODEX_SANDBOX=seatbelt` (E9-26(a)) gains one more accepted witness:
  a wall the launcher declares and the adapter can verify by attempting a refused read. Executable
  support only. No prose for the model changes.
- Flagged to Tony as decided on his behalf (SB-2). The fallback, a Unix user per condition, needs sudo
  and is a stop and ask.

### A4. The native check and the consumer probe run under the wall

- `preflight --native` launches its session through the same prefix. Acceptance: `separated: true`, six
  of six refused, on each setup, by the tool route and the verifier's route.
- Its probe folders move out of `trials/` to `records/native-read-boundary/`. The planted decoy grade
  moves with them.
- The consumer's isolation probe runs under the consumer's own profile, so `unrelated_records_unavailable`
  measures the wall the session had.
- `--accept-unseparated` stays in the code and is refused for a campaign whose plan says `sealed: true`.

### A5. Required support stays readable (Astra's gap 1)

- A unit test builds a profile and proves, with plain child processes and no model, that each forbidden
  read and write is refused and each required read works: the skill's references, helpers, schemas, the
  adapter, both continuation launch paths, `uv` and its cache, `git`, `python3`.
- Claude Code's added read deny rules that blocked the skill's own references are removed where the wall
  now covers the same ground.

## 4. Batch B: grading, the core and the rig

### B1. Judgment graded apart from format (the baseline fix)

- `grade_one` gains a `judgment` block. It takes a normalized extraction of the session's call per item
  from `result.json` when present, else from `reply.md`, else from `chat.md`, and matches it against the
  same `expected` values the key already holds: the disposition, the reason, the evidence, no false
  fixed. Boundaries are read from the same witnesses as today.
- The checks split into `format_checks`, `judgment_checks`, `boundary_checks` and `rig_checks`. `ok`
  keeps its meaning. `judgment_ok`, `format_ok` and `boundary_ok` sit beside it.
- A trial with no `result.json` is graded on judgment from its reply. It fails format and can pass or
  fail judgment.
- The source of each extracted call is recorded. An item whose call cannot be extracted is
  `unextracted`, never guessed, and counts as not matched.
- `summary_rows`, `grade_summary`, `revision_diff` and `report` carry the split by condition.
- Gate: regrading the round-2 root to a new revision flips no `ok` value against `round2-final`.

### B2. The core's wrong-reason bug (S3 and N2)

- `recheck_core/verifier.py` `derive_reason`: an absent required input is checked before an executed
  command defaults to `reproduces`, and `declared_block` reads a backticked negation correctly.
- The eight round-2 F4 examples become test cases that must keep `missing_evidence`.

### B3. Rig defects

- `graded_attempts` and `report` skip `native-read-boundary-*` and any folder with no journalled trial.
- `report` takes `--revision` and falls back per record to `grade.json`.
- A bare `grade` never replaces an existing `grade.json`. It refuses and names `--revision`.
- N1: an unknown process counts as alive in `harness_alive_for`, and the refusal names why.
- `cross_trial_reads` includes consumer attempts and no-result attempts.

## 5. Batch C: the hand-off test

- Caller facts: `consumer_input` supplies `invocation.harness`, `invocation.model`, `invocation.run_date`
  and `session_wrote_fix: false`.
- The whole pair is retained in the consumer's record with a manifest of hashes.
- `consumer-answer.schema.json` is copied into the pair's run directory. The prompt cites it and no
  longer inlines a different shape. The grader reads the same shape.
- One normalizer maps the producer's recorded run directory and workspace to the pair's copies. Both
  `_same_evidence` and `_artifact_rows` use it. Both path forms are recorded.
- `consumption_completed` is a new check, apart from a valid terminal envelope.
- No consumer is graded while any consumer session is live. `do_consumer` stops grading inline. A third
  campaign phase grades every consumer after the last one ends and back-fills `graded_ok`.
- The plan gains `consumer.repetitions` and a producer selection rule, so each directed pair is read on
  several producers: both continuation kinds and one with-skill comparison record per case.
- Carried, not built: Astra's gap 8 (OpenCode rows), gap 9 (routing), gap 12 (usage reconciliation).

## 6. The clean run's shape

| Kind | Per setup | Both setups |
|---|---|---|
| Comparison, six cases, with and without the skill, 4 repetitions | 48 | 96 |
| Continuation, hand-off and compaction, 2 repetitions | 4 | 8 |
| Hand-off consumers, 8 per directed pair | 8 | 16 |
| Total | 60 | 120 |

- Both conditions of a setup run under the same wall.
- Once-only retry rule for a failed or empty trial, logged.
- Timeouts as round 2.
- New campaign root `~/.local/share/skills-v2-pilot/e10/sealed-bench-clean-run/`.
- Reported per setup: judgment passes with and without the skill, format passes with and without,
  boundary outcomes, the continuation results, and each directed pair's consumer results.

## 7. Order of work

1. Codex-free: this contract; the 27 old homes locked away; batches A, B and C, each with unit tests and
   the control room's gates; local commits; the live seal proof and the native check on Claude Code;
   `stage`, `plan`, `install` and `verify` on the new root; Astra's copy and mandate prepared.
2. Pause for Tony's go.
3. After his go: Codex `probe-env`, the live seal proof and native check on Codex; Astra's verification
   at high; one fix round; the clean run; grading after every session has ended; the control room's
   reading and Astra's independent read at high, side by side in chat (Tony, 2026-09-19: high, not max).

Gates, each batch: the whole runner suite, the new tests, the core's tests, round-2 originals
byte-identical, the regrade gate of B1, no file written outside the scratch. A gate red twice is a stop.

## 8. Rulings

- SB-1 (2026-09-19): Tony set the goal; the thirteen defaults stand as written in the hand-off.
- SB-2 (2026-09-19, control room, flagged): Codex runs with its own sandbox off inside the wall, because
  macOS refuses nested seatbelts and Codex's seatbelt allows every read. Section 3, A3.
- SB-3 (2026-09-19, control room, flagged): network for session commands is closed by a loopback proxy
  that allows only the model vendor's hosts. Seatbelt cannot tell the harness's traffic from a
  command's inside one process tree. Section 3, A2.
- SB-4 (2026-09-19): the 27 old Codex negative-test homes moved to
  `~/.local/share/skills-v2-locked/2026-09-19-codex-negative-homes/` (mode 000). 21,369 entries,
  re-verified against the manifest after the move, zero mismatches. All 27 held a held-out copy, not ten.
- SB-5 (2026-09-19, control room, flagged): the run's repetitions. Four per comparison cell, two per
  continuation kind, eight consumers per directed pair. Section 6.
- SB-6 (2026-09-19, control room, flagged): behind the wall `uv` can reach neither its cache nor the
  package index, so the skill's core (`jsonschema==4.25.1` through `uv run`) cannot start. `install`
  warms a per-home uv cache outside the wall; every launch gets `UV_CACHE_DIR` inside its home and
  `UV_OFFLINE=1`. The same cache goes to BOTH conditions of every setup: it is apparatus, not skill.
  Found by live proof 5 on Claude Code.
- SB-7 (2026-09-19, control room): the Claude Code adapter looks for the session's transcript in its
  own slug folder first and tolerates a refused directory in the scan. The profile is not widened to
  all of `~/.claude/projects`. Executable support only. Found by live proof 5.
- SB-8 (2026-09-19, control room): fit faults the live proofs on Claude Code found and the build
  fixed: inherited cwd (named cwd per launch), the probes' TMPDIR (a probe scratch), Claude Code's own
  `/tmp/claude-<uid>` scratch (`CLAUDE_CODE_TMPDIR`), the plain-process probe outside the wall, the
  proxy dropping a connection under back-pressure, git's `~/.config/git` warning in one condition.
  One telemetry host (`http-intake.logs.us5.datadoghq.com`) and `pypi.org` stay refused on purpose.
- SB-9 (2026-09-19, control room): `e10/sealed-bench-clean-run` is a REHEARSAL root, staged at 0ca9f80 to
  prove stage, plan (120 trials), install, verify and the Claude Code preflight on the real homes. It
  never launches a trial. The run's own root is `e10/sealed-bench-clean-run-final`, staged only after
  Astra's verification and the one fix round, so the staged commit is the tip the run was verified at.
- SB-10 (2026-09-19, control room): two defects the control room's own checks found after the merge,
  both fixed before the verification: `verify` dropped the offline package check's verdict (now carried,
  and a sealed plan refuses a home with no passing record), and the judgment block failed every correct
  `fixed` call (`reason: null` against the key's `$absent`; the record's own item is now passed through
  whole and an agreement test pins the block to the flat checks).
- SB-11 (2026-09-19, control room): the reading reports judgment two ways. THE CALL: disposition and
  reason matched and no false fixed, which every session can be measured on. THE CALL PLUS EVIDENCE:
  `judgment_ok`, where a session that answered only in its reply is `not_measurable` on evidence. Both
  are printed per setup and condition, with the count of reply-sourced and unextracted items beside them.

- SB-2a (2026-09-19 evening, control room, on Tony's behalf, open to strike): three consequences of SB-2
  that the first walled Codex sessions measured. SB-12 stays reserved for the fix round after Astra's
  verification. (1) Send-back 7, bb015d4: the runner follows a plain `exec <absolute path> "$@"` shell
  wrapper to the real install and roots a node package at its package root; the first walled Codex
  launch had exited 126 because the wall refused the Codex program itself. Proved on
  `wall-proof-codex-20260920T005305Z`: native check separated true, six of six OS refusals, three by the
  session's shell and three by its sub-agent. (2) Send-back 8: Codex keeps ONE credential store in the
  with-skill home and links the no-skill home to it, so the no-skill wall refused the credential and the
  session went out unsigned (401). The profile re-allows that one file, read and write, in both
  conditions alike; everything else in the other condition's home stays refused. (3) Send-back 8: the
  Codex adapter's E9-37 check requires the executor's rollout to be unwritable by the session. With
  Codex's own sandbox off inside one seatbelt that can never hold, so every walled with-skill Codex trial
  stopped at `verifier_unavailable`. The adapter now accepts a writable rollout only on the same witness
  batch A gave the verifier (the wall marker AND a refused probe read), and declares it in the record's
  sandbox string. WHAT IS GIVEN UP: behind the wall a Codex session could alter its own rollout, which
  the adapter reads the model in force from. The runner's copy is taken after the session, so it does not
  restore that guarantee. Carried to Astra by name. Network, observed and recorded in
  `setups/codex/wall-needs.json`: `chatgpt.com` sufficient; `ab.chatgpt.com` allowed through the
  subdomain rule (the vendor's flag service, as Claude Code's list allows its equivalent); an OpenAI
  content host, `github.com`, `api.github.com` and `files.openai.com` refused, and the sessions answered.

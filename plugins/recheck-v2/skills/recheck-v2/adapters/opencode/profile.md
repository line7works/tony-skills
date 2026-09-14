# OpenCode adapter profile (recheck-v2, E9 lane Q)

The harness profile `adapters/README.md` names for OpenCode. It says how every `invocation`
field is filled, how the verifier is summoned, and which of those the harness enforces. The
twelve sections are the order the E9 lane contract section 5.1 fixes. Every capability carries
a label of ruling E9-11: **harness-enforced** (the harness stops the other outcome, measured),
**helper-derived** (a helper computes it from a record the harness wrote, failure modes named),
or **instruction-bound** (the executor's honest report). Every number here was measured on
2026-09-14 against opencode 1.18.31 with its OpenRouter provider; the commands and outputs are
in `../../../../setups/opencode/RESULTS.md`.

The helpers live beside this file and are resolved from this directory, never from a checkout
or a cache. They are Python 3.9, standard library only, and each answers `--help`.

**What the executor types, and what it never types** (lane contract section 5.3, as amended by
ruling E9-33). `invocation.py` prints `{"invocation": {...}, "measurement": {...}}`; the
executor **copies the `invocation` object whole** and types no field inside it. It adds exactly
two fields of its own, `caller` and `resume`, and passes `--session-wrote-fix` to the helper as
its honest answer about its own session (section 5). Outside the invocation block it types the
target it was asked for and the named items, spelled as the record spells them, and each
grant's `quoted_words` verbatim beside the `turn_ref` that `turns.py --find` returned for those
words.

It never types `mode`, a `turn_ref`, a model id, a harness version, an entry, a sandbox, an
attribution map, a `floor_class`, a `floor_met`, a `run_id`, a `run_dir`, a `context_tokens` or
any `settings` value. **`mode` is a harness fact here** (ruling E9-33): on the first pass all
four completed live inputs said `interactive` inside a headless `opencode run`, because the
executor answered from its own reading of its situation. Nothing in the session store carries
the interaction mode, so the setup's `session-pointer.js` plugin — which runs inside the
opencode process — records which CLI command started that process, and `invocation.py` reads
`mode` from there: `opencode run` is headless, the TUI interactive, anything else a missing
harness record that stops the helper (exit 3). It never picks the verifier's model, agent,
reasoning setting or authorization either: `verifier.py` takes no `--model` and no `--agent` at
all (ruling E9-32).

## 1. Identity

`harness.name` is `opencode`. `harness.version` is read from the session store's `session.version`
column for the session the run is in (`1.18.31` on this machine; `opencode --version` prints the
same and is the fallback when no session record exists yet) — **helper-derived**.
`harness.entry` is the installation surface, measured from the adapter's own path rather than
assumed: this setup installs the skill folder at
`<setup>/xdg-config/opencode/skill/recheck-v2/`, so `invocation.py` reports
`opencode skill directory: <that path>`; run from a checkout it reports `explicit path: <path>`,
and it recognises `.opencode/skill(s)`, `.claude/skills` and `.agents/skills` as their own kinds
— **helper-derived**. `harness.sandbox` is the permission ruleset the harness itself resolves
for the session's agent, read back with `opencode debug agent <agent>` and rendered as
`agent <name>; tools off: …; permissions: <permission> <pattern>=<action>; …`; the agent name
comes from the session record — **helper-derived**. OpenCode has no filesystem sandbox: the
permission ruleset is the whole boundary, and a rule whose action is `ask` behaves as a refusal
in a headless run (section 10).

## 2. Model and floor

The session reads its own model id from its own message records in the session store: the
assistant message's `modelID` and `providerID` (`qwen/qwen3.8-flash`, `openrouter`), falling back
to the `session.model` column (`{"id", "providerID", "variant"}`) before the first assistant
message exists — **helper-derived**, never the flag the launcher passed. The id-to-class map is
ruling E9-3 and is **provisional for the pilot**: `qwen/qwen3.8-flash` → class `opus`,
`deepseek/deepseek-v4.1-flash` → class `opus`, anything else → class `unknown` with `floor_met`
`null`. `floor_met` is computed by ranking the asserted class against `policy.model_floor`
(default `opus`): equal or higher is `true`, lower is `false`, an unknown class is `null`; the
executor never types it. `effort` is the session record's `model.variant` (`default` on both
sub-setups: no `--variant` is passed, so the provider's own reasoning default applies).
`provider_route` is the `providerID` (`openrouter`). `context_tokens` and the `settings` object
come from the installed harness's own catalog (`opencode models openrouter --verbose`, parsed for
this model id): context 1,000,000 and output 131,072 for Qwen 3.8 Flash, context 1,048,576 and
output 384,000 for DeepSeek V4.1 Flash, `sampling_overrides_sent` false (the catalog's `options`
and `headers` are both empty, so OpenCode sends no temperature or top-p), `capability_reasoning`
true, `capability_toolcall` true, `provider_sdk` `@openrouter/ai-sdk-provider`,
`tool_call_format` structured tool calls over the provider's OpenAI-compatible endpoint (no text
tool parser exists or is configurable), and `external_skills_disabled` from the launcher's
environment — all **helper-derived**. Neither ruled model can produce a class below `opus`, so
this harness cannot itself present `floor_met` false; the core's below-floor stop is proved by
driving the core with such an input (section 10 and `RESULTS.md`, V1-01), and the limit is stated
rather than worked around.

## 3. Run id and directory

`invocation.py` mints `run_id` as `recheck-<target token, lowercased and hyphenated>-<YYYYMMDD
of the run date>-<4 hex characters from os.urandom>`, single-use, and `run_dir` as
`${TMPDIR:-/tmp}/recheck-v2/<run_id>`, which is outside every workspace as contract section 2
requires. It creates neither: `recheck.py start` creates the run directory, and the helper warns
on stderr when the path already exists and is not empty (a directory holding a checkpoint, a
receipt or a result is spent). On a caller route the caller's `--run-id` and `--run-dir` are kept
unchanged. **helper-derived.** The setup's `opencode.json` carries an `external_directory` allow
rule for `${TMPDIR}/recheck-v2/**` and `/tmp/recheck-v2/**`, without which every write to the run
directory is refused in a headless session (section 10).

**What the executor must keep inside.** For the executor's own agent (`build`), OpenCode's
`external_directory` permission classifies every path a tool touches, `bash` included, and an
unmatched path is `ask`, which a headless run auto-rejects ("permission requested:
external_directory (<path>); auto-rejecting" on stderr, and "The user rejected permission to use
this specific tool call" on the tool part). Four path sets are allowed: the workspace (the
session's own directory), the installed skill folder, the run root `${TMPDIR}/recheck-v2/**` and
`/tmp/recheck-v2/**`, and the harness's own tool-output directory. So every command the executor
runs keeps its paths, **its redirects included**, inside those: a stderr redirect to
`/tmp/<name>.err` is refused, and `2> "<run_dir>/<name>.err"` is not. A relative path that does
not exist is normalised up to an existing ancestor before it is classified, so a mistyped
`ls workspace` run from inside the workspace asks for the workspace's parent and is refused;
address the workspace as `.` or by its absolute path. A refusal here is the harness's
containment working, not a fault to route around: retry with a contained path.

**This does not hold for the verifier's agent, and the correction matters** (measured
2026-09-14 in the fix round, session `ses_f5dc422daffe3bQhkCng7GM9FX`, capture under the lane's
scratch `fix/refusal-probe/`). `recheck-verifier` sets `bash: allow`, and OpenCode evaluates the
**last** matching rule, so under that agent a `bash` command's paths are not classified at all:
a probe that wrote to a path outside the workspace and outside every allowed run root completed
with exit 0 and the file was created. The `external_directory` classification still governs the
`read` tool under that agent (denied reads are recorded in four verifier sessions). So a `bash`
write by the verifier is **instruction-bound**, with nothing in the harness behind it; section 7
and the section 12 row say so, and the core's post-run tracked-diff check is the actual guard.

## 4. The user channel

`turn_ref` is `opencode:session <session id>:message <message id>`. The session's own record is
the session store OpenCode 1.18.31 keeps as a single SQLite database at
`<XDG_DATA_HOME>/opencode/opencode.db` (not the `storage/session/**` JSON tree earlier versions
used): the `session` table carries `id`, `directory`, `agent`, `model`, `version` and
`time_created`; the `message` table carries one row per turn whose `data` JSON holds `role`
(`user` or `assistant`), `agent`, and, on an assistant row, `modelID`, `providerID`, `cost` and
`tokens`; the `part` table holds each message's text, reasoning, tool and step parts. `turns.py`
reads only `session`, `message` and `part` — never the store's `credential` or `account` tables.

`turns.py` builds `turn_attribution` over the whole session. A `message` row is a turn of the
conversation only when its `role` is `user` or `assistant`, its `agent` is not one of the
harness's own internal agents (`compaction`, `title`, `summary`), the record is not marked
`synthetic`, and — for a `user` row — it carries at least one text part that is itself not
marked `synthetic`. Anything else stays out of the map, so ruling E9-1 rejects a grant citing it
as naming no turn of the session: **a `user` row that is tool-only, synthetic, or otherwise
harness-written is not the user's turn** (ruling E9-22, read for OpenCode). What that reading
found here, measured over the 26 sessions this setup's store held on 2026-09-14: 26 `user` rows,
every one a single non-synthetic text part, and no `synthetic` key anywhere in the store, so
opencode 1.18.31 was not observed writing such a row itself. The rule is the trust boundary, not
a convenience, and `tests/test_turns.py` exercises all four unmapped shapes.

`turns.py --find "<words>"` returns the `turn_ref` of each **user** turn whose own text parts
contain those words verbatim; an assistant turn holding the same words is never returned, and
neither is a synthetic part.

**How the session is bound (ruling E9-32).** Through the harness's own record and nothing else:
the pointer the setup's `session-pointer.js` plugin writes at the `chat.message` hook to
`${TMPDIR}/recheck-v2/opencode/<the opencode process id>.json`, read back through
`$OPENCODE_PID`, which the harness puts in every tool shell (measured: the tool shell receives
`OPENCODE=1` and `OPENCODE_PID` and **no** session id of any kind, so an environment variable
alone cannot do this). The pointer's payload is the harness's own hook input (`sessionID`, the
message `id` and `role`) plus two facts about the harness process itself (`opencode_pid`,
`cli_command`), never model text. There is **no `--session` at run time and no newest-session
fallback**: an absent `$OPENCODE_PID`, an absent or unreadable pointer, a pointer written by
another process, or a pointer naming a session the store does not hold is exit 3 naming what is
missing, never another session. `--session`, `--workspace` and `--db` are accepted only under
`RECHECK_ADAPTER_TEST=1`, the fixture interface. An unusable session record — one holding no
attributable turn — is exit 3 too, never an empty map (ruling E9-29).

**Label: instruction-bound**, with the failure modes named, because OpenCode applies no sandbox
to the executor's own tools. Two of them, both measured in `tests/test_turns.py`:

- **a rewritten pointer.** The pointer file sits in the run root the setup allows, and mode 600
  does not distinguish the harness from its own tool process; a `bash` command in the session
  can rewrite it to name another session, and the helper then binds to that session.
- **a newly written user row.** The SQLite store is writable by the session; a `user` row the
  session's own tools append is indistinguishable from the user's, is mapped as `user`, and a
  grant citing it is accepted by the core (`test_core_authorization.py` records exactly that).

Neither is a protected channel, and this profile does not claim one. A harness-enforced user
channel on OpenCode is carried to E11 as a capability question, the same way lane C carried it
under ruling E9-28. One more failure mode belongs to `--find`: a prompt passed to
`opencode run` as a positional argument is stored with the shell's own quoting around it, so
quoted words must be matched against the stored text, which `--find` does as a substring test.

Forwarding on a station route is the caller's: it forwards the user's grant unchanged and adds
`forwarded_by`, and the core rejects a station-route grant without it (ruling E7-13). The
adapter adds nothing to a forwarded grant.

## 5. `session_wrote_fix`

**instruction-bound** (ruling E9-14). `invocation.py` takes `--session-wrote-fix` as an explicit
flag and defaults to `false`; the helper never guesses it and no harness record answers it. On a
caller route the caller passes it. The executor's honest answer about its own session is the only
source, and an `upgraded` adjudication under a true value is recorded as `disputed` by the core.

## 6. Run date

`invocation.py` reports `--run-date` when the caller or the trial pins one, else the machine's
local calendar date from `datetime.date.today()`. The same date stamps the minted `run_id`, so a
run's id and the records it writes carry one day. **helper-derived** for the clock,
**instruction-bound** for a pinned date.

## 7. The verifier capability

The transport is one fresh `opencode run` per call, launched by `verifier.py` (ruling E9-7,
contract section 7, `references/verifier.md` section 7: a harness without readers supplies the
same contract itself). The exact launch is

```
opencode run --agent recheck-verifier --model <the bound driving session's own> --format json "<hand-off>"
```

with the working directory set to the workspace, `PWD` corrected to the workspace (OpenCode
takes its project directory from `$PWD`, not from the process working directory: a shell that
`cd`-ed elsewhere before calling the helper otherwise hands the fresh session the wrong project
and every workspace read comes back refused, measured 2026-09-14), stdin `/dev/null`, the four
isolated `XDG_*` homes set **unconditionally**, and `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`.

**Neither the model nor the agent is anyone's pick** (ruling E9-32). `verifier.py` takes no
`--model` and no `--agent`; both flags are a usage error. The agent is `recheck-verifier`,
always. The model is the bound driving session's own, read from the harness's record through the
same session pointer `turns.py` binds to — the session's assistant `modelID`/`providerID` first,
then its `session.model` column — and there is **no default and no configured fallback**: a
driving session whose model this helper cannot read is a missing harness record and stops it
(exit 3). The isolated setup and its pinned binary are required before any launch and there is
no PATH fallback; an absent setup, an absent binary, an absent brief or an unbindable session is
exit 3 naming what is missing (A7a, ruling E9-34), never a reported status.

**The paths are closed before anything is created** (Astra finding 4). `--brief` must be the
core's own `<run_dir>/checklist.md`, `--scratch` must be `<run_dir>/verifier`, `--raw` and both
launch captures must resolve inside that scratch after every symlink, `--call-id` must match the
schema's `run_id` pattern `[A-Za-z0-9._-]+`, and no destination is ever overwritten. Each of
those is exit 2, checked before the scratch directory exists.

The hand-off text is a fixed constant of this adapter, not the executor's words: it names the
brief file, says that file is the complete mandate, names the workspace and the scratch
directory, and asks for the report on standard output. Measured across the five preserved runs'
seven verifier sessions, each child's first `user` row is exactly that constant (743 to 752
characters, differing only in the two paths it carries; the rows are kept under the lane's
scratch `fix/child-rows/`) and every child session's `agent` is `recheck-verifier`. The fresh
context receives the brief's path, the workspace and the scratch directory, and nothing from the
driving session: no summary, no history, no fixer account, no orchestration text. It cannot see
the driving conversation at all (a separate session id, a separate process), and it is never
given the run id or the run directory, only `<run_dir>/verifier`. Whether the child can *reach*
the driving session's store is a boundary the control room measures, not something this profile
asserts: a separate process is not by itself a protection.

Containment is the `recheck-verifier` agent defined in the setup's `opencode.json`: the `edit`,
`write`, `patch`, `webfetch`, `websearch`, `task`, `skill` and `question` tools are switched off
and denied, `bash`, `read`, `grep` and `glob` are allowed, and the model is fixed to the setup's
own. `opencode debug agent recheck-verifier` shows the resolved ruleset (`tools off: edit,
question, skill, task, webfetch, write`; `edit *=deny`, `webfetch *=deny`, `write *=deny`,
`bash *=allow`), and the tool roster the session is given omits every denied tool. Edit, write,
web fetch, agent spawning and skill calls are therefore **harness-enforced** for the tools that
carry them: the model is not offered them and cannot call them. Measured in the fix round's
refusal probe: asked in words to call `webfetch`, the model reported "no webfetch tool is
available in this session" and made no tool call at all, so a roster-denied tool leaves **no
part in the event stream** — there is nothing for the helper to report as refused, and this
profile no longer claims otherwise.

A write performed through `bash` is **instruction-bound**, and the fix round measured how
completely: `bash *=allow` is the last matching rule for that agent, so `external_directory`
does not classify a bash path under it at all (section 3). A bash write anywhere succeeds. The
mandate's "writes confined to the scratch directory" is the verifier's own discipline, and the
core's boundary check over the tracked diff is what actually catches a violation. What is
measured rather than claimed: across the four completed live runs the result's
`boundary_violations` is `[]` in every one, and the verifier's own scratch writes were
`export-comma.log` and `export-plain.log` (run `recheck-a-20260920-0866`, F1-01 on Qwen,
child session `ses_f5e31683cffeCAPM67mTq8rP7C`), `export-comma.log` (run `…-a1d3`, F1-01 on
DeepSeek, child `ses_f5e1a05baffeKn2yhOSoxypDO8`), `export-comma.log` and `parse-detail.log`
(run `…-a034`, F2-01), and `export-comma.log` (run `…-2e71`, F6-04). The first pass's profile
named an `independent-parse.log`: **no such file exists** in any run directory, preserved or
original, and the claim is withdrawn (Astra finding 16's question about "the F1 session behind
independent-parse.log" has no answer because the file was never written).

The channels the harness injects into that context on its own, measured with sentinel
instruction files rather than assumed: OpenCode's own system prompt for the configured agent;
`<XDG_CONFIG_HOME>/opencode/AGENTS.md` when it exists (this setup ships none); and the
workspace's `AGENTS.md`, or its `CLAUDE.md` when there is no `AGENTS.md`. A `.opencode/AGENTS.md`
and a `README.md` were not injected, and a `CLAUDE.md` sitting beside an `AGENTS.md` was not.
`verifier.py` lists exactly the channels that exist for the call, so `record-call --injected`
carries the measured list. **harness-enforced** as a fact of the harness, **helper-derived** as a
declaration.

The report comes back as the session's final message text, which `verifier.py` assembles from the
`--format json` event stream's text parts and writes to `--raw`; the whole event stream is kept
at `<scratch>/launch-<call id>.json` and the child's stderr at `<scratch>/launch-<call id>.stderr`.
The status mapping onto `verifier.md` section 4: exit 0 with non-empty text **and the child's own
model row in the session store** → `ok`; exit 0 with non-empty text and no model row →
`lane-unavailable` naming the missing record, because a model that ran is reported as a fact or
not at all (ruling E9-32); exit 0 with no text → `empty`; killed at the timeout (900 s, the
readers row value) → `timed-out`; any other non-zero exit → `transport-failed` with the child's
stderr tail as `--note`, refined to `unknown-model`, `unauthorized` or `lane-unavailable` when
the stderr names one; `OPENROUTER_API_KEY` absent from the environment → `unauthorized`. An
absent binary is **not** a status: it is exit 3 (A7a, ruling E9-34). The model that ran and the
transport kind are read back from the record, not from the flags: the model from the verifier
session's own assistant message (`providerID/modelID`) in the session store, the kind the
constant `opencode-session`.

**Refusals are classified from the recorded permission outcome, not from a tool-name list**
(ruling E9-32, Astra finding 5). A `tool` part whose state is `denied` or `rejected`, or whose
error is the harness's own permission rejection — "The user rejected permission to use this
specific tool call.", measured verbatim on 1.18.31 across `read`, `write` and `bash` parts — is
a call the harness stopped **before it ran**, so it carries no side effect and becomes one
`--refused` line naming the tool and the path or command it was given. A denied `bash` counts;
so does a denied `read`. Any other error is reported in `--note` as an error with an **unknown**
side effect, never as "no side effect": a tool that failed after its request completed may well
have had one. A `tool` part named `unknown` with `metadata.interrupted` true is a harness
artifact of an aborted call, neither a refusal nor a completed action, and is counted in the
note. What the old tool-name allowlist cost, re-run over the retained records (the capture is
under the lane's scratch `fix/refusal-classification.txt`): in verifier session
`ses_f5e267831ffeofVCcwoI9jCNfs` it reported **0** refusals where two denied `read` calls were
recorded, and in executor session `ses_f5e29eaeeffeokB1zSyDmdz1nu` **0** where two denied `bash`
calls were recorded; the classifier reports all four. `verifier.py` never retries: the core
decides (contract section 7, one re-send under a fresh call id, then stop).

## 8. Delivery

**Label: harness-enforced** for the delivery itself (the `skill` tool's own recorded output
carries the whole body), **helper-derived** for nothing here; every figure below is a byte or
character count taken from the harness's own record. The measurements are
`../../../../setups/opencode/RESULTS.md` section 5, the surface matrix
`RESULTS.md` section 3 as re-measured in the fix round (raw catalogs under the lane's scratch
`fix/surfaces/`, one `opencode debug skill` capture per candidate, no model call).

The installation surface this setup ships is the isolated global skill directory,
`<XDG_CONFIG_HOME>/opencode/skill/<name>/SKILL.md`. Measured with the shared `delivery-probe`,
the installed 1.18.31 reads **nine** surfaces and ignores **two** (the first pass's prose said
seven while its own table listed nine; the count is reconciled here against a fresh measurement
of all eleven candidates): the global `<XDG_CONFIG_HOME>/opencode/skill/` and `/skills/`; the
workspace's `.opencode/skill/` and `/skills/`; the workspace's `.claude/skills/` and
`.agents/skills/`; the home's `~/.claude/skills/` and `~/.agents/skills/` (the real home, which
is why the setup sets `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`); and any directory named in the
config's `skills.paths` — nine. It does **not** read `<workspace>/skills/`, and with
`XDG_CONFIG_HOME` set it does not read `~/.config/opencode/skill/` — two. The switches, measured
again: `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` drops all four `.claude`/`.agents` surfaces,
workspace and home; `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` drops both `.claude/skills` surfaces
and leaves `~/.agents/skills` read (the first pass said it dropped `~/.claude/skills` only).

The rendering path is the native `skill` tool: the model calls `skill` with the skill's name and
the harness returns a `<skill_content name="…">` block holding the body after the frontmatter,
followed by a `<skill_files>` list of paths inside the skill folder. Delivery is complete on this
surface. **Bytes are UTF-8 bytes and are stated beside the character counts the harness records**
(ruling E9-34; the first pass reported the real body's character count as its byte count):

| | file | what the harness recorded as delivered |
|---|---|---|
| delivery probe | 25,831 bytes = 25,831 characters (ASCII only) | 25,976 bytes = 25,976 characters |
| the real recheck-v2 body | **23,332 bytes**, 23,308 characters | **24,045 bytes**, 24,021 characters |

The probe's tool output held the body verbatim, `SENTINEL S24` and the `END OF BODY` line
included, and the model listed all 25 sentinels and `END-OF-PROBE`; the real body's record held
the whole body, and the model reproduced the first sentence of step 8, the last Gotchas bullet
and the last References row verbatim without reading a file. No cut, so no first missing
sentinel. The delivered figures are the `skill` tool part's `state.output` length in the session
store, counted in both units over all nine recorded `skill` calls (eight of `recheck-v2`, all
24,021 characters / 24,045 bytes; one of `delivery-probe`, 25,976 of each).

One gap worth naming: the `<skill_files>` list is capped (10 entries on the real body,
all under `scripts/`) and named neither `references/` nor `adapters/`, so the executor learns the
skill root from those paths and reads the references with the `read` tool, which the harness
allows because it auto-allows each installed skill's own directory.

One executor behaviour belongs here rather than in the harness's column: in three of the four
completed live sessions the executor delivered `chat.md` with code fences and an added sentence
around it, where SKILL.md step 8 says to print that file verbatim as the whole reply (the
DeepSeek session's text matched after trimming a final newline). That is an **executor
observation, instruction-bound**, not a harness fact, and the control room's fresh proofs
re-measure it; nothing in this adapter enforces the shape of the reply.

## 9. Sidecars and invocation restrictions

**Label: harness-enforced for what the loader records, "prevents nothing" for the restrictions
themselves.** The measurement is `../../../../setups/opencode/RESULTS.md` section 6 (the
`opencode debug skill` record of the probe, and one live session under
`prompts/manual-only-probe.txt`).

OpenCode reads `name`, `description` and the body from `SKILL.md` frontmatter and ignores every
other field: `opencode debug skill` reports exactly `name`, `description`, `location` and
`content` for the manual-only probe, and neither `disable-model-invocation: true` nor
`user-invocable: true` appears anywhere in its record. The Codex sidecar `agents/openai.yaml`
with `policy.allow_implicit_invocation: false` is ignored as policy: it is listed only as one
more file under `<skill_files>`.

The manual-only probe's outcome: **ignored**. Asked in words ("I need the manual-only probe run
now. Please run the manual-only probe.") the session called the `skill` tool with
`{"name": "manual-only-probe"}` and replied `PROBE-RAN`. There is no separate explicit-invocation
form for skills in this harness; the `skill` tool is the one invocation path, and it ran. An
invocation restriction that is ignored **prevents nothing**: recheck-v2 must not be marked
manual-only for this harness without a harness-level guard (a permission rule denying the `skill`
tool, or a `skills.paths` arrangement that keeps the skill out of the catalog), because the
frontmatter flag and the Codex sidecar both do nothing here. This is also why recheck-v2's
auto-invocability (ruling E9-5) costs nothing on OpenCode: there is no restriction to lose.

## 10. Negative tests

**Label: harness-enforced where the row says `prevented activation`, enforced-by-the-core where
it says so, ignored where the harness does nothing.** Each row's behavior is now **derived** from
the check's exit status, the harness's own catalog and its diagnostics rather than assumed: a
check that did not produce a real observation reads `check failed`, the row's `ok` is false and
the script exits 4 (ruling E9-34, Astra finding 11 — a loader that exited 1 was previously
reported as `ignored` seven times). The measurement is
`../../../../setups/opencode/RESULTS.md` section 7 and the JSON the script prints, one object
per row with `exit_status`, `catalog` and `ok`.

The table of lane contract section 9.2, each test run in its own throwaway copy of the isolated
setup by `../../../../setups/opencode/negative-tests.sh`; the full observations, with the
harness's own message where it had one, are in `RESULTS.md`.

| Test | Behavior | What the harness did |
|---|---|---|
| a malformed `agents/openai.yaml` | ignored | still listed with its own name and description: OpenCode never reads the Codex sidecar, so no policy was in force to lose |
| a missing `agents/openai.yaml` | ignored | unchanged |
| `SKILL.md` with the `name` field removed | prevented activation | absent from the catalog, **with no message at all** |
| a broken frontmatter delimiter | prevented activation | absent from the catalog, **with no message at all** |
| a duplicate skill name on two surfaces | ignored | one copy listed (the `skill/` one wins over `skills/`), the other dropped silently |
| `references/verifier.md` deleted from the installed copy | enforced by the core, not the harness | the core stops as `stopped`, `reference unavailable: references/verifier.md`; the harness still lists and would still deliver the skill |
| a symlinked `SKILL.md` file | ignored | listed normally: unlike Codex, OpenCode follows a symlinked `SKILL.md` |
| a symlinked skill directory | ignored | listed normally |
| an update over an edited install: `install.sh` then `verify-install.sh` | enforced | the row edits the installed `SKILL.md` and replaces `references/` with a symlink, then runs the **real installer** against the throwaway setup and verifies the package: `install.sh` exit 0, `verify-install.sh` exit 0, `ok=true`, `diff_empty=true`, `symlinks_in_package=[]`, no findings |

Two behaviours that change how this adapter is built, both recorded in `RESULTS.md` with their
commands: a headless `opencode run` auto-rejects any permission whose action is `ask`
("permission requested: external_directory (<path>); auto-rejecting" on stderr, "The user
rejected permission to use this specific tool call" on the tool part), which is why the setup
allows `external_directory` under the run root and why section 3 tells the executor to keep
every path and redirect inside the allowed sets; and `opencode debug skill` cuts its stdout at
65,536 bytes when stdout is a pipe while writing all of it to a file, which is why every helper
and script captures a harness listing by redirection.

## 11. Installed-package verification

**Label: helper-derived** (the script computes every check from the installed bytes and the
harness's own listing; nothing here is the executor's word). The measurement is
`../../../../setups/opencode/RESULTS.md` section 4, which carries the script's own JSON.

`setups/opencode/verify-install.sh` prints one JSON object and exits 4 on any finding. It checks:
the path the harness actually loads the skill from (`opencode debug skill`, captured to a file)
equals the installed folder; `diff -r` of the installed folder against the canonical one,
excluding `__pycache__`, is empty; the installed `SKILL.md`'s `name`, `description` and
`metadata.version` equal the canonical ones; **every referenced path resolves inside the
installed skill root after every symlink** — the Markdown links *and* the backticked paths that
SKILL.md, the adapter index and each `adapters/*/profile.md` actually use (12 links and 83
backticked paths on this branch, none outside, none reached through a symlink); **no symlink
anywhere in the installed tree**, because identical bytes behind a symlink pass `diff -r`
(Astra finding 10: an installed `adapters/opencode/profile.md` symlink pointing outside the
root was reported as verified); and `recheck.py skill-identity` run from the installed copy
reports the same `content_sha256` as the canonical checkout. Per ruling E9-16 the identity's
`version` and `commit` come from the packaging around the skill and read `unversioned` on this
host-skill copy: they are recorded, never compared. Backticked tokens that resolve to nothing in
the package (`chat.md`, `result.json`, and on this lane-only branch the other lanes'
`claude-code/…` and `codex/…` entries in the adapter index) are listed under
`backticked_tokens_not_package_paths` rather than treated as findings; the other lanes' files
arrive on the integration branch.

## 12. Capability labels

One row per capability of pilot contract section 13.

| Capability | Label | The measurement |
|---|---|---|
| Read any file in the workspace | harness-enforced | the `read`, `grep` and `glob` tools are allowed with `read * = allow`; the live proof's verifier read `src/widget/export.py` and the build doc. A `read` outside the allowed roots is refused and recorded (four verifier sessions carry such a part) |
| Run commands in the workspace with writes confined to scratch and ignored caches | instruction-bound for the confinement, harness-enforced for the running | `bash` is allowed and ran the scenario command. Nothing in the harness confines a `bash` write under the verifier's agent: `bash *=allow` is the last matching rule, so `external_directory` does not classify a bash path at all (measured in the fix round's refusal probe, `ses_f5dc422daffe3bQhkCng7GM9FX`: a write outside the workspace and outside every allowed root completed with exit 0). Confinement is the mandate's discipline and the core's post-run tracked-diff check is the actual guard: `boundary_violations` is `[]` on all four completed runs, and the verifier's own scratch writes are listed in section 7 |
| Create exactly one fresh verifier context per call, with the same read-and-run capability, the mandate's restrictions, and no access to the driving conversation | harness-enforced for the fresh context and the denied tools; **unmeasured** for "no access to the driving conversation" | one `opencode run --agent recheck-verifier` per call, a separate process with its own session id, and the denied tools are absent from its roster (`opencode debug agent recheck-verifier`); each child's first `user` row is the fixed hand-off constant and nothing else (seven child sessions, `fix/child-rows/`). Separate-process creation does **not** establish that the child cannot read the shared driving-session store; that boundary is the control room's live check, and until it is run this row claims no protection for it |
| Declare what the harness injects into that context on its own | helper-derived | `verifier.py` lists the system prompt plus the instruction files that exist, by the rule measured with sentinel files (section 7, `RESULTS.md` section 3) |
| Supply the user channel for grants: `turn_ref` for the user's message, and forwarding for station callers | **instruction-bound** (ruling E9-32) | `turns.py` binds to the session only through the harness's own pointer, keyed by `$OPENCODE_PID`, with no `--session` at run time and no newest-session fallback; ambiguity and an absent record are exit 3. But OpenCode applies no sandbox to the executor's own tools, so the pointer file and the SQLite store both stay writable by the session: a rewritten pointer selects another session and a newly written `user` row is accepted as the user's. Both failure modes are named in section 4 and recorded by `tests/test_turns.py` and `tests/test_core_authorization.py`. Forwarding is the caller's |
| Assert whether the running model satisfies `policy.model_floor` | helper-derived, on a provisional map | the id from the session's own message record, the class from ruling E9-3's map, `floor_met` by rank. This harness cannot present a below-floor id under D3a; the core's stop is proved by driving it with such an input (`RESULTS.md` section 8, V1-01, validator `ok: true`) |
| Report the harness name, version, entry path, sandbox, and the model id and settings actually used | helper-derived | version from the session record, entry from the adapter's own path, sandbox from `opencode debug agent`, model and settings from the message record and `opencode models --verbose`; `invocation.py`'s `measurement` object names the record behind every field |
| State whether the driving session authored any fix under review | instruction-bound | `--session-wrote-fix`, default false; no harness record answers it |
| Attribute turn references to the user, the assistant, or a station | helper-derived for the attribution, instruction-bound for the channel it rests on (the row above) | the `role` field of the harness's own message records; internal-agent rows, `synthetic` rows and tool-only `user` rows left unmapped (ruling E9-22) |
| Deliver the complete skill body and let the core load its references on demand | harness-enforced | the `skill` tool's recorded output holds the whole body: 24,045 bytes / 24,021 characters for a 23,332-byte / 23,308-character file (section 8); references are read from the installed folder, which the harness auto-allows |
| Return the result document to the caller unchanged | instruction-bound | the executor hands `result.json` over; nothing in the harness touches it. Measured limit: in three of four live sessions the executor added fences and a sentence around `chat.md` (section 8) |
| Refuse or surface, never silently drop, a prohibited action | harness-enforced for a permission refusal, instruction-bound for a `bash` action | a refusal is read from the harness's own recorded permission outcome — state `denied`/`rejected`, or the error "The user rejected permission to use this specific tool call." — and becomes one `--refused` line, a denied `bash` and a denied `read` included; any other error is reported with an **unknown** side effect, never "no side effect" (section 7, `fix/refusal-classification.txt`). A roster-denied tool such as `webfetch` is never offered to the model and leaves no part at all, so there is nothing to surface for it |

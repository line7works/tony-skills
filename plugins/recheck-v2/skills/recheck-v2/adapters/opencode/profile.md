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

**What the executor types, and what it never types** (lane contract section 5.3). It types
`mode`, `caller` and `resume`; `session_wrote_fix` as its honest answer about its own session
(section 5); the target it was asked for and the named items, spelled as the record spells them;
and each grant's `quoted_words` verbatim beside the `turn_ref` that `turns.py --find` returned
for those words. It never types a `turn_ref`, a model id, a harness version, an entry, a
sandbox, an attribution map, a `floor_class`, a `floor_met`, a `run_id`, a `run_dir`, a
`context_tokens` or any `settings` value: `invocation.py` and `turns.py` print all of those as
facts and the executor copies them. It never picks the verifier's model, reasoning setting or
authorization either: `verifier.py` reads the model sub-setup in force from the harness's own
record.

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

**What the executor must keep inside.** OpenCode's `external_directory` permission classifies
every path a tool touches, `bash` included, and an unmatched path is `ask`, which a headless run
auto-rejects ("permission requested: external_directory (<path>); auto-rejecting" on stderr, and
"The user rejected permission to use this specific tool call" on the tool part). Four path sets
are allowed: the workspace (the session's own directory), the installed skill folder, the run
root `${TMPDIR}/recheck-v2/**` and `/tmp/recheck-v2/**`, and the harness's own tool-output
directory. So every command the executor runs keeps its paths, **its redirects included**, inside
those: a stderr redirect to `/tmp/<name>.err` is refused, and `2> "<run_dir>/<name>.err"` is not.
A relative path that does not exist is normalised up to an existing ancestor before it is
classified, so a mistyped `ls workspace` run from inside the workspace asks for the workspace's
parent and is refused; address the workspace as `.` or by its absolute path. A refusal here is
the harness's containment working, not a fault to route around: retry with a contained path.

## 4. The user channel

`turn_ref` is `opencode:session <session id>:message <message id>`. The session's own record is
the session store OpenCode 1.18.31 keeps as a single SQLite database at
`<XDG_DATA_HOME>/opencode/opencode.db` (not the `storage/session/**` JSON tree earlier versions
used): the `session` table carries `id`, `directory`, `agent`, `model`, `version` and
`time_created`; the `message` table carries one row per turn whose `data` JSON holds `role`
(`user` or `assistant`), `agent`, and, on an assistant row, `modelID`, `providerID`, `cost` and
`tokens`; the `part` table holds each message's text, reasoning, tool and step parts. `turns.py`
reads only `session`, `message` and `part` — never the store's `credential` or `account` tables.

`turns.py` builds `turn_attribution` over the whole session: every `user` row maps to `user`,
every `assistant` row to `assistant`, and a row written by one of the harness's own internal
agents (`compaction`, `title`, `summary`) stays out of the map, so ruling E9-1 rejects a grant
citing it as naming no turn of the session. `turns.py --find "<words>"` returns the `turn_ref` of
each **user** turn whose own text parts contain those words verbatim; an assistant turn holding
the same words is never returned.

The session locates its own record in this order, and the choice is reported as `resolved_by`:
(1) an explicit `--session`; (2) the pointer the setup's `session-pointer.js` plugin writes at
the `chat.message` hook to `${TMPDIR}/recheck-v2/opencode/<the opencode process id>.json`, read
back through `$OPENCODE_PID`, which the tool shell is given (measured: the tool shell receives
`OPENCODE=1` and `OPENCODE_PID` and **no** session id of any kind, so an environment variable
alone cannot do this); (3) the newest session in the store whose `directory` is the workspace.
The pointer's payload is the harness's own hook input (`sessionID`, the message `id` and `role`),
never model text. **helper-derived**, with these failure modes: the plugin absent or disabled
(`--pure`, `OPENCODE_DISABLE_DEFAULT_PLUGINS`) drops route 2; two sessions in one workspace
directory make route 3 ambiguous, and the helper reports the candidate count so the ambiguity is
visible rather than silent; a session whose pointer names an id the store does not hold falls
back to route 3 with a line on stderr. One more failure mode belongs to `--find`: a prompt passed
to `opencode run` as a positional argument is stored with the shell's own quoting around it, so
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
opencode run --agent recheck-verifier --model <the setup's own> --format json "<hand-off>"
```

with the working directory set to the workspace, `PWD` corrected to the workspace (OpenCode
takes its project directory from `$PWD`, not from the process working directory: a shell that
`cd`-ed elsewhere before calling the helper otherwise hands the fresh session the wrong project
and every workspace read comes back refused, measured 2026-09-14), stdin `/dev/null`, the
isolated `XDG_*` homes, and `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`. The model is not the
executor's pick and not a helper constant: with no `--model` the helper reads the sub-setup in
force from the harness's own records, the driving session's own model first, then the setup's
configured `model`. The hand-off text is a fixed constant of this adapter,
not the executor's words: it names the brief file, says that file is the complete mandate, names
the workspace and the scratch directory, and asks for the report on standard output. The fresh
context receives the brief's path, the workspace and the scratch directory, and nothing from the
driving session: no summary, no history, no fixer account, no orchestration text. It cannot see
the driving conversation at all (a separate session id, a separate process), and it is never
given the run id or the run directory, only `<run_dir>/verifier`.

Containment is the `recheck-verifier` agent defined in the setup's `opencode.json`: the `edit`,
`write`, `patch`, `webfetch`, `websearch`, `task`, `skill` and `question` tools are switched off
and denied, `bash`, `read`, `grep` and `glob` are allowed, and the model is fixed to the setup's
own. `opencode debug agent recheck-verifier` shows the resolved ruleset, and the tool roster the
session is given omits every denied tool. Edit, write, web fetch, agent spawning and skill calls
are therefore **harness-enforced** for the tools that carry them: the model is not offered them
and cannot call them. A write performed through `bash` is **instruction-bound**: `bash` must stay
allowed for the scenarios to run, so the mandate's "writes confined to the scratch directory" is
the verifier's own discipline there, and the core's own boundary check over the tracked diff is
what actually catches a violation. Measured on the F1-01 verifier call: the verifier wrote only
`export-comma.log` and `independent-parse.log` under its scratch directory and `git status
--porcelain` in the workspace was empty afterwards.

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
The status mapping onto `verifier.md` section 4: exit 0 with non-empty text → `ok`; exit 0 with
no text → `empty`; killed at the timeout (900 s, the readers row value) → `timed-out`; any other
non-zero exit → `transport-failed` with the child's stderr tail as `--note`, refined to
`unknown-model`, `unauthorized` or `lane-unavailable` when the stderr names one; the binary
missing → `lane-unavailable`; `OPENROUTER_API_KEY` absent from the environment → `unauthorized`.
The model that ran and the transport kind are read back from the record, not from the flags: the
model from the verifier session's own assistant message (`providerID/modelID`) in the session
store, the kind the constant `opencode-session`. Prohibited actions the transport refused with no
side effect are taken from the event stream: a `tool` part whose tool is one the agent denies and
whose state is `error`, `denied` or `rejected` becomes one `--refused` line. A `tool` part named
`unknown` with `metadata.interrupted` true is a harness artifact of an aborted call, not a
refusal, and is not listed. `verifier.py` never retries: the core decides (contract section 7,
one re-send under a fresh call id, then stop).

## 8. Delivery

The installation surface this setup ships is the isolated global skill directory,
`<XDG_CONFIG_HOME>/opencode/skill/<name>/SKILL.md`. Measured with the shared `delivery-probe`,
the installed 1.18.31 reads seven surfaces and ignores two: the global
`<XDG_CONFIG_HOME>/opencode/skill/` and `/skills/`; the workspace's `.opencode/skill/` and
`/skills/`; the workspace's `.claude/skills/` and `.agents/skills/`; the home's
`~/.claude/skills/` and `~/.agents/skills/` (the real home, which is why the setup sets
`OPENCODE_DISABLE_EXTERNAL_SKILLS=1`); and any directory named in the config's `skills.paths`.
It does **not** read `<workspace>/skills/`, and with `XDG_CONFIG_HOME` set it does not read
`~/.config/opencode/skill/`, so the isolation holds.

The rendering path is the native `skill` tool: the model calls `skill` with the skill's name and
the harness returns a `<skill_content name="…">` block holding the body after the frontmatter,
followed by a `<skill_files>` list of paths inside the skill folder. Delivery is complete on this
surface. The probe's 25,831-byte file was recorded as 25,976 characters of tool output holding
the body verbatim, `SENTINEL S24` and the `END OF BODY` line included, and the model listed all
25 sentinels and `END-OF-PROBE`; the real body, 23,308 bytes, was recorded as 24,021 characters
holding the whole body, and the model reproduced the first sentence of step 8, the last Gotchas
bullet and the last References row verbatim without reading a file. No cut, so no first missing
sentinel. One gap worth naming: the `<skill_files>` list is capped (10 entries on the real body,
all under `scripts/`) and named neither `references/` nor `adapters/`, so the executor learns the
skill root from those paths and reads the references with the `read` tool, which the harness
allows because it auto-allows each installed skill's own directory.

## 9. Sidecars and invocation restrictions

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
| an update from a symlink back to a copy, then diff | enforced | `before=symlink after=copy diff=empty`; `install.sh` removes the installed folder before copying, so neither form survives a reinstall |

Two behaviours that change how this adapter is built, both recorded in `RESULTS.md` with their
commands: a headless `opencode run` auto-rejects any permission whose action is `ask`
("permission requested: external_directory (<path>); auto-rejecting" on stderr, "The user
rejected permission to use this specific tool call" on the tool part), which is why the setup
allows `external_directory` under the run root and why section 3 tells the executor to keep
every path and redirect inside the allowed sets; and `opencode debug skill` cuts its stdout at
65,536 bytes when stdout is a pipe while writing all of it to a file, which is why every helper
and script captures a harness listing by redirection.

## 11. Installed-package verification

`setups/opencode/verify-install.sh` prints one JSON object and exits 4 on any finding. It checks:
the path the harness actually loads the skill from (`opencode debug skill`, captured to a file)
equals the installed folder; `diff -r` of the installed folder against the canonical one,
excluding `__pycache__`, is empty; the installed `SKILL.md`'s `name`, `description` and
`metadata.version` equal the canonical ones; every relative link in the installed `SKILL.md`,
`adapters/README.md` and `references/*.md` resolves to an existing path inside the installed
skill root (12 links checked, none outside); the installed folder and its `SKILL.md` are real
files, not symlinks; and `recheck.py skill-identity` run from the installed copy reports the same
`content_sha256` as the canonical checkout. Per ruling E9-16 the identity's `version` and
`commit` come from the packaging around the skill and read `unversioned` on this host-skill copy:
they are recorded, never compared.

## 12. Capability labels

One row per capability of pilot contract section 13.

| Capability | Label | The measurement |
|---|---|---|
| Read any file in the workspace | harness-enforced | the `read`, `grep` and `glob` tools are allowed with `read * = allow`; the live proof's verifier read `src/widget/export.py` and the build doc |
| Run commands in the workspace with writes confined to scratch and ignored caches | instruction-bound for the confinement, harness-enforced for the running | `bash` is allowed and ran the scenario command; nothing in the harness confines a `bash` write, so confinement is the mandate's discipline and the core's post-run tracked-diff check is the actual guard. Measured: the verifier's only writes were two logs under its scratch directory and `git status --porcelain` was empty afterwards |
| Create exactly one fresh verifier context per call, with the same read-and-run capability, the mandate's restrictions, and no access to the driving conversation | harness-enforced | one `opencode run --agent recheck-verifier` per call, a separate process with its own session id; the denied tools are absent from its roster (`opencode debug agent recheck-verifier`) |
| Declare what the harness injects into that context on its own | helper-derived | `verifier.py` lists the system prompt plus the instruction files that exist, by the rule measured with sentinel files (section 7) |
| Supply the user channel for grants: `turn_ref` for the user's message, and forwarding for station callers | helper-derived | `turns.py` over the session store's `message` rows; the plugin pointer and the newest-in-directory fallback, with the failure modes of section 4. Forwarding is the caller's |
| Assert whether the running model satisfies `policy.model_floor` | helper-derived, on a provisional map | the id from the session's own message record, the class from ruling E9-3's map, `floor_met` by rank. This harness cannot present a below-floor id under D3a |
| Report the harness name, version, entry path, sandbox, and the model id and settings actually used | helper-derived | version from the session record, entry from the adapter's own path, sandbox from `opencode debug agent`, model and settings from the message record and `opencode models --verbose` |
| State whether the driving session authored any fix under review | instruction-bound | `--session-wrote-fix`, default false; no harness record answers it |
| Attribute turn references to the user, the assistant, or a station | helper-derived | the `role` column of the harness's own message records; internal-agent rows left unmapped |
| Deliver the complete skill body and let the core load its references on demand | harness-enforced | the `skill` tool's recorded output holds the whole body (section 8); references are read from the installed folder, which the harness auto-allows |
| Return the result document to the caller unchanged | instruction-bound | the executor hands `result.json` over; nothing in the harness touches it |
| Refuse or surface, never silently drop, a prohibited action | harness-enforced for a denied tool, instruction-bound for a `bash` action | a denied tool is not in the roster and a call to one is reported as an error part in the event stream, which `verifier.py` turns into a `--refused` line; a `bash` command is not classified by the harness |

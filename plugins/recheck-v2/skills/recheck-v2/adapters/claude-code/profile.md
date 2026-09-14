# Adapter profile: Claude Code

The recheck-v2 adapter for Claude Code (E9 lane C; the lane contract
`docs/plans/2026-09-14-recheck-v2-e9-adapters.md` sections 5 and 6). Read this after
`../README.md` and before step 2 of `../../SKILL.md`; read section 7 again before step 4.

Every fact below was measured on 2026-09-14 on this machine with Claude Code 2.1.270 and is
labelled `harness-enforced`, `helper-derived`, or `instruction-bound` (ruling E9-11). The
measurement is named beside the label. The setup that produced them is
`../../../../setups/claude-code/` and its record is that directory's `RESULTS.md`.

**What the executor types and what it never types.** The executor runs the three helpers and
copies their output into the input document. It may type `mode`, `caller`, `resume`, the
target, the named items, `session_wrote_fix` as its honest answer, and a grant's
`quoted_words` verbatim beside the `turn_ref` that `turns.py --find` returned. `mode` is typed
from `invocation.py`'s `mode_hint`, which is a fact and not a pick: a headless `claude -p`
session's tool shell carries `CLAUDE_CODE_SESSION_ATTENDED=0` and
`CLAUDE_CODE_ENTRYPOINT=sdk-cli`, an interactive one carries `1` and `cli` (both measured
2026-09-14), and the helper falls back to `unknown` when neither is set. A run that types
`interactive` in a headless session asks its one question into a channel nobody reads, which
contract section 2 calls a failure; the lane's own F1-01 live proof typed `interactive` in a
`claude -p` session before `mode_hint` existed. It never types
a `turn_ref`, a model id, a harness version, an attribution, `floor_met`, a run id, a run
directory, a `session_model`, or a verifier row, model, effort, or authorization.

## 1. Identity

`harness.name` is `claude-code`. `harness.version` comes from `claude --version`, whose first
token on this machine is `2.1.270`; `invocation.py` runs that command and reports the token,
and exits 3 when the binary is not on PATH (`helper-derived`). `harness.entry` is derived
from the helper's own path: a copy under the active `CLAUDE_CONFIG_DIR`'s
`plugins/cache/<marketplace>/<plugin>/<version>/` is `plugin`, a copy under a
`.claude/skills/` or `.agents/skills/` directory is `host skill`, anything else is
`explicit path`, and a cache copy that is not under the active config directory reads
`explicit path (installed plugin cache loaded with --plugin-dir)` (`helper-derived`; measured
by running the helper from both surfaces). `harness.sandbox` is the permission mode in force:
Claude Code exports no variable naming it to a tool shell (measured: the tool shell's
environment carries `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_PID`, `CLAUDE_EFFORT`,
`CLAUDE_CODE_ENTRYPOINT` and no permission mode), so `launch.sh` exports
`RECHECK_HARNESS_SANDBOX` with the `--permission-mode` value it passed and `invocation.py`
reports it; outside the setup the field reads `unknown (no permission-mode record reachable
from the session)` and the run still validates, since the schema asks only for a non-empty
string (`helper-derived` from the launcher's own record, `instruction-bound` nowhere: the
helper never asks the model).

**Sign-in, the lane's one stop.** An isolated `CLAUDE_CONFIG_DIR` does **not** keep the
machine's sign-in. Measured: `CLAUDE_CONFIG_DIR=~/.local/share/skills-v2-pilot/claude-code/config
claude -p 'say ok' --output-format json` answers `"result": "Not logged in · Please run
/login"`, `is_error: true`, `total_cost_usd: 0`. E9 section 6 rules for exactly this case, so
every live run loads the pilot with `--plugin-dir` against the machine's own configuration
directory, and `launch.sh` adds `--setting-sources local` (the machine's user settings, which
is where installed plugins are enabled, are dropped: the catalog is the 18 built-in skills
plus the plugins named on the command line, and no v1 station) and `--strict-mcp-config` (no
MCP server). The catalog each live session actually had is recorded in its `launch.json` from
the session's own `init` event. The install into the isolated config directory is real and
verified (`verify-install.sh`), but no session can run inside it until it is signed in; that
is the lane's recorded stop, not a workaround.

## 2. Model and floor

`model.id` is the `message.model` of the last non-sidechain `assistant` record in the
session's own transcript, a value the harness wrote (`helper-derived`). The map of ruling
E9-3, which `invocation.py` applies and `tests/test_invocation.py` covers: `claude-opus-*`,
`claude-fable-*` and `claude-mythos-*` are class `opus` with `floor_met` true against the
default floor `opus`; `claude-sonnet-*` is `sonnet` and `claude-haiku-*` is `haiku`, both
`floor_met` false; anything else is `unknown` with `floor_met` null, which the core turns into
`verifier_unavailable` (`unknown_capability`). None of the Claude classes is provisional. Two
measured cautions. First, the trace's `init.model` carries a context suffix the transcript
drops: one session recorded `claude-opus-5[1m]` in its `init` event and `claude-opus-5` in
every `message.model`; both match `claude-opus-*`, so the class is the same, and the helper
reports the transcript's form. Second, the model a session's system prompt names can differ
from the model its transcript records: in the builder's own session the system prompt said
`claude-opus-5[1m]` while all 137 assistant records said `claude-fable-5-1`. The helper reads
the record, never the model's account of itself (E8-A17 says the adapter reports "the id the
harness reports for this session"), and the same id is what `verifier.py` puts in
`session_model`. `effort` comes from that record's `effort` field, cross-checked against
`$CLAUDE_EFFORT`; `provider_route` is `anthropic` unless `CLAUDE_CODE_USE_BEDROCK`,
`CLAUDE_CODE_USE_VERTEX` or `CLAUDE_CODE_USE_FOUNDRY` is set; `settings` carries the
entrypoint, the effort as recorded and as the environment gives it, and the permission mode.
`context_tokens` is **not reported**: the window appears only in the `result` event's
`modelUsage` (`contextWindow: 1000000` measured there), which a session cannot read about
itself, and the field is optional in the schema.

## 3. Run id and directory

`invocation.py` mints `recheck-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>`
(the token slugged from `--target-token`, the date the run date) and
`${TMPDIR:-/tmp}/recheck-v2/<run_id>` as the run directory, which is outside every workspace
because `TMPDIR` is the user's per-session temporary directory. The helper names the
directory and never creates it: `recheck.py start` creates it, and a run directory that
already holds a checkpoint, a receipt, or a result is spent. Ids are single use: every call
mints fresh randomness, and a resume passes the same input document again rather than calling
the helper again. On a caller route `--caller NAME --run-id ID --run-dir DIR` are passed
together and the caller's ids are kept unchanged (`helper-derived`; the three flags are
refused unless all three are present, exit 2).

## 4. The user channel

`turn_ref` is `claude-code:session <sessionId>:msg <uuid>`, both fields read from the
session's own transcript record. `turns.py` builds the whole map; `turns.py --find "<words>"`
answers with the user turn references whose text contains those words verbatim, and prints no
user text. The executor takes the reference from that answer and never composes one.

*How the session finds its own transcript*, in the order `turns.py` tries and the measurement
behind each: (1) `--transcript`; (2) `--session-id`; (3) **the harness's own
`CLAUDE_CODE_SESSION_ID` in the tool shell's environment**, resolved to
`<config>/projects/*/<id>.jsonl` — measured in an interactive session and in a headless
`claude -p` session, and the id equals the transcript's file name in both; (4) a hook payload
keyed by `CLAUDE_PID` at `${TMPDIR}/recheck-v2/claude-code/<pid>.json`, for a setup that ships
one; (5) the newest transcript whose records name the workspace as their `cwd`, whose note
says how many matched. The label is `helper-derived` from a harness-written record.
Candidate (a) of E9 section 6 as it is written there does **not** hold and is not what this
adapter ships: the hook's `$PPID` is the `claude` process (measured 14773) while the Bash
tool's shell has an intervening `/bin/zsh` in a headless session (measured `$PPID` 16243,
`CLAUDE_PID` 14773), so a payload keyed by the hook's `$PPID` and read back through the tool
shell's own `$PPID` misses. `CLAUDE_PID` is the value that matches, and candidate (3) needs no
hook at all, so `plugins/recheck-v2/hooks/hooks.json` is not shipped and the plugin adds no
`SessionStart` context noise.

*Roles.* A non-sidechain `assistant` record is `assistant`. A non-sidechain `user` record
whose `message.content` is a string or text blocks is the user's turn — **except** when the
record carries `isMeta`, `turnCompanion`, `sourceToolUseID` or `toolUseResult`, which the
harness sets on records it wrote itself. That exception is this adapter's, not the lane
contract's, and it is load-bearing: the body of a skill the session invokes is delivered as a
`user` record of text blocks (measured: the 25,770-byte delivery-probe body landed as one,
with `isMeta: true`, `turnCompanion: true` and `sourceToolUseID`), so the contract's rule as
written would attribute a delivered skill body to the user and let a grant cite its uuid. With
the exception, the same probe session maps exactly one user turn (the prompt) and the body
stays unmapped, counted under `unmapped_harness_written`. `isSidechain` records (a subagent's,
the verifier's included) stay unmapped, so a grant can never cite the verifier's own turn.
*Failure modes:* a session whose transcript has not been flushed yet has no map (exit 3, and
the executor stops rather than guessing); two sessions in one directory make candidate (5)
ambiguous and the note says so; a harness-injected `user` record that carries none of the four
keys would still map as `user` (none was observed).

*The station route.* A calling station passes the input whole, its own
`turn_attribution` included, and the executor changes nothing. Where a Claude session hosts a
station, `--station-ref REF` (repeatable) puts that reference in the map as `station`; the
values come from the caller's payload, never from the executor.

## 5. `session_wrote_fix`

The executor's honest answer from the session it runs in, `instruction-bound` (ruling E9-14):
true when this session authored any fix under review. `invocation.py` takes
`--session-wrote-fix` as an explicit flag and defaults to false; it never guesses. On a caller
route the caller passes the value and the executor forwards it unchanged. The core stores it
in the checkpoint, a resume uses the stored value, and an `upgraded` adjudication under a true
value is recorded as `disputed` with the item left open (E8-13).

## 6. Run date

`invocation.py --run-date YYYY-MM-DD` when the request pins one (a trial pins
`trial-defaults.json`'s date, 2026-09-20); otherwise the machine's local calendar date from
`datetime.date.today()` (`helper-derived`). On a caller route the caller's date travels in the
payload. The `_sources.run_date` field says which of the two produced the value.

## 7. The verifier capability

The transport is the readers component: row `claude-session`, profile `repo-with-tools`, which
readers runs as a fresh `general-purpose` subagent through the Agent tool with the composed
prompt handed over as the file `<call dir>/prompt.md`. `verifier.py --brief <run_dir>/checklist.md
--workspace <ws> --scratch <run_dir>/verifier --raw <run_dir>/verifier/raw.md --call-id <id>`
prints the request block of `../../references/verifier.md` section 6 with `session_model`
filled from the harness record and `authorized` omitted (a Claude row is an `anthropic` row
and needs no word); `row`, `profile` and `floor` are the profile's and the input's, never the
executor's picks, and `model`, `effort`, `output_budget` and `isolation` are never written.
`isolation: worktree` is deliberately not requested: the scenario must run in the real
checkout. The executor invokes `/readers` with that block and hands the sidecar back to
`verifier.py --sidecar <path>`, which prints the `record-call` flags.

*What the fresh context receives:* the brief's path as its `mandate`, the workspace, and
`<run_dir>/verifier` as its scratch. It receives nothing from the driving session: no
conversation, no reasoning, no prior finding (readers' "cold means cold" rule). *What the
harness injects on its own*, from the readers contract's "The Claude lane" for the Agent
route, measured by readers on 2026-09-07 and 2026-09-08 and reported here rather than
re-measured: the workspace's instruction files and their imports, the user's global
instruction file and its imports, the repo's auto-memory index, the harness's git-status
block, the `userEmail` line, and the harness's tool rosters. `verifier.py` lists all six under
`--injected`, plus the sidecar's own `workdir_instruction_files`, so `run.verifier.injected_channels`
names them and the mandate treats them as data to verify.

*Containment.* On this route it is `instruction-bound`: readers' own roster labels
`repo-with-tools` isolation `unmeasured` for `claude-session`, and its parity line is "web
tools forbidden by instruction". This setup raises one part of it to `harness-enforced`:
`launch.sh` passes `--disallowed-tools WebFetch WebSearch` and the settings deny both, so the
"no web tool" clause of the mandate is enforced by the harness for the whole session,
subagents included, and a prohibited fetch appears in the trace as a denial rather than as a
promise kept. "No other model, no MCP tool, no outbound service" stays `instruction-bound`,
with `--strict-mcp-config` removing every MCP server as a second measured floor. "No call to
any skill or station" is `harness-enforced` in this setup only in the sense that no v1 station
is in the catalog (`--setting-sources local`), which the session's `init` event records.

*The report.* readers writes the capture to `raw_path` and the sidecar beside it;
`verifier.py --sidecar` maps `status` → `--status`, `raw_file`/`raw_path` → `--raw`,
`effective_model` → `--model`, `transport` → `--kind`, `workdir_instruction_files` plus the
six channels → `--injected`, `reason` → `--note`, and reports readers' `oversize` as
`invalid-request` with the estimate and the limit in the note (verifier.md section 6). It
downgrades a claimed `ok` whose raw file is missing or empty to `capture-failed`, so `ok` is
only ever recorded with a report on disk. It never retries: the core decides (one re-send
under `<run_id>-verify-2`, then the run stops).

*A call the harness cannot make.* If readers cannot supply a fresh context at all, the status
is `lane-unavailable` and the core stops as `verifier_unavailable`. Nothing is graded from the
driving context.

## 8. Delivery

Two surfaces ship. **The installed plugin** (`claude plugin install recheck-v2@tony-skills`
into the isolated `CLAUDE_CONFIG_DIR`), loaded into a live session with `--plugin-dir` onto
the install cache because the isolated configuration directory has no sign-in (section 1);
and **the explicit path** (`--plugin-dir <worktree>/plugins/recheck-v2`). The rendering path
is the same on both: the harness delivers the whole `SKILL.md` body, minus the frontmatter
block, as one `user` record of text blocks carrying `isMeta`, `turnCompanion` and
`sourceToolUseID`, which is also where the delivered bytes are counted.

*The delivery probe*, 25 sentinels over 25,831 bytes: **25 of 25 on both surfaces**, S01
through S24 plus `SENTINEL S25: end of body`, and the model's list cross-checked against the
text the harness recorded as delivered (the probe's record holds all 25 sentinels and the
`END OF BODY` line; 25,770 bytes of body text). No cut, so no first missing sentinel.

*The real body*, 23,332 bytes on disk: delivered whole, 22,511 bytes of body text in the
harness's own record (the 821-byte frontmatter block is rendered separately). Asked to quote
from the delivered text without reading any file, the model returned the last row of the
References table, the last bullet of the Gotchas section, and the heading of the last
numbered Procedure step, all three byte-identical to the canonical file; the record also
carries `## Gotchas`, `## Failure handling`, `## References` and the output block's
`SKILL NOTE:` line. The last procedure step and the Gotchas section both reach the model,
which is what E9-6 asks.

*The listing budget.* `claude plugin details recheck-v2` and the fresh-session listing with
the pilot catalog present are recorded in `RESULTS.md`.

## 9. Sidecars and invocation restrictions

Claude Code reads the `SKILL.md` frontmatter and ignores `agents/openai.yaml` entirely: the
Codex sidecar is not in the plugin's component inventory and never reaches the model
(recorded in `RESULTS.md` from `claude plugin details`). recheck-v2 ships no
`disable-model-invocation`, so it is auto-invocable, which is what E9-5 and E7's trigger set
require.

*The manual-only probe* (`disable-model-invocation: true`, `user-invocable: true`) is
**harness-enforced**, the strongest of the three outcomes. Asked in words ("Please run the
manual-only probe for me"), the Skill tool refused with the harness's own message: `Skill
manual-only-probe cannot be used with Skill tool due to disable-model-invocation. Ask the user
to run /manual-only-probe themselves — it cannot be invoked via the Skill tool. Do not
replicate this skill's workflow by other means — it is reserved for explicit user invocation.`
The model relayed the refusal and did not reproduce the skill's one-line workflow by hand.
Invoked explicitly as `/manual-only-probe`, it ran and answered `PROBE-RAN` in one turn. So
the restriction prevents activation and the explicit route still works, on 2.1.270.

## 10. Negative tests

`../../../../setups/claude-code/negative-tests.sh` runs each case in a throwaway copy of the
isolated setup and prints one JSON line per case with the observed behavior
(`enforced` / `prevented activation` / `ignored` / `crashed`) and the harness's own message.
The measured table is in that directory's `RESULTS.md`.

## 11. Installed-package verification

`../../../../setups/claude-code/verify-install.sh` prints one JSON object: `diff -r -x
__pycache__` of the installed plugin against this worktree's, the installed `SKILL.md`
frontmatter `name`, `description` and `metadata.version` against the canonical, every relative
path the installed `SKILL.md`, `adapters/README.md` and `references/*.md` **link** resolved
inside the installed plugin root, and the installed copy's `recheck.py skill-identity`
`content_sha256` against the canonical checkout's. Under ruling E9-16 the identity's `version`
and `commit` are recorded, never compared: the cache copy is outside git and reads
`commit: unversioned`. Backticked file names in prose (`chat.md`, `result.json`,
`docs/plans/...`) are artifact names and repo-relative paths, not links; they are listed for
the record and gate nothing. The measured output is in `RESULTS.md`.

## 12. Capability labels

One row per capability of pilot contract section 13.

| Capability | Label | The measurement |
|---|---|---|
| Read any file in the workspace | `harness-enforced` | the Read tool is allowed and the file tools are confined to the working directories plus `--add-dir`; every live case read the build doc and the source |
| Run commands in the workspace, writes confined to scratch and ignored caches | `instruction-bound` | the mandate confines them; Bash is allowed by the setup's allow list, so the harness does not stop a tracked-file write. The core's boundary check after the run is the real guard (contract section 9) |
| Exactly one fresh verifier context per call, with the mandate's restrictions and no access to the driving conversation | `harness-enforced` for the freshness, `instruction-bound` for the restrictions | the Agent tool starts a fresh subagent whose records carry `isSidechain: true` and which receives only `<call dir>/prompt.md`; readers' roster labels `repo-with-tools` isolation `unmeasured` |
| Declare what the harness injects into that context | `helper-derived` | `verifier.py` lists the sidecar's `workdir_instruction_files` plus the six channels readers measured for the Agent route (contract "The Claude lane", 2026-09-07 and 2026-09-08) |
| The user channel for grants, and forwarding for stations | `helper-derived` | `turns.py` over the session's own transcript; the harness wrote every `sessionId`, `uuid`, `isSidechain`, `isMeta` and role the map uses. Forwarded station references come from the caller's payload |
| Assert whether the running model satisfies `policy.model_floor` | `helper-derived` | `message.model` from the transcript through the E9-3 map; `floor_met` null on an unknown id stops the run |
| Report harness name, version, entry, sandbox, model and settings | `helper-derived`, except `sandbox` | `claude --version`, the helper's own path, the transcript; the permission mode has no harness record reachable from a tool shell and comes from the launcher's `RECHECK_HARNESS_SANDBOX`, else reads `unknown` |
| State whether the driving session authored a fix | `instruction-bound` | ruling E9-14: an explicit flag, defaulting to false |
| Attribute turn references to user, assistant, or station | `helper-derived` | as the user channel above, with the harness-written exception of section 4 |
| Deliver the complete skill body and let the core load its references on demand | `harness-enforced` | 25 of 25 sentinels on both surfaces and the real body's tail delivered, cross-checked against the harness's own record (section 8) |
| Return the result document to the caller unchanged | `instruction-bound` | the executor hands `result.json` over; nothing in the harness rewrites it |
| Refuse or surface, never silently drop, a prohibited action | `harness-enforced` for web tools and for a manual-only skill, `instruction-bound` otherwise | `--disallowed-tools WebFetch WebSearch` plus the settings deny; the Skill tool's own refusal message on `disable-model-invocation`; the F6-04 live case records what the session did with the bait |

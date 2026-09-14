# Adapter profile: Claude Code

The recheck-v2 adapter for Claude Code (E9 lane C; the lane contract
`docs/plans/2026-09-14-recheck-v2-e9-adapters.md` sections 5 and 6). Read this after
`../README.md` and before step 2 of `../../SKILL.md`; read section 7 again before step 4.

Every fact below was measured on 2026-09-14 on this machine. Two harness versions appear,
because the machine updated between the two rounds: the live proofs, the delivery probes and
the manual-only probe ran on **2.1.270**, and the fix round's gates, the three new live
measurements and the reinstall ran on **2.1.271**. Each measurement below says which. Every
claim is labelled `harness-enforced`, `helper-derived`, or `instruction-bound` (ruling E9-11)
with the record it comes from named beside it; a claim with no record is not made. The setup
that produced them is `../../../../setups/claude-code/` and its record is that directory's
`RESULTS.md`.

**What the executor types and what it never types.** The executor runs the three helpers and
copies their output into the input document. Ruling E9-33: `invocation.py` prints the whole
`invocation` object, `mode` included, and the executor **types no field of it** — not `mode`,
not `caller`, not `resume`, and none of the facts it never typed before (a `turn_ref`, a model
id, a harness version, an attribution, `floor_met`, a run id, a run directory, a
`session_model`, a verifier row, model, effort, or authorization). It may type the target, the
named items, `--session-wrote-fix` as its honest answer to the helper (ruling E9-14), and a
grant's `quoted_words` verbatim beside the `turn_ref` that `turns.py --find` returned for
**those words**. The helper prints a second object, `measurement`, which is never copied
anywhere: the input schema closes `invocation` with `additionalProperties: false`, so a
measurement key that lands there makes the document invalid (`tests/test_invocation.py`
composes the helper's output into an input and validates both ways against the real schema).

## 1. Identity

`harness.name` is `claude-code`. `harness.version` comes from `claude --version`, whose first
token was `2.1.270` on the live-proof round and `2.1.271` on the fix round; `invocation.py`
runs that command and reports the token, exits 3 when the binary is not on PATH, and records
the `version` field the session's own transcript records carry as a cross-check
(`measurement._sources.version_records_in_transcript`) (`helper-derived`).

`harness.entry` is derived from the helper's own path: a copy under the active
`CLAUDE_CONFIG_DIR`'s `plugins/cache/<marketplace>/<plugin>/<version>/` is `plugin`, a copy
under a `.claude/skills/` or `.agents/skills/` directory is `host skill`, anything else is
`explicit path`, and a cache copy that is not under the active config directory reads
`explicit path (installed plugin cache loaded with --plugin-dir)` (`helper-derived`; measured
by running the helper from both surfaces).

`harness.sandbox` is the permission mode in force, and it **is** a harness record: the
transcript's `user` records carry `permissionMode`, measured `acceptEdits` on the first user
record of all three live sessions (`live/F1-01/transcript.jsonl` and its two siblings) and on
the committed test fixture. `invocation.py` reads the last recorded value and reports it
(`helper-derived` from the harness's own record); the launcher's `RECHECK_HARNESS_SANDBOX` is
kept only as a cross-check and a disagreement is reported, never resolved
(`measurement._sources.sandbox` says which was used and whether they agreed). Two measured
limits: an interactive session's first user record can carry **no** `permissionMode` (this
control-room session's did not) and a slash-command prompt's record carries none either, and
then the launcher's value stands, or the field reads `unknown (no permission-mode record
reachable from the session)`. The earlier claim that "Claude Code exports no variable naming
it, so the value comes only from the launcher" was true of the environment and false of the
record; the record is the source now.

**Sign-in, the lane's one stop.** An isolated `CLAUDE_CONFIG_DIR` does **not** keep the
machine's sign-in. Measured: `CLAUDE_CONFIG_DIR=~/.local/share/skills-v2-pilot/claude-code/config
claude -p 'say ok' --output-format json` answers `"result": "Not logged in · Please run
/login"`, `is_error: true`, `total_cost_usd: 0`. E9 section 6 rules for exactly this case, so
every live run loads the pilot with `--plugin-dir` against the machine's own configuration
directory, and `launch.sh` adds `--setting-sources local` (the machine's user settings, which
is where installed plugins are enabled, are dropped: the catalog is the built-in skills plus
the plugins named on the command line, and no v1 station) and `--strict-mcp-config` (no MCP
server). The catalog each live session actually had is recorded in its `launch.json` from the
session's own `init` event. The install into the isolated config directory is real and
verified (`verify-install.sh`), but no session can run inside it until it is signed in; that
is the lane's recorded stop, not a workaround.

## 2. Model and floor

`model.id` is the `message.model` of the last non-sidechain `assistant` record in the
session's own transcript, a value the harness wrote (`helper-derived`). The map of ruling
E9-3, which `invocation.py` applies and `tests/test_invocation.py` covers: `claude-opus-*`,
`claude-fable-*` and `claude-mythos-*` are class `opus` with `floor_met` true against the
default floor `opus`; `claude-sonnet-*` is `sonnet` and `claude-haiku-*` is `haiku`, both
`floor_met` false; anything else is `unknown` with `floor_met` null, which the core turns into
`verifier_unavailable` (`unknown_capability`). None of the Claude classes is provisional.

Two measured cautions, each with its record:

- The trace's `init.model` carries a context suffix the transcript drops: `live/F1-01/trace.jsonl:1`
  records `claude-opus-5[1m]` while every `message.model` in that session's transcript reads
  `claude-opus-5`. Both match `claude-opus-*`, so the class is the same; the helper reports the
  transcript's form.
- The model a session's system prompt names can differ from the model its transcript records.
  Witness, re-measurable: in the control-room session that wrote this round
  (`~/.claude/projects/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90.jsonl`, 1,431
  records) the system prompt states `claude-opus-5[1m]` while **all 372** assistant records
  carry `message.model: claude-fable-5-1`; the count and the scan are in the fix round's
  `fix/own-session-model-witness.txt`. The first pass reported a 137-record version of this
  observation with no witness in the packet, and that number is withdrawn in favour of this
  one. The helper reads the record, never the model's account of itself (E8-A17 says the
  adapter reports "the id the harness reports for this session"), and the same id is what
  `verifier.py` puts in `session_model`.

`effort` comes from that record's `effort` field, cross-checked against `$CLAUDE_EFFORT`;
`provider_route` is `anthropic` unless `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` or
`CLAUDE_CODE_USE_FOUNDRY` is set; `settings` carries the entrypoint, the effort as recorded and
as the environment gives it, and the permission mode. `context_tokens` is **not reported**: the
window appears only in the `result` event's `modelUsage` (`contextWindow: 1000000` measured
there), which a session cannot read about itself, and the field is optional in the schema.

## 3. Run id and directory

`invocation.py` mints `recheck-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>`
(the token slugged from `--target-token`, the date the run date) and
`${TMPDIR:-/tmp}/recheck-v2/<run_id>` as the run directory, which is outside every workspace
because `TMPDIR` is the user's per-session temporary directory. The helper names the
directory and never creates it: `recheck.py start` creates it, and a run directory that
already holds a checkpoint, a receipt, or a result is spent. Ids are single use: every call
mints fresh randomness, and a resume passes the same input document again rather than calling
the helper again (the one field a resume flips is `invocation.resume`, which SKILL.md's Resume
step names). On a caller route `--caller NAME --run-id ID --run-dir DIR` are passed together
and the caller's ids are kept unchanged (`helper-derived`; the three flags are refused unless
all three are present, exit 2), and the caller route also fixes `mode` to `headless`, which
contract section 2 and the schema both require.

## 4. The user channel

`turn_ref` is `claude-code:session <sessionId>:msg <uuid>`. The session id is the one the
discovery bound (below) and the uuid is the record's own; the reference is never composed from
a value inside an arbitrary record. `turns.py` builds the whole map; `turns.py --find "<words>"`
answers with the user turn references whose text contains those words verbatim, and prints no
user text. The executor takes the reference from that answer, for the grant's own words, and
never composes one.

*How the session finds its own record* (ruling E9-28), one route and no fallback: the harness's
own `CLAUDE_CODE_SESSION_ID` in the tool shell's environment, resolved to
`<config>/projects/*/<id>.jsonl`. It is then **bound** to this session three ways before any
map is built: the file is named for that id; every `user` and `assistant` record in it carries
that `sessionId` (a file holding another session's records is exit 3, naming the foreign id);
and, when `--workspace` is given, some record of the session names that workspace as its `cwd`
(another workspace's record is exit 3, naming the cwds the file does carry). The variable
unset, no file named for it, or two files named for it under different project directories:
exit 3 naming the case. There is no newest-transcript candidate, no hook-payload candidate, and
no `hooks.json` shipped; `--transcript` and `--session-id` are the fixture interface and are a
usage error (exit 2) unless `RECHECK_ADAPTER_TEST=1`. Two measured details behind the binding:
one session's records can carry several `cwd` values (this control-room session carried seven),
so the cwd binding is "a record of this session names the workspace", never "every record
does"; and the `--workspace` flag is optional, so when it is absent the helper says so in
`workspace_binding` rather than pretending the check ran.

*The label is `instruction-bound`*, not `helper-derived`, and this is the honest reading the
reviewer forced: Claude Code applies **no sandbox to the session's own tools**, so the
transcript on disk stays writable by the very session whose turns it attributes. The failure
modes, in the reviewer's words: **a substituted record** (a file named for this session whose
records were written by something else) is now refused by the session-id binding, and **a
rewritten role** (an assistant record whose `type` is changed to `user`) is **accepted** — the
helper cannot tell a rewritten record from a real one. `tests/test_turns.py`'s
`InstructionBoundLimitTest` records exactly that: a copy of the fixture transcript with one
assistant record's `type` rewritten to `user` maps that turn as the user's. E9-28 leaves that
to the harness, and a harness-enforced channel on Claude Code (a hook-written hash chain, or a
record the session cannot write) is carried to E11.

*Roles* (ruling E9-22). A non-sidechain `assistant` record is `assistant`. A non-sidechain
`user` record whose `message.content` is a string or text blocks is the user's turn — **except**
when the record carries any of the keys `isMeta`, `turnCompanion`, `sourceToolUseID` or
`toolUseResult`. The test is the key's **presence**, not its truthiness: `toolUseResult: {}`,
`isMeta: false` and `sourceToolUseID: null` are the harness's marks as much as a truthy value
is, and the truthiness test the first pass shipped let a planted record carrying
`toolUseResult: {}` become a user grant. Measured across eight transcripts and 346 `user`
records: no record carried any of the four keys with a falsy value, so presence changes nothing
on the harness's real records and closes the forged one. `tests/test_turns.py` covers empty,
false and null for each marker.

The rule is load-bearing because the harness delivers a skill body as exactly the shape the
contract calls a user turn: 25,659 bytes of text blocks carrying `isMeta`, `turnCompanion` and
`sourceToolUseID` in the installed delivery probe's `transcript.jsonl:20`, and 26,212 bytes
carrying `isMeta` and `turnCompanion` (no `sourceToolUseID`, because no Skill call was made)
when the same body arrives through an explicit slash command. Without the exception a grant
could cite a delivered body's uuid.

*Failure modes and the one record that still maps.* A session whose transcript has not been
flushed has no map (exit 3, and the executor stops rather than guessing). A record with no
`user` or `assistant` turn at all is an **unusable session record**: exit 3, never an empty map
(ruling E9-29 — a supplied empty map is a turn list with no turns and rejects every reference,
so printing one would turn an adapter failure into a silently ungrantable run). And one
harness-written `user` record carries none of the four markers: a slash-command invocation
writes `<command-message>…</command-name>` as a plain string `user` record (measured
2026-09-14, session `5075834a-6ac5-45b9-ae08-435ae0665117`), which maps as the user's turn. That
is the right attribution — the user typed the command — but its text is the harness's
expansion, so a grant citing it can only quote that expansion, never prose the user did not
write.

*The station route.* A calling station passes the input whole, its own `turn_attribution`
included, and the executor changes nothing. Where a Claude session hosts a station,
`--station-ref REF` (repeatable) puts that reference in the map as `station`; the values come
from the caller's payload, never from the executor.

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
payload. The `measurement._sources.run_date` field says which of the two produced the value.

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
checkout.

*The request is bound to the core's own call* before anything is printed (verifier.md sections
3 and 6): `--scratch` must be `<run_dir>/verifier`, `--brief` must be that run directory's own
`checklist.md`, and `--raw` must be `<run_dir>/verifier/raw.md` for call 1 or `raw-<k>.md` for
call k, with k read from the call id's `-verify[-k]` suffix; `--run-id` given beside a
`--call-id` from another run is refused. Every mismatch is exit 2 with no request printed, so a
brief from outside the run can no longer reach a verifier (the first pass checked only that the
brief existed, and a mandate pointing at `channels/outside-brief.md` was printed happily).
Tests cover the outside brief, the wrong scratch, a raw path outside the scratch, a re-send
still pointed at call 1's `raw.md`, and the correct `raw-2.md` re-send with call 1's report left
untouched.

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

*Containment, stated as measured and no further.* On this route it is `instruction-bound`:
readers' own roster labels `repo-with-tools` isolation `unmeasured` for `claude-session`, and
its parity line is "web tools forbidden by instruction". What this setup adds is **tool
removal, not a recorded denial**: `launch.sh` passes `--disallowed-tools WebFetch WebSearch`
and the settings deny both, and the measured consequence is that the tools are absent from the
catalog rather than present and refused. The measurement (2026-09-14, 2.1.271, session
`0bf1adf2-84e1-4005-af16-2723373468a8`, `$0.234`, `setups/claude-code/prompts/verifier-fetch-probe.txt`):
a session was asked to start one general-purpose subagent — the verifier's own route — and have
it fetch `https://example.invalid/widget/recheck-status`. The subagent answered that it called
no tool because `WebFetch` is not available to it, that `ToolSearch` replied `No matching
deferred tools found` for `select:WebFetch,WebSearch`, and that it has no tool whose name
begins with `Web`; the parent reported the same for itself. The session's `init` tool catalog
carries no `WebFetch` and no `WebSearch`, and `permission_denials` is `[]`. So: **no web tool
exists in the session or in its subagents (`harness-enforced` by removal), and no denial event
is produced, because there is nothing to deny.** The first pass's claim that "a prohibited
fetch appears in the trace as a denial" is withdrawn: all three live sessions also ended with
`permission_denials: []` and no `WebFetch`/`WebSearch` call in their traces, which proves
absence, not refusal. "No other model, no MCP tool, no outbound service" stays
`instruction-bound`, with `--strict-mcp-config` removing every MCP server as a second measured
floor (`mcp_servers: []` in every session's `init`). "No call to any skill or station" is
enforced in this setup only in the sense that no v1 station is in the catalog
(`--setting-sources local`), which the session's `init` event records.

*File reach is not confined to the workspace.* The first pass claimed the file tools were
confined to the working directories plus `--add-dir`. The records say otherwise: in F1-01's
trace the session's `Read` calls at lines 8, 10, 13, 15, 20, 22, 27, 31 and 56 successfully read
the installed plugin cache under `~/.local/share/skills-v2-pilot/…`, which is neither the
workspace nor an `--add-dir` root. Reading outside the workspace is normal and necessary (the
skill's own references live there); the claim that the harness confines it is dropped. What the
setup does confine is **writing**, and only by instruction plus the core's own boundary check.

*The report.* readers writes the capture to `raw_path` and the sidecar beside it;
`verifier.py --sidecar` maps `status` → `--status`, `raw_file`/`raw_path` → `--raw`,
`effective_model` → `--model`, `transport` → `--kind`, `workdir_instruction_files` plus the
six channels → `--injected`, `reason` → `--note`, and reports readers' `oversize` as
`invalid-request` with the estimate and the limit in the note (verifier.md section 6). It
downgrades a claimed `ok` whose raw file is missing or empty to `capture-failed`, so `ok` is
only ever recorded with a report on disk. **An `ok` must also name the verifier that ran**: an
empty or absent `effective_model` or `transport` is a usage error (exit 2) naming the missing
fields, with no `record-call` flags printed, because a successful call that cannot say which
model produced the report is not a successful call (contract sections 7 and 13, verifier.md
section 5). A failed call may name neither, and still reports its status: no model ran. A
status outside verifier.md section 4's vocabulary is a usage error too, exit 2 (E9 section
5.2). It never retries: the core decides (one re-send under `<run_id>-verify-2`, then the run
stops).

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
`sourceToolUseID`, prefixed by one line naming the skill's base directory. Every count below is
UTF-8 bytes (E9-34), recounted from the records in this round; where a count differs from the
first pass's, the first pass's is withdrawn.

| What | Bytes | The record it was counted in |
|---|---|---|
| delivery probe, worktree surface: the delivered record | 25,643 | `probes/delivery-plugindir/trace.jsonl:6` |
| delivery probe, installed surface: the delivered record | 25,659 | `probes/P1-delivery-installed/trace.jsonl:6` and `…/transcript.jsonl:20` |
| the probe's procedure body on disk (after the frontmatter and the blank line) | 25,490 | the delivery probe fixture's own SKILL.md under the plugin's `setups/_fixtures/` (340 frontmatter + 1 blank + 25,490 = 25,831) |
| the delivered directory header, worktree / installed | 153 / 169 | the difference between each delivered record and the 25,490-byte body |
| the real body: the delivered record | 22,511 bytes (22,487 characters) | `probes/P4-real-body/trace.jsonl:6` and `…/transcript.jsonl:20` |
| the real body on disk | 23,332 | this skill's own [`../../SKILL.md`](../../SKILL.md) = 977 frontmatter through the closing delimiter + 1 blank-line byte + 22,354 procedure bytes |
| the real body's delivered directory header | 157 | 22,511 − 22,354 |

The single claim of "25,770 bytes" in the first pass's profile and RESULTS was wrong for both
probes and is replaced by the four separate counts above; the "821-byte frontmatter" was wrong
too (977 through the closing delimiter, plus one blank-line byte). Stronger than a byte count:
the delivered text minus its header is **byte-identical** to the file's body on all three
records (verified in this round by comparing the record's text against the file).

*The delivery probe*, 25 sentinels: **25 of 25 on both surfaces**, S01 through S24 plus
`SENTINEL S25: end of body`, cross-checked against the text the harness recorded as delivered,
not the model's list. No cut, so no first missing sentinel.

*The real body*: delivered whole. Asked to quote from the delivered text without reading any
file, the model returned the last row of the References table, the last bullet of the Gotchas
section, and the heading of the last numbered Procedure step, all three byte-identical to the
canonical file; the record also carries `## Gotchas`, `## Failure handling`, `## References`
and the output block's `SKILL NOTE:` line. The last procedure step and the Gotchas section both
reach the model, which is what E9-6 asks.

*A third delivery path, measured in the fix round:* an explicit slash command delivers the body
too, even for a skill the catalog's `skills` list omits — see section 10's broken-delimiter row.

*The listing budget.* `claude plugin details recheck-v2` and the fresh-session listing with
the pilot catalog present are recorded in `RESULTS.md`.

## 9. Sidecars and invocation restrictions

Claude Code reads the `SKILL.md` frontmatter and does not read `agents/openai.yaml`: the Codex
sidecar is not in the plugin's component inventory (`claude plugin details` lists one skill and
no agents) and it is not part of any delivered body. What is **not** true is that it "never
reaches the model": the file sits inside the plugin folder, a session's `Read` tool reaches it
like any other file, and one did — the manual-only probe session read
`…/manual-only-probe/skills/manual-only-probe/agents/openai.yaml` at
`probes/P2-manual-words/trace.jsonl:29-30` and quoted its `policy:` block. The accurate claim:
**the harness never delivers the sidecar; the file is readable by any session that looks.**

recheck-v2 ships no `disable-model-invocation`, so it is auto-invocable, which is what E9-5 and
E7's trigger set require.

*The manual-only probe* (`disable-model-invocation: true`, `user-invocable: true`) is
**harness-enforced** on the automatic route. Asked in words ("Please run the manual-only probe
for me"), the Skill tool refused with the harness's own message: `Skill manual-only-probe cannot
be used with Skill tool due to disable-model-invocation. Ask the user to run /manual-only-probe
themselves — it cannot be invoked via the Skill tool. Do not replicate this skill's workflow by
other means — it is reserved for explicit user invocation.` The model relayed the refusal and
did not reproduce the skill's one-line workflow by hand. Invoked explicitly as
`/manual-only-probe`, it ran and answered `PROBE-RAN` in one turn. So the restriction prevents
automatic activation and the explicit route still works, on 2.1.270.

## 10. Negative tests

`../../../../setups/claude-code/negative-tests.sh` runs each case in a throwaway copy of the
isolated setup — its own mutated plugin, its own marketplace, its own `CLAUDE_CONFIG_DIR` — and
prints one JSON line per case with the harness's own message, every child command's exit
status, and the observed behaviour. `--live` adds four sessions: two that read the catalog a
session actually built, one that loads the missing-resource package, and one (two spellings)
that invokes the broken-delimiter skill explicitly. The table below is this lane's own measured
result; `RESULTS.md` carries the same rows with the full harness text.

| Test | Observed | Capability label | The record |
|---|---|---|---|
| a malformed `agents/openai.yaml` | **ignored** — installs, loads as `probe-malformed-sidecar:delivery-probe` | not enforced (Claude never reads the sidecar) | `negative-tests.jsonl`, rows `malformed-sidecar`, `catalog-loaded` |
| the manual-only probe with no `agents/openai.yaml` | **ignored** — loads; the restriction rides on `disable-model-invocation` | `harness-enforced` restriction, sidecar-independent | rows `missing-sidecar`, `catalog-loaded` |
| `SKILL.md` with the `name` field removed | **ignored** — loads as `probe-no-name:probe-no-name`, the name taken from the directory | not enforced | rows `no-name`, `catalog-broken` |
| `SKILL.md` with the opening frontmatter delimiter broken | **prevented automatic activation only** — absent from `skills`, present in `slash_commands`; `/probe-broken-delim` answers `Unknown command`, and the namespaced `/probe-broken-delim:probe-broken-delim` **runs it**: 25 of 25 sentinels and `END-OF-PROBE`, the body delivered as a 26,212-byte `user` record with `isMeta` and `turnCompanion` | `harness-enforced` for the automatic route, **not enforced** for the explicit route | rows `broken-delimiter`, `catalog-broken`, `broken-delimiter-explicit-route`; sessions `08372e02-…` ($0) and `5075834a-…` ($0.176) |
| a duplicate skill name (two plugins, one skill name) | **ignored** — both load, namespaced by plugin | not enforced | rows `duplicate-name`, `catalog-loaded` |
| `references/verifier.md` deleted from the package | **enforced by the core, ignored by the harness** — `claude plugin validate` passes, the install reports `outcome: ok`, and a live session lists the skill (`probe-missing-resource:recheck-v2` in both `skills` and `slash_commands`) and gets a plain `File does not exist` from `Read`; the core stops before any work with `reference unavailable: references/verifier.md`, exit 10 | `instruction-bound` at the harness, `harness-enforced` nowhere, enforced by the core | row `missing-resource` (core exit 10) and `missing-resource-live` (session `070606c7-…`, $0.401) |
| a symlinked `SKILL.md` file | **prevented activation** — `install` reports `ok` and silently drops the symlinked file; the cache holds no `SKILL.md` and the skill never reaches the catalog | `harness-enforced`, silently | row `symlink-skill-file` |
| a symlinked skill directory | **prevented activation** — same silent drop; `skills/` in the cache is empty | `harness-enforced`, silently | row `symlink-skill-dir` |
| an update that turns the source from a copy into a symlink | **enforced** — the installed copy stays a real copy both times, and the row is classified `enforced` only when both installs exit 0 with `outcome: ok` and both diffs are clean | `harness-enforced` | row `update-copy-symlink`, with `exits.txt` |

## 11. Installed-package verification

`../../../../setups/claude-code/verify-install.sh` prints one JSON object and exits 4 on any
finding. What it checks, after the fix round: `diff -r -x __pycache__` of the installed plugin
against this worktree's; the installed `SKILL.md` frontmatter `name`, `description` and
`metadata.version` against the canonical, parsed with a real YAML parser and compared **whole**
(the first pass's hand-rolled `key: value` split read the indented colon inside the folded
description as a nested key, so a changed first description line still compared equal); every
runtime reference the installed `SKILL.md`, `adapters/README.md`, `references/*.md` and every
adapter `profile.md` names — **Markdown links and backticked paths alike**, each resolved from
the document and from the skill root, each required to resolve inside the installed root, to
exist, and to be reached through no symlink (30-plus references checked, where the first pass
checked 7 Markdown links only); an `lstat` walk of the whole installed tree, the root included,
so that a package which must be a copy is a copy and any link — to an external adapter
directory or anywhere else — is a finding; and the installed copy's `recheck.py skill-identity`
`content_sha256` against the canonical checkout's. Every child command's exit status is kept
and its diagnostics reach stderr (the first pass redirected the dependency error away, so an
offline run exited 1 with no output at all). Under ruling E9-16 the identity's `version` and
`commit` are recorded, never compared: the cache copy is outside git and reads
`commit: unversioned`. Two non-gating lists are printed rather than hidden: artifact names and
workspace paths in prose (`chat.md`, `result.json`, `docs/plans/…`), and package paths this
lane's package does not carry (`codex/profile.md`, `opencode/*.py` — lanes R and Q's adapters,
which land at integration). A backticked path whose first segment is one of the skill's own
directories (`references/`, `adapters/`, `scripts/`, …) is **not** in that forgiving bucket: it
must resolve, or it is a finding. The measured output is in `RESULTS.md`.

## 12. Capability labels

One row per capability of pilot contract section 13.

| Capability | Label | The measurement |
|---|---|---|
| Read any file in the workspace | `harness-enforced` | the Read tool is allowed by the setup's settings and every live case read the build doc and the source. Reach is **not** confined to the workspace plus `--add-dir`: F1-01's `trace.jsonl:8` and eight sibling calls read the installed plugin cache outside both (section 7) |
| Run commands in the workspace, writes confined to scratch and ignored caches | `instruction-bound` | the mandate confines them; Bash is allowed by the setup's allow list, so the harness does not stop a tracked-file write. The core's boundary check after the run is the real guard (contract section 9) |
| Exactly one fresh verifier context per call, with the mandate's restrictions and no access to the driving conversation | `harness-enforced` for the freshness, `instruction-bound` for the restrictions | the Agent tool starts a fresh subagent whose records carry `isSidechain: true` and which receives only `<call dir>/prompt.md`; readers' roster labels `repo-with-tools` isolation `unmeasured` |
| Declare what the harness injects into that context | `helper-derived` | `verifier.py` lists the sidecar's `workdir_instruction_files` plus the six channels readers measured for the Agent route (contract "The Claude lane", 2026-09-07 and 2026-09-08) |
| The user channel for grants, and forwarding for stations | `instruction-bound` (ruling E9-28) | `turns.py` reads the session's own transcript, bound by `CLAUDE_CODE_SESSION_ID`, the records' `sessionId`, and the workspace `cwd`; but the session's own tools can write that file, so a substituted record is refused while a rewritten role is not (section 4, and the test that records the limit). Forwarded station references come from the caller's payload |
| Assert whether the running model satisfies `policy.model_floor` | `helper-derived` | `message.model` from the transcript through the E9-3 map; `floor_met` null on an unknown id stops the run |
| Report harness name, version, entry, sandbox, model and settings | `helper-derived` | `claude --version` cross-checked against the transcript's `version` records, the helper's own path, and the transcript's `permissionMode` for the sandbox, with the launcher's variable as a cross-check (section 1) |
| Report the interaction mode | `helper-derived` (ruling E9-33) | `CLAUDE_CODE_SESSION_ATTENDED`, else `CLAUDE_CODE_ENTRYPOINT`, cross-checked against the transcript's own `entrypoint` record; a disagreement or no record at all is exit 3, never a guess. The three live proofs recorded `interactive` inside `claude -p` when the executor typed it, which is the defect the ruling closes |
| State whether the driving session authored a fix | `instruction-bound` | ruling E9-14: an explicit flag, defaulting to false |
| Attribute turn references to user, assistant, or station | `helper-derived` for the mapping, `instruction-bound` for the record it maps | the harness wrote every `sessionId`, `uuid`, `isSidechain` and marker the map uses (E9-22's presence rule), on a file the session could have rewritten (E9-28) |
| Deliver the complete skill body and let the core load its references on demand | `harness-enforced` | 25 of 25 sentinels on both surfaces and the real body's tail delivered, byte-identical to the file after the directory header (section 8) |
| Return the result document to the caller unchanged | `instruction-bound` | the executor hands `result.json` over; nothing in the harness rewrites it. Observed in all three live sessions: the executor printed `chat.md` **verbatim but wrapped**, in a fenced block with a sentence before it and explanation after (F1-01 added one paragraph, F2-01 one, F6-04 three plus an artifact paragraph), where SKILL step 8 says `chat.md` is the whole verdict. An executor-behaviour observation, not a harness fact; the control room's fresh proofs re-measure it |
| Refuse or surface, never silently drop, a prohibited action | `harness-enforced` for a manual-only skill; **tool removal, not refusal**, for web tools; `instruction-bound` otherwise | the Skill tool's own refusal message on `disable-model-invocation`; `--disallowed-tools` plus the settings deny leave no `WebFetch`/`WebSearch` in the session's or its subagents' catalog, so a prohibited fetch has nothing to deny (section 7's measurement); the F6-04 live case records what the session did with the bait |

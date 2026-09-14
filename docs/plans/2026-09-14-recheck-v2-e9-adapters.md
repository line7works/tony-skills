# recheck-v2 E9: the adapters (lane contract)

Step E9 of `~/ObsidianVault/03-projects/tony-skills/skills-v2-execution-plan.md` (Part E, E9;
amendments A7b, R1a, R1b, D3a; plan ruling 17). Written by the control room on 2026-09-14
before any builder started, on Tony's `go for E9`. The pilot contract
`plugins/recheck-v2/skills/recheck-v2/references/pilot-contract.md` (revision 5, amended at
the E9 seam) outranks this document; the E8 lane contract
`docs/plans/2026-09-13-recheck-v2-e8-core.md` fixes the core's design, the CLI (section 6),
and the verifier protocol the adapters drive; this document fixes what the adapters are, the
shape every profile shares, the three lanes, the gates, and the review. Where this document
and the contract disagree, the contract wins and the disagreement is a finding.

Contents: 1 What E9 delivers · 2 Evidence · 3 Boundaries · 4 Rulings (E9-1 to E9-14) · 5 The
adapter, the shape every lane builds · 6 Lane C, Claude Code · 7 Lane R, Codex CLI · 8 Lane Q,
OpenCode with OpenRouter · 9 Gates and tests · 10 The builder's report · 11 Review and close ·
12 Amendments.

## 1. What E9 delivers

Under `plugins/recheck-v2/` (the seam commit on `feat/recheck-v2-e9` already holds the files
marked *seam*; each lane adds the files marked with its letter; the control room adds the rest
at the close):

```text
.claude-plugin/plugin.json              unchanged until the close (control room)
hooks/hooks.json                        C, only when the Claude user channel needs a hook (section 6)
README.md                               status, layout, build record (control room, close)
setups/
  README.md                             what a setup is (seam)
  _fixtures/                            the two shared probes: delivery-probe, manual-only-probe (seam)
  claude-code/                          C: install.sh, launch.sh, verify-install.sh, negative-tests.sh, RESULTS.md
  codex/                                R: the same five, plus the delivery evidence of A7b
  opencode/                             Q: the same five, plus the install proof (D3a) and both model sub-setups
skills/recheck-v2/
  SKILL.md                              seam: one paragraph and one table row point at the adapter index; nothing else
  agents/openai.yaml                    R: the Codex sidecar for recheck-v2 (interface metadata only, E9-5)
  adapters/
    README.md                           the index (seam); lanes do not edit it
    claude-code/                        C: profile.md, invocation.py, turns.py, verifier.py, tests/
    codex/                              R: profile.md, invocation.py, turns.py, verifier.py, tests/
    opencode/                           Q: profile.md, invocation.py, turns.py, verifier.py, tests/
  references/, scripts/                 the E8 core: closed to the lanes (E9-9)
```

Done when (plan E9 plus A7b, R1a): for each of the three setups, a headless session of the
native harness in an isolated pilot setup discovers or explicitly loads recheck-v2, reads the
permitted evidence, executes an allowed check, refuses a prohibited action, captures its actual
model and settings, and produces the common result format, with no v1 station named in the
trace (section 9, the live proof); every profile identifies the same shared-core hash
(`recheck.py skill-identity` printed from the installed copy reports the canonical checkout's
`content_sha256`, and the installed-package diff is empty; E9-16);
the deterministic gates of section 9 are reported with their outputs; the reviews of section
11 close each lane under plan ruling 17.

## 2. Evidence every lane reads

Read completely before starting:

1. The pilot contract, revision 5, in full; sections 2, 7, 8, 13, 14, and 15 twice.
2. `references/verifier.md` (the brief, the report, the statuses, section 5 what the adapter
   reports back, section 6 the readers request, section 7 a harness without readers).
3. `references/input.schema.json` (`invocation`, `authorization`, `policy`),
   `references/examples/input-direct.json` and `input-caller.json`, `examples/README.md`.
4. `SKILL.md` (the executor's procedure the adapter serves; steps 2, 4, and 5 name the seams).
5. The E8 lane contract: section 6 (the CLI and its exit codes), section 7 (the verifier
   protocol), and in section 12 the amendments E8-13, E8-18, E8-24, E8-25, E8-A17, E8-A20,
   E8-A23, E8-A30, E8-A38 (also section 4 for E8-13, E8-18, E8-24, E8-25 in full).
6. This document; `adapters/README.md`; `setups/README.md`; `setups/_fixtures/README.md`.
7. `evals/README.md` ("Layout", "Separation of knowledge", "Identity encoding") and the
   `CASES.md` of the lanes named in section 9 (F1, F2, F6, VXUM, IA): facts about the fixtures.
8. `~/ObsidianVault/01-domain/skills-best-practices.md`: "The harness layer" (the table, the
   adapter fields, the sidecar, the silent failures), "Distribution and versioning" (the
   installed-package verification), "Scripts", "Testing".
9. Lane C also: `plugins/readers/skills/readers/assets/contract.md` ("The request", "The
   result", "Statuses", "Host lanes: compose and record", "The Claude lane", "Isolation") and
   `roster.json` (the `claude-session` row). Lane Q also:
   `~/ObsidianVault/03-projects/tony-skills/skills-v2-setup-inventory.md` "Lane Q".

**The wall.** No E9 agent opens anything under `plugins/recheck-v2/evals/answer-key/` or
`plugins/recheck-v2/evals/trigger-set/held-out/`. Every expected outcome a lane asserts about a
fixture run is derived from that lane's `CASES.md` facts plus the contract, both cited.

## 3. Boundaries every lane keeps

- **Worktree and branch.** Lane C `~/Developer/tony-skills-e9-claude` on
  `feat/recheck-v2-e9-claude`; lane R `~/Developer/tony-skills-e9-codex` on
  `feat/recheck-v2-e9-codex`; lane Q `~/Developer/tony-skills-e9-opencode` on
  `feat/recheck-v2-e9-opencode`; all three cut from `feat/recheck-v2-e9` at the seam commit.
  A lane writes only under its own `setups/<harness>/`, its own `adapters/<harness>/`, and
  its lane-specific files (C: `plugins/recheck-v2/hooks/`; R: `skills/recheck-v2/agents/`),
  plus the scratch directories it is given. Never `git add`, `commit`, `stash`, `checkout`,
  `reset`, or any git command that changes a worktree, its index, or its branches; `git
  status`, `log`, `diff`, `rev-parse` are fine. The control room commits.
- **The core is closed** (E9-9): nothing under `skills/recheck-v2/scripts/`,
  `skills/recheck-v2/references/`, `SKILL.md`, `adapters/README.md`, `setups/README.md`,
  `setups/_fixtures/`, `.claude-plugin/`, `README.md`, `evals/`, or any other plugin. A lane
  that needs a change there reports the exact change with its reason; the control room rules.
- **Runtime.** `/usr/bin/python3` 3.9.6 and git 2.50.1 are the floor. Adapter helpers are
  Python 3.9 syntax, standard library only, no `jsonschema` (they validate nothing; the core
  does). Setup scripts are `zsh` or `sh`, and every external command they run is the harness's
  own CLI, `uv`, `npm`, `git`, `rsync`, `diff`, `python3`, or coreutils.
- **Isolation.** A setup writes only under `~/.local/share/skills-v2-pilot/<harness>/`
  (created by `install.sh`), the scratch directories, and the run directories the trials mint
  under `${TMPDIR:-/tmp}/recheck-v2/`. Never a write under `~/.claude`, `~/.codex`,
  `~/.config/opencode`, `~/.local/share/opencode`, `~/.zshrc`, or any repository other than
  the lane's worktree. A live-home read is permitted only where section 6, 7, or 8 names it.
- **Secrets.** A credential is read at install time from where the section names and copied
  only into the isolated home (mode 600); never into the worktree, a profile, a result, a log,
  a test, or a report; never printed. Existence is checked with `[ -n "$VAR" ] && echo set`.
  Nobody reads `~/.zshrc`.
- **No model call inside a helper** other than the verifier launch the profile documents
  (`verifier.py`), which is the adapter's own capability, never the executor's pick. No MCP
  tool, no web, no other model, no subagent from a helper or a setup script.
- **Fixtures for tests** are built with the E7 generators into a temporary directory
  (`python3 <lane>/build.py --out <tmp>`), never into a worktree and never under `evals/`;
  tests clean up what they build. Every test derives its expectations from `CASES.md` facts
  and the contract, cites the section, and never reads a key.
- **Cost and windows.** One builder per lane; no fan-out inside a lane; no Workflow tool; no
  ultracode. A live harness session costs real tokens: run the section 9 live proof once per
  case, keep the trace, and reuse it.

## 4. Rulings (control room, 2026-09-14, at the seam)

- **E9-1, an unmapped turn reference.** When the adapter supplies
  `invocation.turn_attribution`, that map is the session's turn list: a grant whose `turn_ref`
  is absent from it names no turn of the session and is rejected ("not in the adapter's
  turn_attribution (no turn of this session)"), the same way as a reference that maps to the
  assistant or a station. With no map the field rules of section 8 alone apply (E8-24 stands).
  Reason: E8-24 held each adapter to supplying the map so that a reference the executor
  composed could not pass as the user's; a map that only rejects the references it lists left
  every invented reference accepted. Made at the seam in `recheck_core/inputs.py`
  (`grant_channel_ok`), one test, section 8 and Appendix B of the contract. No fixture outcome
  changes (every IA trial map lists every reference its grants cite).
- **E9-2, where the adapter lives.** The run-time adapter lives inside the skill folder at
  `skills/recheck-v2/adapters/<harness>/` so every install carries it, and `adapters/README.md`
  is the index the body points at (the body names the index, never a harness). The install and
  launch profile lives outside the skill at `plugins/recheck-v2/setups/<harness>/` (it is not
  needed at run time and holds no run-time text). The two shared probes live at
  `setups/_fixtures/`.
- **E9-3, the floor map, provisional.** `policy.model_floor` names the class `opus`. Lane C
  maps `claude-opus-*`, `claude-fable-*`, `claude-mythos-*` to class `opus` with `floor_met`
  true; `claude-sonnet-*` to `sonnet` and `claude-haiku-*` to `haiku`, both `floor_met`
  false; anything else to `unknown` with `floor_met` null. Lane R maps `gpt-6-astra` to class
  `opus`, `floor_met` true; anything else to `unknown`, null. Lane Q maps `qwen/qwen3.8-flash`
  and `deepseek/deepseek-v4.1-flash` to class `opus`, `floor_met` true; anything else to
  `unknown`, null. The R and Q classifications are **provisional for the pilot**, made by the
  control room because rulings D3a and D2 make those the Q and R setups and an unclassified
  id would stop every graded run as `verifier_unavailable`; Tony confirms or overturns them,
  and the readers roster's "Tony classifies ids by roster PR" stands for readers. Each profile
  prints the map and the word "provisional" where it applies.
- **E9-4, the isolated setups.** Lane C: `CLAUDE_CONFIG_DIR=~/.local/share/skills-v2-pilot/claude-code/config`.
  Lane R: `CODEX_HOME=~/.local/share/skills-v2-pilot/codex/home`. Lane Q:
  `XDG_CONFIG_HOME=~/.local/share/skills-v2-pilot/opencode/xdg-config`,
  `XDG_DATA_HOME=~/.local/share/skills-v2-pilot/opencode/xdg-data`, the binary under the
  setup's own npm prefix (`npm install --prefix ~/.local/share/skills-v2-pilot/opencode/npm
  opencode-ai@<pinned>`), never `brew`. A setup installs the pilot from the lane's worktree
  (a local marketplace or a copied folder, as the section says) plus the two probes and, for
  lane C, the readers plugin (the verifier component); nothing else from tony-skills, so the
  trace check for v1 stations has a clean catalog and the profile records the catalog present.
- **E9-5, invocation policy.** recheck-v2 is auto-invocable: its description is written for
  routing and E7's trigger set measures it. Its Codex sidecar `agents/openai.yaml` carries
  interface metadata only (`display_name`, `short_description`) and no
  `allow_implicit_invocation: false`; `SKILL.md` gains no `disable-model-invocation`. A7b's
  manual-only requirement is proved on the shared `manual-only-probe` fixture in every lane
  (section 9), and each profile records whether the harness enforced the restriction,
  prevented activation, or ignored it.
- **E9-6, delivery.** Every lane measures delivery with the shared `delivery-probe` (25
  sentinels over 25,831 bytes, about the size of the recheck-v2 body at 23,332 bytes) on
  every installation surface it ships, cross-checking the model's list against the text the
  harness recorded as delivered; then it measures the real body the same way (the last
  procedure step and the Gotchas section must reach the model). A cut is reported with the
  first missing sentinel and the delivered byte count; the remedy (a compact body with the
  procedure moved into a reference, or a different installation surface) is the control
  room's ruling after the lane reports, never the builder's edit.
- **E9-7, the verifier's containment.** Lane C summons the verifier through the readers
  component (row `claude-session`, profile `repo-with-tools`, the request block of
  `verifier.md` section 6). Lane R launches one fresh `codex exec` per call under
  `-s read-only` with the workspace as its working root, the brief on stdin, the report through
  `-o`, `-c web_search=disabled`, no `-m` and no effort flag (the setup's configured model and
  effort are the session's own and the profile's constants); it measures that a scenario's
  own commands run under `read-only` (X1-01) and, when they do not, reports `workspace-write`
  as the fallback with the label `instruction-bound`. Lane Q launches one fresh `opencode run`
  per call under a dedicated verifier agent defined in the setup's `opencode.json` with edit
  denied, web fetch denied, bash allowed, and the model fixed to the setup's own. Every lane
  declares the channels the harness injects into that context.
- **E9-8, the live proof.** Section 9's live cases are run through the real harness headlessly
  in the isolated setup on built E7 fixtures (opaque directory names, `trial-defaults.json`'s
  run date pinned through `invocation.run_date`): F1-01 (an allowed check executed, the run
  completes), F2-01 (not fixed), one of F6-04 or V4-01 (a prohibited action refused and
  reported, never done), and V1-01 (a below-floor model stops the run before anything is
  graded, driven by presenting the input with `floor_met` false). A1-02 and A2-01 are driven
  through the core (as E8's tests do) with the real `turn_ref` shape and a map the lane's
  `turns.py` built from a real session record of that harness. The trace check greps the
  harness's record of every live session for the v1 station names (`/recheck`, `/signoff`,
  `/inspect`, `/vertical`, `/ship`, `/build`, `/blueprint`, `/precon`, `/architect`,
  `/handoff`, `/wargame`, `/readers` on lanes R and Q) and reports every hit.
- **E9-9, the core is closed to the lanes.** Section 3's boundary. The seam commit made the
  only core changes E9 makes before review: E9-1 and the adapter pointer in `SKILL.md`.
- **E9-10, guide findings.** Builders report findings (`held`, `contradicts`, `adds`,
  `silent`) in the shape of `docs/guide-findings.md`'s line; the control room appends them to
  the log in the main checkout (the log is untracked and lives outside the worktrees).
- **E9-11, capability labels.** Each profile labels every capability of contract section 13
  `harness-enforced` (the harness stops the other outcome; measured), `helper-derived` (a
  helper computes it from a record the harness wrote, with the failure modes named), or
  `instruction-bound` (the executor's honest report), the way the readers roster labels
  isolation; a label is measured, not claimed, and names the measurement.
- **E9-12, the wall stands** (section 2).
- **E9-13, the roster rows** for `qwen/qwen3.8-flash` and `deepseek/deepseek-v4.1-flash`
  (D3) are not a lane's: readers' outside rows need Tony's word per call, and the rows carry
  a `verified_at` that only a readers run can stamp. Carried to the control room after E9, on
  Tony's word. Lane Q's install proof records the values a row would need (context window,
  reasoning support, tool support, prices, the listed date).
- **E9-14, `session_wrote_fix`.** The executor's honest answer from the session it runs in
  (`instruction-bound`); on a caller route the caller passes it. The profile says so and the
  helper never guesses it (`invocation.py` takes `--session-wrote-fix` as an explicit flag and
  defaults to false).

## 5. The adapter: the shape every lane builds

### 5.1 The profile (`adapters/<harness>/profile.md`)

Twelve sections in this order, each answered with measured facts and the label of E9-11; a
section the harness cannot satisfy says so in those words and names the stop the core takes:

1. **Identity.** `harness.name` (`claude-code`, `codex-cli`, `opencode`), `version` (the
   command that prints it), `entry` (`plugin`, `host skill`, `explicit path`: which
   installation surface this setup uses), `sandbox` (the permission or sandbox mode in force
   and where the session reads it).
2. **Model and floor.** Where the session reads its own model id; the id-to-class map of
   E9-3 (with "provisional" where it applies); how `floor_met` is computed; the `effort`,
   `provider_route`, `context_tokens`, and `settings` reported and their sources.
3. **Run id and directory.** `run_id` `recheck-<slice or target token, lowercase>-<YYYYMMDD>-
   <4 hex from os.urandom>`, single-use; `run_dir` `${TMPDIR:-/tmp}/recheck-v2/<run_id>`,
   outside every workspace; the caller route keeps the caller's ids.
4. **The user channel.** The `turn_ref` shape (section 6, 7, or 8 fixes it per lane); how the
   session locates its own record (the transcript, the rollout, the session store); how
   `turns.py` builds `turn_attribution` over the whole session and how the executor finds the
   turn holding the user's quoted words (`turns.py --find "<words>"` returns the user turns
   whose text contains them); the failure modes; the forwarding rule on a station route.
5. **`session_wrote_fix`** (E9-14).
6. **Run date.** The machine's local calendar date from the helper, or the caller's, or the
   trial's pinned date.
7. **The verifier capability.** The transport; the exact launch; what the fresh context
   receives (the brief path, the workspace, the scratch directory) and what it cannot see;
   the containment and its label; the channels the harness injects, measured; how the report
   comes back; the status mapping onto `verifier.md` section 4; the model that ran and the
   transport kind, and where the helper reads them; the retry (the core's, never the
   adapter's).
8. **Delivery.** The installation surface(s) and the rendering path; the delivery probe's
   result per surface; the real body's result.
9. **Sidecars and invocation restrictions.** What the harness reads (`agents/openai.yaml`,
   frontmatter fields), what it enforces; the manual-only probe's outcome.
10. **Negative tests.** The table of section 9 with the observed behavior per test.
11. **Installed-package verification.** The diff, the frontmatter check, the containment
    check, the shared-core hash from the installed copy against the canonical checkout.
12. **Capability labels.** One row per capability of contract section 13, with the label and
    the measurement.

### 5.2 The helpers (`adapters/<harness>/*.py`)

Every helper follows A7a: `--help` with arguments, defaults, an example, and side effects;
JSON on stdout and nothing else; diagnostics on stderr; exit 0 success, 2 usage, 3 missing
dependency (an absent harness record or binary the helper needs, named), 1 anything else;
paths absolute or resolved from the current working directory; tested from another working
directory, with invalid input, and with the record absent.

- `invocation.py [--workspace W] [--target-token T] [--session-wrote-fix] [--run-date D]
  [--caller NAME --run-id ID --run-dir DIR]`: prints `{"run_id", "run_dir", "harness",
  "model", "run_date", "session_wrote_fix", "turn_attribution"}` for the executor to place
  under `invocation` (the executor adds `mode`, `caller`, `resume`). Every value is a fact the
  helper read from a harness record or a command, or a flag the profile names as
  instruction-bound; `floor_met` follows E9-3.
- `turns.py [--find "<words>"] [--json]`: the session's turn list as `{turn_ref: role}` and,
  with `--find`, the user turn references whose text contains the words verbatim.
- `verifier.py --brief <path> --workspace <ws> --scratch <run_dir>/verifier --raw <raw path>
  [--call-id ID]`: lane C prints the readers request block of `verifier.md` section 6 with
  `session_model` filled from the harness record and `authorized` omitted (a Claude row needs
  none); lanes R and Q launch the fresh context, wait, and print the `record-call` flags as
  one object `{"status", "raw", "model", "kind", "injected": [...], "refused": [...],
  "note"}` (statuses in `verifier.md` section 4's vocabulary; `ok` only when the raw file
  exists and is non-empty). A helper that launches never retries: the core decides.

### 5.3 What the executor types and what it never types

The executor runs the helpers and copies their output into the input document; it composes no
`turn_ref`, no model id, no version, no attribution, no `floor_met`. The profile says which
fields it may type (`mode`, `caller`, `resume`, `session_wrote_fix` as its honest answer, the
target, the named items, the grants' `quoted_words` verbatim with the `turn_ref` `turns.py`
returned) and which it never types. A reviewer holds the profile to this.

## 6. Lane C: Claude Code

- **Harness.** Claude Code 2.1.270 (`claude --version`), model `claude-fable-5-1` on this
  machine today (the harness states its model id in its system prompt; the transcript's
  assistant records carry `message.model`, the helper's cross-check). Entry: the plugin,
  installed from the worktree's marketplace into the isolated config dir (`claude plugin
  marketplace add <worktree path>` then `claude plugin install recheck-v2@tony-skills`,
  `readers@tony-skills`, and the two probes by path); also measured: `claude --plugin-dir
  <plugin path>` as the explicit-load surface. Headless runs: `claude -p` with
  `--output-format stream-json` (the trace) and the permission mode the profile records.
  Whether the isolated config dir keeps the machine's sign-in is the first thing to measure;
  if it does not, record the fact and use `--plugin-dir` for the live proof, and say so.
- **The user channel.** The transcript at `~/.claude/projects/<cwd slug>/<sessionId>.jsonl`
  (in the isolated config dir, under its own `projects/`): records with `type` `user` or
  `assistant`, `uuid`, `sessionId`, `isSidechain`, `timestamp`; a `user` record whose
  `message.content` is a string or text blocks is the user's turn; a `user` record carrying
  tool results is not a turn and stays unmapped; `isSidechain` true is a subagent's and stays
  unmapped. `turn_ref` is `claude-code:session <sessionId>:msg <uuid>`. How the session
  locates its own transcript is the lane's measurement, candidates in this order: (a) a
  `hooks/hooks.json` `SessionStart` or `UserPromptSubmit` hook shipped by the plugin that
  writes `{session_id, transcript_path, cwd}` to `${TMPDIR}/recheck-v2/claude-code/<the hook
  process's parent pid>.json`, read back by `turns.py` through its own `$PPID` (both the hook
  and the Bash tool's shell are children of the same `claude` process: measure it); (b) the
  same hook printing one line to stdout at `SessionStart` (context noise once per session:
  record the cost); (c) the newest transcript under the isolated config dir whose `cwd`
  equals the workspace (ambiguous with two sessions in one directory: record it). Nothing is
  written into the workspace. The label: `helper-derived` from a harness-written record when
  (a) or (c) holds; the hook's payload comes from the harness (`session_id`,
  `transcript_path`), never from the model.
- **The verifier.** The readers component, row `claude-session`, profile `repo-with-tools`
  (the Agent route, a fresh general-purpose subagent, the composed prompt handed over as the
  file `<call dir>/prompt.md`): the executor sends the request block with `session_model` from
  `invocation.py` and `mandate` the brief's path; the sidecar maps onto `record-call` as
  `verifier.md` section 6's table says; `--injected` lists the channels readers' contract
  measures for that route (the instruction files and their imports, the global instruction
  file, the memory index, the git-status block, the user-email line, the tool rosters).
  Containment on that route is `instruction-bound` (readers' own label: unmeasured);
  `isolation: worktree` is not requested (the scenario must run in the real checkout).
- **Delivery.** Claude Code delivers the whole `SKILL.md` on invocation; measure it anyway
  with the probe and the real body, and record the listing budget (`claude plugin details
  recheck-v2`) and the fresh-session listing with the pilot catalog present.
- **Sidecars.** Claude reads frontmatter; `agents/openai.yaml` is ignored (record). The
  manual-only probe under `disable-model-invocation: true`: a prompt asking in words must not
  run it (since 2.1.222 the model is told to ask the user); `/manual-only-probe` runs it.

## 7. Lane R: Codex CLI

- **Harness.** codex-cli 0.154.0 (`codex --version`), model `gpt-6-astra`, effort and sandbox
  from the isolated home's `config.toml` (copied from the live one's model, effort, and
  sandbox lines only; approval `never` for headless runs; the marketplace entry
  `[marketplaces.tony-skills]` with `source_type = "local"` pointing at the lane's worktree;
  the pilot plugins enabled). `auth.json` copied from `~/.codex/` into the isolated home at
  install (mode 600, never elsewhere). Entry: the Agent Plugins path (`codex plugin
  marketplace add`, `codex plugin add recheck-v2@tony-skills`); also measured: the host-skill
  path (the skill folder copied under `$CODEX_HOME/skills/` or the workspace's
  `.agents/skills/`), since A7b says to establish which path an installation actually uses
  and the 8,000-byte main-prompt branch belongs to the plugin path only. Headless runs:
  `codex exec --json -o <file> -C <workspace>` with the prompt on stdin and `</dev/null`.
- **The user channel.** The rollout at `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-<ts>-<thread
  id>.jsonl`: `session_meta` (thread id, cwd, `cli_version`, `model_provider`),
  `turn_context` (`turn_id`, cwd, and the model in force), `event_msg` `item_completed` with
  `item.type` `UserMessage` (the user's turn: `id`, `turn_id`) or `AgentMessage`;
  `turn_ref` is `codex:thread <thread id>:turn <turn id>:item <item id>` (E9-15: the item id
  is required because a user message and the assistant's reply in one turn share the thread
  and turn ids; the example input's two-part shape predates this ruling). How the session locates its own rollout is the lane's measurement,
  candidates: (a) `lsof -p $PPID` on the shell's parent (the codex process) naming the open
  rollout file; (b) the `notify` program of `config.toml` (it receives `thread-id` and
  `turn-id` after each turn; in a one-turn `codex exec` it fires too late, record it); (c)
  the newest rollout under the isolated home whose `session_meta.cwd` equals the workspace.
  The user's grant normally arrives in the current prompt, and the rollout records that
  UserMessage as the turn starts (measured 2026-09-14 on a live rollout: ordinal 9).
- **The verifier.** E9-7: one fresh `codex exec` per call, `-s read-only`, `-C <workspace>`,
  `--skip-git-repo-check` only when the workspace is not a git repository (it always is),
  `-c web_search=disabled`, `--json` to `<scratch>/events.jsonl`, `-o <raw path>`, the brief
  on stdin, `</dev/null`, no `-m`, no effort flag. `verifier.py` maps: exit 0 with a non-empty
  raw file to `ok`; exit 0 with an empty file to `empty`; a killed or non-zero child to
  `transport-failed` with the child's stderr tail as `--note`; the row's timeout (900 s, the
  readers value) to `timed-out`. The model and effort that ran come from the events stream
  (`turn_context` or `session_meta`), never from the config file. Injected channels: the
  `$CODEX_HOME/AGENTS.md` handbook and the workspace's `AGENTS.md` when present (the rollout's
  `world_state` shows what was loaded: measure, and list every file it names). Refused
  actions: a sandbox denial the events stream shows with no side effect goes under
  `--refused`; the report's own list is merged by the core.
- **Delivery (A7b, the fixture).** The probe on the plugin path and on the host-skill path;
  the delivered text read from the rollout's developer message that carries the skill (the
  `<skills_instructions>` block or the rendered skill body), byte-counted; the first missing
  sentinel named. Then the real body. Then explicit resource recovery: a prompt asking the
  skill to read `references/verifier.md` by its relative path, and whether Codex resolved it
  from the installed copy or refused. Keep this separate from any compaction test.
- **Sidecars.** `agents/openai.yaml` for recheck-v2 (E9-5). The manual-only probe's sidecar
  with `allow_implicit_invocation: false`: a prompt asking in words must not run it; the
  explicit invocation (the form the installed Codex offers: record it) runs it. Also measure
  the guide's silent failure 2: a sidecar with a malformed optional field, and whether the
  skill stays loadable with the policy lost.

## 8. Lane Q: OpenCode with its OpenRouter provider (D3a)

- **Install first (D3a).** Before any adapter code: `npm install --prefix <setup>/npm
  opencode-ai@<the version `npm view opencode-ai version` prints at install; pin it in
  `install.sh` and `RESULTS.md`>`; the isolated `XDG_CONFIG_HOME` and `XDG_DATA_HOME`;
  `opencode.json` in the isolated config with the `openrouter` provider and two model
  sub-setups, `openrouter/qwen/qwen3.8-flash` and `openrouter/deepseek/deepseek-v4.1-flash`
  (the setup's `launch.sh` takes the model as its first argument; the default is Qwen);
  `OPENROUTER_API_KEY` from the environment, never written down. Prove the install with one
  `opencode run` per model that answers a fixed question, and record for each: OpenCode's
  version, the model id as OpenCode reports it in its session store, the provider route,
  the context window setting, sampling and thinking settings in force, the tool parser or
  tool-call format (the plan's Q record: "the full model digest, ... context setting,
  sampling, thinking mode, and tool parser"; Ollama does not apply under D3a: say so), and
  the cost of the two calls from OpenRouter's generation record. Report the install proof to
  the control room before the adapter, in the report's shape (section 10), and continue.
- **Harness.** `harness.name` `opencode`, `version` from `opencode --version`, `entry` the
  installation surface measured (OpenCode's own `skill` directories under the isolated config
  or the workspace, and whichever of `.claude/skills/` and `.agents/skills/` its 1.x loader
  reads: measure each with the probe, assume none), `sandbox` the permission configuration in
  force. The model id from the session store; `provider_route` `openrouter`.
- **The user channel.** OpenCode's session store under the isolated `XDG_DATA_HOME`
  (`opencode/storage/session/...` and `.../message/<session id>/<message id>.json` with
  `role`; measure the exact layout of the installed version): `turn_ref` is
  `opencode:session <session id>:message <message id>`. How the session locates its own
  store entry: candidates, the newest session in the isolated store whose directory is the
  workspace; an OpenCode plugin (`.opencode/plugin/*.js` in the isolated config) that writes
  the session id keyed by the parent pid at `chat.message`; an environment variable the
  installed version sets for tool shells (measure, assume none).
- **The verifier.** E9-7: one fresh `opencode run` per call: `--model` the setup's own,
  `--agent recheck-verifier` (defined in the setup's `opencode.json`: edit denied, web fetch
  denied, bash allowed, the prompt the hand-off text that names the brief file), `--format
  json` for the trace, the working directory the workspace, the final message captured to the
  raw path by `verifier.py`. Containment: edit denied is `harness-enforced` for the edit
  tools; bash writes are `instruction-bound` (record both). Injected channels: the
  `AGENTS.md` files OpenCode loads and its own system prompt (measure from the session
  store). The model that ran from the session store's message records.
- **Delivery and sidecars.** The probe and the real body per surface; OpenCode ignores
  unknown frontmatter and `agents/openai.yaml` (record what it did with the manual-only
  probe: the guide expects "ignored"; an invocation restriction that is ignored is reported as
  "prevents nothing" and the profile says the skill must not be marked manual-only for this
  harness without a harness-level guard).

## 9. Gates and tests (required output of every builder's brief, R1a)

### 9.1 Hermetic tests (`adapters/<harness>/tests/`, unittest, stdlib, run from another directory)

- Every helper: `--help`; JSON on stdout and nothing else; exit 2 on an unknown argument; exit
  3 with the record or binary absent (a fake home under a temp dir); from another working
  directory.
- `turns.py` on a saved real session record of that harness (a file the lane captured in its
  probe runs, committed under `tests/fixtures/` with any user text replaced by neutral words
  and any credential-looking string removed): the map's roles; tool results and sidechains
  unmapped; `--find` returns the user turn holding the words and not an assistant turn holding
  the same words.
- The floor map: every id class of E9-3 for the lane, including the null case.
- A1-02 and A2-01 through the core with the lane's real `turn_ref` shape and a map from
  `turns.py`: the grant on the assistant's turn rejected naming the attribution (E8-24); the
  station grant without `forwarded_by` rejected (E7-13); a reference absent from the map
  rejected (E9-1); a reference on the user's turn accepted. Expected outcomes from IA
  `CASES.md` and contract section 8, both cited.
- `verifier.py` under a test hook (`RECHECK_ADAPTER_TEST=1` with `RECHECK_ADAPTER_CANNED=<dir>`
  holding a saved raw file and, for R, a saved events stream; set without `RECHECK_ADAPTER_TEST=1`
  the helper refuses with reason `canned response outside test`): the status mapping for
  `ok`, `empty`, `transport-failed`, `timed-out`; the model and kind read from the record.
- The whole existing suite still green: `uv run --with jsonschema==4.25.1 python3 -m unittest
  discover -s plugins/recheck-v2/skills/recheck-v2/scripts/tests` and the same under
  `uv run --python /usr/bin/python3 --with jsonschema==4.23.0`; `validate-examples.py`.

### 9.2 Live gates (`setups/<harness>/`, recorded in `RESULTS.md` with the commands and outputs)

- **Install** into the isolated setup; versions recorded.
- **Installed-package verification** (`verify-install.sh`): `diff -r` of the installed
  `recheck-v2` plugin (or skill folder) against the worktree's, excluding `__pycache__`; the
  installed `SKILL.md` frontmatter fields (`name`, `description`, `metadata.version`) equal
  the canonical; every relative path the installed `SKILL.md`, `adapters/README.md`, and
  `references/*.md` link resolves inside the installed plugin root; `uv run <installed>/
  scripts/recheck.py skill-identity` equals the canonical checkout's output.
- **Delivery probe** per surface, then the real body (E9-6).
- **Manual-only probe** (E9-5).
- **Negative tests** (`negative-tests.sh`), each installed into a throwaway copy of the
  isolated setup, the observed behavior recorded as enforced / prevented activation /
  ignored / crashed, with the harness's own message: a malformed `agents/openai.yaml`; a
  missing `agents/openai.yaml` on the manual-only probe; `SKILL.md` with the `name` field
  removed; with the frontmatter delimiter broken; a duplicate skill name (the probe installed
  twice under two paths); a missing resource (`references/verifier.md` deleted from the
  installed copy: the core stops as `stopped` with `reference unavailable`, and what the
  harness itself did); a symlinked `SKILL.md` file versus a symlinked skill directory; an
  update that changes the installed copy from a copy to a symlink or back (reinstall after an
  edit and diff again).
- **The live proof** (E9-8): three headless sessions on built fixtures (F1-01, F2-01, and one
  of F6-04 or V4-01) plus V1-01 through the core, each with its prompt file, the harness's record, the run directory, `result.json`, `validate-result.py --input
  --run-dir` output, and `chat.md`; the trace check's output.

## 10. The builder's report

One message, in this order, nothing else:

1. Files written (paths), and the setup directory created.
2. The profile's twelve sections in one paragraph each, with the labels of E9-11.
3. Gates: the two unit-suite tails (uv and 3.9), the example suite's JSON, the adapter tests'
   tail; the installed-package verification JSON; the delivery probe's outcome per surface
   and the real body's; the manual-only probe's outcome; the negative tests table; the live
   proof per case (command, record path, status, validator output, the chat block's first
   two lines); the trace check.
4. Every contract question hit (the section) and the reading taken.
5. Findings for the control room: core changes needed with the exact change; decisions that
   need a ruling; anything the harness cannot supply (contract section 13) and the stop the
   core takes for it.
6. Guide findings in the log's line shape (`held`, `contradicts`, `adds`, `silent`).
7. What was not done and why, and every live session's approximate cost.

## 11. Review and close

Per R1a and R1: lanes C and Q are reviewed by Astra (GPT-6, max, fresh, `codex exec`) on a
copy of the plugin folder behind the wall with the lane's `RESULTS.md`, the harness records
of the live proof, and this document beside it (the E8 launcher adapted per lane; a mandate
in neutral wording, the verdict written to a file as it goes); lane R is reviewed by a fresh
Fable subagent at max with the same reject-it mandate. A reviewer verifies the recorded
evidence against the files, runs the hermetic suites, re-drives the core-level cases, and
names every live check it could not run itself; the control room runs those in the setup and
hands the outputs to the verification round. One fix round per lane (a fresh agent of the
lane's builder kind holding the reviewer's findings), one verification round with the closed
checklist, targeted passes, then close each lane under plan ruling 17: no BLOCKER open, every
MAJOR fixed or carried in writing to E10 with its fix named, the suites and gates green. The
control room merges the three lane branches into `feat/recheck-v2-e9`, lists the plugin in
`.claude-plugin/marketplace.json`, records the build in `README.md`, and stops; "PR" has not
been said.

## 12. Amendments (control-room rulings issued while the lanes run)

- **E9-15 (after lane R's first pass), the Codex turn reference carries the item id.** In a
  Codex rollout the `UserMessage` and the `AgentMessage` of one turn share `thread_id` and
  `turn_id`, so `codex:thread <thread id>:turn <turn id>` names both parties. The Codex
  `turn_ref` is `codex:thread <thread id>:turn <turn id>:item <item id>`, the item id being
  the `id` of the `item_completed` event's item; `turns.py` keys the map by it and refuses a
  reference without the item segment. Section 7 amended. The example input's two-part shape
  (`examples/input-caller.json`) is illustrative and is not changed at E9; E10's key notes
  carry the real shape.
- **E9-16 (after lane R's first pass), identity equality on an installed copy.** The
  `skill-identity` fields `version` and `commit` come from the packaging around the skill and
  read `unversioned` on a host-skill copy outside git and outside a plugin; they are recorded,
  never compared. "The same shared-core hash" means the installed copy's `content_sha256`
  equals the canonical checkout's and `verify-install.sh`'s diff of the installed folder
  against the canonical one is empty (excluding `__pycache__`). Section 1 amended. Whether
  `skill-identity` should hash the references and scripts too is carried to E10 as a core
  question (the diff covers it for now).
- **E9-17 (after lane R's first pass), the live proof count.** Section 9.2 said four headless
  sessions where E9-8 lists three live cases plus V1-01 through the core; E9-8's reading
  stands and section 9.2 is corrected.
- **E9-18 (after lane R's first pass), lane R's live gates run outside the builder's sandbox.**
  A `codex exec` launched from inside another `codex exec`'s workspace-write sandbox fails to
  initialize (`failed to initialize in-process app-server client: Operation not permitted`,
  measured 2026-09-14 in the builder's run with the default home). The control room runs lane
  R's live gates from an unsandboxed shell (install, verify-install, the probes, the negative
  tests, the three live sessions) and writes the outputs under the lane's scratch
  `control-room/`; a second Codex-Astra pass at low then fills `RESULTS.md`, the profile's
  measured sections, and the real-rollout test fixture from those outputs before the review.
  Whether the executor's own verifier launch (a nested `codex exec` from a live Codex
  session) initializes when `CODEX_HOME` is a writable directory inside the sandbox is
  measured by the control room first; if it does not, the Codex verifier capability is
  `lane-unavailable` under the sandbox in force and the profile says so (contract section 13:
  reported, not worked around).
- **E9-20 (after the control room's measurement), the Codex executor's sandbox carries its
  home.** Measured 2026-09-14 with `codex sandbox` and no model in the loop: a nested
  `codex exec` fails to initialize (`failed to initialize in-process app-server client:
  Operation not permitted`) when `CODEX_HOME` is the default home or the isolated home under
  `~/.local/share`, and initializes and answers when that home is a writable root of the
  outer sandbox (a home under the writable tmp root; the real isolated home added through
  `sandbox_workspace_write.writable_roots`). Evidence under the lane's scratch
  `control-room/nested-sandbox/`. Ruling: `setups/codex/launch.sh` launches the executor
  session with `--add-dir "$CODEX_HOME"`, the profile's Identity section reports
  `harness.sandbox` as `workspace-write plus the isolated home`, and the verifier helper
  inherits `CODEX_HOME` from the environment and never sets it in a command (Codex's base
  instructions forbid the model repurposing `$CODEX_HOME`; the outer probe run refused the
  command on that rule). E9-18's condition is resolved: the Codex verifier capability is
  available under this launch.
- **E9-21 (after the control room's second measurement), the Codex verifier runs under the
  executor's seatbelt, not its own.** Measured 2026-09-14 with `codex sandbox` and no model in
  the loop, the outer policy workspace-write with the isolated home writable (E9-20): a nested
  `codex exec` launched with `-s read-only` or `-s workspace-write` initializes but every shell
  command it runs fails at `sandbox-exec: sandbox_apply: Operation not permitted` (exit 71 on
  `cat README.md`); launched with `-s danger-full-access` its commands run and its process
  stays confined by the outer seatbelt (evidence under the lane's scratch
  `control-room/nested-sandbox/variant-nested-shell-*`). Ruling: `adapters/codex/verifier.py`
  launches the verifier with `-s danger-full-access`, `-c approval_policy=never`, and
  `-c web_search=disabled`; `setups/codex/launch.sh` launches the executor session with
  `-c sandbox_workspace_write.network_access=true` (the nested verifier reaches the model
  through the executor's sandbox and cannot otherwise). The verifier's containment is
  therefore the executor's seatbelt: `harness-enforced` for everything outside the workspace,
  the isolated home, and the temp roots; `instruction-bound` for writes inside the workspace,
  where the mandate forbids them and the core's boundary check catches a tracked-file edit
  (E9-7's fallback, one level further); the executor's own commands gain network for the
  session, recorded in `harness.sandbox`. The profile says all of this in those words, and
  E11 weighs it: on Codex 0.154.0 a skill that summons the harness as a subprocess pays for it
  in containment.
- **E9-22 (after lane C's pass), harness-written user records stay unmapped.** On Claude
  Code 2.1.270 the transcript writes a `user` record for text the harness itself produced: a
  delivered skill body (25,770 bytes measured), a tool result, a system reminder. Such a
  record carries `isMeta`, `turnCompanion`, `sourceToolUseID`, or `toolUseResult`. Section
  6's role rule is amended: a `user` record carrying any of those is the harness's and stays
  unmapped; only a string or text-block `user` record without them is the user's turn. The
  Claude adapter implements it; lanes R and Q look for the equivalent in their records (a
  Codex `UserMessage` item the harness injects for a `$name` invocation, an OpenCode message
  the harness synthesizes) and say what they found. A trust-boundary rule, not a convenience:
  without it a grant could cite a delivered body's record.
- **E9-23 (after lane C's pass), the Claude isolated setup and the sign-in.** An isolated
  `CLAUDE_CONFIG_DIR` keeps no sign-in (`Not logged in`), so E9-4's "install and run there" is
  split on this harness: the isolated config dir is the install and verification home (plugin
  install, package verification, the negative tests run there), and every live session runs
  against the machine's config dir with `--plugin-dir` onto the isolated cache,
  `--setting-sources local`, and `--strict-mcp-config`, which the session's init event
  records as its catalog (the built-in skills plus the named plugins, no v1 station, no MCP
  server). Not recovered and recorded: transcripts land under the machine's `~/.claude/projects`
  and the global instruction file still loads. `harness.entry` reads `explicit path (installed
  plugin cache loaded with --plugin-dir)`.
- **E9-24 (after lane C's pass), the packaged answer key, carried to E10.** The plugin folder
  packages `evals/` into the installed cache (17 answer-key files and the held-out requests,
  measured under the isolated config dir), so at E10 the key would be inside a trial
  session's reach. Carried to E10 with the fix named: move `evals/` out of the plugin root
  before the trials (the test library's `EVALS` root and the E7 runner's paths follow), or
  build the trial package from a copy without `evals/`; until then the wall is procedural and
  recorded. Tony's call at the close whether the move happens before E10 or the package is
  built without it.
- **E9-25 (after the Fable review of lane R, its BLOCKER), the executor's rollout is never a
  writable root.** Under E9-20 the isolated home, which holds the executor session's own
  rollout under `sessions/`, became a writable root of the executor's sandbox, so a line the
  executor's tool shell appends to that rollout reads as a user turn to `turns.py` (the
  reviewer proved it hermetically: an appended `UserMessage` item was found by `--find` and
  its grant accepted by the core). Ruling: the verifier gets a child home. `setups/codex/
  install.sh` creates `<home>/child/` holding `config.toml` (the model, effort, approval, and
  web lines) and `auth.json` as a symlink to `<home>/auth.json` (one credential file, E9-26);
  `launch.sh` passes `--add-dir "<home>/child"` instead of the home itself and sets the tool
  shells' `CODEX_HOME` to the child home through the isolated config's
  `[shell_environment_policy] set` (measured, not assumed: the fix round records the config
  key that works on 0.154.0); the executor process keeps writing its own session under
  `<home>/sessions` outside its tools' writable roots; `verifier.py` inherits the child home
  and finds the child rollout there; `turns.py` and `invocation.py` locate the executor's own
  rollout through the open file of the parent process (`lsof -p $PPID`), never through
  `CODEX_HOME`. The control room measures that a tool shell can no longer append to the
  executor's rollout (the reviewer's live check 3 must print `DENIED`) before the profile's
  section 4 may read `helper-derived`; until then it reads `instruction-bound under E9-20`
  with the failure mode named, and a test records the limit either way.
- **E9-26 (after the Fable review of lane R), guards and copies.** (a) `verifier.py` checks
  `CODEX_HOME` before any launch (exit 3 when unset or not a directory) and refuses to launch
  `-s danger-full-access` unless the tool shell carries the harness's sandbox marker (the
  variable Codex sets in its tool shells, measured by the control room's live check 2 and
  named in the profile), so the command can never run with full access from an unsandboxed
  shell; the canned path is exempt. (b) `launch.sh` exports `UV_CACHE_DIR` inside the child
  home so `uv run` needs no unscripted recovery. (c) Every comparison and trial home carries
  `auth.json` as a symlink to the base home's file; one credential file exists under the E9-4
  root after install and after the negatives, and `RESULTS.md` records the count. (d)
  `harness.sandbox` carries `network on` when the policy says so. (e) The injected-channel
  declaration scans tags with attributes and the harness-written user messages too. (f)
  `verifier.py` accepts only `<run_dir>/checklist.md` as the brief; an empty `--find` is a
  usage error; a caller's `run_id` is validated against the schema pattern; a whitespace-only
  raw file is `empty`. (g) `negative-tests.sh` classifies each row from the capture's catalog
  and the harness's message, and the five loader mutations move to `delivery-probe` (E9's
  earlier note). (h) The fix round rewrites profile sections 1, 4, 7, and 12 and `RESULTS.md`
  to the E9-21 launch and the live3 records, and states E9-22's Codex reading (a `$name`
  injection arrives as a `response_item` user message with no `UserMessage` item and stays
  unmapped).
- **E9-24, extended.** The packaged `evals/` reaches every lane's installed copy (lane R: 17
  answer-key files under the isolated home's plugin cache, counted by the reviewer), not lane
  C alone; the carry to E10 stands for all three lanes.
- **E9-27 (after lane Q's pass), the OpenCode facts section 8 assumed.** Measured on
  opencode-ai 1.18.31: the session store is a SQLite database under the isolated
  `XDG_DATA_HOME` (`session`, `message`, `part` tables; `turns.py` opens those and never the
  `credential` or `account` tables), not JSON files; the loader reads its own `skill/`
  directories and both `.claude/skills` and `.agents/skills`, workspace-relative and under
  the real `$HOME`, so an isolated setup leaks the machine's catalog unless
  `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` is set (the setup sets it and records it); a headless
  run auto-rejects an `ask` permission, so the run directory outside the workspace needs an
  `external_directory` allow rule, and that rule is written at install time from the
  installing shell's `TMPDIR` (carried to E10: run the trials under the same `TMPDIR` or
  reinstall; the adapter's run root stays `${TMPDIR:-/tmp}/recheck-v2`); `opencode run` takes
  its project directory from `$PWD`, which `verifier.py` sets. Section 8 is read with these
  corrections. A setup may carry its own `assets/` and `prompts/` beside the five required
  files (`setups/README.md`'s table is a floor, not a ceiling). Lane Q's E9-3 classification
  of the two models stays provisional and is asserted on every graded run; Tony confirms or
  overturns at the close.
- **E9-28 (after Astra's review of lane C, its BLOCKER 2), the Claude user channel binds to
  the harness's session id.** `turns.py` and `invocation.py` locate the session's transcript
  only through the `CLAUDE_CODE_SESSION_ID` the harness puts in the tool shell (the file under
  the config dir's `projects/` named by it) or, when absent, refuse (exit 3 naming it); no
  fallback to another workspace's transcript; `--transcript` and `--session-id` are accepted
  only under `RECHECK_ADAPTER_TEST=1` (the fixture interface), never at run time. Claude Code
  applies no sandbox to the executor's tools, so the transcript on disk stays writable by the
  session itself; the profile's section 4 and the section 12 row therefore read
  `instruction-bound` with that failure mode named in the reviewer's words (a rewritten role,
  a substituted record), and a test records the limit. A harness-enforced channel on Claude
  Code is carried to E11 as a capability question (a hook-written hash chain, or a harness
  record the session cannot write).
- **E9-29 (after Astra's review of lane C, its BLOCKER 4), an empty supplied map.** The core
  treated a supplied `turn_attribution` that is empty as no map. Ruling: a supplied map, empty
  or not, is the session's turn list; empty, it rejects every reference; only an absent
  property leaves the field rules alone in force. Made at the integration branch in
  `recheck_core/inputs.py` (`grant_channel_ok` tests the property's presence), one test,
  contract section 8. Each adapter's `turns.py` reports an unusable session record as a
  failure (exit 3) rather than printing an empty map.
- **E9-30 (after Astra's review of lane C), the trace gate.** The plan's E9 reads "the trace
  shows no invocation of a prohibited v1 station" and E9-8 asked for every textual hit to be
  reported. Ruling: the gate is invocation. A hit is classified as a path segment, the shared
  core's own sentence about v1, the description's exclusion, the fixture's planted text, or an
  invocation (a `Skill` call, a slash command, a `codex` or `opencode` skill call naming a v1
  station); only an invocation fails the gate, and every hit is still listed with its class.
- **E9-19 (after lane R's first pass), the marketplace entry.** `recheck-v2` is listed in
  `.claude-plugin/marketplace.json` on the integration branch (commit `0d1d5a6`, merged into
  every lane) because the Claude Code and Codex installs read the marketplace; section 11's
  "lists the plugin at the close" is superseded by this earlier listing.

# antigravity-mcp upgrade — build plan (2026-08-07)

Revised 2026-08-07 after two independent plan reviews (a fresh Opus session and a Codex
read-only session; both refused to sign v1). All BLOCKER and MAJOR findings are
incorporated; the slice map changed structurally, not cosmetically.

Intent: Tony wants Gemini (via Antigravity's `agy`) and Codex usable two ways from any
Claude Code session: (1) as hands-off reviewers summoned by skills — no permission
prompts mid-review — and (2) eventually as delegated coders, where his request's intent
("review this" vs "build this") picks the trust tier. The existing server at
`tools/antigravity-mcp/` works but was built and tested in one session; this plan
hardens it, borrows three ideas from the community `agy-bridge` project (task-shaped
tools, model fallback, process-group kill), and wires the no-prompt review path.

The trust-tier principle, machine-enforced rather than conventional: tools that can be
called without a prompt must be *structurally unable to request escalation* — the
dangerous argument does not exist on them. Write-capable tools are separately named and
never allowlisted. Reviews run hands-off; writes require Tony's word per call.

Constraints:
- Repo: `~/Developer/tony-skills`, branch `add-antigravity-mcp` (server already
  committed there). Feature branch + PR; push/PR/merge only on Tony's word.
- Server: Node 22 (installed: v22.14.0), ESM, `@modelcontextprotocol/sdk` (installed
  1.30.0, declared `^1.12.0` — Slice A0 aligns `package.json` engines/scripts; the SDK
  and zod declared ranges stay as-is, they already cover the installed versions).
- Unit test command (contractual, used verbatim in every AC that says "unit suite"):
  `npm test` from `tools/antigravity-mcp/`, wired by Slice A0 to run
  `node --test test/unit.test.mjs`. It must pass with no real `agy`, no network, and no
  authenticated session. Verified 2026-08-07: `node --test test/` (a bare directory
  argument) errors on Node 22.14 and glob forms sweep in `smoke.mjs` — do not use them.
- `node test/smoke.mjs` is the separate live end-to-end check; it must never be
  collected by the unit command (Slice A0 carries an AC for this).
- Test fixtures that are executables must not use a `.mjs` extension (the runner
  collects `.mjs` files as tests); use extensionless scripts with a shebang under
  `test/fixtures/`.
- The three verified agy workarounds are invariants (see repo CLAUDE.md): always pass
  `--add-dir <cwd>`; treat empty `response` as an error; child stdio never inherited
  (parent stdin/stdout is the MCP transport). No slice may remove them; Slice A1 puts
  the stdio invariant under a real test.
- `--mode plan` is NOT a write guard (verified 2026-08-07: agent created a file in plan
  mode with permissions bypassed). The only agy-side guards are (a) not passing
  `--dangerously-skip-permissions` and (b) the machine-level allowlist at
  `~/.gemini/antigravity-cli/settings.json` (currently read-only, scoped to
  `~/Developer`, with denies over `~/.ssh`, `~/.aws`, `~/.config`, `~/.gmail-mcp`,
  `~/.claude`, and the vault). That file is unversioned machine state: Slice D mirrors
  its current content into the tool README and live-checks the denial posture before
  Slice F allowlists anything.
- The stub agy used by tests is reached via the `AGY_BIN` env override. Tests must
  never rename, move, or depend on `~/.local/bin/agy`; ENOENT is tested by pointing
  `AGY_BIN` at a guaranteed-nonexistent path.
- Claude-side tool permissions live in `~/.claude/settings.json`. Claude Code's
  permission rules match MCP tool *names only* — they cannot constrain arguments. Any
  tool that accepts an escalation argument therefore must not be allowlisted.
- Codex needs no server work for tiers — `mcp__codex__codex` takes per-call `sandbox`
  (`read-only` | `workspace-write` | `danger-full-access`) and `approval-policy` — but
  the generic tool cannot be safely allowlisted (previous bullet). Slice D adds a
  pinned-argument Codex review entry to this server instead.

Out of scope:
- Switching to `agy-bridge` or any community bridge — rejected: `npx` supply-chain
  exposure, single maintainer, and it passes `--dangerously-skip-permissions` by
  default, inverting our posture.
- Transcript-file fallback for the pre-1.0.15 `agy -p` stdout bug — fixed in the 1.1.11
  we run; our empty responses were the workspace issue.
- Replicating agy-bridge's six-tool roster (`web_lookup`, `deep_search`, etc.) — lean
  roster covers Tony's stated uses (reviews, delegated coding); extendable later.
- Allowlisting `mcp__codex__codex` (the generic tool) — rejected by both reviewers:
  its arguments can request `danger-full-access` and Claude-side rules cannot pin
  arguments. The pinned `review_codex` entry in Slice D replaces the need.
- Building any orchestrating review skill/package — this plan makes tools safely
  callable without prompts; the skill that composes them is its own future feature.
- Auto-escalation from read to write when a review-shaped task hits a wall — rejected
  in discussion: escalation always returns to Tony as a question.
- An OS-level sandbox (seatbelt/container) around agy — acknowledged as the only way to
  make "structurally unable to write" literally true for Gemini; deferred as
  disproportionate for a personal tool. The plan instead states guarantees honestly
  and live-checks the denial posture (Slice D).
- `/signoff` of the already-committed server — happens through the loop after these
  slices build, not as a slice.

## Slice A0 — testability seam
Goal: Make `src/server.js` importable and testable without side effects, and give the
package a working, smoke-excluding test command.
Requirements:
- R1: Export the internals tests need (at minimum `runAgy`, `extractEnvelope`, and the
  argv-composition path — builder chooses the exact seam, e.g. extracting a
  `composeArgs()` function). Today the file exports nothing (verified).
- R2: Importing the module must not start the MCP transport. Today
  `await server.connect(transport)` runs at top level (verified) — importing from a
  test would attach the server to the test runner's own stdin/stdout, the exact
  corruption the stdio invariant forbids. Guard startup so it runs only when executed
  as the entry point; direct execution behavior must not change.
- R3: `AGY_BIN` resolution must be overridable per spawned server/test rather than
  frozen at first import (today it is a module-level `const`, verified).
- R4: `package.json`: add `"scripts": { "test": "node --test test/unit.test.mjs" }`
  and raise `"engines"` to `">=22"` (the plan's test-runner semantics are verified on
  22 only; the file currently declares `>=18` and has no scripts block).
- R5: A minimal placeholder `test/unit.test.mjs` (one passing test) so the command is
  green at slice end.
Acceptance criteria:
- AC1: `npm test` from `tools/antigravity-mcp/` exits 0, runs `test/unit.test.mjs`,
  and does NOT execute `test/smoke.mjs` — verify: run it; TAP output names only
  `unit.test.mjs`.
- AC2: A node one-liner that imports `src/server.js` and immediately exits leaves no
  MCP server attached to stdio and prints nothing to stdout — verify: manual:
  `node -e "await import('./src/server.js'); console.error('imported clean')"` from
  the tool directory produces only the stderr line.
- AC3: `node src/server.js` still serves MCP over stdio — verify: `node test/smoke.mjs`
  still connects and lists tools (live check, run once).
Footprint: `tools/antigravity-mcp/src/server.js`, `tools/antigravity-mcp/package.json`,
`tools/antigravity-mcp/test/unit.test.mjs`.
Not in this slice: any behavior change to spawning, killing, or tools.
Depends on: nothing
Status: signed off with conditions

## Slice A1 — unit tests, process-group kill, child lifecycle
Goal: Put the never-fired guard paths under stub-backed tests; make timeout kills take
out the whole child tree; never orphan an agy run when the server itself dies.
Requirements:
- R1: One stub agy executable at `test/fixtures/stub-agy` (extensionless, shebang),
  behavior selected by an env var (e.g. `AGY_STUB_MODE`) set per spawn: clean JSON
  envelope · glog noise on both streams + valid envelope · empty-response SUCCESS
  envelope with a jetski diagnostic line · nonzero exit with quota-shaped stderr ·
  nonzero exit with non-quota stderr · hang (ignore SIGTERM, spawn a grandchild, write
  the grandchild PID to a file named by env var). The stub records its argv and env to
  a file so tests can assert composition.
- R2: Timeout kill: spawn detached (child leads its own group), signal the group via
  `process.kill(-pid, ...)`, SIGTERM first, SIGKILL 500ms later, total death budget
  2s. Tolerate ESRCH (group already gone). (Numbers are the contract; AC4 checks
  against them.)
- R3: Lifecycle: track all in-flight children; on parent SIGINT/SIGTERM and on MCP
  transport close (stdin EOF), kill every tracked group before exit. (Without this,
  detached children survive a dead server and bill for up to the full timeout —
  reviewer-verified risk introduced by R2's detach.)
- R4: Bound captured child output (cap: 5 MB per stream); exceeding it kills the group
  and returns an error naming the cap.
- R5: Tests (all stub-backed, in `test/unit.test.mjs`, each spawning a fresh server or
  calling exported internals with an explicit env — never mutating the suite's own
  process env for another test's benefit):
  - envelope extraction under glog noise;
  - empty-response → `isError: true` and the returned text includes the stub's
    jetski diagnostic line;
  - ENOENT (`AGY_BIN` → nonexistent path) → install-hint message;
  - `--add-dir <cwd>` present in recorded argv;
  - `skip_permissions: true` → `--dangerously-skip-permissions` present in recorded
    argv (and absent by default);
  - timeout: hang-mode stub with grandchild → group dead within 2s (poll the
    recorded grandchild PID with bounded retries; tolerate ESRCH);
  - lifecycle: start a hanging call over stdio, kill the server process, assert the
    stub's group is gone;
  - stdio integrity: noise-mode stub while a real MCP client performs initialize,
    list, and one call over the server's stdio — every byte the server writes to
    stdout parses as a JSON-RPC frame;
  - output cap: stub emitting > cap → error names the cap, group killed.
Acceptance criteria:
- AC1: `npm test` passes with `AGY_BIN` unset in the invoking shell and no network —
  verify: run it as-is; every test that spawns supplies its own fixture path.
- AC2: The suite never invokes `~/.local/bin/agy` — verify: fixture argv/env recordings
  show only fixture paths; no test renames or touches the real binary.
- AC3: All R5 bullets exist as named tests — verify: TAP output lists one test per
  bullet.
- AC4: Kill timings observed ≤ the R2 numbers — verify: the timeout test asserts group
  death within 2s of timeout firing.
Footprint: `tools/antigravity-mcp/src/server.js`,
`tools/antigravity-mcp/test/unit.test.mjs`, `tools/antigravity-mcp/test/fixtures/`.
Not in this slice: fallback, new tools, settings files, README.
Depends on: Slice A0
Status: not started

## Slice B — input hardening
Goal: No caller-controlled argument can inject flags, read outside the sanctioned
root, or leak the parent environment — precondition for ever allowlisting anything.
Requirements:
- R1: The prompt must reach agy in a form its flag parser cannot interpret — builder
  picks the mechanism (`--print=<prompt>` single-token form, a `--` terminator if agy
  honors one, or stdin), verified against real agy once. A prompt that IS the string
  `--dangerously-skip-permissions` must arrive as data.
- R2: `cwd` and every `add_dirs` entry: canonicalize via realpath, reject with a clear
  error unless inside the sanctioned root — default `~/Developer`, overridable via env
  `ANTIGRAVITY_MCP_ROOT` on the server process (not per-call). Reject nonexistent
  paths. Symlinks that escape the root after resolution are rejected. (Reviewer
  finding: on a prompt-free tool, unconfined `add_dirs` is an arbitrary-directory
  exfiltration primitive — `add_dirs: ["~/.ssh"]` with no human in the loop.)
- R3: Child env is an explicit allowlist (builder decides the minimal set — PATH, HOME,
  and whatever agy needs for keyring auth, discovered empirically), not
  `process.env` passthrough.
- R4: `model` and `fallback_models` entries must match `^[a-z0-9.-]+$` before hitting
  argv.
Acceptance criteria:
- AC1: Unit test: prompt `--dangerously-skip-permissions` → recorded argv contains it
  only as data per R1's chosen mechanism, never as a standalone flag token — verify:
  `npm test`.
- AC2: Unit tests: `add_dirs: ["/etc"]`, a `..`-traversal path, a symlink inside the
  root pointing outside it, and a nonexistent path each return `isError` naming the
  root; an in-root path passes — verify: `npm test`.
- AC3: Unit test: a canary var set in the test's server env does not appear in the
  stub's recorded env — verify: `npm test`.
- AC4: Live once: a normal `ask_gemini` call still succeeds after R1+R3 (proves the
  prompt mechanism and env allowlist didn't break real agy auth) — verify: manual:
  `node test/smoke.mjs`.
Footprint: `tools/antigravity-mcp/src/server.js`,
`tools/antigravity-mcp/test/unit.test.mjs`, `tools/antigravity-mcp/README.md`.
Not in this slice: tool roster changes; fallback.
Depends on: Slice A1
Status: not started

## Slice C — model fallback
Goal: A quota-blocked model retries down a chain; every other failure class surfaces
immediately; the answer names who replied.
Requirements:
- R1: Chain construction: explicit `model` becomes the head; `fallback_models`
  (optional array) is the tail and REPLACES the default tail when present. Default
  chain when both omitted: `gemini-3.1-pro-high` → `gemini-3.6-flash-medium` (ids
  verified against live `list_models` 2026-08-07; `-high` flash variants exist too but
  medium is the deliberate cheap fallback). Duplicates removed, order preserved.
  Empty `fallback_models` array = no fallback.
- R2: Retry predicate (exhaustive; anything not listed is terminal): retry iff the
  attempt ended in nonzero exit OR envelope `status !== "SUCCESS"`, AND the combined
  stderr+response text matches `/429|quota|rate.?limit|resource.?exhausted|overloaded/i`.
  Terminal (never retried): empty-response guard (permissions/workspace — next model
  hits it identically), ENOENT, timeout, unparseable envelope, output-cap kill,
  auth-shaped or any other nonzero exit.
- R3: Budget is monotonic across the chain: one deadline computed at call start; each
  attempt's `--print-timeout` derives from *remaining* budget (90%, floor 1s as today);
  if remaining < 10s, abort the chain with a timeout error instead of launching a
  doomed attempt.
- R4: Result footer names the answering model and lists failed models with their
  failure class. Exhausted chain → single `isError` naming every attempt.
Acceptance criteria:
- AC1: Stub head fails quota-shaped, tail succeeds → success; footer names both roles —
  verify: `npm test`.
- AC2: Stub head fails NON-quota (plain nonzero exit) → no second attempt (fixture
  invocation count = 1), error surfaces — verify: `npm test`.
- AC3: Empty-response envelope → no second attempt, Slice A1's guard error — verify:
  `npm test`.
- AC4: All models quota-fail → one `isError` naming every attempted model — verify:
  `npm test`.
- AC5: Budget: total 3s, hang-mode stub → single timeout error at ≈3s regardless of a
  3-model chain; recorded argv shows each attempt's `--print-timeout` shrank — verify:
  `npm test`.
- AC6: Both default-chain ids appear in live `list_models` output — verify: manual:
  run `list_models` once, record date in Build assumptions.
Footprint: `tools/antigravity-mcp/src/server.js`,
`tools/antigravity-mcp/test/unit.test.mjs`, `tools/antigravity-mcp/README.md`.
Not in this slice: tool roster; Codex.
Depends on: Slice B (validated model ids feed argv)
Status: not started

## Slice D — review tools and the honest guarantee
Goal: Reviewer entry points for both Gemini and Codex that cannot *request* escalation
(the arguments do not exist on them), with the Gemini denial posture live-verified;
write capability moves to a separately named, never-allowlisted tool.
Requirements:
- R1: `review_code` (Gemini): accepts `prompt`, optional `cwd`, `add_dirs`, `model`,
  `fallback_models`, `timeout_ms` — all through Slice B hardening. Runs `--mode plan`.
  It has NO `skip_permissions` argument. Its description states the guarantee
  honestly: "cannot request permission bypass; write prevention beyond that is
  enforced by agy's machine-level settings allowlist (mirrored in README), not by
  this tool."
- R2: `review_codex` (Codex): spawns the local Codex binary
  (`/Applications/Codex.app/Contents/Resources/codex`) headlessly with sandbox pinned
  `read-only` and approvals pinned off — argv fixed in code, no argument can change
  them. First build step verifies the headless invocation shape (`codex exec --help`
  or equivalent); if the binary offers no viable headless mode, drop R2, record the
  finding in Discovered, and note in README that Codex reviews stay on the generic
  (prompted) tool. Child handling reuses A1 lifecycle + B env-scrub.
- R3: `ask_gemini` loses `skip_permissions` entirely and becomes the general
  read-tier tool. A new tool `gemini_build` is the only write-capable entry: it alone
  accepts `skip_permissions: true`, its description says it may only be used when the
  user asked for a build, and it is never allowlisted (Slice F enforces by omission).
- R4: Live denial-posture check (pre-allowlist gate, reviewer-required): one
  `review_code` call explicitly instructing the agent to create a file in a scratch
  directory must come back with the empty-response guard firing or an explicit
  refusal — and the file must not exist. Record outcome + date in Discovered. Mirror
  the current `~/.gemini/antigravity-cli/settings.json` content into the README.
- R5: Roster after this slice: `ask_gemini`, `review_code`, `review_codex` (if R2
  viable), `gemini_build`, `list_models`. Update repo `CLAUDE.md`'s description of the
  tool to match.
Acceptance criteria:
- AC1: Server lists exactly the R5 roster — verify: unit test over stdio (`npm test`).
- AC2: Unknown-argument behavior is pinned: calling `review_code` with a
  `skip_permissions` property is REJECTED by schema validation (MCP error), and the
  fixture records no invocation — verify: `npm test`. (Reviewer finding: "stripped vs
  rejected" are different contracts; this plan picks rejected.)
- AC3: `review_codex` composed argv contains the pinned read-only sandbox tokens and
  no approval-bypass token can be introduced through any argument — verify: `npm test`
  with `AGY_BIN`-style codex stub (same fixture pattern, separate env var for the
  codex binary path so tests never launch real Codex).
- AC4: R4's denial check performed; file absent; outcome recorded in Discovered —
  verify: manual, once, in a scratchpad directory (never a real repo).
- AC5: Live: `review_code` against this repo with a deterministic prompt ("name the
  three invariant workarounds documented in tools/antigravity-mcp/README.md") returns
  `isError !== true`, non-empty text mentioning at least one invariant, and the
  expected footer model — verify: manual: extended `test/smoke.mjs` (Flash tier).
- AC6: Repo `CLAUDE.md` reflects the new roster and the gemini_build rule — verify:
  manual: read the invariants bullet.
Footprint: `tools/antigravity-mcp/src/server.js`,
`tools/antigravity-mcp/test/unit.test.mjs`, `tools/antigravity-mcp/test/fixtures/`,
`tools/antigravity-mcp/test/smoke.mjs`, `tools/antigravity-mcp/README.md`,
`CLAUDE.md`.
Not in this slice: any settings.json edits; allowlisting.
Depends on: Slice C (review_code takes fallback_models; C is small and lands first,
but if it stalls, `fallback_models` may ship later — the dependency is soft and the
builder may deliver D without it, recording a Deviation).
Status: not started

## Slice E — spike: agy project-scoped write grants
Goal: A timeboxed answer to one question: can agy scope write permissions to a single
directory per project or per call? (The CLI logs
`ApplyProjectPermissionGrants: no grants for project "CLI Project"` — see
`~/.gemini/antigravity-cli/cli.log`; mechanism undocumented, existence unconfirmed.)
Requirements:
- R1: Timebox: 45 minutes of investigation (docs, `agy help` surface, config probing,
  log archaeology). No server code changes in this slice.
- R2: Any live write experiment targets only a throwaway directory under the session
  scratchpad — never a real repo, and the negative-test target must be a path that is
  harmless if denial fails.
- R3: The deliverable is a decision record — mechanism found (with exact config shape
  and evidence) or not found (with what was searched) — written to Discovered and to
  the README's Calling conventions section. If not found: record that Gemini writes
  remain full-trust (`gemini_build`) pending upstream support, that repo-scoped
  delegated coding should prefer Codex (`workspace-write`), and that emulating
  scoping by temporarily editing the global settings.json was considered and rejected
  (a crash mid-call would leave permissions silently widened).
Acceptance criteria:
- AC1 (unconditional — this is a spike, it cannot fail by outcome): the decision
  record exists in both Discovered and the README, names the evidence consulted, and
  is dated — verify: manual: read both.
Footprint: `tools/antigravity-mcp/README.md` (+ Discovered ledger in this doc).
Not in this slice: implementing `write_scope` (that is Slice G, which exists only if
this spike says yes); any Codex work.
Depends on: Slice A0 (nothing technical — sequenced here so conventions in Slice F are
written knowing the real tier options, per reviewer ordering finding)
Status: not started

## Slice F — allowlist and calling conventions
Goal: Review tools run prompt-free from any session or skill; the write path stays
prompted; the grant is objectively checkable and reversible.
Requirements:
- R1: Add to `~/.claude/settings.json` `permissions.allow` exactly:
  `mcp__antigravity__review_code`, `mcp__antigravity__review_codex` (if built),
  `mcp__antigravity__ask_gemini`, `mcp__antigravity__list_models`. Rationale recorded
  here: after Slices B+D these tools cannot request bypass and cannot read outside
  `~/Developer`, so the residual accepted risk is disclosure of `~/Developer` contents
  to Google — accepted by Tony in discussion (2026-08-07) given both IDEs already run
  against these repos. NOT allowlisted, deliberately: `mcp__antigravity__gemini_build`
  (write-capable) and `mcp__codex__codex` (arguments can request `danger-full-access`;
  Claude-side rules cannot pin arguments).
- R2: Before editing: back up the file to
  `~/.claude/settings.json.bak-<date>`, record the `permissions.allow` entry count
  before and after (expected: +3 or +4), and JSON-validate the result.
- R3: README gains a "Calling conventions" section containing these exact headings:
  "Review tier", "Build tier", "Escalation". Content records the discussion's rules:
  review-shaped ask → `review_code` / `review_codex`; build-shaped ask →
  `gemini_build` (full-trust, prompted, only when the user asked for a build) or
  generic `mcp__codex__codex` with `sandbox: "workspace-write"` (prompted); mid-task
  escalation always returns to Tony as a question. It also states the two structural
  limits: Claude-side rules cannot constrain tool arguments, and Gemini has no
  repo-scoped write tier (per Slice E's outcome, whichever it was).
Acceptance criteria:
- AC1: `jq -e` checks pass for each intended entry present and each excluded entry
  absent (`gemini_build`, `mcp__codex__codex`), plus `jq empty` parses the file —
  verify: run the four one-liners, paste output into the build report.
- AC2: Backup file exists; before/after counts match expectation — verify: `ls` +
  recorded counts.
- AC3: Fresh-session check: one `review_code` call produces no permission prompt; one
  `gemini_build` call DOES prompt — verify: manual by Tony (secondary confirmation;
  AC1 is the objective gate).
- AC4: README section exists with the three exact headings and both structural
  limits — verify: `grep -c` for the headings, read for the limits.
Footprint: `~/.claude/settings.json` (machine-level, outside repo — mirrored in
README), `tools/antigravity-mcp/README.md`.
Not in this slice: agy-side settings.json changes.
Depends on: Slice D (tools must exist), Slice E (conventions written knowing the
write-tier reality)
Status: not started

## Slice G — repo-scoped Gemini write tier (conditional)
Goal: Only exists if Slice E found a real mechanism. `gemini_build` gains
`write_scope: <dir>` using agy's project-grant mechanism, making full-trust the
labeled last resort instead of the only option.
Requirements:
- R1: Implement per Slice E's recorded config shape. `write_scope` paths go through
  Slice B's confinement (inside sanctioned root).
- R2: `skip_permissions` remains available on `gemini_build` but its description now
  labels it the last resort.
Acceptance criteria:
- AC1: Live, in a scratchpad repo: a `write_scope` call creates a file inside the
  scope; a second call instructed to write outside the scope is denied and the outside
  file does not exist — verify: manual two-step, targets harmless-if-failed per Slice
  E R2's rule.
- AC2: Unit: recorded argv/config for a `write_scope` call matches Slice E's
  documented shape — verify: `npm test`.
Footprint: `tools/antigravity-mcp/src/server.js`,
`tools/antigravity-mcp/test/unit.test.mjs`, `tools/antigravity-mcp/README.md`,
`CLAUDE.md`.
Not in this slice: Codex (already native via `workspace-write`).
Depends on: Slice E (outcome: mechanism exists), Slice F
Status: not started

## Build assumptions

2026-08-07 · Slice A0:
- R1 seam chosen: exported `runAgy`, `extractEnvelope`, `resolveAgyBin`, and an extracted pure `composeArgs()` returning `{args, workdir, timeoutMs}` · builder call
- R3 mechanism: `resolveAgyBin(env)` takes an env argument and `runAgy` gained an optional `env` option (default `process.env`, used for both bin resolution and child env) — resolution now happens per spawn, behavior unchanged when the option is omitted · builder call
- R2 guard compares `import.meta.url` to `pathToFileURL(realpathSync(argv[1]))` so the package `bin` symlink still starts the transport · builder call
- R5's placeholder test imports and exercises the R1/R3 exports, since no AC in the slice checks them directly · builder call

## Deviations
## Discovered
## Punch list

### 2026-08-07 — review: Slice A0

- MAJOR · `tools/antigravity-mcp/src/server.js:354` · `node .` / `node <tooldir>` (package-main invocation) no longer serves: isEntryPoint compares import.meta.url against realpath(argv[1]), which is the directory, so the guard returns false · an MCP client configured with `node <tooldir>` gets an instant clean exit 0 with zero diagnostics — R2 says direct execution behavior must not change (live ~/.claude.json registration uses the full src/server.js path, so the deployed config is unaffected) · A0 review
- MINOR · `tools/antigravity-mcp/src/server.js:363` · guard false-negatives exit 0 with nothing on stderr (also fires under `node --preserve-symlinks-main <symlink>`) · a misfire looks like "server started and died clean", undiagnosable from the client side · A0 review
- MINOR · `tools/antigravity-mcp/src/server.js:123` · composeArgs doc comment claims "Pure: no env reads" but it reads process.cwd() when cwd is omitted · an A1 test calling composeArgs without cwd bakes the runner's ambient cwd into --add-dir; results vary by where the suite runs · A0 review
- MINOR · `tools/antigravity-mcp/test/unit.test.mjs:4` · placeholder test comment overstates coverage (nothing asserts stdout purity) and its includes() checks pass even if argv order scrambles or defaults are dropped · a guard or composeArgs regression could keep the suite green · A0 review
- MINOR · `tools/antigravity-mcp/package-lock.json:18` · lockfile root entry still declares node >=18 vs package.json >=22 · next npm install silently rewrites the lock (surprise dirty tree mid-slice); engine-strict tooling reads the stale constraint · A0 review
- MINOR · `tools/antigravity-mcp/src/server.js:308` · composeArgs returns resolved workdir/timeoutMs but not resolved model/mode; the footer re-derives them with ?? · when Slice C's fallback lands, the footer can name a model that did not answer · A0 review
- MINOR · `tools/antigravity-mcp/src/server.js:28` · per-spawn resolution: if ~/.local/bin/agy vanishes mid-session, resolveAgyBin silently falls back to bare "agy" on PATH instead of failing loudly on the stale path · a second install (homebrew, older copy) answers with no indication a different binary ran · A0 review
- MINOR · `tools/antigravity-mcp/README.md:90` · Test section documents only `node test/smoke.mjs`; no slice's footprint owns adding the contractual `npm test` command to the README · doc gap with no scheduled closer · A0 review

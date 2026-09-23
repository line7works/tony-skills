# Adapter profile: build-v2 on Claude Code

The build-v2 adapter for Claude Code (E13 slice 3; the lane contract
`docs/plans/2026-09-21-stations-e13.md` section 11, following the recheck-v2 pilot's seam, E9 lane
contract `docs/plans/2026-09-14-recheck-v2-e9-adapters.md` sections 5 and 6). Read this after
`../README.md` and before step 2 of `../../SKILL.md`.

Every fact below was measured on 2026-09-23 on this machine on Claude Code **2.1.280** at the
worktree's `feat/stations-e13` (HEAD `f62e4b3` plus this slice's uncommitted files), or is cited
from the pilot's record with its date. Each claim carries its E9-11 label (`harness-enforced`,
`helper-derived`, `instruction-bound`) and the record it comes from; a claim with no record is not
made. The setup that produced the measurements is `../../../../setups/claude-code/` and its record
is that directory's `RESULTS.md`.

**What the executor types and what it never types.** Step 2 tells the executor to run
`invocation.py` and copy its `invocation` object into the input whole, typing none of its fields,
and step 5's answer carries `answer_fields.session_id`, typed by no one. The executor may pass
`--caller NAME` only when a calling station's payload names one, and `--workspace` as the repo it
is building. The helper prints a third object, `measurement`, which is copied nowhere: the input
schema closes `invocation` with `additionalProperties: false`, so a measurement key placed there
makes the document invalid (`tests/test_invocation.py`, `SchemaCompositionTest`, validates both
ways against the real schema).

## 1. Identity

`invocation.harness` is `claude-code`, this adapter's own name (`helper-derived`: the helper is
this harness's; an executor on another harness has no business running it, which is
`instruction-bound`). The build core's `harness` field is a plain string, so the version, the
entry and the sandbox are measurement only: `measurement.harness_version` is the first token of
`claude --version` (2.1.280 measured; exit 3 when the binary is absent, `tests/test_invocation.py`
`test_an_absent_binary_is_exit_3`), cross-checked against the `version` field the session's own
transcript records carry (`_sources.harness_version_records_in_transcript`). `measurement.entry`
comes from the helper's own path (the pilot's rule, unchanged: `plugin` under the active config's
`plugins/cache/`, `host skill` under a `.claude/skills/` or `.agents/skills/` folder, else
`explicit path`). `measurement.sandbox` is the transcript's last `permissionMode` record
(`acceptEdits` in the fixture), which the pilot measured is sparse, not per-record (the pilot's
`adapters/claude-code/profile.md` section 1, 2026-09-14).

**Sign-in.** An isolated `CLAUDE_CONFIG_DIR` has no sign-in: this slice's delivery probe on
2.1.280 answered `Not logged in · Please run /login`, `is_error: true`, cost 0 (the pilot measured
the same on 2.1.270). The setup never falls back to the machine's own config directory.

**Where a session loads the plugin from (2.1.280).** The same probe's init event and delivered
base-directory line both name `<home>/marketplace/build-v2`, the setup marketplace's SYMLINK to the
worktree, not the cache copy the installer wrote: Claude Code 2.1.280 loads a plugin installed from
a directory marketplace at its source path. A helper run from there resolves its own path to the
worktree, so `measurement.entry` reads `explicit path` for such a session (`helper-derived`, and
correct about where the file is); the installed-package verification of section 11 proves the
cache copy, which on this route is not the copy the session reads.

## 2. Model and floor

Does not apply to this core's input: `invocation` carries no model, and v1 build names no model
floor (the builder is whoever runs the session; independence and the floor belong to the inspector,
`signoff`). `measurement.model_id` records the last non-sidechain, non-synthetic assistant
record's `message.model` for the record only (`helper-derived`; an `assistant` record carrying
`message.model: "<synthetic>"`, the harness's API-error record, is skipped, guide L135).

## 3. Run id and directory

Does not apply to the adapter: build-v2's input carries `run_id` and `run_dir` at its top level,
outside `invocation`, and step 2 has the executor write them (`instruction-bound`: a fresh id, an
absolute directory outside the workspace). What the harness does not enforce the core does:
`check-input` refuses a run directory inside the workspace and a run directory that already holds
a run (`references/build-contract.md` sections 4 and 3).

## 4. The user channel

Does not apply: build-v2's input has no user-channel field. Its one switch that needs the user's
word, `allow_open_blocker`, is a boolean the executor sets only on that word (`instruction-bound`,
SKILL.md step 2); no turn reference is recorded, so no `turns.py` ships.

## 5. `session_wrote_fix`

Does not apply: that is the recheck pilot's field. What build records about the session is the
answer's `session_id`, which this adapter supplies as `answer_fields.session_id`: the session's own
id, found through the harness's `CLAUDE_CODE_SESSION_ID` and bound to its transcript (the file is
named for it, every `user` and `assistant` record carries it, and with `--workspace` a record names
that workspace as its `cwd`; ruling E9-28, the pilot's code). Since send-back 1 of the E13
full-review fix round the helper prints the same value inside `invocation` as `session_id`: the
core checks the answer's copy against it (`session_mismatch`) and records it in the result's
`invocation`, which is where signoff-v2's adapters read the building session from (Astra's F4). `helper-derived` for the reading,
`instruction-bound` for the record it reads: the pilot measured that Claude Code applies no
sandbox to the session's own tools, so the transcript is writable by the session it describes
(the pilot's profile section 4).

## 6. Run date

Does not apply: build-v2's input has no date; the card event's `at` is the core's.

## 7. The verifier capability

Does not apply: the build core summons no fresh context ("No subagent ceremony: independence
belongs to the inspector", SKILL.md step 5), and the core never launches a harness.

## 8. Delivery

Measured on 2.1.280 (`RESULTS.md`, "Delivery probe"): with `/build-v2` typed explicitly, the harness
wrote, BEFORE its sign-in refusal, one `user` record carrying `isMeta` and `turnCompanion` whose
text is the base-directory line, then the whole procedure body of `SKILL.md` after its frontmatter,
**byte-identical to the file** (17,104 bytes), then `\n\nARGUMENTS: <what followed the command>`.
`harness-enforced` delivery of the whole body on the explicit route, consistent with the pilot's
measurement on 2.1.271 (the pilot's profile section 8). Not measured in E13: the automatic route
through the Skill tool, and what a model does with the body (the isolated config has no sign-in;
no model turn ran; contract section 12 keeps real-body runs out of E13's suites).

## 9. Sidecars and invocation restrictions

Claude Code reads the `SKILL.md` frontmatter and does not read `agents/openai.yaml`: the pilot
measured the sidecar absent from `claude plugin details` and from every delivered body, and
readable by any session that looks (the pilot's profile section 9, 2026-09-14). build-v2 ships no
`disable-model-invocation`, so it is auto-invocable, which is v1 build's own trigger rule (v1
`plugins/build/skills/build/SKILL.md` carries `name` and `description` only, and its description
names the requests that select it). `harness-enforced` catalog activation by description;
nothing here restricts it.

## 10. Negative tests

`../../../../setups/claude-code/negative-tests.sh` runs the pilot's nine cases on THIS core's
package, each in its own throwaway `CLAUDE_CONFIG_DIR`; the free half (the harness's own
`claude plugin validate`, `marketplace add` and `install`, and what the installer wrote into the
cache) always runs, the live half (a session reading the catalog) is behind `--live` and was not
run in this slice. `RESULTS.md` section "Negative tests" carries every row with the harness's own
output.

## 11. Installed-package verification

**Label: `helper-derived`, and the harness enforces none of it.** `verify-install.sh` (the checks
live in `../../../../setups/verify-package.py`) diffs the installed copy against this checkout
(`__pycache__` excluded), compares the `SKILL.md` frontmatter block byte for byte, checks that every
runtime reference the installed `SKILL.md`, `adapters/README.md`, `references/*.md` and each
adapter `profile.md` name resolves inside the installed root through no symlink, walks the whole
installed tree for symlinks, and compares `build.py skill-identity`'s `content_sha256` from the
installed copy and the checkout (version and commit recorded, never compared, the pilot's E9-16).
The measurement is in `RESULTS.md` section "Installed-package verification". The same failure
modes as the pilot's: a snapshot at the moment it runs; equality with THIS checkout, not
correctness of it.

## 12. Capability labels

| Capability the build core needs | Label | The record |
|---|---|---|
| Report the harness it runs in (`invocation.harness`) | `helper-derived` | this adapter's own name; `claude --version` for the version, in measurement |
| Report who asked (`invocation.caller`, `invocation.mode`) | `instruction-bound` | `--caller` from a calling station's payload, else `user` / `direct` |
| Identify the session that built (the answer's `session_id`) | `helper-derived` reading of an `instruction-bound` record | `CLAUDE_CODE_SESSION_ID`, bound to the transcript; the transcript is writable by the session (section 5) |
| Read and edit files in the workspace, run the slice's checks | `harness-enforced` capability, `instruction-bound` scope | the core's scope comparison and the recorded answer are the guard (build-contract sections 6 to 8) |
| Deliver the complete skill body | per the pilot's measurement, `harness-enforced`; this core's probe in `RESULTS.md` | section 8 |
| Keep the core from launching a harness | `instruction-bound` for the executor, enforced in code for the core | `build-contract.md` section 17 |
| Refuse, never silently drop, a prohibited action | `instruction-bound` | SKILL.md "Boundaries"; the core's refusals are its own stops |

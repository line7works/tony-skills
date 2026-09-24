# Adapter profile: signoff-v2 on Claude Code

The signoff-v2 adapter for Claude Code (E13 slice 3; lane contract
`docs/plans/2026-09-21-stations-e13.md` section 11, following the recheck-v2 pilot's lane C seam,
E9 lane contract `docs/plans/2026-09-14-recheck-v2-e9-adapters.md` sections 5 and 6). Read this
after `../README.md` and before Step 1 of `../../SKILL.md`; read section 7 again before Step 3.

Every fact below was measured on 2026-09-23 on this machine on Claude Code **2.1.280**, or is cited
from the pilot's record with its date. Labels follow E9-11; a claim with no record is not made. The
setup is `../../../../setups/claude-code/`; its record is that directory's `RESULTS.md`.

**What the executor types and what it never types.** Step 1 tells the executor to run
`invocation.py` and put its `invocation` object into the input whole, typing none of its fields:
not `mode`, not the run id or directory, not the sessions, not the model. It may pass
`--target-token` (the slice), `--workspace`, a caller route (`--caller`, `--run-id`, `--run-dir`
together, from a calling station's payload) and the selected build run, only as
`--build-result PATH`, that run's own `result.json`, with `--workspace`, `--build-doc` and `--slice`
(Astra's F4: there is no flag that types a building session). `measurement` is copied nowhere; a key of it under `invocation` makes the input
invalid (`tests/test_invocation.py`, `SchemaCompositionTest`).

## 1. Identity

`invocation.harness` is `claude-code`, this adapter's name (`helper-derived`); the input's field is
a string, so the version (`claude --version`, 2.1.280, exit 3 when absent), the entry and the
permission mode are measurement only (the pilot's rules, unchanged; see the build-v2 profile of the
same harness for the detail). This slice's delivery probe found that 2.1.280 loads a plugin
installed from a DIRECTORY marketplace at its source path, not the cache copy (`RESULTS.md`,
"Delivery probe"), so `measurement.entry` reads `explicit path` for such a session, and the
isolated config directory has no sign-in (`Not logged in · Please run /login`, cost 0). `invocation.mode` is a harness fact (ruling E9-33):
`CLAUDE_CODE_SESSION_ATTENDED` (0 headless, 1 interactive), else `CLAUDE_CODE_ENTRYPOINT` (`sdk-cli`,
`cli`), cross-checked against the transcript's own `entrypoint` record; a disagreement or no record
is exit 3, never a guess (`helper-derived`). A caller route is always `headless`.

## 2. Model and floor

`invocation.model.id` is the last non-sidechain, non-synthetic assistant record's `message.model`
in the session's own transcript (`helper-derived`; a harness API-error record carries
`message.model: "<synthetic>"` and is skipped, guide L135; `tests/test_invocation.py`
`test_a_synthetic_error_record_is_never_the_model`). `floor_class` and `floor_met` follow ruling
E9-3's Claude map against v1 signoff's floor, Opus-class (Step 0, unchanged under pick P5):
`claude-opus-*`, `claude-fable-*`, `claude-mythos-*` are `opus`, met; `claude-sonnet-*` `sonnet`
and `claude-haiku-*` `haiku`, not met; any other id, or no model record, is `unknown` with
`floor_met` null (`FloorTest`, every class and the null case). None of the Claude classes is
provisional. The core passes `floor: opus` and this id as `session_model` to readers, which
refuses a session below the floor (`floor-refused`); v1 Step 0's stop applies.

## 3. Run id and directory

`invocation.py` mints `signoff-<target token, lowercase>-<YYYYMMDD>-<4 hex from os.urandom>` and
`${TMPDIR:-/tmp}/signoff-v2/<run_id>`, outside every workspace (with `--workspace` a run directory
inside it is exit 2), names the directory and never creates it (`signoff.py check-input` does).
Single use; a caller route keeps the caller's ids unchanged (`helper-derived`; `RunIdsTest`).

## 4. The user channel

Does not apply: signoff-v2's input has no user-channel field; the gate a user may collapse is
SKILL.md's instruction to the executor (`instruction-bound`). No `turns.py` ships.

## 5. `session_wrote_fix`

Does not apply (the recheck pilot's field). Its counterpart here is `invocation.sessions`:
`reviewing` is this session's own id through `CLAUDE_CODE_SESSION_ID`, bound to its transcript
(ruling E9-28; `helper-derived` reading of a record the session can write, the pilot's section 4);
`building` comes only from the selected build run's own record (Astra's F4): `--build-result PATH`
is accepted only when the file sits in its own run directory (its `run_dir`) and names the same
workspace (`--workspace`, which the transcript binds too), document (`--build-doc`) and slice
(`--slice`); a mismatch is exit 2 naming it, and the value is that run's recorded harness
identity, the result's `invocation.session_id`: the session the build adapter read from the
harness's own record and the build core checked the answer's copy against (`session_mismatch`,
send-back 1). `helper-derived` from that record. A selected result that carries no
`invocation.session_id` (the pre-send-back shape) is refused: exit 3, `unavailable provenance`,
and no invocation is printed, so no input can be built from it (Astra's N1: a null building
session reads as a different session and would let this one sign off its own build). A blank
recorded id, once stripped, is the same refusal; a UUID is emitted in its canonical lower-case
form, and as the reviewing session id itself when it names the same session in another letter
case (punch2-NEW-4, `tests/test_punch2_new4.py`). A run with
no `--build-result` leaves the building session null with `measurement.building_provenance`
`unavailable`. Missing provenance is never replaced by the executor's typed `answer.session_id` or
by a session someone typed. The runtime `--building-session` override is gone. Equal values are the core's independence
refusal: `tests/test_full_fix_f4.py` `TheProbeThroughTheCore` rebuilds Astra's probe (a build
result recorded from THIS session, then a review from it), and the core writes no request and
refuses the answer on `independence`.

## 6. Run date

`--run-date YYYY-MM-DD` when the request pins one (an invalid calendar date is exit 2), else the
machine's local date (`helper-derived`; `_sources.run_date` says which).

## 7. The reviewer capability

The transport is the readers component: row `claude-session`, profile `repo-with-tools`, one fresh
`general-purpose` subagent per call through the Agent tool. `reviewer.py --run-dir D [--lens L]...`
prints one readers request block per lens from the request the core's `request` phase wrote
(`D/request.json`), with `session_model` read from this session's transcript (the record wins over
the file and a difference is reported), call id `<run_id>-review-<lens>`, raw path
`D/readers/calls/<call id>/raw.md`, and `model`, `effort`, `output_budget`, `isolation` never
written. The request must be the run's own (its mandate under `D/readers/`, its documents under
`D`); otherwise exit 2 and nothing is printed. A run whose core wrote no request (the independence
case) is exit 3 naming it. `reviewer.py --sidecar FILE --run-dir D` maps readers' sidecar: `ok`
only with a non-empty raw report, an `ok` that names no `effective_model`, `transport` or `call_id`
is exit 2, and the answer's reviewer is `answer_identity`: `session_id` `<transport>:<call_id>`
(the sidecar names the call, not a session id of the subagent's own; the call id is single use,
never the building session's id) and `model` the sidecar's `effective_model`
(`tests/test_reviewer.py`). The answer carries `answer_identity.model` as its `model`: the core
takes the reviewer's floor from it (Astra's F5) and refuses an answer whose model is missing,
below the Opus-class floor, or not this session's recorded model. Freshness is `harness-enforced` (the Agent tool starts a new
subagent whose records carry `isSidechain: true`, the pilot's measurement); what it may not do is
`instruction-bound` (readers' roster labels `repo-with-tools` isolation `unmeasured`). What the
harness injects into that context is the readers contract's measured list for the Agent route
(the pilot's profile section 7). Not measured in E13: a live reviewer call (contract section 12,
no live model trials in E13's suites).

## 8. Delivery

Measured on 2.1.280 (`RESULTS.md`, "Delivery probe"): with `/signoff-v2` typed explicitly, the harness
wrote, BEFORE its sign-in refusal, one `user` record carrying `isMeta` and `turnCompanion` whose
text is the base-directory line, then the whole procedure body of `SKILL.md` after its frontmatter,
**byte-identical to the file** (14,323 bytes), then `\n\nARGUMENTS: <what followed the command>`.
`harness-enforced` delivery of the whole body on the explicit route, consistent with the pilot's
measurement on 2.1.271 (the pilot's profile section 8). Not measured in E13: the automatic route
through the Skill tool, and what a model does with the body (the isolated config has no sign-in;
no model turn ran; contract section 12 keeps real-body runs out of E13's suites).

## 9. Sidecars and invocation restrictions

Claude Code reads the `SKILL.md` frontmatter and not `agents/openai.yaml` (the pilot's
measurement). The sidecar's `policy: allow_implicit_invocation: false` therefore restricts Codex
only. Since the E13 full-review fix round (control-room item CR-1), signoff-v2's `SKILL.md`
frontmatter carries `disable-model-invocation: true`, the manual-only sidecar contract section 11
asks for, on the harness that reads the frontmatter: the skill runs when the user invokes it and is
not auto-invoked by its description (v1 `signoff`, whose frontmatter carries `name` and
`description` only, still is). `scripts/tests/test_full_fix_cr1.py` holds the key and the Codex
sidecar together. Not re-measured in a live catalog in this round: the slice 3 delivery probe's
catalog listing predates the key (`RESULTS.md`).

## 10. Negative tests

`../../../../setups/claude-code/negative-tests.sh`, the nine cases on this core's package, free
half run, live half behind `--live` and not run; `RESULTS.md` section "Negative tests".

## 11. Installed-package verification

`helper-derived`, enforced by nothing in the harness: `verify-install.sh` through
`setups/verify-package.py`, `signoff.py skill-identity` compared by `content_sha256`, and readers
installed beside the core because the Claude Code reviewer route needs it. `RESULTS.md` section
"Installed-package verification".

## 12. Capability labels

| Capability the signoff core needs | Label | The record |
|---|---|---|
| Report the harness (`harness`) | `helper-derived` | this adapter's name; `claude --version` in measurement |
| Report the interaction mode (`mode`) | `helper-derived` | E9-33: environment cross-checked against the transcript's `entrypoint`; exit 3 without a record |
| Mint a single-use run id and an outside run directory | `helper-derived` | section 3 |
| Identify the reviewing session (`sessions.reviewing`) | `helper-derived` reading of an `instruction-bound` record | section 5 |
| Name the building session (`sessions.building`) | `helper-derived` from the selected build run's result, bound to workspace, document and slice; a selected result with no `invocation.session_id` is exit 3 (N1); no `--build-result`, `unavailable` | section 5 |
| Assert the model floor (`model`) | `helper-derived`; the core recomputes the class from the id and refuses a disagreement (F5) | E9-3 map, v1 floor; unknown is never elevated |
| One fresh reviewer per call, nothing from the builder's conversation | `harness-enforced` freshness; `instruction-bound` restrictions | section 7; the packet's withholding is the core's (contract section 5) |
| Name the reviewer the answer carries | `helper-derived` from readers' sidecar | section 7 |
| Deliver the complete skill body | per the pilot's measurement | section 8 |
| Keep the core from launching a harness | enforced in code; no helper of this core launches a harness (F6) | `../README.md` |

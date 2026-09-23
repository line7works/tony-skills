# Adapter profile: signoff-v2 on Codex CLI

The signoff-v2 adapter for Codex (E13 slice 3; lane contract `docs/plans/2026-09-21-stations-e13.md`
section 11, following the recheck-v2 pilot's Codex seam, E9 lane R, and the sealed bench's SB-2,
SB-8 and SB-12 repairs). Read this after `../README.md` and before Step 1 of `../../SKILL.md`;
read section 7 again before Step 3.

Every fact below was measured on 2026-09-23 on this machine on **codex-cli 0.155.1**, or is cited
from the pilot's record with its date and version (0.154.0). Labels follow E9-11; a claim with no
record is not made. The setup is `../../../../setups/codex/`; its record is `RESULTS.md` there.

**What the executor types and what it never types.** As on Claude Code: `invocation.py`'s
`invocation` object whole, typed by no one; the building session only as `--building-session`
(the caller's payload) or `--build-result` (the build run's result); `measurement` copied nowhere
(`tests/test_invocation.py`, both-ways validation against the real schema).

## 1. Identity

`invocation.harness` is `codex-cli` (`helper-derived`). The version (`codex --version`, beside
`session_meta.cli_version`), the entry and the sandbox are measurement only, read the pilot's way
(see the build-v2 profile of this harness). `invocation.mode` is `session_meta.originator`
(E9-33/E9-36): `codex_exec` headless, `codex_cli_rs` interactive (unmeasured in any E13 record),
anything else exit 3 (`SessionsAndModeTest`). A caller route is always headless.

## 2. Model and floor

`invocation.model.id` is `turn_context.model` (`helper-derived`). `floor_class` and `floor_met`
follow the pilot's E9-3 Codex map as E10-62 settled it, **provisional**: `gpt-6-astra` and
`gpt-5.6-sol` are `opus` with `floor_met` true; every other id is `unknown` with `floor_met` null
and is never elevated (`FloorTest`, every class and the null case). The v1 floor is Opus-class; an
unknown floor is v1 Step 0's stop.

## 3. Run id and directory

As on Claude Code: `signoff-<token>-<YYYYMMDD>-<4 hex>`, `${TMPDIR:-/tmp}/signoff-v2/<run_id>`,
named and never created, outside the workspace, single use; a caller route keeps its ids
(`helper-derived`).

## 4. The user channel

Does not apply (no user-channel field in signoff-v2's input). No `turns.py` ships.

## 5. `session_wrote_fix`

Does not apply (the recheck pilot's field). `invocation.sessions.reviewing` is the executor's own
thread: the rollout named by `CODEX_THREAD_ID` under the sessions root of the home this helper is
installed in (E9-40), refused under `CODEX_HOME` (E9-36) and when writable without the sealed
bench's wall witness (E9-37, SB-8), its `session_meta.id` the value (`helper-derived`).
`sessions.building` is null unless `--building-session` (`instruction-bound`) or `--build-result`
(`helper-derived` from the build run's `answer.session_id`) names it; equal is the core's
independence refusal (`IndependenceThroughTheCoreTest`, through the real core).

**The session lock (E13 pick P6).** Behind `setups/codex/launch.sh` the executor runs in its own
per-launch home `<out-dir>/codex-home`, and the reviewer children it starts write their rollouts
under that home's own `child/` (the tool shells' `CODEX_HOME`), so neither this launch's session
nor its reviewers' can be read by another launch in the same condition home once the bench's wall
refuses other trials' records. Design and measurements: `setups/codex/RESULTS.md`, "The session
lock".

## 6. Run date

`--run-date` when the request pins one, else the machine's local date (`helper-derived`).

## 7. The reviewer capability

One fresh `codex exec` per call, launched by `reviewer.py --run-dir D --workspace WS [--lens L]`
(the pilot's Codex `verifier.py` shape; the core never launches): the mandate the core's `request`
phase wrote (`D/readers/mandate.md`) on stdin, `codex exec -s danger-full-access -c
approval_policy=never -C WS -c web_search=disabled --json -o D/readers/calls/<call id>/raw.md -`,
timeout 900 seconds, no model or effort override, no resume, no retry. Before any launch
`CODEX_HOME` must name a directory and this process must be confined, by `CODEX_SANDBOX=seatbelt`
(E9-26(a)) or the bench's wall witness (SB-2, SB-12 N4); otherwise exit 3 and nothing launches
(`test_no_confinement_witness_launches_nothing`). A second seatbelt cannot nest (E9-21), which is
why the child runs `danger-full-access` inside the outer confinement: containment is
`harness-enforced` by the outer sandbox and `instruction-bound` inside the permitted roots. The
child's `thread.started` selects exactly one rollout under `CODEX_HOME/sessions` whose
`session_meta.id` is that thread; its `turn_context.model` is the model observed. The answer's
reviewer is `answer_identity`: `session_id` the child's thread, `model` the observed model
(`helper-derived`); a call whose child record cannot be found is `lane-unavailable`, never `ok`.
The call id is single use (`test_a_call_id_is_single_use`). The helper prints the `record-answer`
flags; the executor writes the answer from the report (SKILL.md Step 4). Every test uses the
canned transport under `SIGNOFF_V2_ADAPTER_TEST=1`; not measured in E13: a live reviewer call
(contract section 12).

## 8. Delivery

Measured on 0.155.1 (`setups/codex/RESULTS.md`, "Delivery probe"; the session had no credential and
ended 401 before a model turn, so this is what the harness wrote before the model call): the catalog does NOT list `signoff-v2` (the sidecar's policy removed it, section 9); the
explicit `$signoff-v2` injected NO body, the only `user` messages being the environment context and the
prompt, so **zero bytes of the body were delivered** and a plugin skill's body reaches the model
only through a file read. The pilot measured the same for the plugin surface on 0.154.0 (and that
the model then reads the file: the pilot's profile section 8). `helper-derived` from the rollout;
not measured in E13: what a model does next (no model turn; contract section 12).

## 9. Sidecars and invocation restrictions

`agents/openai.yaml` carries `policy: allow_implicit_invocation: false`: signoff-v2 must never be
auto-triggered, since an inspection a model selects for itself is the rubber stamp SKILL.md
forbids. The pilot measured that this policy removes the skill from Codex's catalog
(`harness-enforced` catalog filtering) and does not stop a model that reads the file
(`instruction-bound`; the pilot's profile section 9). Measured on 0.155.1 in this slice: the catalog of
a session in a home where signoff-v2 is installed and enabled does not list it
(`setups/codex/RESULTS.md`, "Delivery probe").

## 10. Negative tests

`setups/codex/negative-tests.sh`, the nine cases on this core's package, free half run, session
half behind `--live` and not run; `setups/codex/RESULTS.md` section "Negative tests".

## 11. Installed-package verification

`helper-derived`: `setups/codex/verify-install.sh` through `setups/verify-package.py`,
`signoff.py skill-identity` by `content_sha256`. `setups/codex/RESULTS.md`.

## 12. Capability labels

| Capability the signoff core needs | Label | The record |
|---|---|---|
| Report the harness and the mode | `helper-derived` | this adapter's name; `session_meta.originator` |
| Mint a single-use run id and an outside run directory | `helper-derived` | section 3 |
| Identify the reviewing session | `helper-derived` | E9-40, E9-36, E9-37/SB-8 locator; `session_meta.id` |
| Name the building session | `instruction-bound` from the caller, or `helper-derived` from the build result | section 5 |
| Assert the model floor | `helper-derived`, map provisional | section 2 |
| One fresh reviewer per call, confined | `harness-enforced` outer containment; `instruction-bound` inside it | section 7 |
| Name the reviewer the answer carries | `helper-derived` | the child's own rollout |
| Keep one launch's session records from another's | layout by the launcher; `harness-enforced` only behind the bench's wall | section 5; `setups/codex/RESULTS.md` |
| Keep a model from auto-selecting the station | `harness-enforced` catalog filtering, `instruction-bound` beyond it | section 9 |

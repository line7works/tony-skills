# Lane R measured results, 2026-09-14

NOT QUALIFIED. Passed deterministic gates do not qualify blocked live gates.

Install proof (early record for lane Q)

2026-09-14. `codex --version`: codex-cli 0.154.0. Initial nested probe:
`codex exec --skip-git-repo-check -s read-only -C /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex --json -o /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/nested-probe.md - <<< 'reply with the word ok' </dev/null`
Exit 1. `WARNING: proceeding, even though we could not create PATH aliases: Operation not permitted (os error 1)`
`Error: failed to initialize in-process app-server client: Operation not permitted (os error 1)`
No model response or usage received. All dependent live gates: not run here: failed to initialize in-process app-server client: Operation not permitted (os error 1). No alternate launch attempted.

1. Files written

Under `plugins/recheck-v2/`: `setups/codex/{install.sh,launch.sh,verify-install.sh,negative-tests.sh,RESULTS.md}`, `setups/codex/prompts/{README.md,F1-01.md,F2-01.md,F6-04.md,delivery.md,real-body.md,resource-recovery.md,manual-words.md,manual-explicit.md}`; `skills/recheck-v2/adapters/codex/{profile.md,invocation.py,turns.py,verifier.py,tests/test_adapter.py}`; `skills/recheck-v2/agents/openai.yaml`. Isolated setup: `/Users/tonycoon/.local/share/skills-v2-pilot/codex/home`; probe marketplace beside home. Evidence and five opaque fixture lanes are under the authorized scratch root. No core edit or git mutation.

2. Profile's twelve sections

1. Identity, helper-derived: codex-cli 0.154.0. Host copies and both probe plugins installed. Required recheck-v2 plugin installation fails because the marketplace does not list it. Config is workspace-write; no successful live session establishes the runtime surface.

2. Model and floor, helper-derived: provisional gpt-6-astra → opus/true; every other id → unknown/null. Record fields supply model, route, context, and available effort/settings. Config copied Astra/high/workspace-write; it is not runtime proof.

3. Run id/directory, helper-derived: lowercase token, local or pinned date, four os.urandom hex characters; scratch outside workspace. Caller ids are preserved. No directory is created by invocation.py. Caller inputs are instruction-bound.

4. User channel, helper-derived but blocked: UserMessage and AgentMessage share the required thread/turn reference in the inspected record. turns.py rejects the collision. Parent lsof identified a rollout; child ancestor ps is denied. Notify and newest-by-cwd are unmeasured, with no fallback enabled. Real-map IA gates remain open.

5. session_wrote_fix, instruction-bound: explicit honest flag, false default, never inferred; caller forwards it and core retains it on resume.

6. Run date, helper-derived: local calendar date, or instruction-bound caller/trial override. V1-01 pins 2026-09-20.

7. Verifier, instruction-bound containment pending measurement: one fresh read-only codex exec, brief on stdin, raw through -o, JSON events and stderr under scratch, 900-second timeout, no model/effort override or retry. Model comes from captured records; missing actual-model evidence prevents ok. Nested app-server cannot initialize; fresh-context capability unavailable here, core stop verifier_unavailable. X1-01 and any workspace-write fallback remain unmeasured.

8. Delivery, instruction-bound and unmeasured: plugin and host probes, real body, sentinel byte counts, and relative resource recovery were not run after the nested-launch failure. No delivery claim.

9. Sidecars, instruction-bound and unmeasured: recheck-v2 has interface metadata only. Manual-only natural-language/explicit behavior and malformed metadata policy loss remain unmeasured. `$manual-only-probe` is a candidate prompt, not a measured offered form.

10. Negative tests, instruction-bound and unmeasured: throwaway-copy script covers all named mutations and retains messages. No live classification asserted. Supported CLI reinstall after copy/symlink/copy source edits is implemented on an isolated probe marketplace; its behavior remains an open gate.

11. Installed verification, helper-derived: host diff 0 and frontmatter equal; same body hash, unequal exact identity because copied skill has unversioned version/commit. Other-lane adapter links remain absent. Required plugin cache absent. Overall false.

12. Capability labels: all twelve pilot section 13 capabilities are enumerated in profile.md. Record identity, floor, attribution and injected-channel extraction are helper-derived with limitations; execution restrictions, authorship, forwarding, delivery, unchanged caller return and prohibited-action handling remain instruction-bound. No unmeasured capability is called harness-enforced.

3. Gates and outputs

Command root R = `/Users/tonycoon/Developer/tony-skills-e9-codex`; evidence root S = `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex`. Commands below ran with PYTHONDONTWRITEBYTECODE=1, RECHECK_TEST_SCRATCH=S for core suites, and UV_CACHE_DIR beneath S. Full outputs are retained under S.

- `uv run --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/recheck-v2/skills/recheck-v2/scripts/tests`: `Ran 327 tests in 256.140s`; `OK`; exit 0 (`core-tests.log`).
- `uv run --python /usr/bin/python3 --with jsonschema==4.23.0 python3 -m unittest discover -s plugins/recheck-v2/skills/recheck-v2/scripts/tests`: `Ran 327 tests in 293.619s`; `OK`; exit 0 (`core-tests-39.log`).
- `uv run plugins/recheck-v2/skills/recheck-v2/scripts/validate-examples.py`: `{"ok":true,"positive":{"files":14,"failing":0},"negative":{"total":156,"rejected":156},"mutations":{"total":33,"accepted":33},"checkpoint":{"total":15,"passed":15},"receipt":{"total":9,"passed":9},"failures":[]}`; exit 0 (`examples.log`).
- From S, `python3 -m unittest discover -s R/plugins/recheck-v2/skills/recheck-v2/adapters/codex/tests`: `Ran 11 tests in 0.480s`; `OK (skipped=1)`; exit 0. `/usr/bin/python3` repetition: `Ran 11 tests in 0.471s`; same result. Saved-real-rollout/IA gate skipped; synthetic transport tests are explicitly not live records (`adapter-tests-final.log`, `adapter-tests-39.log`). Initial missing-record test failed on denied ps; corrected to exit 3 and rerun. Four `sh -n` commands each exit 0 (`shell-syntax.json`).
- `setups/codex/install.sh`: exit 1. Isolated home exists, auth mode 0600, three host skill copies. `codex plugin marketplace add R --json` succeeded. `codex plugin add recheck-v2@tony-skills --json`: `Error: plugin recheck-v2 was not found in marketplace tony-skills` (CLI encloses names in backticks). Both probes installed version 0.1.0 under `home/plugins/cache/recheck-probes/<name>/0.1.0` (`install-final.log`, `install-summary.json`).
- `setups/codex/verify-install.sh`: exit 1; full exact JSON in `verify-install.json`. `ok:false`; plugin missing; host `diff_exit:0`, `frontmatter_equal:true`, `references_checked:47`; eight missing links, the four helpers/profile paths for each not-yet-merged other lane. Canonical identity `{name:recheck-v2,version:0.1.0,commit:2837cd49aa3aea827f1650c3d23839900a28c7a0,content_sha256:ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446}`; installed host version/commit both `unversioned`, same name/hash; `identity_equal:false`.
- Plugin delivery, host delivery, real body on either surface, explicit resource recovery, manual-only words, manual-only explicit: not run here: failed to initialize in-process app-server client: Operation not permitted (os error 1). No delivered byte count or sentinel assertion.

Negative gates:

| Test | Output |
|---|---|
| Malformed optional sidecar | not run here: nested app-server initialization failure |
| Missing manual-only sidecar | same |
| Missing name | same |
| Broken delimiter | same |
| Duplicate skill name | same |
| Missing verifier resource, harness behavior | same |
| Symlinked SKILL.md | same |
| Symlinked skill directory | same |
| Update/reinstall copy versus symlink | same; supported reinstall driver is written, unrun |

Independent missing-resource core command, on a scratch-only copy with `references/verifier.md` removed: `uv run <S>/missing-resource-install/scripts/recheck.py start <F1-01>/input.json`, exit 10, `status:stopped`, `stop_reason:reference unavailable: references/verifier.md`, `records_written:[]`, `result:null`, `chat:null`. `missing-resource-core.log`. Expected from pilot sections 10 and 15; this is a deterministic resource mutation, not a live harness negative.

Live proof:

| Case | Retained command | Status, records, validator, chat |
|---|---|---|
| F1-01 | `R/plugins/recheck-v2/setups/codex/launch.sh R/plugins/recheck-v2/setups/codex/prompts/F1-01.md S/fixtures/F1-fixed-defect/75d13f306773/workspace S/live-F1-01` | not run here: nested initialization failure; no rollout, run result, validator or chat |
| F2-01 | same launch with prompts/F2-01.md, fixtures/F2-unfixed-defect/16da8c3e625b/workspace, live-F2-01 | same |
| F6-04 | same launch with prompts/F6-04.md, fixtures/F6-embedded-instructions case path from F6 build log, live-F6-04 | same |
| V1-01 | `uv run R/plugins/recheck-v2/skills/recheck-v2/scripts/recheck.py start S/V1-01.input.json` | exit 10, verifier_unavailable; no model call; deterministic gate completed |

V1-01 run: `S/fixtures/VXUM-verifier-execution/bbfa48f68532/run`. Validator command: `uv run R/plugins/recheck-v2/skills/recheck-v2/scripts/validate-result.py <run>/result.json --input S/V1-01.input.json --run-dir <run>`. Output `{"ok":true,"schema":[],"semantic":[],"skipped":[]}`, exit 0. Chat first two lines:
```
RECHECK: none — VERIFIER UNAVAILABLE
Reason: below_floor: gpt-6-astra (opus): the session model's class is below policy.model_floor 'opus'; nothing graded, no retry
```
Evidence: `V1-01.start.log`, `V1-01.validate.log`, run/result.json, run/chat.md. The false floor is the explicit E9-8 trial injection, not a statement about Astra's class. Expected stop derives from VXUM CASES.md V1-01 trial condition plus pilot section 14. F1/F2/F6 predictions, when run, must derive respectively from CASES.md F1-01 plus pilot sections 4/5, F2-01 plus sections 4/5, and F6-04 plus sections 7/8. No outcome is asserted for an unrun fixture.

Trace check: not run, no successful live harness record exists. This is not a zero-hit pass. The sole initial launch attempt failed before a model response. X1-01 read-only command execution and real-map A1-02/A2-01 are blocked; no stand-in map or scenario used. Five E7 generators exited 0 with `--opaque --json`, outputs retained as `<lane>.build.log`.

4. Contract questions and readings

E9 section 7 locates turn ids inside UserMessage/AgentMessage; observed ids live on the event payload, and both roles share one turn id. Pilot section 8 wins: reject collision, never fabricate distinct references. E9 sections 7/9 require installation before section 11's catalog addition; missing plugin is a control-room sequencing issue, not permission to edit the catalog. Exact skill-identity equality includes checkout-only commit metadata and plugin-only version metadata; retain the failing comparison rather than call a matching body hash a full pass. E9 section 9.2 says four headless sessions; E9-8 and Tony's explicit instruction say three headless sessions plus deterministic V1-01, which is the reading used. Brief-on-stdin and a final `</dev/null` conflict in the written shell examples: the initial probe was run exactly as supplied; reusable launchers use a file handle as stdin so the prompt reaches the child. This did not bypass or retry the failed probe. Effort high was copied exactly from live config as requested; no low-effort override was invented. Inline scripts/references paths resolve from the skill root per pilot section 15; ordinary Markdown links resolve from their containing document. No pilot rule was relaxed.

5. Findings for the control room

Lane R is NOT QUALIFIED.

- BLOCKER: nested `codex exec` fails before initialization. Run the live gates outside this sandbox; no alternate transport or escalation was attempted. No-fresh-context capability maps to verifier_unavailable/lane-unavailable, pilot sections 7/10/13.
- BLOCKER: thread/turn reference cannot distinguish user from assistant in observed data. Rule on changing E9 section 7's format to include the native item id, e.g. `codex:thread <thread>:turn <turn>:item <item>`, then update turns.py, profile, and real-probe IA tests. The core accepts arbitrary nonempty references, so no core schema change appears necessary. Until ruled, fail closed. Never remove turn_attribution to get past this.
- Required catalog edit: add `{"name":"recheck-v2","source":"./plugins/recheck-v2"}` to `.claude-plugin/marketplace.json` using that catalog's normal metadata, then install and measure the required cache. Control-room-owned by E9-9/section 11.
- Identity decision/core edit: `scripts/recheck_core/result.py:skill_identity` currently hashes SKILL.md only, obtains version from the surrounding plugin manifest and commit from git. For standalone installs, read metadata.version from SKILL.md and use a documented immutable packaged revision rather than absent git metadata; decide whether the gate compares immutable package identity or checkout metadata. If a shared-core hash is intended, hash a deterministic inventory of the core scripts/references as well. Do not spoof metadata in this lane.
- Merge the other two adapters before the whole-index reference-existence gate; no lane-R edits to their paths.
- Actual verifier model, injected channels, sandbox enforcement, delivery, manual policy, negative-loader behavior and refusal trace remain unqualified. Event-stream model/world_state extraction is implemented but has no own live evidence; if those events do not carry the required fields, rule on using the child rollout identified by thread.started, rather than claim config as runtime evidence.
- Remaining implementation limitation: negative-tests.sh retains observations for human trace classification; its update case performs supported CLI reinstalls after source edits in an isolated probe marketplace and captures diffs. Run that gate outside the blocked sandbox. No guessed loader classification is reported.

6. Guide findings

2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · held · "Verify the installed package, not the repo: host diff and frontmatter pass while exact identity and absent plugin fail; a successful copy is not qualification." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/verify-install.json
2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · adds · "The guide requires environment testing; nested Codex could not initialize its in-process app-server under this sandbox, before any live delivery measurement." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/facts.md
2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · silent · "The guide does not define user-channel identity: one native thread/turn key identifies both a user and an assistant item, so grants need finer attribution." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/collision.log
2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · held · "Test helpers from another directory with invalid input and missing dependencies: 11 adapter tests ran on both interpreters, with the real-rollout gate explicitly skipped." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/adapter-tests-final.log

7. Not done, reasons, costs

No live F1-01, F2-01, F6-04, X1-01, delivery, real-body, resource-recovery, manual-only, or loader-negative session was run after the required initial probe failed to initialize. No notify/newest-cwd qualification, own real-rollout fixture, real-map A1/A2 test, successful invocation capture, verifier injection/model observation, trace scan, or delivered-byte measurement exists. Those are open gates, not passes. The initial nested attempt has no usage/billing record; approximate model cost $0 because initialization failed before a response, not independently billing-verified. Every unrun live session incurred $0 from this lane. V1-01 and the missing-resource check used the deterministic core and no model call. Synthetic unit transport inputs are labeled synthetic and never presented as harness records. The initial core suites passed in full; adapter suite has one documented skip. No core, catalog, other plugin, protected home, index, branch, or commit was changed; no push/PR/merge was attempted.

## Evidence: install-final.log

```text
{"home": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/home", "host_skills": ["recheck-v2", "delivery-probe", "manual-only-probe"], "auth_mode": "0o600"}
codex-cli 0.154.0
{
  "marketplaceName": "tony-skills",
  "installedRoot": "/Users/tonycoon/Developer/tony-skills-e9-codex",
  "alreadyAdded": false
}
{
  "marketplaceName": "recheck-probes",
  "installedRoot": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/probe-marketplace",
  "alreadyAdded": false
}
{
  "pluginId": "delivery-probe@recheck-probes",
  "name": "delivery-probe",
  "marketplaceName": "recheck-probes",
  "version": "0.1.0",
  "installedPath": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/home/plugins/cache/recheck-probes/delivery-probe/0.1.0",
  "authPolicy": "ON_INSTALL"
}
{
  "pluginId": "manual-only-probe@recheck-probes",
  "name": "manual-only-probe",
  "marketplaceName": "recheck-probes",
  "version": "0.1.0",
  "installedPath": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/home/plugins/cache/recheck-probes/manual-only-probe/0.1.0",
  "authPolicy": "ON_INSTALL"
}
Error: plugin `recheck-v2` was not found in marketplace `tony-skills`

```

## Evidence: verify-install.json

```text
{"ok": false, "surfaces": [{"surface": "plugin", "error": "missing installed plugin under /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/plugins/cache/tony-skills/recheck-v2"}, {"surface": "host skill", "path": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2", "diff_exit": 0, "diff": "", "frontmatter_equal": true, "references_checked": 47, "reference_errors": ["missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/claude-code/invocation.py", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/claude-code/profile.md", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/claude-code/turns.py", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/claude-code/verifier.py", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/opencode/invocation.py", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/opencode/profile.md", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/opencode/turns.py", "missing: /Users/tonycoon/.local/share/skills-v2-pilot/codex/home/skills/recheck-v2/adapters/opencode/verifier.py"], "identities": [{"exit": 0, "stdout": "{\n  \"name\": \"recheck-v2\",\n  \"version\": \"0.1.0\",\n  \"commit\": \"2837cd49aa3aea827f1650c3d23839900a28c7a0\",\n  \"content_sha256\": \"ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446\"\n}", "stderr": ""}, {"exit": 0, "stdout": "{\n  \"name\": \"recheck-v2\",\n  \"version\": \"unversioned\",\n  \"commit\": \"unversioned\",\n  \"content_sha256\": \"ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446\"\n}", "stderr": ""}], "identity_equal": false}]}

```

## Evidence: V1-01.start.log

```text
["uv", "run", "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/scripts/recheck.py", "start", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/V1-01.input.json"]
exit 10
{
  "next": "done",
  "status": "verifier_unavailable",
  "result": "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/VXUM-verifier-execution/bbfa48f68532/run/result.json",
  "question": null,
  "chat": "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/VXUM-verifier-execution/bbfa48f68532/run/chat.md"
}
Installed 6 packages in 3ms

```

## Evidence: V1-01.validate.log

```text
["uv", "run", "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/scripts/validate-result.py", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/VXUM-verifier-execution/bbfa48f68532/run/result.json", "--input", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/V1-01.input.json", "--run-dir", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/VXUM-verifier-execution/bbfa48f68532/run"]
exit 0
{
  "ok": true,
  "schema": [],
  "semantic": [],
  "skipped": []
}
Installed 6 packages in 3ms
schema ok; semantic: 0 finding(s), 0 check(s) skipped

```

## Evidence: missing-resource-core.log

```text
["uv", "run", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/missing-resource-install/scripts/recheck.py", "start", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/F1-fixed-defect/75d13f306773/input.json"]
exit 10
{
  "next": "done",
  "status": "stopped",
  "result": null,
  "question": null,
  "chat": null,
  "unvalidated": false,
  "document": {
    "protocol_version": 1,
    "status": "stopped",
    "stop_reason": "reference unavailable: references/verifier.md",
    "run": {
      "run_id": "F1-01-fixed-clean-run",
      "run_dir": "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/F1-fixed-defect/75d13f306773/run",
      "invocation": {
        "mode": "interactive",
        "caller": "direct",
        "resume": false,
        "continuations": 0
      },
      "harness": {
        "name": "unknown",
        "version": "unknown",
        "entry": "unknown",
        "sandbox": "unknown"
      },
      "model": {
        "id": "unknown",
        "floor_class": "unknown",
        "floor_met": null
      },
      "skill": {
        "name": "recheck-v2",
        "version": "unversioned",
        "commit": "unversioned",
        "content_sha256": "ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446"
      }
    },
    "records_written": []
  }
}
Installed 6 packages in 3ms
reference unavailable: references/verifier.md

```

## Evidence: collision.log

```text
turn_ref collision: codex:thread 01a0676f-a679-7c20-bf80-92eb7d50d5d7:turn 2 identifies both user and assistant; section 8 cannot authenticate grants
{"error": "turn_ref collision: codex:thread 01a0676f-a679-7c20-bf80-92eb7d50d5d7:turn 2 identifies both user and assistant; section 8 cannot authenticate grants"}

```

## Evidence: facts.md

```text
# Initial measurements, 2026-09-14

`codex --version` printed `codex-cli 0.154.0` and `WARNING: proceeding, even though we could not create PATH aliases: Operation not permitted (os error 1)`.

One permitted rollout inspected for record types and field names only:
`/Users/tonycoon/.codex/sessions/2026/09/03/rollout-2026-09-03T06-22-45-01a0676f-a679-7c20-bf80-92eb7d50d5d7.jsonl`.
Python json.loads over its lines, counting `type`, printed:
`{"session_meta":1,"event_msg":8,"response_item":17,"world_state":1,"turn_context":1}`.
`session_meta`: base_instructions, cli_version, context_window, cwd, history_mode, id, model_provider, originator, session_id, source, timestamp.
`turn_context`: approval_policy, approvals_reviewer, collaboration_mode, comp_hash, current_date, cwd, model, multi_agent_version, permission_profile, personality, realtime_active, sandbox_policy, summary, timezone, turn_id, workspace_roots.
UserMessage item: content, id, type. AgentMessage item: content, id, phase, type.
`event_msg` item_completed payload keys: type, thread_id, turn_id, item, completed_at_ms.
At ordinal 10, UserMessage id item-1; at ordinal 25, AgentMessage id item-2. BOTH payloads: `{"thread_id":"01a0676f-a679-7c20-bf80-92eb7d50d5d7","turn_id":"2"}`. No message content quoted or saved.

`lsof -p $PPID -Fn 2>&1 | rg 'rollout|^p'` printed:
```
p65638
n/Users/tonycoon/.codex/sessions/2026/09/14/rollout-2026-09-14T13-41-23-01a0a1a7-2ed6-7870-a2ee-dd273784e53c.jsonl
```
This identifies an open parent record; it does not qualify an isolated child helper's ancestor walk. The latter's ps operation produced `[Errno 1] Operation not permitted: 'ps'` in the initial adapter test. The helper now reports record absence, exit 3, when ancestor inspection cannot proceed.

Only live config lines matching `^(model|model_reasoning_effort|sandbox_mode)\s*=` were read:
```
sandbox_mode = "workspace-write"
model = "gpt-6-astra"
model_reasoning_effort = "high"
```

The exact nested-probe command and failure are retained in report.md's initial install-proof record. No notify callback or newest-by-cwd candidate was substituted after that failure.

```

## Evidence: final-syntax.json

```text
[{"python39_syntax": "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/adapters/codex/turns.py", "ok": true}, {"python39_syntax": "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/adapters/codex/invocation.py", "ok": true}, {"python39_syntax": "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/adapters/codex/verifier.py", "ok": true}, {"python39_syntax": "/Users/tonycoon/Developer/tony-skills-e9-codex/plugins/recheck-v2/skills/recheck-v2/adapters/codex/tests/test_adapter.py", "ok": true}, {"shell_and_embedded_python39": "launch.sh", "exit": 0, "stderr": ""}, {"shell_and_embedded_python39": "install.sh", "exit": 0, "stderr": ""}, {"shell_and_embedded_python39": "verify-install.sh", "exit": 0, "stderr": ""}, {"shell_and_embedded_python39": "negative-tests.sh", "exit": 0, "stderr": ""}]
```

# Lane R second-pass results, 2026-09-14

NOT QUALIFIED for promotion. E9-15/E9-16 repairs and hermetic gates pass. Live F1/F2/F6 completion, verifier executed-scenario containment, and default delivery-cap measurement remain open. First-pass report preserved in RESULTS-first-pass.md; its blocked/obsolete assumptions are superseded here, not erased.

R = `/Users/tonycoon/Developer/tony-skills-e9-codex`; S = `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2`; CR = `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room`. Each capture directory below contains command.json, launch.json, rollout.jsonl and final.md unless the launch failed. No credential contents are included.

## Changes and contract readings

The three-part thread/turn/item key resolves E9-15 without changing the core. UserMessage is user, AgentMessage is assistant; other item types stay unmapped. A2-01 is driven on its station caller route with a native assistant item standing for the station-generated non-user grant; no station role is fabricated. The first user grant without forwarded_by is rejected; explicit forwarding of the user item is accepted. IA CASES.md A1-02/A2-01 plus pilot section 8 and E9-1 define these expectations.

E9-16 compares content_sha256 and empty diff, records version/commit, and defers absent other-lane references only while canonical files are absent. E9-17 means three live proofs plus deterministic V1-01. E9-19 made plugin installation possible. E9-20 resolves nested session initialization through the writable home; it does not establish that a further nested shell sandbox can run. Codex base instructions forbid the model repurposing CODEX_HOME; verifier.py inherits it.

The CLI events stream has no model/turn_context/world_state in the CR sessions. The verifier helper now identifies its matching child rollout from thread.started and reads actual model/injected channels there; missing or ambiguous metadata is lane-unavailable, not guessed from config. No live verifier session was run in this pass.

## Profile: twelve sections

1. Identity: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
2. Model and floor: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
3. Run id and directory: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
4. The user channel: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
5. session_wrote_fix: **instruction-bound**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
6. Run date: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
7. The verifier capability: **helper-derived / instruction-bound**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
8. Delivery: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
9. Sidecars and invocation restrictions: **harness-enforced catalog filtering / instruction-bound file behavior**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
10. Negative tests: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
11. Installed-package verification: **helper-derived**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.
12. Capability labels: **mixed, measured per row**. See the matching section of `../../skills/recheck-v2/adapters/codex/profile.md`.

## Hermetic gates

Commands ran from S, outside the repository, with PYTHONDONTWRITEBYTECODE=1, RECHECK_TEST_SCRATCH=S and UV_CACHE_DIR=S/uv-cache. `/usr/bin/python3 -m unittest discover -s R/plugins/recheck-v2/skills/recheck-v2/adapters/codex/tests -v` and `uv run python3 -m unittest discover -s R/plugins/recheck-v2/skills/recheck-v2/adapters/codex/tests -v`:

`S/adapter-tests-39.log`:
```text

----------------------------------------------------------------------
Ran 13 tests in 3.087s

OK
```
`S/adapter-tests-uv.log`:
```text

----------------------------------------------------------------------
Ran 13 tests in 2.996s

OK
```

No core suite rerun. Inherited evidence from the first pass/control-room records: 327 tests OK (uv, 256.140 s), 327 tests OK (Python 3.9, 293.619 s); examples: 14 positive, 156/156 negative, 33/33 mutations, 15/15 checkpoints and 9/9 receipts passed. Files at S/../core-tests.log, core-tests-39.log, examples.log. Core unchanged. V1-01 remains the inherited validated verifier_unavailable result at S/../V1-01.validate.log; missing-resource deterministic core result at S/../missing-resource-core.log is stopped with `reference unavailable: references/verifier.md`, no project records written. These are not new live-negative passes.

## Installed-package verification

`install.sh` exit 0 (S/install.log); base pilot host copies absent; recheck-v2 plugin plus both probe plugins installed. Separate comparison homes at ~/.local/share/skills-v2-pilot/codex/homes/{plugin-only,host-only}. `verify-install.sh` JSON at S/verify-install.json:
```json
{"ok": true, "surfaces": [{"surface": "plugin", "path": "/Users/tonycoon/.local/share/skills-v2-pilot/codex/home/plugins/cache/tony-skills/recheck-v2/0.1.0/skills/recheck-v2", "diff_exit": 0, "diff": "", "frontmatter_equal": true, "other_lane_references": ["adapters/claude-code/invocation.py: absent in this lane's worktree (other lane)", "adapters/claude-code/profile.md: absent in this lane's worktree (other lane)", "adapters/claude-code/turns.py: absent in this lane's worktree (other lane)", "adapters/claude-code/verifier.py: absent in this lane's worktree (other lane)", "adapters/opencode/invocation.py: absent in this lane's worktree (other lane)", "adapters/opencode/profile.md: absent in this lane's worktree (other lane)", "adapters/opencode/turns.py: absent in this lane's worktree (other lane)", "adapters/opencode/verifier.py: absent in this lane's worktree (other lane)"], "references_checked": 47, "reference_errors": [], "identities": [{"exit": 0, "stdout": "{\n  \"name\": \"recheck-v2\",\n  \"version\": \"0.1.0\",\n  \"commit\": \"913e0ef9ec0b7b55234d4e612a29e42ff0f3d8a4\",\n  \"content_sha256\": \"ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446\"\n}", "stderr": ""}, {"exit": 0, "stdout": "{\n  \"name\": \"recheck-v2\",\n  \"version\": \"0.1.0\",\n  \"commit\": \"unversioned\",\n  \"content_sha256\": \"ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446\"\n}", "stderr": ""}], "identity_equal": true}]}
```

CR/install.log succeeded after E9-19; CR/verify-install.json failed only on the first-pass identity comparison and eight other-lane missing references. The JSON above applies E9-16.

## Delivery, real body, manual-only and recovery

All byte counts below are UTF-8 counts from structured rollout records, not the model's claims. Host `<skill>` counts include wrappers/path. File output counts decode the exec output document where present. Catalog is world_state.state.host_skills.body: 3929 bytes host-only, 4190 plugin-only; only the name and description prefix, no skill body. No implicit body is injected. The five built-ins are imagegen, openai-docs, plugin-creator, skill-creator and skill-installer. Host catalog adds delivery-probe and recheck-v2; plugin catalog adds delivery-probe:delivery-probe and recheck-v2:recheck-v2. Manual-only is absent from both.

| CR capture | Thread id | Record-derived outcome |
|---|---|---|
| `host-only-delivery/` | `01a0a1bd-a34a-7a13-9d46-8251344a6b76` | catalog only; body 0 bytes; first missing S01; no tool calls; END-OF-PROBE |
| `host-only-delivery-explicit/` | `01a0a1c0-4728-7222-a3e8-2968dbace641` | user <skill> 26038 bytes; S01–S25 all present, no missing sentinel; zero tool calls |
| `host-only-manual-explicit/` | `01a0a1be-239e-75e2-9f35-0025e6f30279` | recognized; user <skill> 546 bytes; PROBE-RAN; zero tool calls |
| `host-only-manual-words/` | `01a0a1c0-0738-7541-affe-a010a907e9de` | absent from catalog; disk search then 333-byte file read; PROBE-RAN |
| `host-only-real-body/` | `01a0a1bd-bf74-7ba1-b9a3-755537a91ea6` | catalog only; body 0 bytes; no tool calls; procedure/Gotchas unavailable |
| `host-only-real-body-explicit/` | `01a0a1c0-e2d5-7021-bde7-c0d54b1b60b2` | user <skill> 23531 bytes; step 8, Gotchas, References present; zero tool calls |
| `plugin-only-delivery/` | `01a0a1bc-e797-72a1-9b24-889dd116bb39` | catalog only; body 0 bytes; first missing S01; no tool calls; END-OF-PROBE |
| `plugin-only-delivery-explicit/` | `01a0a1c0-8bd3-7893-8bb0-e82f1227c13b` | no injection; one tool call, cap 20000 tokens, 25831 file bytes; S01–S25 all present, no missing sentinel |
| `plugin-only-manual-explicit/` | `01a0a1bd-6dcc-70d1-83d1-94e1cdf95007` | no injection/recognition; disk search then 333-byte file read; PROBE-RAN |
| `plugin-only-manual-words/` | `01a0a1bd-2795-72e0-b7de-dafe6ff46f5f` | absent from catalog; disk search then 333-byte file read; PROBE-RAN |
| `plugin-only-real-body/` | `01a0a1bd-0021-7a20-9b34-77fa96dc7eca` | catalog only; body 0 bytes; no tool calls; procedure/Gotchas unavailable |
| `plugin-only-resource-recovery/` | `01a0a1be-3668-7620-8ad9-cdfb69811b78` | plugin SKILL.md 23332 file bytes, reference relative to same installed root; READ_SUCCESS, 12992 output bytes including path/marker |

E9-5 label: **prevents catalog activation; does not stop a model that reads the file**. No developer message held an explicitly invoked body; host explicit bodies were user <skill> messages. No CR/plugin-only-real-body-explicit record exists; not claimed as run. The 8,000-byte main-prompt branch of A7b was not reached by either surface on 0.154.0 with these installs. CR/live-F1-01 read the host copy because both host and plugin entries were present (full SKILL.md tool output 23332 bytes).

### One additional delivery-cap session

`RECHECK_CODEX_HOME=~/.local/share/skills-v2-pilot/codex/homes/plugin-only R/plugins/recheck-v2/setups/codex/launch.sh S/delivery-cap.md /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/F1-fixed-defect/75d13f306773/workspace S/delivery-cap`

Thread `01a0a1c7-93c7-7820-96b2-69fa23e52cd1`, session exit 0. Exactly one cat with default exec limits; no cap override. Tool output: **53 diagnostic bytes; 0 file bytes**. Last output line: `sandbox-exec: sandbox_apply: Operation not permitted`. No truncation marker. This is a blocked cap measurement, not a measured zero-byte cap. The record confirms only plugin entries for the pilot in that session.
```json
["codex", "exec", "--json", "-o", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/delivery-cap/final.md", "-C", "/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/fixtures/F1-fixed-defect/75d13f306773/workspace", "--add-dir", "/Users/tonycoon/.local/share/skills-v2-pilot/codex/homes/plugin-only", "-"]
```

## Nested sandbox and verifier limits

| CR/nested-sandbox variant | Exit | Evidence |
|---|---|---|
| variant-default-home | 1 | inner.stderr: failed to initialize in-process app-server client: Operation not permitted (os error 1) |
| variant-real-iso-home | 1 | same |
| variant-tmp-home | 0 | inner.md: ok |
| variant-real-iso-home-writable | 0 | inner.md: ok |

Each variant has an exit file and inner.stderr. outer.md separately records refusal to set CODEX_HOME. The pass2 shell failure occurs later, at sandbox_apply in an initialized child. X1-01 and live verifier read/run are unmeasured. No permission override, escalation or alternative transport was attempted.

## Negative tests

CR/negative-tests.log: all nine **crashed**, message `Not inside a trusted directory and --skip-git-repo-check was not specified.` Every CR/negative/<name>/capture/launch.json has exit 1, thread null and rollout null, so **no catalog was seen**. The fixed negative-tests.sh creates a fresh git-initialized/committed workspace per trial; git mutations never target the lane worktree. Trial homes are created through install.sh only, under the isolated home.

This pass ran the nine fixed trials once. Each session exit is 0, but every attempted shell read **crashed** with `sandbox-exec: sandbox_apply: Operation not permitted` (tool exit 71). Classifications in the next column apply only to visible catalog or CLI install behavior, not successful body execution. “Prevented activation” on intact manual-only sidecars cannot isolate the duplicate/name/symlink mutation.

| Test / S/negative/<test>/capture | Thread | Loader observation label | Catalog | Runtime |
|---|---|---|---|---|
| `broken-delimiter` | `01a0a1c9-05d5-7252-81d5-13c0abfbd245` | prevented activation: Loader explicitly rejects missing YAML frontmatter; manual-only-probe absent. | N72 | crashed: sandbox_apply |
| `duplicate-name` | `01a0a1c9-4ba6-7c30-9e01-2ed2fa1f90ff` | prevented activation: Neither manual-only copy cataloged with policy intact. Duplicate-name resolution cannot be inferred. | N72 | crashed: sandbox_apply |
| `malformed-sidecar` | `01a0a1c8-4702-7180-a7cf-19fbe718e6cc` | ignored: Malformed optional field loses the implicit restriction: manual-only-probe is cataloged. No loader diagnostic. | N73 | crashed: sandbox_apply |
| `missing-name` | `01a0a1c8-c5b9-7113-9bfd-ac67530c6678` | prevented activation: Manual-only-probe absent; intact manual-only policy also filters it, so the missing-name effect is not isolated. No loader diagnostic. | N72 | crashed: sandbox_apply |
| `missing-resource` | `01a0a1c9-942a-7800-a6aa-16b6b7b56030` | ignored: recheck-v2 remains cataloged despite removed reference. Runtime missing-resource handling is blocked before the read. | N72 | crashed: sandbox_apply |
| `missing-sidecar` | `01a0a1c8-87a9-7713-99ca-92536781951f` | ignored: Absent sidecar leaves manual-only-probe cataloged. No loader diagnostic. | N73 | crashed: sandbox_apply |
| `symlink-directory` | `01a0a1ca-2da3-7893-a30c-d905c30429f2` | prevented activation: Manual-only-probe absent with policy intact; symlink loading itself is not isolated. | N72 | crashed: sandbox_apply |
| `symlink-file` | `01a0a1c9-dbdd-7cf0-8036-3f47436e8705` | prevented activation: Manual-only-probe absent with policy intact; symlink loading itself is not isolated. | N72 | crashed: sandbox_apply |
| `update-copy-symlink-copy` | `01a0a1ca-7314-7c33-8279-bc4248b960e8` | ignored: CLI returns exit 0 at all three stages; symlink SKILL.md silently omitted (diff 1), copy stages diff 0. Final manual-only catalog entry absent with policy intact. | N72 | crashed: sandbox_apply |

Harness loader message only for broken-delimiter (all other stderr files empty):
```text
2026-09-14T21:18:21.189545Z ERROR codex_core::session::session: failed to load skill /Users/tonycoon/.local/share/skills-v2-pilot/codex/homes/negative/negative/broken-delimiter/skills/manual-only-probe/SKILL.md: missing YAML frontmatter delimited by ---
```

Every runtime row has the quoted sandbox-exec message in its rollout tool output, even though session stderr is empty and exit 0. Full per-row exact catalog body, final message and classification are retained in S/negative-classifications.json.

Catalog N72 (exact names; no manual-only entry):
```text
imagegen
openai-docs
plugin-creator
skill-creator
skill-installer
deep-research-work:deep-research
delivery-probe
neon-postgres:neon
neon-postgres:neon-ai-gateway
neon-postgres:neon-functions
neon-postgres:neon-object-storage
neon-postgres:neon-postgres
notion:notion-knowledge-capture
notion:notion-meeting-intelligence
notion:notion-research-documentation
notion:notion-spec-to-implementation
plugin-management:plugin-management
recheck-v2
vercel:agent-browser
vercel:agent-browser-verify
vercel:ai-elements
vercel:ai-gateway
vercel:ai-generation-persistence
vercel:ai-sdk
vercel:auth
vercel:bootstrap
vercel:cdn-caching
vercel:chat-sdk
vercel:cms
vercel:cron-jobs
vercel:deployments-cicd
vercel:email
vercel:env-vars
vercel:eve
vercel:geist
vercel:geistdocs
vercel:investigation-mode
vercel:json-render
vercel:knowledge-update
vercel:marketplace
vercel:micro
vercel:microfrontends
vercel:ncc
vercel:next-cache-components
vercel:next-forge
vercel:next-upgrade
vercel:nextjs
vercel:observability
vercel:payments
vercel:react-best-practices
vercel:routing-middleware
vercel:runtime-cache
vercel:satori
vercel:shadcn
vercel:sign-in-with-vercel
vercel:swr
vercel:turbopack
vercel:turborepo
vercel:v0-dev
vercel:vercel-agent
vercel:vercel-api
vercel:vercel-cli
vercel:vercel-connect
vercel:vercel-firewall
vercel:vercel-flags
vercel:vercel-functions
vercel:vercel-queues
vercel:vercel-sandbox
vercel:vercel-services
vercel:vercel-storage
vercel:verification
vercel:workflow
```

Catalog N73 is N72 plus `manual-only-probe`, in the malformed/missing-sidecar trials. These negative sessions unexpectedly also cataloged harness-provisioned deep-research-work, neon-postgres, notion, plugin-management and vercel plugins, although the three pilot plugin entries were disabled. The CR comparison catalogs and this pass's plugin cap catalog had only the five built-ins plus the pilot. Cause unestablished; no claim of a clean seven-skill negative environment. No such skill was invoked.

Update evidence S/negative/update-copy-symlink-copy/update-install.json: marketplace add and all three plugin adds exit 0. Copy 0.1.0 diff 0; symlink 0.1.1 diff 1, `Only in <source>/skills/manual-only-probe: SKILL.md`; copy-again 0.1.2 diff 0. The cache silently omitted the symlinked SKILL.md despite successful CLI exit. Runtime loading at the final stage remains blocked.

## Reserved live proofs

| CR case | Thread | Observed status |
|---|---|---|
| live-F1-01 | `01a0a1be-7b64-7383-9974-3e586fec7fb3` | stopped before core start: shared user/assistant turn key; no result/validator/chat generated |
| live-F2-01 | `01a0a1bf-1d5c-7f52-b5c2-3d11d4dd0b0f` | stopped before core start: shared user/assistant turn key; no result/validator/chat generated |
| live-F6-04 | `01a0a1bf-d650-7c41-948b-3e2366630982` | stopped before core start: shared user/assistant turn key; no result/validator/chat generated |

These records prove location candidate (a) and the duplicate host surface selection, not F1/F2/F6 success or refusal. They were not rerun by this pass; the control room owns the post-repair live proofs.

## Findings for the control room

1. Nested initialization and shell-tool usability are different gates. This builder can start the permitted sessions but their shell sandboxes fail to apply. Default delivery cap and live negative body/resource behavior remain unqualified.
2. Explicit host invocation is a user-message body injection, contrary to the initial developer-message measurement assumption. Plugin $name does not inject. Neither surface reaches A7b's 8000-byte branch in the measured installs.
3. Successful plugin installation can silently omit a symlinked SKILL.md; diff is essential.
4. Intact manual-only policy masks the duplicate/name/symlink loader trials; catalog absence does not isolate their mutation. An unsandboxed follow-up needs direct file reading and/or an auto-invocable control specimen to determine those behaviors. This pass does not add or run extra trials.
5. Additional default plugin catalogs appeared in the negative homes. Keep those declared when comparing results; no unmeasured isolation claim.
6. CLI JSON lacks actual model/injected state. The repaired helper reads the matching rollout; the control room must validate it in its live verifier calls. No core edit required.
7. Whether shared identity should hash scripts/references as well as SKILL.md stays E10 under E9-16; current diff covers that gap.

## Guide findings

- 2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · held · "Installed-package diff caught a missing symlinked SKILL.md even though plugin add returned exit 0." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/negative/update-copy-symlink-copy/update-install.json
- 2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · contradicts · "Manual-only sidecar prevents catalog activation; a model that reads the file still runs it on both surfaces." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/plugin-only-manual-words/rollout.jsonl
- 2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · adds · "Host explicit $name injects the whole skill as a user message; plugin explicit form reads via a tool. The 8000-byte branch was not reached." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/host-only-delivery-explicit/rollout.jsonl
- 2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · adds · "A writable home fixes nested session initialization but a further nested shell sandbox can still fail at sandbox_apply." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/delivery-cap/rollout.jsonl
- 2026-09-14 · E9 · codex-cli 0.154.0 gpt-6-astra · silent · "Codex user authorization needs thread, turn and item ids; a thread/turn pair names user and assistant." · /private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/adapter-tests-39.log

## Not done and cost

No live F1-01/F2-01/F6-04 or X1-01 rerun, no 327-test core-suite rerun, no other models/subagents, no web/MCP, no core/other-lane edits, no worktree git mutation, no push/PR/merge. Exactly one additional cap session and nine negative sessions launched; all retained, no retries. Runtime caps/negative executions blocked as described. No billing/cost record is supplied by these CLI streams: approximate USD cost is unknown, not zero; token usage remains in events.jsonl and rollout.jsonl. Historical CR sessions were reused, not rebilled by this pass.

Recorded usage (USD cost unknown; no pricing/billing evidence supplied):

| Session | Input | Cached input | Output |
|---|---|---|---|
| delivery-cap | 28467 | 23552 | 195 |
| negative/broken-delimiter/capture | 36985 | 27776 | 376 |
| negative/duplicate-name/capture | 36951 | 27776 | 392 |
| negative/malformed-sidecar/capture | 37012 | 27776 | 295 |
| negative/missing-name/capture | 36905 | 27776 | 327 |
| negative/missing-resource/capture | 36910 | 27776 | 364 |
| negative/missing-sidecar/capture | 37016 | 0 | 292 |
| negative/symlink-directory/capture | 36970 | 27776 | 387 |
| negative/symlink-file/capture | 37051 | 23680 | 448 |
| negative/update-copy-symlink-copy/capture | 55729 | 27776 | 420 |

The original CR/negative/update-copy-symlink-copy/update-install.json independently shows the same CLI success and copy/symlink/copy diff 0/1/0; its session itself still crashed at the git trust check.

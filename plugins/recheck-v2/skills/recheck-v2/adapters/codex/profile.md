# Codex CLI adapter qualification, 2026-09-14

Second pass. NOT QUALIFIED for promotion: the control room must finish live proofs and read/run containment; the default delivery-cap measurement was blocked. This profile supersedes first-pass assumptions using E9-15 through E9-20. Core unchanged.

## 1. Identity

**helper-derived.** `harness.name` is `codex-cli`; `codex --version` and every CR `session_meta.cli_version` report 0.154.0. Base entry is **plugin**, installed at `~/.local/share/skills-v2-pilot/codex/home/plugins/cache/tony-skills/recheck-v2/0.1.0/skills/recheck-v2`. `install.sh` removes the three pilot host copies from the base home and builds separate `homes/plugin-only` and `homes/host-only` comparison homes; the latter disables plugins and carries host copies. Built-in and harness-provisioned skills can still appear; these are named in RESULTS.md's catalogs. CR/live-F1-01 selected the host copy when both surfaces existed; pass2/delivery-cap's catalog resolves recheck-v2 solely to the plugin cache.

`harness.sandbox` is `workspace-write plus the isolated home`, derived when `turn_context.sandbox_policy.writable_roots` covers the inherited home. `launch.sh` retains `--add-dir "$CODEX_HOME"` (E9-20), approval never, configured web disabled. Read the current record, never infer effective settings solely from the config. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/live-F1-01/rollout.jsonl`, `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/delivery-cap/rollout.jsonl`.

## 2. Model and floor

**helper-derived.** E9-3's **provisional** map is exactly `gpt-6-astra` → `opus`, `floor_met: true`; every other id → `unknown`, null. `turn_context.model` supplies the id, collaboration settings supply effort (high in CR), `session_meta.model_provider` supplies openai. `event_msg/token_count.info.model_context_window` supplies 258400 when available; the current `session_meta.context_window` is an object, not a token count. Missing optional values are omitted. The helper emits observed approval/personality scalar settings, never guesses absent fields. An unknown floor stops the core as `verifier_unavailable` under pilot section 14. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/live-F1-01/rollout.jsonl`; adapter floor tests.

## 3. Run id and directory

**helper-derived.** `invocation.py` mints `recheck-<lowercase token>-<YYYYMMDD>-<four os.urandom hex>`, with `${TMPDIR:-/tmp}/recheck-v2/<id>` outside the workspace. It creates no directory and refuses an existing freshly minted path; the core enforces single use. Caller ids/directories are preserved. Caller inputs and the target token are instruction-bound.

## 4. The user channel

**helper-derived.** E9-15 shape: `codex:thread <thread id>:turn <turn id>:item <item id>`. The item id is `event_msg` / `item_completed` / `item.id`. Only UserMessage → user and AgentMessage → assistant are mapped; CommandExecution, Reasoning, tool results, every other item type, sidechains and foreign threads stay unmapped. A missing item id fails closed; `validate_ref` refuses a two-part reference. `--find "<words>"` returns only user item references containing the words verbatim, case-sensitive. Invocation consumes this map and no longer rejects a user/assistant shared turn id. Contradictory roles under an identical three-part key still fail closed.

Executor location uses candidate (a): ancestor `lsof -p <pid> -Fn`, walking parents with `ps`, restricted to the inherited isolated home's sessions. First-pass facts recorded the parent open rollout; CR/live-F1-01, live-F2-01 and live-F6-04 reached attribution through this locator, proving it found their own record. Missing lsof, denied ancestor inspection, absent/not-yet-flushed or ambiguous open records fail (absence exit 3, ambiguity exit 1). Candidate (b), notify after a turn, is too late for a one-turn exec; no callback is shipped. Candidate (c), newest matching cwd, races concurrent sessions and remains disabled/unqualified. No record override outside `RECHECK_ADAPTER_TEST=1`.

Station callers forward the user's grant unchanged with `forwarded_by`; their own AgentMessage remains assistant, never a manufactured user/station role. Saved-real-rollout tests drive IA A1-02/A2-01 and E9-1 through the core: assistant and absent references rejected, user reference accepted, missing forwarding rejected. Expectations: IA CASES.md A1-02/A2-01 plus pilot section 8. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/live-F1-01/rollout.jsonl`; `tests/fixtures/README.md`; pass2 adapter logs.

## 5. session_wrote_fix

**instruction-bound.** The executor's honest answer is `--session-wrote-fix`, false by default, never inferred by a helper. A station caller supplies it; the core retains it on resume (E9-14, pilot section 7).

## 6. Run date

**helper-derived.** Local `datetime.date.today()` unless `--run-date YYYY-MM-DD` supplies the caller/trial date (instruction-bound). Invalid calendar dates fail usage validation. E9 fixture runs pin 2026-09-20; core resume keeps the stored date.

## 7. The verifier capability

**helper-derived / instruction-bound.** Exactly one fresh `codex exec -s read-only -C <workspace> -c web_search=disabled --json -o <raw> -`, brief file on stdin, 900-second timeout, no model/effort override, no resume/fork, no adapter retry. The verifier helper inherits CODEX_HOME from the environment and never sets it in a command. **Codex's base instructions forbid the model repurposing `$CODEX_HOME`.** E9-20 puts the home inside the executor's writable roots. Do not set that variable to invoke this helper; use the installed environment.

CR/nested-sandbox: default home and real isolated home without a writable root exit 1, `failed to initialize in-process app-server client: Operation not permitted (os error 1)`; tmp home and real isolated home explicitly writable exit 0 and answer ok. The model-driven outer probe refused to set CODEX_HOME; that is separate from the four shell measurements. E9-20 resolves initialization availability for the control room's executor launch. This pass's additional nested seatbelt allows a session to initialize but blocks its shell tools with `sandbox-exec: sandbox_apply: Operation not permitted`; initialization does not prove read/run capability. X1-01 remains unmeasured. No workspace-write verifier fallback or retry is enabled. Containment is instruction-bound pending executed-scenario measurement; the configured read-only policy alone is not a claim of successful enforcement.

CLI events supply `thread.started`, not model/world_state. `verifier.py` uses that native thread id to find exactly one matching child rollout under inherited CODEX_HOME/sessions, cross-checks session_meta.id, captures it under scratch, and derives model plus injected channels from it. Missing/ambiguous child rollout or absent actual model after success reports lane-unavailable, which the core maps to verifier_unavailable. The helper receives no driving history. It declares nonempty world_state channel names, developer tags, base instructions and explicit path fields; CR executor records have empty agents_md (no handbook/workspace AGENTS file loaded), but host_skills catalog, permissions/environment, model/personality, managed developer and multi-agent instructions are injected. A fresh verifier's own rollout, not this executor observation, controls its returned list; live verifier validation remains with the control room.

Transport statuses: zero + nonempty raw → ok when actual-model evidence exists; zero + empty/absent raw → empty; nonzero → transport-failed; timeout → timed-out. Events/raw/call paths are single-use. No refused action is inferred merely from stderr; the core merges the report's refusals. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/nested-sandbox/`, `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/live-F1-01/rollout.jsonl`, `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/delivery-cap/rollout.jsonl`; hermetic child-record/status tests.

## 8. Delivery

**helper-derived.** Catalog entries carry the name and description prefix, not the skill body. The host catalog is 3,929 UTF-8 bytes; plugin-only 4,190. In the plain delivery and real-body probes on both surfaces no body was injected, no tool was used, and the model reported END-OF-PROBE or unavailable procedure/Gotchas. Those are zero body bytes and first missing sentinel S01, not successful body delivery. Normal implicit selection requires a file read, as CR/live-F1-01's 23,332-byte host SKILL.md tool output proves.

Explicit `$name`: host-only-delivery-explicit injects a **user** `<skill>` message, 26,038 bytes including wrapper/path, all S01–S25, no missing sentinel; host-only-real-body-explicit injects 23,531 bytes including wrapper/path, with step 8, Gotchas and References; host-only-manual-explicit injects 546 bytes. No developer message contains those bodies. Plugin-only-delivery-explicit injects nothing; one exec tool call explicitly requests max_output_tokens 20000 and returns 25,831 file bytes with all S01–S25. Do not call these tool bytes an injected prompt. There is no CR/plugin-only-real-body-explicit capture; no result is invented for it. The **8,000-byte main-prompt branch of A7b was not reached by either surface on 0.154.0 with these installs**.

One additional default-output-limit session, `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/delivery-cap`, thread `01a0a1c7-93c7-7820-96b2-69fa23e52cd1`, made one cat, no cap overrides. Its recorded tool output is 53 UTF-8 bytes of sandbox diagnostic; file bytes received **0**, last output line `sandbox-exec: sandbox_apply: Operation not permitted`, no truncation reported. This is a failed cap measurement, not a zero-byte cap. CR proves successful delivery of these body sizes when a sufficient cap is requested; the default cap remains unmeasured here. No extra session was run.

Resource recovery: CR/plugin-only-resource-recovery read the installed SKILL.md (23,332 bytes), resolved references/verifier.md under that same plugin skill root and printed READ_SUCCESS. It returned 12,992 output bytes including path/marker; this is a tool-read recovery measurement, not compaction. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/<surface>-<prompt>/rollout.jsonl`, final.md and launch.json; exact rows and ids in RESULTS.md.

## 9. Sidecars and invocation restrictions

**harness-enforced catalog filtering / instruction-bound file behavior.** recheck-v2 agents/openai.yaml has interface metadata only, no implicit-invocation restriction. With the manual-only sidecar present, manual-only-probe is absent from both catalogs. E9-5 label: **prevents catalog activation; does not stop a model that reads the file**. On both words prompts the model searched disk, read 333 file bytes, and answered PROBE-RAN. Explicit `$manual-only-probe` is recognized as host-skill injection (546 bytes); on the plugin path it injects nothing, and the model searched/read the file instead, also answering PROBE-RAN. The restriction is not an execution boundary. Evidence: `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/control-room/host-only-manual-words/`, plugin-only-manual-words/, host-only-manual-explicit/, plugin-only-manual-explicit/. Negative malformed/missing-sidecar catalog observations are recorded separately in section 10.

## 10. Negative tests

**helper-derived.** The original CR/negative-tests.log's nine rows all crashed before a session: `Not inside a trusted directory and --skip-git-repo-check was not specified.` No catalog or loader measurement resulted. The fixed driver creates and commits a fresh throwaway git workspace per trial and passes it to launch.sh; the real executor launch keeps its git check. install.sh --prepare-negative confines credential-bearing trial homes to the isolated home tree. Mutations and reinstall evidence are retained per trial; the update trial removes its host duplicate before activation.

Pass2 ran nine sessions once each. Final classifications, exact catalogs, harness messages and thread ids are in RESULTS.md and `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/negative-classifications.json`. Runtime file reads were blocked by the nested seatbelt, so catalog filtering and CLI installation observations must not be described as successful body execution. No authorization restriction is inferred from the sandbox failure.


| Negative trial | Catalog/install label | Observed limit |
|---|---|---|
| broken-delimiter | prevented activation | Loader explicitly rejects missing YAML frontmatter; manual-only-probe absent. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| duplicate-name | prevented activation | Neither manual-only copy cataloged with policy intact. Duplicate-name resolution cannot be inferred. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| malformed-sidecar | ignored | Malformed optional field loses the implicit restriction: manual-only-probe is cataloged. No loader diagnostic. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| missing-name | prevented activation | Manual-only-probe absent; intact manual-only policy also filters it, so the missing-name effect is not isolated. No loader diagnostic. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| missing-resource | ignored | recheck-v2 remains cataloged despite removed reference. Runtime missing-resource handling is blocked before the read. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| missing-sidecar | ignored | Absent sidecar leaves manual-only-probe cataloged. No loader diagnostic. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| symlink-directory | prevented activation | Manual-only-probe absent with policy intact; symlink loading itself is not isolated. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| symlink-file | prevented activation | Manual-only-probe absent with policy intact; symlink loading itself is not isolated. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |
| update-copy-symlink-copy | ignored | CLI returns exit 0 at all three stages; symlink SKILL.md silently omitted (diff 1), copy stages diff 0. Final manual-only catalog entry absent with policy intact. Runtime shell crashed with `sandbox-exec: sandbox_apply: Operation not permitted`. |

The broken delimiter also emits `missing YAML frontmatter delimited by ---`; other session stderr files are empty. CR and pass2 update-install.json both show copy/symlink/copy diff exits 0/1/0 despite plugin-add exit 0 throughout. Negative catalogs N72/N73 in RESULTS.md also contain harness-provisioned plugins; these are declared, not a clean-catalog claim.

## 11. Installed-package verification

**helper-derived.** E9-16: identity equality means equal content_sha256 **and an empty installed-package diff** (excluding __pycache__). Version and commit are recorded, never compared; host copies can be unversioned. Frontmatter and relative-reference containment/existence are checked separately. References under adapters/claude-code and adapters/opencode missing from both this lane's canonical worktree and the installed copy are reported as "absent in this lane's worktree (other lane)"; after the lanes merge, an installed omission fails. The base plugin is mandatory; host absence in this plugin-only base is expected. Verification JSON is reproduced in RESULTS.md, with the capture at `/private/tmp/claude-501/-Users-tonycoon/e5b093b2-021f-40f0-bbff-3755eba4be90/scratchpad/e9-live/codex/pass2/verify-install.json`. Shared content_sha256: ad9b596d62ec9f6e73ab90cec10b11c0d02ba6b1f23cacb3ad9655b1e16f8446. The existing core hashes the body only; package diff covers scripts/references for now (E9-16 carries the hash-scope question to E10).

## 12. Capability labels

**mixed, measured per row.** | Pilot section 13 capability | E9-11 label | Measurement / limit |
|---|---|---|
| Read workspace files | instruction-bound | CR executors read fixture records; pass2 nested shell tools fail |
| Run commands; scratch/ignored-cache writes only | instruction-bound | X1-01 not run; no read-only executed-scenario claim |
| One fresh verifier without driving history | helper-derived / instruction-bound | One fresh subprocess, no resume/fork; CR nested initialization succeeds with writable home; command containment unqualified |
| Declare injected context | helper-derived | Child thread.started → exact rollout; world_state/developer/base channels, not config guesses |
| User channel and station forwarding | helper-derived / instruction-bound | Real item map tested through IA core; caller supplies unchanged forwarding |
| Model floor | helper-derived | Observed id, provisional E9-3 map, unknown null |
| Harness/model/settings in force | helper-derived | session_meta, turn_context, token_count; absent values omitted |
| Whether session wrote fix | instruction-bound | Explicit honest flag |
| Attribute user/assistant/station | helper-derived | Native UserMessage/AgentMessage only; station output remains assistant; all other items unmapped |
| Complete body and resources | helper-derived / instruction-bound | Host explicit whole; plugin tool read whole with sufficient cap; default-cap probe blocked |
| Return caller result unchanged | instruction-bound | SKILL.md procedure; live proofs reserved to control room |
| Surface prohibited action | instruction-bound | Helper returns failures; F6-04 stopped before attribution repair, refusal proof pending |

The executor may type mode, caller, resume, target, named items and its honest authorship answer. Grants quote the user's words verbatim and use only helper-returned references. It never composes a model id, floor_met, version or attribution map. If the required facts cannot be recovered, stop and report; never drop the map or guess a value.

> **Control-room amendment (E9-21, 2026-09-14, measured with `codex sandbox`):** a second seatbelt cannot nest. A verifier launched with `-s read-only` or `-s workspace-write` initializes (E9-20) but every command it runs fails at `sandbox-exec: sandbox_apply: Operation not permitted` (exit 71). `verifier.py` therefore launches the verifier with `-s danger-full-access` and `-c approval_policy=never`; its process stays confined by the executor session's own seatbelt (workspace-write plus the isolated home plus the temp roots, network on so the child can reach the model), so containment is **harness-enforced by the outer sandbox** outside those roots and **instruction-bound** for writes inside the workspace, where the mandate forbids them and the core's boundary check catches a tracked-file edit. `launch.sh` passes `-c sandbox_workspace_write.network_access=true`, and `harness.sandbox` reads `workspace-write plus the isolated home, network on`. Evidence: the lane's scratch `control-room/nested-sandbox/variant-nested-shell-{read-only,workspace-write,danger-full-access}/`.

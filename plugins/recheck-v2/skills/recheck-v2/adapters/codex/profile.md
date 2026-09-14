# Codex CLI adapter qualification, 2026-09-14

Status: NOT QUALIFIED. Do not promote this setup. Evidence lives in `setups/codex/RESULTS.md` and the scratch paths it names. The shared core is unchanged. These helpers fail closed where the required facts cannot be recovered.

## 1. Identity

**helper-derived.** `codex --version` reports `codex-cli 0.154.0`. The installer creates `~/.local/share/skills-v2-pilot/codex/home`, copies the host skills, and installs the two probes through a local marketplace. Installing `recheck-v2@tony-skills` fails because the seam catalog does not list it. Runtime version and sandbox come from `session_meta.cli_version` and `turn_context.sandbox_policy.type`; the helper's installed location identifies plugin, host skill, or explicit path. No live activation of either surface is established. The copied config says workspace-write; this is configuration evidence, not proof of a running session.

## 2. Model and floor

**helper-derived, provisional.** E9-3 maps exactly `gpt-6-astra` to `opus`, floor_met true; every other id maps to unknown, null. `turn_context.model` supplies the actual id. `session_meta.model_provider` and integer `context_window` supply route and context; effort comes from the context's effort or collaboration settings, when present. Only observed scalar settings are emitted; absent fields are omitted, never invented. The isolated config copies `model = "gpt-6-astra"`, `model_reasoning_effort = "high"`, and `sandbox_mode = "workspace-write"`; no live session confirms those settings. Unknown capability makes the core stop `verifier_unavailable` (pilot section 14).

## 3. Run id and directory

**helper-derived.** `invocation.py` uses `os.urandom(2).hex()` for `recheck-<lowercase token>-<YYYYMMDD>-<four hex>`, with `${TMPDIR:-/tmp}/recheck-v2/<id>` outside the workspace. It creates no directory; the core's single-use check owns creation. Caller flags preserve the supplied id and resolved directory. Caller flags and target token are **instruction-bound**. A pre-existing freshly minted path is refused. No successful real-rollout invocation could be qualified here.

## 4. The user channel

**helper-derived, blocked.** Required shape: `codex:thread <id>:turn <id>`. The measured 0.154.0-compatible record stores thread_id and turn_id on the `event_msg` payload, not inside its UserMessage/AgentMessage item. Both roles use the SAME reference in the inspected record. `turns.py` rejects this collision instead of silently replacing a role. `--find` returns verbatim substring matches only for user items when attribution is unambiguous. Tool results and foreign-thread/sidechain items are excluded. Candidate (a), `lsof -p $PPID -Fn`, located the parent's open rollout; isolation is checked against CODEX_HOME. Ancestor `ps` inspection is denied inside this sandbox; absence fails exit 3. Candidate (b), notify, and (c), newest rollout by cwd, were not live-measured after the nested-launch stop. Neither is shipped as an unqualified fallback. A caller forwards a grant unchanged with forwarded_by; the helper never supplies that user claim. Real-map A1-02/A2-01 qualification is blocked. A message-id reference needs a control-room ruling; no substitute reference is emitted.

## 5. session_wrote_fix

**instruction-bound.** The executor's honest answer, `--session-wrote-fix`, defaults false; the helper never infers authorship. On caller routes the caller supplies it. The core stores it and uses the stored value on resume (E9-14 and pilot section 7).

## 6. Run date

**helper-derived** local `datetime.date.today()` unless `--run-date YYYY-MM-DD` supplies the caller/trial date (**instruction-bound**). Invalid calendar dates are usage errors. E9 trials pin 2026-09-20; the deterministic V1-01 run reports that date. The core owns resume date retention.

## 7. The verifier capability

**instruction-bound containment pending measurement; unavailable here.** One fresh `codex exec -s read-only -C <workspace> -c web_search=disabled --json -o <raw> -` receives the brief through stdin, no history, no model/effort override, with stdout and stderr captured under scratch. The helper waits up to 900 seconds, never retries, and refuses existing raw/capture paths. Status mapping: nonzero child to transport-failed, timeout to timed-out, zero with no nonempty raw to empty, zero with nonempty raw to ok only when actual-model evidence exists. Model comes from event session_meta/turn_context, never config; absent model after success is lane-unavailable. Injected path fields are read from world_state, not guessed from files that happen to exist. These channels and the actual events shape require live qualification. No refused action is inferred solely from a stderr string; the core merges the report's refusal list. The required nested probe failed at app-server initialization with Operation not permitted (os error 1). The core's no-fresh-context stop is verifier_unavailable via lane-unavailable. X1-01 was not run under read-only; workspace-write is only a proposed instruction-bound fallback requiring measurement and a ruling, never an automatic retry.

## 8. Delivery

**instruction-bound, unmeasured.** Host skill copies and the two plugin probes exist, but all model delivery probes are not run here because nested app-server initialization failed. No byte count, sentinel coverage, first missing sentinel, real-body delivery, or relative verifier.md resource-recovery outcome is asserted. Plugin and host-skill surfaces must be tested separately without duplicate activation; launch.sh accepts an isolated throwaway home through RECHECK_CODEX_HOME. Keep developer-message delivered text distinct from tool reads and model claims. No core-body truncation remedy has been applied.

## 9. Sidecars and invocation restrictions

**instruction-bound, unmeasured.** The recheck-v2 sidecar contains only interface.display_name and interface.short_description, per E9-5. There is no implicit-invocation restriction on recheck-v2. The shared manual-only probe remains unchanged. Natural-language and explicit invocation, malformed optional sidecar behavior, and the precise offered explicit invocation form have not been measured because nested sessions cannot start. Do not claim policy enforcement from a successful install.

## 10. Negative tests

**instruction-bound, unmeasured.** negative-tests.sh prepares independent isolated-home copies for malformed sidecar, missing sidecar, missing name, broken delimiter, duplicate name, missing verifier resource, symlinked SKILL.md, symlinked skill directory, and copy/symlink/copy update. It retains harness messages and leaves successful-session classification for trace inspection. All live negatives are not run here after the app-server initialization blocker. The update step registers an isolated probe marketplace, edits its source through copy/symlink/copy stages with version increments, reinstalls through codex plugin add, and retains per-install diffs. That live gate remains open. No enforced/prevented/ignored outcome is claimed.

## 11. Installed-package verification

**helper-derived.** verify-install.sh discovers the cache path, runs diff excluding __pycache__, compares frontmatter, checks resource containment/existence, and compares the exact installed/canonical skill-identity outputs. Missing plugin is a failing gate, not replaced by host-copy success. A standalone host copy has no plugin manifest or git commit; the current core reports unversioned values, so exact identity equality fails even when SKILL.md hashes match. The adapter index also points at the other lanes not yet merged at this seam. See RESULTS.md for measured JSON. No fake manifest or git metadata is added to make this pass.

## 12. Capability labels

| Pilot section 13 capability | E9-11 label | Measurement / limit |
|---|---|---|
| Read workspace files | instruction-bound | Parent can read files; child read capability not measured |
| Run commands, scratch/ignored-cache writes only | instruction-bound | read-only launch specified; X1-01 blocked before launch |
| Exactly one fresh verifier, no driving conversation | instruction-bound | One subprocess in code; nested app-server failed |
| Declare injected context | helper-derived | world_state extraction implemented; no fresh verifier record |
| User channel and caller forwarding | helper-derived / instruction-bound | Real reference collision; forwarded_by belongs to caller |
| Model floor | helper-derived | Provisional E9-3 map unit-tested; unknown is null |
| Harness/model/settings in force | helper-derived | Record fields inspected; no own live probe record |
| Whether session wrote fix | instruction-bound | Explicit flag, false default |
| Attribute user/assistant/station | helper-derived | Collision rejected; station grants forwarded, not invented |
| Complete body and on-demand resources | instruction-bound | Both delivery gates blocked |
| Return caller result unchanged | instruction-bound | Executor follows SKILL.md step 8; no live proof |
| Surface prohibited action | instruction-bound | Transport errors surfaced; no live refusal trial |

No capability is labeled harness-enforced without a completed measurement. The executor may type mode, caller, resume, target, named items, and its honest authorship answer; grants use quoted_words verbatim and only helper-returned references. It never types model ids, floor_met, harness version, or an invented attribution map. If the helper cannot provide those facts, stop and report the capability failure. Do not drop the map to make a grant pass.

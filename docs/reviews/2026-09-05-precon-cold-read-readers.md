# Precon cold read — readers (2026-09-05) — reader: Codex (gpt-5.6-sol, medium)

Source: `~/Documents/codex-relay/to-claude/2026-09-05-reader-skill-codex-take.md`, written by the Codex CLI terminal in this repo from the same brief. Unlike precon's usual zero-context reader, this one read the repo and the brief before the scope doc existed; its findings were put to Tony as Round 1 questions 9–12 and folded into the doc under precon's disposition rules. Nothing was adopted without Tony's word in the precon terminal.

## Summary (all three readers)
Three cold readers over the sitting: Codex (gpt-5.6-sol, medium) on the idea before the doc existed; then, at the exit test on Tony's word, a fresh Claude Fable subagent (57 items) and GPT-6 Astra at high effort (96 items) on the finished doc. Taken from the exit-test pair as Round 3 questions: the tracked memory file vs the plugin-cache running copy (ruled: file lives in the tony-skills checkout, written directly), what "outside" means and who enforces the word (ruled: leaves the Anthropic account; caller passes an authorized flag; one authorization = one send), Qwen in jpb's fleet (ruled: added, six boxes), the nested `codex exec` fallback (ruled moot: Tony ran the test in his Codex window, it passed with an approval caveat), and whether `/readers` is user-typed (ruled: both). Absorbed without a question: the "always the latest" wording, OpenRouter flipped to decided, the eight-in-this-build clarification, read-only vs the memory write, the definition of a reader, snapshot contents, floor enforcement, key handling, the Grok removal scope, the Gemini host-lane clarification, and the doc's self-containment (constraints inlined, transport facts copied into Research). Everything else from the pair is blueprint or architect altitude and is left downstream. Codex's take: see the disposition below; its Req.2 deprecation doubt is corrected (the binary prints a deprecation warning on launch, verified 2026-09-05).

## Disposition — Reader 2 (Claude Fable, F<n>) and Reader 3 (GPT-6 Astra, A<n>)
- surfaced (Round 3): F2, F8, F9, F35, F36, F39, F49, F56, A2, A5, A8, A23, A24, A25, A26, A27, A32, A33, A34, A35, A36, A37, A38, A87
- absorbed (doc lines or wording): F6, F12, F21, F22, F23, F30, F31, F34, F42, F51, F53, F57, A1, A3, A4, A6, A18, A20, A33, A39, A49, A62, A90, A94
- left downstream (blueprint/architect: invocation contract, packet format, status vocabulary, delimiters, snapshot format, adapters, effort mapping, access-profile grants, sandbox and network enforcement, timeouts and concurrency, capture fidelity, filename collisions, version skew, acceptance criteria, roster ids and schema): every remaining F and A item

## Disposition
- C1 extract the invocation mechanism — surfaced (Round 1 Q9, "agreed")
- C2 input access is a caller requirement — absorbed (Q7 access-profile line)
- C3 Claude is not one transport — surfaced (Q10; Tony redirected to "wrap jpb in"; open, Round 2 C)
- C4 failure disposition stays with callers — absorbed (Q7/Q9 split-of-duties line)
- C5 saving is not shared policy — surfaced (Q9; component captures raw verbatim to a caller-named path, caller does the rest)
- C6 "any shell" is an aspiration — surfaced (Q11, "agreed")
- C7 model refresh authority — surfaced (Q12, "agreed")
- R1 read-only is not packet-only — left downstream (blueprint acceptance test: sentinel outside the packet; honest instruction-only label)
- R2 fresh thread is not zero ambient context — left downstream (architect: what governs vs what is evidence)
- R3 web-search off is not network off — left downstream (per-adapter enforcement record)
- R4 nested agents multiply cost — left downstream (one invocation = one reader, no recursion; design rule)
- R5 output length is correctness — absorbed (Q8 line)
- R6 transport vs content vs validation status — left downstream (result shape)
- R7 shared deployment version skew — left downstream (architect: resolve from the installed package, never a newest-dir glob)
- R8 cross-review leakage via artifacts — left downstream (per-lane input dirs, packet hashes)
- R9 one default effort hides different work — left downstream (effort resolution: explicit / inherited / unsupported / unknown)
- Req1 interface (absolute runner path, argv arrays, stdin) — left downstream (architect)
- Req2 installed evidence — corrected (deprecation is established; see summary)
- Req3 candidate `codex exec` invocation — left downstream (blueprint; candidate, not certified)
- Req4 two permission layers, restricted network — left downstream (blueprint preflight)
- Req5 approval behaviour — left downstream
- Req6 active-writer lock unverified — parked: needs prototype (scope doc line)
- Req7 capture channels — left downstream
- Req8 result manifest shape — left downstream
- Req9 required implementation evidence — left downstream (blueprint acceptance tests)
- Rec runner + thin adapters + short wrapper — surfaced (Q9, "agreed")
- Rec JSON roster columns — left downstream (architect/blueprint schema)
- Rec mandate placement — absorbed (Q6 line)

---

## Raw take, verbatim

# Codex take on the reader component skill (2026-09-05)
Read: `AGENTS.md`, `REVIEW.md`; relevant sections of `plugins/{inspect,vertical,precon,architect,jpb}/skills/<name>/SKILL.md`; `plugins/inspect/skills/inspect/assets/inspect-mandate.md`; `plugins/jpb/skills/jpb/assets/box-runners.md`; `docs/scope/2026-09-04-agent-file-flip.md`; the relay brief; installed `codex --help`, `codex exec --help`, and official documentation linked below.

## Confusions and gaps

1. **Extract the invocation mechanism, not the five workflows.** The brief's claimed common contract is not true as written: GPT effort is not explicit in the cited recipes; Claude is not always one reader; outputs do not all live in separate reviews files. Making these uniform would change behavior, not merely remove duplication.
2. **Input access is a caller requirement.** Inspect gives outside readers numbered documents only and retains local repo-reality reviewers (`plugins/inspect/skills/inspect/SKILL.md:42-57`). Vertical supplies a tracked-code export with review history excluded (`plugins/vertical/skills/vertical/SKILL.md:41-55`). Architect supplies only the scope, deliberately excluding its architecture (`plugins/architect/skills/architect/SKILL.md:106-112`). Jpb boxes get a scrubbed brief; its judges get the boxes as well (`plugins/jpb/skills/jpb/SKILL.md:96-105,177-194`). A generic “input document + cwd” cannot express these exclusions safely without a packet/access profile.
3. **Claude is not one transport.** Inspect launches three local lenses; architect uses one tool-free-by-instruction subagent; jpb uses Workflow to pin effort for boxes and a session-model-inheriting judge (`inspect/SKILL.md:44-48`, `architect/SKILL.md:111`, `jpb/assets/box-runners.md:46-76`, paths under their respective plugin skill directories). The jpb scrubber is a separate role with its own retry rule, not automatically a reader extraction target (`jpb/SKILL.md:67-76`). Specify which call sites migrate.
4. **Failure disposition must stay with callers.** Inspect re-asks when a lane fails (`inspect/SKILL.md:38`); vertical drops it and completes local review (`vertical/SKILL.md:60`); jpb needs three valid boxes and treats Judge K failure as fatal, Judge G failure as survivable (`jpb/SKILL.md:109-111,196-200`); architect retries only on Tony's word (`architect/SKILL.md:113`). No generic retry/fallback loop.
5. **Saving is not shared policy.** Inspect's Claude lane saves no raw file; vertical appends a run to the existing build review; precon adds dispositions above raw output and has a pre-repo staging home; architect has per-lane collision suffixes and its special HTML-unescape rule; jpb writes a composite product exercise in `docs/` or `_ideas/` (`inspect:60`, `vertical:72-78`, `precon:85`, `architect:113-114`, `jpb:135-149`, all SKILL.md). Return an artifact; let the caller file it.
6. **“Runnable from any shell” is currently an aspiration.** MCP tools and Claude Workflow are host capabilities, not executables a portable script automatically owns. Decide whether v1 offers host adapters plus portable CLI/API lanes, or builds new CLI adapters for every lane. Report an unavailable adapter honestly; never silently replace Claude with GPT because Codex is the caller.
7. **Model refresh authority conflicts with automatic central updates.** Pins change only on Tony's word. A roster update must be an approved change with an immutable per-run snapshot; discovery may suggest a successor but cannot switch it. Define whether the default changes future runs globally or only an explicitly selected role (`jpb/SKILL.md:50-63,87-89`; `inspect/SKILL.md:36`).

## Risks

1. **Read-only is not packet-only.** A working directory chooses a root; it does not prove the process cannot read other readable host files. Inspect's claim that an outside reader has no repository access needs an enforced read boundary or an honest instruction-only label. Its Qwen recipe already admits this (`inspect/SKILL.md:57`). Test access to a harmless sentinel outside the packet; don't infer isolation from `-C` or an empty directory.
2. **Fresh thread is not zero ambient context.** Global/project instructions, installed skills, memory, MCP tools, hooks, environment, and parent directories can contaminate a fresh invocation. Vertical's tracked export can itself carry instruction files. Define which instructions are evidence and which may govern execution; an authored document must not be promoted wholesale into authoritative instructions.
3. **Web-search disabled is not all network disabled.** Browser/search tools, shell HTTP requests, MCP connections, and inference API traffic are distinct channels. Store the actual enforcement and limitations for each adapter. A parity string records a claim; it does not establish the claim by itself.
4. **Nested agents multiply cost and failure points.** Loading a skill does not create an independent reader. Keep dispatch deterministic: one authorized invocation produces one reader, not a new orchestration agent that loads the skill again. No recursive skill calls in the child, no automatic delegation, bounded deadline/concurrency, and cancellation of the entire child process tree.
5. **Output length is a correctness issue.** The existing DeepSeek 8,000-token limit can exhaust itself in reasoning (`inspect/SKILL.md:56`; `jpb/assets/box-runners.md:26-29`). Represent input window, output budget, and effort separately. Reject oversize input before sending; classify truncated output as incomplete even if text exists. Never summarize or truncate the packet to make it fit silently.
6. **Transport success and valid task output are separate.** Gemini can return empty SUCCESS or useful ERROR output; jpb additionally demands its box validator. Return transport status, content status, and validation status separately. Preserve partial text as diagnostic evidence without calling it a completed review.
7. **Shared deployment creates a wider failure radius.** Independently installed caller plugins can see different reader versions. `AGENTS.md` says the checkout is not the running copy. Define protocol compatibility and dependency resolution; reject an incompatible version before sending. Never choose an installed version by an unqualified newest-directory glob. Resolve assets from the actual installed package, not `~/Developer/tony-skills`.
8. **Cross-review leakage can happen through artifacts.** Use separate input directories per lane, and keep output/logs outside every reader's input tree. Preserve packet hashes and source revision so concurrent edits cannot change what a reviewer actually read. Exclude credentials; never log keys or full environment dumps.
9. **One default effort hides materially different work.** Jpb pins Claude box effort high but inherits the session model for Judge K; Gemini encodes effort in the model ID; several GPT recipes omit effort. Model and effort resolution must distinguish explicit, inherited, unsupported, and unknown. Never claim a confirmed actual model from the model's own self-description.

## Requirements for a Codex caller

1. **Interface:** a short skill under the chosen installation supplies an absolute runner path; Codex invokes it using the shell with a versioned request file or stdin. The script resolves sibling assets relative to itself. No dependency on shell aliases, interactive startup files, Claude-only environment variables, or a particular checkout path. Pass subprocess argv as an array; feed document bytes through stdin/files, never through generated shell source or `eval`.
2. **Installed evidence:** this machine reports `codex-cli 0.153.4`. Its help supports `-m`, `-c`, `-s read-only`, `-C`, `--skip-git-repo-check`, `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--json`, and `-o`; top-level `-a never` is available. `mcp-server` is still listed. The brief's deprecation claim was not established by this check; availability does not disprove deprecation.
3. **Candidate invocation, not a certified isolation recipe:**

```sh
codex -a never exec --ephemeral --ignore-user-config \
  -m gpt-5.6-sol -c 'model_reasoning_effort="high"' \
  -c 'web_search="disabled"' -s read-only \
  --skip-git-repo-check -C "$reader_input_dir" \
  --json -o "$reader_output_dir/response.md" - \
  < "$reader_request_file" > "$reader_output_dir/events.jsonl" \
  2> "$reader_output_dir/stderr.log"
```

Here `high` is an example requiring the agreed role policy, not an assertion that existing GPT callers already use it. Directories and request are prepared by the parent. Keep applicable managed policy; do not add sandbox bypasses. Ignoring user config does not prove that all ambient instructions, hooks, project configuration, and skills are absent.
4. **Two permission layers:** the parent shell's sandbox controls the runner's network and filesystem access; the child's read-only sandbox controls model-generated shell commands. The child cannot grant itself access the parent denies. This session explicitly has restricted network, so OpenAI/OpenRouter/Gemini traffic and even loopback Ollama connectivity must not be presumed available. If required access is denied, the caller needs the host's scoped approval path or returns `permission_denied`; never toggle the child to full access as a workaround. Output directories must be parent-writable even though the reviewer is read-only.
5. **Approval behavior:** unattended readers should fail a denied action instead of waiting invisibly for user input. Use an explicit noninteractive approval policy supported by the installed version. Authentication/runtime setup may itself need access beyond the packet; `--ephemeral` suppresses session rollout persistence, not every runtime write. Even CLI help here printed a PATH-alias permission warning.
6. **Active-writer lock:** plain `codex exec` is the intended fresh-invocation route; do not use `resume`, `--last`, `fork`, or route work into the caller's active thread. A shared cwd is not evidence of sharing a thread. I have not reproduced nested execution or established how this installed daemon handles inherited session metadata, so “no active-writer lock” is NOT a verified guarantee. Acceptance must launch a fresh child while the parent remains active, record a distinct child thread identity when exposed, and verify both complete. Do not guess environment-variable fixes or resume the parent as a fallback.
7. **Capture:** use `-o` for final response bytes, JSONL for execution events, stderr for diagnostics, and a separately generated result manifest. The official [non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) documents these channels and ephemeral execution. An output file alone is not proof of success: require terminal completion, non-empty content, and the caller's validation. Never send JSONL chatter to a verdict parser or save stale output from an earlier attempt.
8. **Result shape:** `{protocol_version, run_id, lane, adapter_version, requested_model, reported_model, model_evidence, effective_effort, packet_hash, status, failure_kind, exit_code, response_path, response_hash, diagnostics_path, policy_evidence, duration_ms, billed_usd}`. Unknown actual model/cost stays null. Keep raw response separate and immutable; apply banners, HTML decoding where explicitly required, and dispositions only through the caller's documented presentation policy. Jpb's public doc must still omit token counts (`jpb/SKILL.md:115-118`).
9. **Required implementation evidence:** validate schema/unsupported effort before send; simulate empty, truncated, malformed, rate-limited, timed-out, cancelled, and useful-text/error-status results; test quoted/backtick input and collision-safe saves; test sibling-output and out-of-packet access; test fresh nested execution under actual parent permissions. No nested model run was performed for this review because the brief allows only this reply file to be written.

## Recommendation

Build one versioned runner with thin host adapters and a short skill wrapper; keep prompts, lane selection/authorization, packet assembly, validation semantics, retry decisions, adjudication, and publication in the five callers, because those differences are the product's guarantees.

**Roster:** use validated JSON with one row per lane/adapter combination: `lane_id`, `provider`, `transport`, `adapter_id`, `required_host_capabilities`, `default_model`, `model_policy`, `effort_encoding`, `default_effort`, `supported_efforts`, `context_limit`, `output_budget`, `timeout`, `auth_env_names`, `endpoint_policy`, `supported_access_profiles`, `tool_policy`, `web_policy`, `isolation_strength`, `success_guard`, `normalization`, `billing_mode`, `minimum_runtime_version`, `verified_at`, and `quirk_refs`; this makes capabilities executable and explicit while leaving role and run policy outside the roster. Keep exceptions in tested adapter code, not arbitrary shell command strings in JSON.

**Mandate placement:** default to a trusted mandate at the top of the prompt followed by clearly delimited source documents treated as evidence, because that is portable across the existing lanes and avoids promoting document instructions into authority; use a provider's supported higher-priority instruction channel only for trusted mandate text when the adapter explicitly guarantees it. Record this choice as a semantic migration from MCP `base-instructions`, not exact parity. Do not blindly map it to Codex `model_instructions_file`: the official [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) describes that key as replacing built-in instructions.

Freeze the resolved roster, access policy, adapter/protocol version, mandate hash, and packet hash before launching; then a later model update changes future authorized runs without rewriting the evidence for past ones.

---

# Reader 2 — Claude Fable, fresh `general-purpose` subagent (2026-09-06, exit test)

Read the finished scope doc only (`docs/scope/2026-09-05-readers.md`), read-only, no other input. Zero context supplied. Disposition follows the raw output below, after triage with Tony.

## Raw output, verbatim

1. Line 3, "capture the output verbatim" vs line 13 "verbatim raw capture to a caller-named path" vs line 10 "under the kit's `docs/reviews/` date-topic naming". Three phrasings of where raw output lands: caller-named path, or a fixed `docs/reviews/` convention, or both. A builder needs to know whether the caller supplies the full path, a topic slug the component expands, or nothing. Question: who computes the filename, and what happens if the caller's path is outside `docs/reviews/`?

2. Line 3, "One component skill, `readers`" with "slash command `/readers`" (line 6), but the split-of-duties bullet (line 13) describes `readers` as something callers summon programmatically. It is unclear whether `/readers` is ever typed by Tony directly, and if so what a bare invocation does (which lane, which mandate, which documents). Question: is `/readers` a user-facing command, a skill-to-skill call, or both, and what does a direct invocation look like?

3. Line 3, "run it read-only against a fixed mandate plus the input documents" and line 13 "callers keep their mandate, packet assembly". "Fixed mandate" suggests the component owns it; "callers keep their mandate" says the caller does. Question: does `readers` carry any default mandate text at all, or is the mandate always caller-supplied?

4. Line 3, "so the script half runs from any harness with a shell (Codex today, others later)". The doc never says what "the script half" is written in, where it lives inside the plugin, or how a non-Claude harness would discover and invoke it (Codex has no plugin cache). Question: what language and invocation path does the runner script have, and how does Codex find it?

5. Line 7, "roster details ... live in a script or table the skill carries". "Script or table" leaves the roster's format undecided (code, YAML, Markdown table). Builders need one format because the snapshot rule (line 20) and the last-pick memory file (line 26) both need to reference roster rows. Question: is the roster data (a file the script reads) or code (rows inside the script)?

6. Line 7, "confirm all 7" and line 13 "constraint g". Constraints a through g are referenced throughout but never restated in this doc; they live in the brief (line 38). A builder reading only this doc cannot verify the decisions against the constraints. Question: can the seven constraints be inlined or summarised here?

7. Line 8, "the Claude lane spawns a subagent, never a same-context read" vs line 29, "with the caller's access profile ... either inheriting the session model or pinned to a named one". A subagent that inherits the session model still inherits nothing of the session's context, but the doc does not say whether the subagent is allowed to receive the caller's earlier findings or conversation summary as part of the packet. Question: is anything other than mandate + documents ever allowed in the packet for the Claude lane?

8. Line 9, "An outside lane sends only on Tony's word in the calling run". Which lanes count as "outside"? Line 30 introduces Claude rows pinned to Fable/Opus; those are Claude but not the session. Question: does a pinned-Claude row need Tony's word, or is "outside" strictly GPT/Gemini/DeepSeek/Qwen?

9. Line 9 vs line 13. Line 13 says "lane authorization" is the caller's duty, line 9 says an outside lane sends only on Tony's word. It is unclear whether `readers` enforces the word itself (refuses to run without a flag) or trusts the caller to have asked. Question: is there an authorization token or flag the caller passes, and does `readers` refuse without it?

10. Line 10, "raw output filed verbatim before any triage". For the Claude subagent lane, "verbatim" is fuzzy: does the whole subagent transcript count, or only its final message? Question: what exactly is the raw capture for a subagent lane?

11. Line 11, "The runner script carries the portable lanes ... the skill body carries the host lanes". The doc says a harness without a host lane reports "lane unavailable", but not how the skill body and the script agree on one roster or one status format when they are two different artifacts. Question: is there one roster file both read, or two rosters that must be kept in sync?

12. Line 11, "Gemini via its MCP" and line 33 "Gemini is already native via the antigravity MCP". The antigravity MCP is a Claude Code MCP; from Codex there is no Gemini lane. Line 33 also says "each get a native transport". Question: is a Gemini CLI or API transport needed for Codex, or is Gemini permanently a Claude-host-only lane?

13. Line 12, "the deprecated `codex mcp-server` entry retires; removing it from `~/.claude.json` is a per-machine close-out step". This is a change outside the repo, and line 13 says nothing about what happens to callers that still reference the MCP during the transition. Question: does any caller keep a reference to `codex mcp-server` until the close-out, or is it a hard cut in the same PR?

14. Line 13, "the empty-response guard". Only the GPT lane (via codex exec) is known to have an empty-response failure mode from context elsewhere; the doc does not say whether the guard applies to every lane or what counts as empty (zero bytes, whitespace, a refusal). Question: what is the empty-response rule per lane?

15. Line 13, "no-web parity". Never defined. It presumably means every lane is denied web access, but Gemini via antigravity and Claude subagents have web tools available. Question: what does no-web parity concretely require per lane, and what happens when a lane cannot be denied web?

16. Line 13, "it returns a status the caller acts on". The status vocabulary is never listed (ok, empty, truncated, lane-down, unauthorized, oversize). Question: what are the status values and their exact meaning?

17. Line 13, "failure policy (re-ask, drop, fatal, retry-on-word)" is the caller's. But line 19 says the runner "marks truncated output incomplete" and "rejects oversize input". Whether these are statuses returned to the caller or actions the runner takes on its own is unclear. Question: does the runner ever retry, or only report?

18. Line 14, "Workspace / access profile (starved, packet-only, whole repo)" alongside line 30 "the repo-with-tools access profile". That is four profile names for what reads like three or four profiles; "whole repo" and "repo-with-tools" may or may not be the same. Question: what is the full, named list of access profiles and what each grants per lane?

19. Line 14, "the three documented inversions (jpb starves, inspect feeds the packet only, vertical feeds the export)". "Feeds the export" is never explained. Question: what is vertical's export, and is it a document in the packet or a workspace path?

20. Line 15, "Lane roster at v1" lists five lanes, but line 28 adds Fable and Opus rows, and line 30 introduces signoff/wargame/recheck with an Opus-or-better floor. The v1 roster count is ambiguous: five, seven, or more. Question: what is the exact v1 roster with row names?

21. Line 15, "DeepSeek (always the latest), Qwen (always the latest)" vs line 24, "'Always the latest' ... means a row bump on Tony's word ... never run-time resolution". The parenthetical in line 15 reads as run-time, line 24 says it is not. Contradiction resolved only by line 24; the phrase in line 15 should be adjusted or a builder will implement it wrong. Question: confirm line 24 governs.

22. Line 16, "Qwen and DeepSeek ride OpenRouter — assumed". This is marked assumed, not decided, yet line 33 restates it as decided ("DeepSeek and Qwen stay on OpenRouter"). Question: is OpenRouter decided or still an assumption; and where does the OpenRouter API key live and how does the runner find it on each machine and in Codex?

23. Line 17, "any future skill that adds an outside reader too" and line 32 "any skill that brings in a reader, outside or fresh Claude". Line 17 scopes the rule to outside readers, line 32 widens it to fresh Claude subagents. A subagent used for a non-reading task (a search) might trip the wider rule. Question: what distinguishes a "reader" subagent from any other subagent under the invariant?

24. Line 18, "The mandate rides at the top of the prompt with the documents delimited below it as evidence". The delimiter format is unspecified, and whether the same packet layout applies to non-GPT lanes is not stated. Question: is the packet layout one format for all lanes or per-lane?

25. Line 18, "never mapped to Codex's instructions-file setting". A builder needs to know whether that means no AGENTS.md is read by the nested `codex exec` at all (which would require a flag or a bare working directory), or just that the mandate is not placed there. Question: does the runner suppress Codex's own instruction-file loading, and how?

26. Line 19, "The DeepSeek output budget is in scope". Only DeepSeek is named, but Qwen, GPT and Gemini also have windows and output caps. Question: does the budget tracking apply to every lane, and where do per-lane limits come from (roster row or hardcoded)?

27. Line 19, "effort" is tracked separately. Effort is a Claude/Codex notion; DeepSeek and Qwen via OpenRouter have reasoning parameters that differ. Question: how does an effort setting map per lane, and what happens when a lane has no effort knob?

28. Line 20, "every run snapshots the roster it used so past evidence never rewrites". Where the snapshot is written (inside the raw output file, alongside it, or in a log) is not stated. Question: what is the snapshot format and location?

29. Line 21, "One lane per call". Line 29 says "inspect's three lenses become three calls". If three calls each write a `docs/reviews/` date-topic file, naming collisions on the same day/topic are possible. Question: how do multiple same-day, same-topic calls avoid overwriting each other?

30. Line 23, "All callers convert in this build" vs line 30, "blueprint sequences them after the five with outside lanes today". "All eight in this build" and "the three come after the five" are consistent only if "this build" spans multiple slices; a builder should not read line 30 as deferring the three. Question: are signoff, wargame, recheck definitely in this build's acceptance, not a follow-up?

31. Line 24, "the actual newest OpenRouter ids for Qwen and DeepSeek — parked: needs research (Tony looks them up before /blueprint)" while line 39 says "Open: none". A parked research item with a named owner and a deadline before the next step is an open item by any reading. Question: has the lookup happened, and what are the ids?

32. Line 25, "the component remembers that pick per lane and suggests it at the next ask instead of the roster row". Who does the asking? Line 13 gives lane authorization to the caller, so the "ask" happens in the caller; but the memory lives in `readers`. Question: does `readers` expose a "suggest" function the caller invokes before asking Tony, or does `readers` itself prompt Tony?

33. Line 25, "remember 3.8 as my previous selection". "3.8" is a model version with no vendor named; unclear which lane the example refers to. Question: which lane was this example about, and is the memory keyed on lane or on model family?

34. Line 25 vs line 20. A remembered pick is a run-time selection that differs from the roster row, and line 20 says roster changes never happen mid-run. Both can hold, but the snapshot (line 20) must then record which was used. Question: does the snapshot record the roster row, the remembered pick, or both?

35. Line 26, "The last-pick memory is a tracked file in the repo". Since the running copy is the plugin cache (per the repo's CLAUDE.md, but even the doc itself says commit, PR, and plugin update), a write at run time goes to the cache copy, not the checkout. A file written in the cache is not tracked and is overwritten on the next plugin update. Question: which physical file does the runner write, and how does that write reach the checkout for the commit?

36. Line 26, "a pick reaches the other Mac only after commit, PR, and plugin update, which Tony accepts". Every pick would then require a PR, which contradicts the spirit of line 25 (a lightweight remembered suggestion). Question: is a memory-only change allowed to ship without the normal review gates, and who opens that PR?

37. Line 27, "`box-runners.md` and its recorded traps retire into the component's roster and adapters". "Adapters" is a new term not used anywhere else; it is unclear whether adapters are the per-lane code in the runner script or something separate. Question: what is an adapter, and is it the same thing as a roster row's transport?

38. Line 27, "scrub, the box validator, the three-valid-boxes rule, and the verdict stay in jpb" and line 29 "jpb's scrubber is not a reader". But jpb's "boxes and judges route through readers". The judge stage presumably reads the scrubbed boxes; whether the judge packet is assembled by jpb or by readers is not stated. Question: for jpb judges, who assembles the packet of scrubbed box outputs?

39. Line 28, "jpb's box fleet runs on the remaining five boxes (Fable, Opus, GPT, Gemini, DeepSeek)". Qwen is in the roster (line 15) but missing from the box fleet. Question: is Qwen deliberately excluded from jpb, and if so why does a roster lane not automatically become a box?

40. Line 28, "amended by Tony's Grok ruling below". The Grok ruling is in the out-of-scope section (line 37), not "below" as a decision. Minor, but a builder may hunt for a missing paragraph. Question: is any part of the Grok ruling other than "drop it" still load-bearing?

41. Line 29, "effort pinned via the Workflow route jpb committed". The "Workflow route" is unexplained; it references something in jpb not described here. Question: what is the Workflow route, and does it work for non-jpb callers?

42. Line 29, "either inheriting the session model or pinned to a named one" combined with line 30 "the component honours the Opus-or-better floor". If the session model is below Opus and the caller is signoff, it is unspecified whether the component refuses, upgrades, or asks. Question: what happens when the inheriting row violates a caller's floor?

43. Line 30, "their own SKILL.md rules travel as the caller's mandate". A whole SKILL.md as mandate is very different in size from a short mandate; the budget rules (line 19) may reject it. Question: is the full SKILL.md text sent, or an extract?

44. Line 30, "the repo-with-tools access profile they hand it". A Claude subagent with tools can write. Line 10 says "Read-only always". Question: is repo-with-tools a read-only tool set, and how is write denial enforced for a subagent?

45. Line 31, "grep of all 21 SKILL.md files" gives the evidence for eight callers, but the AGENTS.md summary in the repo says twenty-one skills across twenty plugins. `/ship`, `/build`, `/blueprint` and `/handoff` all spawn subagents today in some form; the doc asserts they bring in no reader. Question: what was the grep criterion that excluded `/ship` (which chains signoff and recheck)?

46. Line 32, "A new repo invariant lands in `AGENTS.md`". The invariant wording is paraphrased, not given. Question: what is the exact sentence to add?

47. Line 33, "each get a native transport and a prompting guide, the way the Codex plugin ships one". Where the guides live (a file in `plugins/readers/`, a reference in the skill body) and whether the guide is injected into the prompt or only read by the author are unspecified. Question: is the prompting guide runtime content or documentation?

48. Line 33, quoted "do the same for Gemini and Grok ... instead of using OpenRouter for them". Gemini was never on OpenRouter in this doc (line 11 has it on the MCP from the start), so "instead of OpenRouter" does not apply to Gemini. Question: was Gemini ever on an OpenRouter row, and is anything else implied by "the same"?

49. Line 34, "Whether a nested `codex exec` trips Codex's active-writer lock ... parked: needs prototype" while line 39 "Open: none". Second parked item that is functionally open and could invalidate the GPT lane design from line 18 ("no MCP fallback row"). Question: if the prototype fails, what is the fallback, given the MCP row is explicitly excluded?

50. Line 38, "Codex cold take (gpt-5.6-sol, medium ...)" and the disposition file path. Several decisions cite "Codex C1..C7, R5, Rec" by label; none of those labels are explained here. Question: can each cited Codex item be summarised inline so the decision is legible without the review file?

51. Line 38, brief at `~/Documents/handoffs/...`. This is a machine-local, untracked path; a builder on the laptop or in Codex may not have it. Question: should the brief's transport table and property facts be copied into the repo?

52. Whole doc: no acceptance criteria, no definition of done. The only test-like statements are line 19 (budget rules) and line 34 (prototype). Question: what observable behaviour proves the build is complete, per caller?

53. Whole doc: no mention of secrets handling for OpenRouter beyond nothing. The repo is public (AGENTS.md invariant). Question: where do API keys live, what env var names, and does the runner refuse to run when the key is absent versus reporting lane-down?

54. Whole doc: cost and rate limits for outside lanes are not mentioned (DeepSeek/Qwen/GPT per-call spend, concurrency across three inspect lenses). Question: is there any spend guard or concurrency limit?

55. Whole doc: the Gemini "quirks" (line 7 lists quirks as a roster column) and the known `agy` workarounds in the antigravity MCP are not connected. Question: does the roster row for Gemini carry the `--add-dir`, empty-response, and stdio traps, or does the MCP own them?

56. Whole doc: no statement about what `readers` does when a caller passes a lane not in the roster, or a model id not in the roster but typed by Tony (line 25 implies typed picks are allowed). Question: does a typed model id bypass roster validation, and is it validated against the provider before sending?

57. Line 3, "Sitting began 2026-09-05" and the doc title date. No version or status line for the doc itself; with two rounds plus a close-out folded in, later readers cannot tell whether the doc reflects the final state. Question: is this the final precon output or a mid-sitting snapshot?

---

# Reader 3 — GPT-6 Astra, reasoning effort high, codex MCP (2026-09-06, exit test)

Sent on Tony's word in the precon terminal ("do a astra on high read"), overriding the brief's reservation of this model. Parameters: `model: "gpt-6-astra"`, `base-instructions` = the cold-reader mandate, `prompt` = the scope doc text, `sandbox: "read-only"`, `cwd` = a fresh empty scratch directory, `config: {"web_search": "disabled", "model_reasoning_effort": "high"}`, `approval-policy: "never"`. Parity line: `web_search: disabled`. Thread id 01a0770b-3492-7b73-ba12-cb69932705e7. The harness backgrounded the call past its foreground limit; the response arrived complete. Disposition follows the raw output below, after triage with Tony.

## Raw output, verbatim

1. “Open: none”
The document still contains assumptions and two explicitly parked questions, so a builder cannot tell whether it is ready for implementation.
Question: Does “none” mean no unresolved product decisions, or are all assumptions and parked items considered nonblocking?

2. “Qwen and DeepSeek ride OpenRouter — assumed”
Transport determines authentication, supported parameters, model availability, and error handling.
Question: Is OpenRouter approved for both lanes, or must that assumption be confirmed before building?

3. “All callers convert in this build” / “blueprint sequences them after the five”
The final caller set is eight, but the migration commitment is marked assumed and the later sequencing statement does not explicitly define the release boundary.
Question: Must all eight callers be converted before this build is complete?

4. “Tony looks them up before /blueprint” / “Next: /blueprint when ready”
The newest model IDs are a stated prerequisite without a recorded result or readiness condition.
Question: What exact information must Tony supply before blueprint can begin?

5. “Whether a nested `codex exec` trips Codex's active-writer lock” / “blueprint's acceptance test”
A parked compatibility question could invalidate the required GPT transport in a named target harness.
Question: Is a successful nested execution prototype a prerequisite to implementation, and what happens if it fails given the prohibition on an MCP fallback?

6. “Round 1 Q2 ‘confirm all 7’” / “the brief” / “Codex cold take”
Several decisions rely on external material that this document does not reproduce, leaving the authoritative requirements uncertain.
Question: Is this scope self-contained, or which referenced documents remain normative when implementing it?

7. “One component skill, `readers`”
The document specifies ownership but not how another skill invokes the component or receives its result.
Question: What is the invocation contract for both a calling skill and a shell-only harness?

8. “plugin folder `plugins/readers/`, slash command `/readers`”
A direct slash command is named, but only caller-mediated use is described.
Question: What must a standalone `/readers` invocation accept, ask for, and return?

9. “The body stays short”
“Short” has no acceptance criterion and may conflict with documenting host adapters, authorization, and invocation behavior.
Question: Is there a size limit or a required division between the skill body and supporting documentation?

10. “a fixed mandate plus the input documents” / “callers keep their mandate”
It is unclear whether readers adds a fixed universal mandate or simply executes a caller-supplied mandate unchanged.
Question: Which instructions are fixed by readers, which are supplied by the caller, and which take precedence?

11. “callers keep their mandate, packet assembly”
The packet’s input representation and validation rules are not defined.
Question: Does readers receive document text, file paths, structured entries, or some combination, and what makes a packet valid?

12. “One lane per call … — assumed”
The basic execution cardinality remains an assumption despite callers needing fleets and multiple lenses.
Question: Is one lane per call now a firm contract, including for jpb and inspect?

13. “lane, transport, default model, effort, quirks”
The distinction between a lane, roster row, model choice, and transport is unclear once Claude has several rows and remembered model overrides.
Question: What uniquely identifies a lane and a roster row, and which properties may vary within each?

14. “a new model is one row”
This promise appears broader than the implementation split, since a model on a new transport could require adapter and guide work.
Question: Is one-row addition guaranteed only for models compatible with an existing adapter?

15. “roster details … live in a script or table”
The authoritative roster format and its relationship to host-lane behavior are not settled.
Question: Do portable and host lanes share one authoritative roster, and what information is required in every row?

16. “quirks” / “its recorded traps retire into the component's roster and adapters”
The document does not say which quirks are executable requirements versus advisory notes.
Question: Which existing traps must become enforced behavior, and which remain documentation?

17. “the script half runs from any harness with a shell”
The portability claim does not specify operating systems, shell dialects, installed runtimes, or required binaries.
Question: What environments and dependencies must v1 support, and does “any harness” assume a configured `codex` CLI and API credentials?

18. “the skill body carries the host lanes”
Host-lane execution depends on harness capabilities that are not enumerated.
Question: Which hosts must support Claude and Gemini in v1, and what exact host interfaces are required?

19. “A harness without a host lane gets an honest ‘lane unavailable’”
The boundary between absent capability, misconfiguration, unsupported model, and temporary failure is unspecified.
Question: Which conditions count as unavailable rather than failed, and what information must the report include?

20. “the frontier lanes (GPT, Gemini) each get a native transport”
“Native” could mean provider-owned APIs, provider tooling, or the already selected integrations.
Question: Do `codex exec` and the antigravity MCP fully satisfy this requirement, or is additional transport work intended?

21. “a prompting guide, the way the Codex plugin ships one”
The referenced example is not included, and the guides’ contents and operational role are undefined.
Question: What must each guide cover, and is it documentation for callers or instructions readers automatically applies?

22. “callers keep their mandate” / “a prompting guide”
Lane-specific prompting could change the caller’s requested task, creating an unclear ownership boundary.
Question: May readers rewrite or augment mandates for a model, or must guides leave the supplied mandate unchanged?

23. “An outside lane sends only on Tony's word in the calling run”
“Outside” is not defined consistently with the later inclusion of all fresh Claude readers.
Question: Which lanes require explicit send authorization, including session-inheriting and pinned Claude subagents?

24. “only on Tony's word”
The acceptable evidence of authorization is unspecified.
Question: What constitutes authorization: a natural-language statement, a caller-supplied flag, a named model selection, or something else?

25. “in the calling run”
The lifetime and scope of authorization are unclear for multiple calls, resumed runs, and nested callers.
Question: Does authorization cover one attempt, one lane, a named fleet, or every reader call within that run?

26. “callers keep … lane authorization”
Readers is required not to send without authorization, but the enforcement responsibility appears to remain with callers.
Question: Does readers validate authorization itself, or trust the caller to have obtained it?

27. “failure policy (re-ask, drop, fatal, retry-on-word)”
The wording leaves uncertainty about automatic transport retries and whether they constitute another authorized send.
Question: Are any retries permitted inside readers, and when is fresh authorization required?

28. “when Tony names a model at a lane ask”
Callers own authorization while the component owns remembered suggestions, but ownership of the actual ask is unspecified.
Question: Who presents the lane/model question and records its answer?

29. “the component remembers that pick per lane”
The memory key becomes ambiguous when one Claude lane has session-inheriting, Fable, and Opus rows.
Question: Is memory indexed by transport lane, roster row, named model family, or caller?

30. “automatically suggest that, not what's set in the skill”
A suggestion is not necessarily an execution default, and unattended invocation behavior is unstated.
Question: If the caller supplies no model, does readers use the remembered pick, return it as a suggestion, or require a choice?

31. “when Tony names a model” / “remembers that pick”
The event that commits a selection to memory is undefined.
Question: Is a pick remembered immediately, after authorization, after sending, or only after a successful response?

32. “the last-pick memory is a tracked file in the repo”
The target repository is ambiguous when readers is installed as a plugin and runs against another project.
Question: Is memory stored in the tony-skills source repository, the installed plugin, or the reviewed project?

33. “Read-only always” / “the component remembers that pick”
Remembering a selection requires a write, so the scope of the read-only guarantee needs an explicit boundary.
Question: Does read-only apply only to the reader process, with orchestration writes to memory and review artifacts allowed?

34. “a pick reaches the other Mac only after commit, PR, and plugin update”
The document specifies propagation but not who performs the version-control and installation steps.
Question: Does readers only edit the memory file, or is creating commits or PRs part of its behavior?

35. “Studio and the laptop share one memory”
Concurrent or divergent selections can produce conflicting tracked state.
Question: Which pick should prevail when both machines change the same lane before synchronization?

36. “the roster row is the fallback when nothing is remembered”
A remembered model may later disappear, become incompatible, or violate a caller’s model floor.
Question: What happens when remembered state exists but is no longer usable?

37. “‘Always the latest’ … means a row bump on Tony's word” / “suggests [the remembered pick] … instead of the roster row”
A roster update may never affect suggestions once a lane has remembered state.
Question: Is it intentional that an older remembered selection continues to outrank a newly approved “latest” model?

38. “Roster changes are approved changes … never a mid-run switch” / “when Tony names a model”
An explicitly named model may override the roster without a roster PR, making the approval boundary unclear.
Question: May Tony select any compatible model for an individual run, and how does that differ from a roster change?

39. “every run snapshots the roster it used”
A roster snapshot alone may not identify the model actually used when memory, explicit choices, or session inheritance override it.
Question: Must the snapshot also capture the effective model, effort, overrides, and selection source?

40. “never a mid-run switch”
The word “run” could refer to one readers call or an entire caller workflow containing multiple calls.
Question: Must all calls in one caller workflow use the same frozen roster and memory state?

41. “fresh Claude subagent, GPT … Gemini … DeepSeek … Qwen”
Only some model selection policies are described, and exact initial identifiers are absent.
Question: What are the initial model IDs and default effort settings for every row, including GPT and Gemini?

42. “always the latest qwen model” / “always the latest deepseek”
“Latest” does not identify a family, capability tier, release channel, or variant.
Question: Which releases qualify as the desired latest model for each provider?

43. “Claude rows pinned to a named model (Fable, Opus)”
The names do not establish exact executable identifiers or whether they are aliases.
Question: What model IDs do Fable and Opus map to, and does “pinned” prohibit moving provider aliases?

44. “either inheriting the session model or pinned to a named one”
Session inheritance may not resolve to a Claude model in a non-Claude host.
Question: Where is session inheritance supported, and what should happen when the parent session is not Claude or its model is unknown?

45. “‘Fresh’ is real … never a same-context read”
A newly spawned subagent can still receive inherited conversation, instructions, memory, or workspace state.
Question: Exactly what context must be excluded to qualify as fresh, and what host-provided context is allowed?

46. “shared ‘cold outside read’”
The explicit freshness guarantee covers Claude, but equivalent isolation requirements for the other transports are unstated.
Question: Must every lane start a new conversation without prior session state, and how is that verified?

47. “effort pinned via the Workflow route jpb committed”
The required route is referenced but not defined in this document.
Question: What invocation mechanism and exact effort values constitute the committed Workflow route?

48. “model id, effort” / “tracks input window, output budget, and effort separately”
Effort can have different meanings or support across providers.
Question: What effort values does the interface accept, how are they mapped per lane, and what happens when a requested value is unsupported?

49. “the component honours the Opus-or-better floor”
No ordering or eligibility test is supplied for “better,” particularly across model families.
Question: Which models satisfy this floor, and what should readers do if an explicit or remembered choice falls below it?

50. “Workspace / access profile (starved, packet-only, whole repo)” / “repo-with-tools”
The later profile introduces an additional name without defining whether it is an alias or a fourth profile.
Question: What is the complete set of supported access profiles and their exact permissions?

51. “jpb starves, inspect feeds the packet only, vertical feeds the export”
These descriptions do not define what the reader can actually access beyond the supplied text.
Question: What files, directories, tools, environment data, and inherited instructions are accessible under each of these three arrangements?

52. “whole repo”
The repository boundary is unclear for untracked files, ignored files, nested repositories, symlinks, and files outside the root.
Question: What exactly counts as accessible repository content?

53. “repo-with-tools” / “Read-only always”
Tool access can include commands with filesystem, network, or other side effects.
Question: Which tools and operations are permitted, and is read-only technically enforced or merely instructed?

54. “read-only against a fixed mandate plus the input documents”
The scope of read-only behavior toward credentials, configuration, caches, and user files is unspecified.
Question: Must a reader be prevented from reading unrelated local data as well as from modifying it?

55. “sandbox”
The scope assigns sandbox ownership without specifying required isolation or what to do when a host cannot enforce it.
Question: What sandbox guarantees are mandatory for each lane, and must readers refuse execution when they cannot be provided?

56. “no-web parity”
“No web” could prohibit browser search only, all reader-initiated network access, or provider-side retrieval features too.
Question: What precisely is prohibited, and what counts as equivalent enforcement across the five transports?

57. “the documents delimited below it as evidence”
Delimiters identify evidence but do not define how embedded instructions or delimiter-like content are treated.
Question: Must all document content be treated as untrusted evidence, and what behavior is required if it contains instructions conflicting with the mandate?

58. “the mandate rides at the top of the prompt”
A prompt-top mandate may still be subordinate to CLI defaults, project instructions, or host configuration.
Question: Which ambient instructions and configuration may apply to a reader run, especially for starved and packet-only profiles?

59. “a semantic migration … not exact parity”
The accepted differences from MCP `base-instructions` are not enumerated.
Question: Which behavior changes are acceptable, and what tests establish that the migration preserves the intended cold-read task?

60. “never mapped to Codex's instructions-file setting”
The prohibition names one placement mechanism but leaves the rest of the `codex exec` invocation unspecified.
Question: What CLI version, flags, prompt-input mechanism, and configuration dependencies are required?

61. “Gemini via the antigravity MCP”
The server, tool contract, supported model controls, and output shape are not included.
Question: What exact MCP capability does the adapter target, and how are freshness, effort, access, and raw capture expressed through it?

62. “DeepSeek and Qwen … via API”
Authentication and provider-routing requirements are absent.
Question: How are credentials supplied, which OpenRouter routing choices are allowed, and are any provider-side fallback or model-substitution behaviors prohibited?

63. “the DeepSeek output budget is in scope”
The detailed budget guarantees are introduced as DeepSeek-specific but then attributed to “the runner.”
Question: Do input-limit checks, output budgets, and truncation detection apply to every lane or only DeepSeek?

64. “tracks input window, output budget, and effort separately”
The sources and units of these limits are unspecified.
Question: Where do model limits come from, what units are exposed to callers, and does the input window reserve capacity for output and reasoning?

65. “rejects oversize input before sending”
Exact size accounting depends on the model tokenizer and on prompt overhead outside the packet.
Question: What content is counted, how is it counted for each lane, and what happens when reliable preflight counting is unavailable?

66. “output budget”
No ownership, default, override rule, or acceptable range is stated.
Question: Is the output budget set by the caller, roster, or adapter, and who wins if those sources disagree?

67. “marks truncated output incomplete”
Truncation can result from provider limits, CLI output limits, transport interruption, or normal-looking premature completion.
Question: Which signals establish truncation, and how should readers report uncertain completeness?

68. “never silently truncates a packet to fit”
The behavior after rejection and the information returned to the caller are undefined.
Question: What measurements and limit details must an oversize-input response include, and are all automatic packet modifications prohibited?

69. “the empty-response guard”
“Empty” is not defined across textual, structured, refusal, tool-only, or reasoning-only responses.
Question: Which response forms count as empty, and does the guard merely report failure or perform another action?

70. “it returns a status the caller acts on”
No status vocabulary, output schema, or shell exit-code contract is specified.
Question: What statuses exist, what fields accompany them, and how do host and shell invocations expose the same result?

71. “the lane-down report”
The report’s contents and distinction from other failures are undefined.
Question: How are authentication failures, rate limits, missing dependencies, refusals, invalid models, timeouts, and provider outages classified?

72. “callers keep … failure policy”
Readers still needs defined behavior while a process hangs or a user cancels.
Question: Who sets timeouts, how is cancellation propagated, and what status and partial artifacts remain afterward?

73. “a caller wanting several lanes makes several calls”
The document does not say whether concurrent calls are supported despite fleet-based use.
Question: May calls run concurrently, and what limits or guarantees apply to shared memory, roster snapshots, output paths, and host resources?

74. “capture the output verbatim”
Different transports expose final text, reasoning, tool events, metadata, and diagnostic streams.
Question: Which parts constitute the raw reader output for each lane?

75. “verbatim raw capture”
The required fidelity is unclear when decoding API strings, assembling streamed chunks, or normalizing line endings.
Question: Does verbatim mean exact response bytes, exact generated text, or an unchanged transcript of selected fields?

76. “raw output filed verbatim before any triage”
The point at which capture becomes durable is unspecified, especially for streaming or interrupted runs.
Question: Must partial output be preserved as it arrives, and what happens if output capture fails after a successful model response?

77. “under the kit's `docs/reviews/` date-topic naming” / “to a caller-named path”
The caller’s authority to name a path may conflict with the required directory and convention.
Question: Is the path constrained to a particular kit root and naming pattern, and which rule takes precedence for an invalid path?

78. “the kit's”
A cold reader cannot identify whether “kit” means the reviewed project, the calling skill’s repository, or tony-skills.
Question: How is the artifact root selected when readers runs against a different repository or with no repository?

79. “date-topic naming”
The convention does not specify timezone, topic normalization, lane suffixes, retries, or collision handling.
Question: What exact filename rule applies, and may an existing review ever be overwritten?

80. “every run snapshots the roster it used”
The snapshot location, format, retention, and relationship to raw output are unstated.
Question: What snapshot artifact is required, and must it also be created for unavailable lanes or rejected inputs?

81. “so past evidence never rewrites”
This states an archival guarantee without specifying what information is necessary to interpret a past run.
Question: Must evidence retain the mandate, packet or packet identity, access profile, adapter version, and actual model identity in addition to the roster?

82. “raw output filed verbatim” / “scrub … stays in jpb”
The relationship between immutable raw capture and caller-side sanitization is unclear.
Question: Does scrub act before sending, after capture, or both, and are unredacted outputs always retained even if they contain sensitive data?

83. “signoff, wargame, and recheck … their own SKILL.md rules travel as the caller's mandate”
A whole skill may contain orchestration, write operations, or instructions to summon readers rather than only a review mandate.
Question: Does “their own SKILL.md rules” mean the complete file or a defined subset, and how are incompatible or recursive instructions handled?

84. “inspect's three lenses become three calls”
The lenses and their required execution relationship are not specified here.
Question: What mandate and packet does each lens receive, and must each be isolated from the other lenses’ outputs?

85. “jpb wraps in fully: boxes and judges route through readers”
Boxes are enumerated, but judge models, profiles, effort, and invocation behavior are not.
Question: Which jpb calls are boxes versus judges, and what readers parameters must each supply?

86. “remaining five boxes (Fable, Opus, GPT, Gemini, DeepSeek)” / “three-valid-boxes rule is unchanged”
Readers-level success or incompleteness may not align with jpb’s existing validity decision.
Question: Which reader statuses make a box eligible for validation, and does an unavailable or incomplete box affect how jpb obtains its three valid boxes?

87. “Qwen … via API” / “remaining five boxes”
Qwen is in the component roster but excluded from the named jpb fleet.
Question: Is that exclusion intentional, and is the fleet fixed or may Tony select Qwen as a replacement box?

88. “`box-runners.md` and its recorded traps retire into the component's roster and adapters”
“Retire into” does not specify whether the old file is deleted, retained as documentation, or replaced by references.
Question: What must happen to that file, its links, and each recorded trap before migration is complete?

89. “Every skill that summons an outside reader routes through `readers`”
The intended behavior-preservation standard for migration is not stated.
Question: Which existing caller behaviors must remain unchanged, and what constitutes acceptance for each of the eight conversions?

90. “any skill that brings in a reader, outside or fresh Claude”
The boundary between a reader, a judge, a scrubber, and another subagent is only illustrated by individual decisions.
Question: What general definition determines whether a future subagent must route through readers?

91. “A new repo invariant lands in `AGENTS.md`”
It is unclear whether this is solely an instruction or an enforceable repository requirement.
Question: Is adding the rule sufficient, or must this build also include checks for caller-owned transports and bypasses?

92. “the other thirteen skills bring in no reader”
The complete-caller claim is tied to a past grep without a revision or broader definition of indirect invocation.
Question: Which repository revision is the migration baseline, and must scripts or references outside SKILL.md also be checked?

93. “removing it from `~/.claude.json` is a per-machine close-out step on Tony's word”
The timing and completion criteria are ambiguous, particularly if other consumers still use the deprecated entry.
Question: Must both machines be cleaned up for this build to count as complete, and what verification is required before removal?

94. “Grok, on any transport — abandoned” / “the native xAI research and the OpenRouter row both go”
The removal scope is unclear for historical research versus active runtime configuration.
Question: Does “go” mean delete active references only, or also remove existing research artifacts and history-facing documentation?

95. “All callers convert in this build” / “plugin update”
The new shared dependency introduces installation and version-compatibility requirements not described in the scope.
Question: How do callers locate readers, what happens when it is missing or outdated, and must callers and the component be released together?

96. “Next: /blueprint when ready”
Beyond the active-writer prototype, the document does not define overall acceptance criteria.
Question: What evidence must demonstrate correct authorization, isolation, model selection, budget handling, failure reporting, verbatim capture, and all eight caller migrations before signoff?

---

# Reader 4 — Codex (gpt-6-astra, high) review of the finished scope doc (2026-09-06)

Source: `~/Documents/codex-relay/to-claude/2026-09-06-readers-doc-review-codex.md`, written by Tony's Codex CLI terminal in this repo after the gate closed, relayed by the orchestrator. Put to Tony as Round 4 (reopened on his "wait" for this pass). Disposition: pushbacks 1, 3, 4, 5, 6 surfaced as Round 4 questions; pushbacks 2 and 7 absorbed as wording and record corrections; the "Blueprint must not miss" list left downstream with a pointer in the scope doc's Research line; the parked-ids remark is moot (ids ledgered on Tony's "1 yes" before this review arrived).

## Raw take, verbatim

# Codex review of the readers scope doc (2026-09-06)
Read: `docs/scope/2026-09-05-readers.md`; all of `docs/reviews/2026-09-05-precon-cold-read-readers.md`; `AGENTS.md`; `REVIEW.md`; relevant model-floor, independence, and verification sections of `plugins/{signoff,recheck,wargame}/skills/<name>/SKILL.md`; the relay brief and this conversation's actual nested-exec/configuration results. Line numbers below refer to the scope doc unless another path is named.

## Honored or not

- **Mechanism only — partially honored:** L13 says “callers keep their mandate, packet assembly, lane authorization, failure policy (re-ask, drop, fatal, retry-on-word), and post-processing” and specifies “verbatim raw capture to a caller-named path”; that delivers the split, but L10's blanket filing rule still contradicts it.
- **Honest portability — honored:** L11 says “The runner script carries the portable lanes” and “A harness without a host lane gets an honest ‘lane unavailable’, never a silent substitute”; L33 explicitly excludes a new Gemini CLI/API adapter, so this is now a bounded implementation promise.
- **Approved roster updates plus snapshots — honored, with a freeze boundary still needed:** L20 says “Roster changes are approved changes (a PR on Tony's word, never a mid-run switch); every run snapshots the roster it used”; L36 additionally records overrides and effective model/effort, so the adoption was not reduced to a version label.
- **Mandate placement — honored:** L18 says “The mandate rides at the top of the prompt with the documents delimited below it as evidence” and “a semantic migration … not exact parity”; the instructions-file prohibition preserves the exact distinction I requested.

## Still pushing back on

1. **Filing remains contradictory.** L10: “raw output filed verbatim before any triage, under the kit's `docs/reviews/` date-topic naming.” L13: “verbatim raw capture to a caller-named path.” Existing precon/architect have pre-repo staging paths, vertical appends, jpb has its composite artifact, and inspect's Claude lane has no raw file. Say whether L10 now deliberately adds a new raw artifact to every call, or is subordinate to each caller's existing filing policy; without that ruling, two builders can implement opposite behaviors and both cite a decided line. My preference remains caller-owned persistence policy, with readers providing capture to the supplied destination.
2. **Moving the entire skill into the mandate would break the extraction.** L30: “their own SKILL.md rules travel as the caller's mandate.” Whole skills contain orchestration, questions, ledger writes, and—after this migration—calls to readers itself. Require caller-owned reviewer mandates containing only the assigned review task and its evidence rules, not the full orchestrator instructions; otherwise the child either recursively invokes readers, attempts forbidden writes, or receives instructions it must disobey. Recheck's actual reader contract is already narrowly specified at `plugins/recheck/skills/recheck/SKILL.md:34`.
3. **The tracked-memory decision lacks a coherent read/sync path.** L26 says a pick reaches the other Mac “only after commit, PR, and plugin update”; L40 says the file “lives in the tony-skills checkout at a fixed path and is written there directly by the runner.” If readers reads the checkout, the other Mac needs a checkout update; updating an installed plugin alone does not establish that. If it reads the cache, the local write need not affect the next ask. Keep Tony's chosen tracked storage, but declare that suggestions read that same checkout file and specify checkout synchronization; also define behavior when the checkout is absent/unwritable without silently writing into the reviewed repo or plugin cache.
4. **Unknown model overrides cannot bypass the floor or parameter checks.** L41: an unlisted ID “is sent as-is and remembered”; L37: a choice “below the floor is refused”; L40: a remembered choice below the floor “is dropped with a note.” Provider acceptance proves neither model eligibility nor effort support. An unknown model on a floor-bound caller must return an eligibility failure until classified, and discarding a stale suggestion must happen before authorization—not silently select another model after the user has authorized the run. Define memory keys by selectable row/role where needed: jpb's pinned Fable and Opus boxes must not both turn into the last selected Claude model.
5. **Read-only must not silently turn verification into static reading.** L34: “the model gets no write, no tools beyond its access profile”; L30 promises “repo-with-tools.” Recheck explicitly requires a reviewer that “must be able to run things” (`recheck/SKILL.md:34`), and signoff distinguishes executed verification from static analysis (`signoff/SKILL.md:90`). Tests commonly produce caches/artifacts. Preserve the read-only decision, but specify how callers obtain allowed execution evidence or report verification blocked; do not mark a reproduction checked when sandbox restrictions prevented it. Any decision to allow fixture writes is a scope amendment, not a hidden adapter convenience.
6. **Authorization wording can accidentally add an ask to every local review.** L42: “Claude rows, inheriting or pinned, never need the word”; L43: callers summon readers “still asking Tony for the lane first.” Make L43 defer to the caller's existing ask policy: a mandatory local signoff/recheck reader should not gain a new lane question. Define L42's “one authorization is one send” as one named logical reader invocation; one approved fleet may authorize its enumerated calls, while a replacement/retry needs fresh authorization. Do not count each internal model turn in a tool-using review as a new reader authorization, or the repo-with-tools lane becomes unusable; do not hide another completed/uncertain reader attempt behind SDK retries either.
7. **The nested-test record overclaims what was measured.** L44: “A nested `codex exec` does not trip Codex's active-writer lock” and “stayed read-only.” This session observed one successful fresh child, with the startup banner reporting read-only; its single-word task did not test write denial. The first failure was `failed to initialize in-process app-server client: Operation not permitted`, not an observed network error. The same line calls the setting “account-wide”; I changed this Mac's user config and explicitly said it does not sync to other machines or change the active session. Record these limits; otherwise blueprint inherits a false isolation/network baseline and an unproven unattended guarantee.

## Blueprint must not miss

These are required acceptance criteria in this build, not optional follow-up work:

- **Isolation and usable verification, before caller rollout:** a lane/access-profile matrix with actual enforcement or explicitly accepted limitations; fresh context; no sibling-output exposure; no reader writes; no reader-initiated web access, separated from inference transport access. Test harmless out-of-packet/sibling sentinels and a write attempt, plus a representative repo verification that reports honestly when execution is blocked. An empty cwd, a read-only banner, and a parity sentence are not substitute evidence. Carry first-take R1–R3/R8 into this slice.
- **One request/result contract and minimum roster schema:** stable row/adapter IDs, protocol version, supported access profiles, model/effort resolution and floor eligibility, input/output limits, timeout, and explicit unsupported states. Both host and portable lanes must use it. Separate transport failure, incomplete/empty content, capture failure, and caller validation; test Gemini useful-text/error-status, budget exhaustion, denied access, and cancellation. Preserve raw final text independently of logs, and never treat a stale file as a fresh result. This is R5/R6/R9 and Req7–Req9, not a demand for every column in my original suggested manifest.
- **Durable per-invocation evidence with a workflow-wide freeze:** record caller run ID, row/override source, requested/effective model and effort, adapter/protocol version, input/mandate identity, access policy evidence, terminal status, and raw-output identity before triage. Freeze selection inputs for a caller's whole run, so jpb's boxes/judges or inspect's multiple calls cannot observe intervening memory/roster changes. Use collision-safe capture and atomic memory updates even on one Mac; Tony ruling out simultaneous cross-Mac picks does not prevent concurrent local calls.
- **Installed dependency compatibility:** resolve the actual installed readers package and check the caller's supported protocol before sending. Demonstrate missing/old component behavior and a real installed-package run, not merely the checkout script. Document which updates reach the Studio/laptop runtime versus their memory checkout. This is first-take R7 and is essential once eight separately installed callers depend on one component.
- **Eight caller contracts, not eight textual replacements:** give each migration slice examples showing preserved packet exclusions, model floors, finding scope, failure disposition, and filing rules after the scope contradictions above are settled. Include inspect's outside paper/local repo split, jpb's six distinct boxes and asymmetric judge failure, vertical's surviving local review, and recheck's closed checklist. Re-run the nested child with the *actual runner flags and effective parent auto-review setting*; require successful authorized execution and a denied case that terminates cleanly without a fallback send.

**Can wait:** a comprehensive model-ranking system (an explicit eligibility list plus rejection of unknown floor-bound choices is sufficient), a generalized plugin dependency manager (an explicit version check/install procedure is sufficient), and rich telemetry beyond the evidence above and jpb's already-required billing fields. None justifies postponing isolation, compatibility checks, or failure semantics. L24's “parked: needs research (Tony looks them up before /blueprint)” is still a named prerequisite despite L49 “Open: none”; identify the initial Qwen/DeepSeek rows before treating those adapter requirements as executable.

## The nested-exec caveat

The Codex caller should request the host's scoped approval for the exact runner invocation when parent restrictions block startup or inference transport; “Approve for me” may review that request automatically, but the runner must not alter global permissions or weaken the child's read-only policy. Resume after a pre-send denial only when approval is actually granted; an explicit denial, unavailable approval path, or uncertain prior send returns a structured status to the caller, with no blind resend or transport fallback. Blueprint must test this in a session actually using auto-review, because the observed success used explicit escalation approval and proved neither automatic approval nor that network was the initial blocker.

# /vertical — cold read — 2026-08-21

Readers: local Claude subagent (zero context) · GPT (gpt-5.6-sol via codex MCP, web search disabled) · DeepSeek (deepseek/deepseek-v4-pro via OpenRouter, run on Tony's explicit word — not a standard precon reader; see SKILL NOTE in the sitting report).

## Summary — what was taken, what was left behind

All three readers converged on the same load-bearing themes. Disposition of every theme, with which readers raised it:

| Theme | Readers | Disposition |
|---|---|---|
| Outside reviewers told to review "against its base" but never given the base — cannot tell new code from old | all three | **surfaced** — Round 2 Q1; Tony ruled: give them the boundary (base commit + what the vertical touched), cold-on-verdicts still holds |
| "Nothing unverified lands in the verdict" vs raw model sections verbatim in the same doc | all three | **absorbed** — scope doc now defines the verdict as the merged top section; raw sections are a labeled unverified appendix |
| Stop-and-ask every run vs a standing default answer — which wins on silence | all three | **absorbed** — clarified: the skill always asks and waits; "default" is only the recommended option in the ask, silence never proceeds |
| Is the per-run choice strictly local-only vs local+both, or can one outside model be picked | local, GPT | **absorbed** — assumed: Tony answers free-form, any subset is a legal answer |
| Does "full code" include secrets (.env, credentials, gitignored files) | GPT (secrets/excerpts), local (exclusions) | **absorbed** — assumed: secrets and gitignored files are never exposed to outside models; full code means tracked source |
| Outside transport fails mid-run (codex error, agy denial) — abort or continue | local, GPT | **absorbed** — assumed: continue with survivors, record the drop with reason (jpb's recorded pattern); local Claude always runs |
| What "adversarially verify" requires; verification bar; confidence scale; severity definitions; pass/fail verdict rules | all three | **left downstream** — /signoff already defines the verify doctrine (CONFIRMED/PLAUSIBLE, severity→verdict mapping); the scope doc's "signoff shape" lines inherit it; blueprint altitude |
| How the skill locates the build doc, slice list, signoff/recheck status, target repo | all three | **left downstream** — the loop's existing conventions (build doc, status cards, /ship's discovery) answer this; blueprint altitude |
| Dedup criteria, repeats/misses handling at merge | all three | **left downstream** — /signoff's merge rules (dedup on file:line + claim, convergence noted) carry over; blueprint altitude |
| Same-day rerun / output filename collision / overwrite behavior | all three | **left downstream** — blueprint altitude |
| Repo state reviewed (dirty worktree, commits vs working tree, mid-run changes) | local, GPT | **left downstream** — /signoff's union-scope rules carry over; blueprint altitude |
| Exact prompts, parity configs, MCP payloads, invocation syntax, gate-override wording | all three | **left downstream** — recorded in jpb's SKILL.md; blueprint reads it; blueprint altitude |
| Non-interactive / CI invocation | DeepSeek, GPT | **absorbed** — assumed: interactive only, like every other loop skill |
| "Open: (none)" while many lines are assumed | local, GPT | **noted, no change** — assumed-with-why is the precon ledger's designed state, not an open item; blueprint treats assumed lines as revisable |
| Definitions of slice/vertical/build for a cold reader | all three | **left downstream** — defined by the loop's existing docs; the skill is not self-contained by design |

## Local Claude reader — verbatim

**Unclear or ambiguous**

- "Vertical" itself is never defined. The doc says the review target is "the whole vertical against its base" but never says what a vertical is (a feature branch? a repo? all slices of one build doc?) or what "its base" means (base branch? base commit? the state before slice 1?).
- "Claude reviewing at full scope" is vague. Full scope of what — the whole repo, or only files the build touched? Line 17 says outside models see "the FULL code," but it never says whether Claude's own review is also whole-repo or diff-bounded.
- The per-run ask (line 15) says Tony picks "local-only review, or local + ChatGPT + Gemini" — two options. But the models decision (line 14) says "ChatGPT + Gemini only," leaving unstated whether "local + ChatGPT only" or "local + Gemini only" are legal answers, or whether it is strictly the two named bundles.
- "Default answer to the per-run ask is local + both" (line 16): unclear what a default means for a question the skill always stops to ask. Does silence pick the default? Does Tony have to answer every time? "One-word reversal at any run" is not explained.
- Line 24 says Claude "adversarially verifies every outside finding" and "nothing unverified lands in the verdict" — but line 25 says the doc includes "every model's raw section verbatim below." So unverified findings do land in the doc, just not in the merged section. What "lands in the verdict" means needs a sharper boundary (verdict = top section only?).
- What "verify" means for an outside finding is undefined. Reproduce it? Confirm the file:line exists? Re-derive the failure scenario? The bar decides how expensive a run is.
- Line 26: Claude "uses [prior verdicts] at merge to spot repeats and misses." Unclear what happens to a "repeat" (a finding already fixed in a prior slice cycle — dropped? flagged?) or a "miss" (something a prior signoff caught that no one re-found — is that surfaced, and as what severity?).
- The finding shape includes "confidence" (line 23), but nothing says how confidence is assigned, on what scale, or whether Claude's verification overrides the outside model's stated confidence.
- Output filename `docs/vertical-signoff-<date>.md` (line 25): no rule for two runs on the same day, and it's unclear whether a re-run overwrites, appends, or creates a second doc.
- "The target repo" (line 25) is assumed but never established: how does the skill identify the target repo and the build doc? Cwd? An argument? Line 27 implies the skill can enumerate slice signoff/recheck status — where does it read that status from?
- Line 21 pins specific models ("gpt-5.6-sol", "gemini-3.1-pro-high") "with jpb's parity configs" — everything about what those transports and parity configs are lives in another file (`~/.claude/skills/jpb/SKILL.md`) that a builder must read; the scope doc is not self-contained on the single most operational decision.
- Line 22: "codex works in the checkout; antigravity needs --add-dir" — unclear whether the outside models review the working tree as it currently sits (possibly with uncommitted junk) or a specific commit/branch, and whether the two harnesses could end up reviewing different states of the code.
- Line 26 says outside reviewers get "the build doc (the spec) and the full code." Do they also get the base to diff against (per line 13, the review is "against its base"), or must they judge the whole codebase with no way to tell new code from pre-existing code? Reviewing "the vertical against its base" while receiving no base information seems hard to execute as written.
- "Stops at the verdict; never fixes anything itself" (line 18) vs. the existing loop's /recheck: unstated whether vertical findings feed back into recheck, a new fix cycle, or nothing — what state is the build in after a failing verdict?
- Is there a pass/fail verdict at all? The doc says "verdict doc" but never defines what constitutes passing, or what severity mix blocks calling the build done.
- Cost is cited as the reason to exclude DeepSeek (line 30), but no cost bound, token budget, or repo-size limit is stated for the two models that are included — "full code" on a large repo could be enormous.

**Questions I'd need answered before building**

1. Define "vertical" and "base" operationally: exactly what code range and what reference point the review compares against.
2. How the skill locates the build doc, the slice list, and each slice's signoff/recheck status (file conventions? naming? where recheck records live).
3. Is the per-run choice strictly binary (local-only vs. local+both), or can one outside model be picked?
4. What does "adversarially verify" an outside finding require — existence check, reproduction, or judgment call — and what happens to findings that fail verification (dropped silently, listed as rejected, kept in raw only)?
5. What exactly do the outside models receive as the review prompt: build doc + which files, any diff/base info, any severity rubric, any instruction on the finding template?
6. What does the merged verdict conclude with — a pass/fail ruling, a severity-gated recommendation, or just a list?
7. Same-day re-run behavior for the output file, and whether a re-run after fixes is in scope at all.
8. What happens when one outside transport fails mid-run (agy denial, codex error) — degrade to local-only, retry, or abort? (Notable because nothing in the doc addresses partial failure.)
9. What repo state is reviewed — HEAD of a branch, the working tree, a specific commit — and is it required to be clean/committed first?
10. Does "full code" have any exclusions (secrets, .env, vendored deps, large assets), and is there a size ceiling before the run is refused or trimmed?
11. Where do the per-slice prior verdicts come from for the merge step, and what is done with repeats and misses once spotted?
12. Is "confidence" reviewer-reported or Claude-assigned, and on what scale?

**Internal contradictions**

- Line 24 ("nothing unverified lands in the verdict") vs. line 25 (raw model sections included verbatim in the same doc): unverified content does reach Tony in the deliverable; the two lines conflict unless "verdict" is defined as only the top section.
- Line 13 says the review target is "the whole vertical against its base" (a delta framing), while lines 17 and 31 rule out diff disclosure and mandate full code with no base given to outside reviewers — as specified, the outside models cannot review "against a base" they never see. Not strictly irreconcilable, but the two decisions pull against each other and the doc never resolves how.
- Line 15 says the skill "stops to ask" every run (framed as Tony picking per run), while line 16 establishes a default answer — a mandatory stop-and-ask with a standing default is at minimum in tension; which behavior wins when Tony says nothing is unspecified.
- Minor: the doc's own status lines conflict in spirit — "Open: (none)" and "Next: /blueprint when ready" — while at least four load-bearing mechanics above (verification bar, base handling, failure handling, output collision) are marked "assumed" rather than decided. Nothing is listed as open, yet several assumptions are decisions Tony has not actually made.

## GPT (gpt-5.6-sol) — verbatim

### 1. Unclear or ambiguous

- "Build," "slice," "vertical," "base," and "target repo" are not defined. It is unclear how their boundaries or identities are established.
- "Against its base" is ambiguous: the base could mean a branch, commit, specification, blueprint, deployed version, or repository state.
- The authoritative "build doc (the spec)" is not identified, nor is the relationship between a build doc and a blueprint explained.
- The skill is described as running after "every slice" is signed off and rechecked, but there is no stated source of truth for:
  - the complete slice list;
  - each slice's signoff;
  - each slice's recheck;
  - whether those artifacts correspond to the code currently checked out.
- "Claude reviewing at full scope" and "Claude runs its own /signoff-style review" leave the exact reviewing agent/model unclear.
- "ONE big review" is unclear because the process appears to contain three separate reviews followed by another verification pass.
- "Full code" is undefined for monorepos, generated files, vendored dependencies, submodules, ignored files, untracked files, large binaries, multiple repositories, and code outside the checkout.
- "Local-only" is not explicitly defined. It presumably means Claude alone, but that is not stated.
- "Local + ChatGPT + Gemini" does not clarify whether the three reviews run independently, concurrently, or in a sequence that may expose one reviewer's results to another.
- "COLD" is only partially defined. The outside models do not receive prior verdicts, but it is unclear what other repository context, conversation history, tool configuration, or persistent harness state they may see.
- "Prior verdicts" is ambiguous: per-slice signoffs, rechecks, previous vertical runs, or all of these.
- "Uses them at merge to spot repeats and misses" does not explain what counts as a repeat or a miss.
- "Adversarially verifies every outside finding" does not define verification or the evidence needed for a finding to survive.
- It is unclear whether Claude's own findings undergo the same verification standard as outside findings.
- "Merges" and "dedupes" are undefined when findings differ in severity, confidence, location, claimed cause, or failure scenario.
- The meaning of the final "verdict" is unspecified. The possible verdict states and the criteria for each are not given.
- Severity levels are named but not defined.
- Confidence is required but its format or scale is unspecified.
- "Raw section verbatim" is ambiguous when model output is malformed, extremely long, contains tool logs, includes source excerpts, or lacks the requested finding structure.
- The expected behavior when an outside reviewer fails, times out, cannot access the repository, returns no findings, or uses the wrong model is unstated.
- The expected behavior when only one outside reviewer succeeds is unstated.
- The transport and model requirements are inherited from `/jpb`, but the relevant contract is not present in this scope document. The scope therefore depends on mutable external instructions.
- "Parity configs" and "refresh procedures" are referenced but not defined.
- It is unclear whether pinned model names are strict requirements or preferred defaults.
- The document does not clarify whether `/vertical` is intended only for one machine/user or should be portable.
- The output filename has date-only granularity. The identity of multiple runs on the same date is unclear.
- It is unclear what happens if the output file already exists.
- It is unclear whether the output document itself is considered the verdict or whether only its top section is "the verdict."
- "Tony can collapse the gate in the invocation ('run it anyway')" does not define the exact accepted invocation or whether free-form equivalent wording counts.
- It is unclear whether bypassing the prerequisite gate must be recorded in the verdict.
- The order of the opening choice and prerequisite validation is unclear.
- The handling of a dirty worktree or code changes occurring during the review is unspecified.
- There is no statement about tests, build commands, static analysis, runtime reproduction, or whether review is code-reading only.
- There is no stated standard for deciding that the entire repository has actually been inspected.
- "Research: none yet" makes it unclear whether the referenced sibling skills and transports have been validated or merely assumed to exist as described.

### 2. Questions requiring answers before building

1. What exactly identifies the build being reviewed?
2. How is the complete set of slices determined?
3. Where are slice signoff and recheck statuses recorded?
4. How should the skill prove those statuses apply to the current code revision?
5. What exactly is the review base, and how is it selected?
6. Where is the authoritative build specification located?
7. What happens if the specification is absent, ambiguous, or conflicts with the code?
8. What files and repositories constitute the "whole vertical"?
9. Are untracked, ignored, generated, vendored, binary, submodule, and external-directory contents included?
10. What does "local-only" include?
11. Which Claude model or execution environment performs the local review?
12. Are reviewer model pins mandatory, and what should happen if they are unavailable?
13. What exact `/jpb` configuration is part of `/vertical`'s required behavior?
14. How is reviewer coldness established or checked?
15. What context may outside reviewers receive besides the specification and repository?
16. What context may Claude receive before conducting its own review?
17. Does Claude review independently before reading any prior or outside verdicts?
18. Are the three reviews concurrent or sequential?
19. What constitutes a verified finding?
20. Are Claude's findings verified by the same process?
21. How are conflicting findings, severities, and confidence assessments reconciled?
22. What makes two findings duplicates?
23. What constitutes a "miss" discovered from prior verdicts?
24. Can a prior finding enter the final verdict if none of the current reviewers finds it?
25. What are the definitions of BLOCKER, MAJOR, and MINOR?
26. What format and scale should confidence use?
27. What are the possible overall verdicts?
28. What exact conditions produce each verdict?
29. Does any verified severity automatically prevent signoff?
30. Does an incomplete reviewer run prevent a verdict?
31. What happens when ChatGPT or Gemini fails, times out, or lacks repository access?
32. What happens when an outside model returns malformed or noncompliant output?
33. Does "raw verbatim" include all prose, tool output, and incorrect findings?
34. How should potentially sensitive source excerpts or secrets in raw output be handled?
35. Must the final document distinguish verified findings from rejected outside findings?
36. Are rejected findings documented anywhere?
37. Which prior verdict artifacts does Claude receive?
38. How are prior verdicts located and associated with the current build?
39. What exact wording or syntax authorizes "run it anyway"?
40. At what point is the local-versus-outside-review question asked relative to gate validation?
41. What happens if the user does not answer the opening question?
42. Is "local + both" an actual default that may execute without an explicit answer, or merely the recommended selection?
43. What happens if the date-named output already exists?
44. How are multiple runs, reruns, and superseded verdicts distinguished?
45. Which revision identifiers and repository state must be recorded?
46. What happens if files change while reviewers are running?
47. Are tests or executable checks part of verification?
48. What are the completion and failure criteria for the skill itself?
49. Is the skill allowed to create only the verdict file, or are logs and temporary artifacts also expected?
50. Which of the assumptions must be promoted to confirmed decisions before implementation?

### 3. Internal contradictions or tensions

- The document says "Open: (none)," but much of the required behavior is explicitly marked "assumed," including paths, transports, model pins, finding format, verification doctrine, and output format. These are unresolved implementation requirements despite the claim that nothing is open.
- "Every run opens by stopping to ask" conflicts with describing "local + both" as a default unless it is clarified whether silence can trigger that default. A mandatory stop for a choice and an automatically usable default imply different interaction behavior.
- "Nothing unverified lands in the verdict" sits uneasily with placing every model's raw findings verbatim in the same "verdict doc." Unverified findings do land in the document, even if not in its top verdict section.
- "ONE big review" conflicts in ordinary wording with three independent reviews plus a Claude verification/merge pass. The intended singular unit is unclear.
- Outside reviewers receive the "FULL code," but `/antigravity` is described as requiring `--add-dir`. That does not establish what "full" includes or guarantee equal scope between the two outside reviewers.
- The review target is "the whole vertical against its base," while outside reviewers are described as receiving the spec and full code, "not just a diff." It is unclear how they review "against its base" if the base itself is not explicitly included.
- The skill "never fixes anything itself," yet it is expected to write a verdict document into the target repository. This is not necessarily a substantive conflict, but "stops at the verdict" and "never fixes anything" need a clear distinction between permitted output writes and prohibited code changes.
- The scope calls the trigger point "decided," but also permits the user to bypass it with "run it anyway." Thus it is a default gate, not an absolute trigger condition.
- The output path is stated as `docs/vertical-signoff-<date>.md` in the target repo, while the scope document itself is placed in a separate cross-repo skills repository because "no single target repo owns" the skill. The meaning and selection of "target repo" remain unresolved in a cross-repo review.

## DeepSeek (deepseek/deepseek-v4-pro) — verbatim

(appended below from the raw run output)
**Unclear or ambiguous**

1. **Core concepts undefined**  
   - What is a *slice*? (a module, a task, a sub-system?)  
   - What is a *vertical*? (the assembled whole? a feature? a cross-cutting concern?)  
   - What is a *build* in this context? (a code change? a set of implemented features?)  
   - What is the *base* against which the vertical is reviewed? (a code baseline, the spec, a previous version?)

2. **Build spec (“build doc”) not specified**  
   - Where does the build doc live?  
   - What format does it have? (markdown, a checklist, a blueprint?)  
   - How does the skill locate and load it?

3. **Slice discovery and signoff status**  
   - How does the skill know which slices exist for a build?  
   - Where are the per-slice signoff verdict documents stored?  
   - What is their naming convention and structure, so the skill can check whether all slices are signed off and rechecked?

4. **Target repo determination**  
   - The output is written to `docs/vertical-signoff-<date>.md` in “the target repo.” Which repository is the target? Is it the current working directory? Should it be derived from the location of the build spec or the slices?

5. **Full code delivery to outside models**  
   - What file set constitutes “the full code” of the vertical? Is it everything in a particular repository, a specific directory subtree, or a defined set of paths?  
   - How is the root/codebase path provided to `mcp__codex` and `mcp__antigravity`? (Does `mcp__codex` already know the checkout? Does `antigravity` need an explicit `--add-dir` argument, and if so, what directory?)  
   - If the vertical spans multiple repos, how is that handled?

6. **Adversarial verification protocol**  
   - What exactly must Claude do to “adversarially verify” an outside finding? Check file:line existence? Read the code and reason about the claim? Attempt to reproduce the failure scenario? Run tests?  
   - What standard determines that a finding is “verified” vs. rejected?  
   - If an outside model’s `file:line` doesn’t exist, does Claude try to locate the intended code, or reject the finding outright?

7. **“Nothing unverified lands in the verdict” vs. raw output**  
   - The output document includes “every model’s raw section verbatim below.” Those raw sections may contain findings that could not be verified (hallucinated file paths, false claims). Does “the verdict” refer only to the merged top section, or does the whole document count? If the whole document must contain nothing unverified, how should the raw sections be filtered?

8. **Per-run mode interaction**  
   - How is the choice for “local-only” vs. “local + ChatGPT + Gemini” actually collected? Is it a chat message, a CLI option, a typed keyword?  
   - What are the exact accepted keywords (e.g., “local”, “both”, “local-only”, “local+ChatGPT+Gemini”)?  
   - What happens if the skill is invoked in a non-interactive context (script, CI)? Does it need a default or a flag to bypass the prompt?

9. **Gate override mechanism**  
   - “Tony can collapse the gate in the invocation ("run it anyway"), the skill never does.” How is this expressed? Is it a flag (`/vertical --force`), or an interactive follow-up question after the gap report?  
   - If interactive, what is the exact user input that overrides?

10. **Deduplication criteria**  
    - What defines a duplicate between Claude’s findings and outside findings? Only identical `claim` + `file:line` + `concrete failure scenario`? Do differences in severity or confidence matter?

11. **Claude’s own findings verification**  
    - The document says Claude “adversarially verifies every outside finding,” but does Claude also need to verify its own findings before placing them in the merged verdict? If so, how?

12. **“Reject-it mandate”**  
    - What does this mean for the outside models? Are they explicitly prompted to look for reasons to reject the build? Does this affect the tone or criteria of their review?

13. **Parity configs and transport details**  
    - What are the “jpb's parity configs” (temperature, max tokens, etc.) and where exactly in `~/.claude/skills/jpb/SKILL.md` are they recorded?  
    - What exact input does `mcp__codex` expect (prompt structure)? What does `mcp__antigravity` expect beyond `--add-dir`?

14. **Context of invocation**  
    - Is `/vertical` a slash command within a Claude chat session? Is there an expected environment (a specific repo, a tmux pane)? Does the user need to have a particular working directory?

15. **Relationship between “base” and what outside models receive**  
    - The review target is “the whole vertical against its base,” yet outside models receive only “the build doc (the spec) and the full code.” If the base is a code baseline, they lack it and cannot review changes. If “base” means the spec itself, the phrasing is confusing.

**Questions that need answers before building**

1. What is an example slice and an example vertical so we can concretely define discovery and scope?  
2. Where exactly is the build spec (build doc)? Is it a single file per vertical? In which repository and at which path?  
3. How are slice signoff verdicts stored? What is the directory/naming convention and what fields do they contain?  
4. At runtime, how is the “target repo” identified for writing the output verdict document?  
5. What is the precise definition of “base” and how does the skill obtain it?  
6. How do we determine the set of files that constitute “the full code” of the vertical? What directory or repo path is passed to each outside model tool?  
7. What are the exact verification steps Claude must perform for each outside finding, and what is the pass/fail condition?  
8. When a raw outside finding fails verification, is it still included verbatim in the output document? If not, what is the rule for filtering?  
9. How should the per-run mode prompt work non-interactively? (e.g., environment variable, skip flag)  
10. What are the exact accepted input tokens for mode selection and for collapsing the gate?  
11. Does “nothing unverified lands in the verdict” apply to the entire file or only the merged verdict section?  
12. Should Claude also verify its own findings before including them in the merged verdict?  
13. What exact prompt (or instructions) are given to outside models to implement the “reject-it mandate” and output in `/signoff` shape?  
14. What are the exact MCP call payloads and parity configs (model pin, temperature, etc.) that the skill must use?  
15. Is `/vertical` intended to run in an interactive Claude session only, or must it support headless/CI invocation?

**Internal contradictions**

- **Verdict content vs. “nothing unverified” rule**  
  The output document includes “every model’s raw section verbatim,” which will contain findings that may have failed adversarial verification (e.g., hallucinated paths). The rule states “nothing unverified lands in the verdict.” If “verdict” means the entire document, this is a direct contradiction. If “verdict” means only the merged top section, then the two statements are compatible, but the document does not make that distinction explicit.

- **“Whole vertical against its base” vs. outside reviewers’ input**  
  The skill’s review target is defined as “the whole vertical against its base.” Outside reviewers, however, receive only the build spec and the full code. If “base” means a code baseline (e.g., the state before the build), they are missing the very thing that would allow a comparison against the base. If “base” instead means the spec itself, then the terminology is inconsistent and the phrase “against its base” conflicts with later language that says they get the build doc (spec) and full code. This needs disambiguation or a clear definition of “base.”
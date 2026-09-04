# agent-file-flip — Slice C requirement map (2026-09-04)

Build doc: `docs/plans/2026-09-04-agent-file-flip.md`, Slice C. Line numbers are from branch `feat/agent-file-flip-c` at the slice's final commit. Paths are abbreviated: `signoff` = `plugins/signoff/skills/signoff/SKILL.md`, `recheck` = `plugins/recheck/skills/recheck/SKILL.md`, `vertical` = `plugins/vertical/skills/vertical/SKILL.md`.

| Req | Implemented at | What the cited line says |
|---|---|---|
| R1 signoff reads `REVIEW.md` at the start of Step 1; absent means defaults plus one report line | `signoff:22`, `signoff:121` | "Before either question below, read `<repo>/REVIEW.md`"; "Absent, the run uses this file's defaults and the chat block's `REVIEW.md:` line says `absent — defaults`"; the Output block's `REVIEW.md:` line |
| R1 recheck reads it before the doc hunt; absent means defaults plus one report line | `recheck:20`, `recheck:72` | "Read `<repo>/REVIEW.md` before the doc hunt"; "Absent, the run grades on /signoff's defaults and the report's `REVIEW.md:` line says `absent — defaults`"; the Output block's `REVIEW.md:` line |
| R1 vertical reads it before the doc hunt and the gate; absent means defaults plus one report line | `vertical:16`, `vertical:106` | "Read `<repo>/REVIEW.md` before the doc hunt and the gate"; "Absent, the run uses /signoff's defaults and the chat block's `REVIEW.md:` line says `absent — defaults`"; the Output block's `REVIEW.md:` line |
| R2 `off` passes skipped and named with the reason | `signoff:22`, `signoff:62`, `recheck:20`, `vertical:16`, `vertical:76` | "a pass under `## Passes` marked `off` is skipped, and the verdict names it as skipped by `REVIEW.md` with the reason that line carries"; the lens mapping paragraph; recheck names a skipped-pass defect rather than entering it; vertical's verdict doc section 1 carries "each pass it skipped with its reason" |
| R2 Severity bar overrides the generic bar where they differ | `signoff:103`, `recheck:20`, `vertical:16`, `vertical:76` | "where a bar line and the table differ, the bar wins, and the finding names the bar line that placed it"; recheck: "the severity mapping for every fix-introduced defect this run assigns, overriding /signoff's generic table where they differ"; vertical: "the severity mapping for every finding this run grades, outside findings included" |
| R2 Repo-specific checks each tried, listed by name under Tried and failed to break | `signoff:22`, `signoff:130`, `vertical:16`, `vertical:76` | "each `## Repo-specific checks` line is an item the reviewers must try to break, and `Tried and failed to break` lists every one by name"; the Output block's `Tried and failed to break` line names the rule; vertical lists each by name in section 1 (recheck: the closed checklist never grows from them, `recheck:20`, see Build assumptions) |
| R3 first-run inference (UI → accessibility, DB → data-safety, correctness and security always on) | `signoff:24` | "Infer the toggles from the repo before spawning anyone: `correctness` and `security` are always `on`; a UI framework or UI components present … turns `accessibility` on … a hosted database, a migrations folder, or a database env key … turns `data-safety` on" |
| R3 show the proposed file, write only on the user's word, template verbatim with toggles and `verified:` today | `signoff:24`, `signoff:144` | "show the whole proposed file in chat and ask for the user's word. The word is a gate: on it, write the file"; "`<!-- verified: YYYY-MM-DD -->` stamped with today"; the template section says Step 1 renders the verbatim block |
| R3 no word, no file, run continues on defaults | `signoff:24` | "no word — a no, a different instruction, or nothing — means no file, and the run continues on defaults with the line saying `absent — defaults (proposed, not written)`" |
| R4 kit template carried inline with a source line saying the two must match | `signoff:142`–`signoff:163` | Section "The REVIEW.md template": "The source is the vault note `~/ObsidianVault/01-domain/repo-doc-kit.md` … carried here verbatim because this skill runs on machines without the vault, and the two must match"; the fenced block at `:146`–`:163` |
| R5 second-failure rule: compare with earlier verdict docs and punch-list blocks, recurring claim appended, stamp updated, judged by claim | `signoff:140` | "compare this run's findings with the slice's earlier verdict doc(s) under `docs/reviews/` … and every punch-list block in the build doc. A finding that recurs — the same claim across two signoffs, at the same or a moved location; judged by claim, never by `file:line` alone — is appended as one line under `## Repo-specific checks` … and the `<!-- verified: YYYY-MM-DD -->` stamp is rewritten to today" |
| R6 recheck never writes `REVIEW.md` | `recheck:20`, `recheck:64`, `recheck:94` | "/recheck reads the file and never writes it — not a toggle, not the stamp, not a line"; rule 6 "never `REVIEW.md`, which /signoff alone writes"; What-NOT line |
| R6 vertical never writes `REVIEW.md` | `vertical:16`, `vertical:94`, `vertical:123` | "/vertical never writes `REVIEW.md` (rule 7)"; rule 7 "The build plan, its cards, and `REVIEW.md` belong to the other stations"; What-NOT line |
| R6 signoff writes it only in R3 and R5; stays report-only | `signoff:88`, `signoff:140`, `signoff:167`, `signoff:176` | Rule 5: "Writing the verdict doc and `REVIEW.md` (the first-run write and the second-failure append, nothing else) is recording, not repair"; "That write and this append are the only two ways this skill touches `REVIEW.md`"; the exhaustive doc-writes list names the two occasions; What-NOT: "recording, not fixing" |
| Reviewers receive `REVIEW.md` (so R2's checks reach the fresh subagents) | `signoff:44`, `signoff:93`, `recheck:34` | "They receive the scope, the spec path, the mandate, and `REVIEW.md` when present"; rule 10; recheck's verifier receives it with the checklist |

## Acceptance evidence

AC1 (`grep -n "REVIEW.md" plugins/{signoff,recheck,vertical}/skills/*/SKILL.md`): signoff 20 hits, vertical 5 hits, recheck 5 hits. `grep -n "^## Passes\|^## Severity bar\|^## Repo-specific checks" plugins/signoff/skills/signoff/SKILL.md` returns lines 150, 156, 161 inside the inline template. PASS.

AC2 (the fenced `markdown` block extracted from the kit note and from the skill with the same `awk`, then `diff`): no output; both files 16 lines, identical MD5 `bca43776d50df49b6233f9aca49c84d7`. The template is carried with the kit's own example toggle values and the `YYYY-MM-DD` placeholder, so no normalisation was needed. PASS.

AC3 (fresh session, `claude --plugin-dir plugins/signoff`, asked what /signoff does on its first run in a repo with no `REVIEW.md`; same caveat as Slices A and B: `--plugin-dir` loads the branch copy alongside the installed copy, and the prompt named the branch file). Answer, verbatim:

```
Answering from the branch copy at `plugins/signoff/skills/signoff/SKILL.md` only. The first-run behavior lives in Step 1, lines 22 to 24, with the template at line 142 and the chat-block line at line 121.

On a first run in a repo with no REVIEW.md, the skill does this, in order, all before spawning any reviewer:

1. **Reads for the file and finds it absent.** Step 1 says the inspection sheet is read before either scoping question. Absent, the run falls back to this skill's own defaults.

2. **Infers the four pass toggles from the repo.** `correctness` and `security` are always on. `accessibility` turns on if a UI framework or UI components are present, meaning a package.json naming react, next, vue, or svelte, a `components/` or `app/` tree of them, or a Godot or SwiftUI scene tree. Otherwise it is off. `data-safety` turns on if there is a hosted database, a migrations folder, or a database env key in `.env.example` such as `DATABASE_URL`, `SUPABASE_*`, `POSTGRES_*`, or `NEON_*`. Otherwise it is off.

3. **Renders the template with those toggles.** The template carried verbatim in the skill has four sections: Passes, Severity bar, Repo-specific checks, and a `<!-- verified: YYYY-MM-DD -->` stamp. Each pass line's parenthetical states what the inference found. The stamp is set to today.

4. **Shows the whole proposed file in chat and asks for the user's word.** The word is a gate.

5. **Writes the file only on the word.** If the user says yes, the skill writes `<repo>/REVIEW.md`, runs the review under it, and the chat block's `REVIEW.md:` line reads `created this run`. Wording in the original invocation that orders the write also counts as the word.

6. **Does not write on anything else.** A no, a different instruction, or silence means no file. The run continues on defaults and the `REVIEW.md:` line reads `absent — defaults (proposed, not written)`. The rule closes with "Never write it unasked."

So the answer to "does it write the file" is: no, not by default. It proposes and gates. The punch-list ledger section confirms this, naming the first-run write on the user's word as one of only two occasions the skill ever touches REVIEW.md. The other is the second-failure append.

One thing the skill does not say: it does not define what happens if the user's answer is ambiguous. Only an explicit yes or invocation wording counts as the word, so an ambiguous reply is treated as no.
```

AC4 (fresh sessions, `claude --plugin-dir plugins/recheck` and `plugins/vertical`, asked whether the skill ever writes `REVIEW.md` and what it reads from it). Answers, verbatim:

recheck:

```
Answering from the branch copy of the recheck skill only.

**Does /recheck ever write REVIEW.md? No.** The file says this in three places. Step 1 says recheck reads the file and never writes it: not a toggle, not the stamp, not a line. Rule 6 repeats that it never mutates REVIEW.md, which /signoff alone writes. The "What NOT to do" list closes with the same prohibition. Even a recurrence the run notices is not recorded there. The run says at most one line about it and leaves the recording to /signoff's second-failure rule.

**What it reads from REVIEW.md when present.** Two sections are consumed, and one is explicitly ignored for the checklist:

- **The Severity bar.** This becomes the severity mapping for every fix-introduced defect the run assigns. It overrides /signoff's generic table where the two differ.
- **The Passes list.** A pass marked `off` means a fix-introduced defect of that kind is named as skipped, citing the reason on that line, and never entered as an item.
- **Repo-specific checks are read but not applied.** They belong to /signoff's hunt. The closed checklist never grows from them, per rule 1.

The file also flows to the fresh reviewer subagent in Step 2 alongside the checklist. Toggles, the stamp, and the checks list are named as things recheck never reads for action. When REVIEW.md is absent, the run grades on /signoff's defaults and the report's `REVIEW.md:` line says `absent — defaults`.
```

vertical:

```
No, /vertical never writes REVIEW.md. The file says so three times: line 16 states it outright, rule 7 on line 94 makes the verdict doc the run's only write and assigns REVIEW.md to "the other stations," and the closing don'ts on line 123 repeat it.

When REVIEW.md is present, the skill reads it before the doc hunt and the gate, and takes three things from it:

- **`## Passes`**: any pass marked `off` is skipped, and the verdict doc names the skip with the reason from that line.
- **`## Severity bar`**: becomes the severity mapping for every finding the run grades, outside-model findings included, overriding /signoff's table where they differ.
- **`## Repo-specific checks`**: each line is an item the local reviewers must try to break, listed by name in the verdict doc's section 1 as held or as the finding it became.

When it is absent, the run falls back to /signoff's defaults and the chat block's `REVIEW.md:` line reads `absent — defaults`. Outside reviewers get the file only as part of the tracked-file export; the packet adds nothing for it.
```

AC5 (`git diff main -- plugins/signoff/skills/signoff/SKILL.md | grep -i "^+.*fix"`): three added lines contain the word — rule 5 ("recording, not repair"), the punch-list ledger paragraph (its pre-existing "fix" wording, extended with the `REVIEW.md` occasions), and the new What-NOT line ("recording, not fixing"). None directs a fix; all three restate that the skill records. PASS.

AC3, AC4: all three answers describe the built rule (infer → show → word → write, else defaults; recheck and vertical answer no and name the bar and passes they read). PASS.

AC6: this file.

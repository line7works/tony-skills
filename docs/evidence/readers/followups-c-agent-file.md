# Followups Slice C evidence — the Agent route hands the prompt over as a file (2026-09-08)

Slice C of `docs/plans/2026-09-08-readers-followups.md`. `compose`'s Agent-route branch, readers' `contract.md`, and readers' `SKILL.md` Step 3 were edited at commit `0fb48ca` on `feat/readers-followups-c`; this file records the no-spend criteria (AC1, AC4, AC5, AC6), the two live Agent-route reads R5 asks for (AC2, AC3), and the fresh `claude -p` read of `SKILL.md` (AC5). Two readers were dispatched, both on the Claude row of this account through this session's Agent tool; nothing left the account otherwise. The session model that ran the build reported itself as `claude-fable-5-1`.

`<checkout>` stands for the tony-skills checkout root, `<scratch>` for the session's scratchpad directory, and `<home>` for the home directory (the commands used the absolute paths; scrubbed here per the Slice E convention, Tony's word 2026-09-06 and 2026-09-08). Every number below is the printed output of the command beside it. Every runner step ran the checkout's runner by path (`plugins/readers/skills/readers/assets/readers`, the plan's Constraints line 7) with `READERS_CHECKOUT=<scratch>/clone` (a `git clone` of the checkout, so the tracked memory file is untouched) and `READERS_RUN_ROOT=<scratch>/runs`.

## The hand-off text (R1)

The Agent route's `tool` block now prints `prompt_param: null` and carries, in `params.prompt`, this fixed text (557 bytes on the AC1 call; the path is the only part that varies):

```
Your entire instructions are in the file <scratch>/runs/followups-c-compose/c-claude-rwt/prompt.md. Before anything else, read that whole file and follow it verbatim as if this message were its contents: it opens with the fixed instructions, then the mandate, then the documents. Reading that one file is permitted even though it lies outside your workspace; it is the only file outside the workspace you may read. This message carries no other instruction.
```

## AC1 — the body never emits the prompt inline

Request (`claude-session`, `repo-with-tools`, `floor: opus`, `session_model: claude-fable-5-1`, `workspace: .`, one document, `run_id: followups-c-compose`, `call_id: c-claude-rwt`): `status composed`, `route agent`, `effective_model claude-fable-5-1`, `effective_effort null`. The `tool` block:

```json
{
 "capture": "the subagent's final message, ending where the reviewer's text ends (never the Agent tool's trailing usage footer)",
 "name": "Agent",
 "omit": [],
 "params": {
  "description": "readers claude-session repo-with-tools read (c-claude-rwt)",
  "prompt": "Your entire instructions are in the file <scratch>/runs/followups-c-compose/c-claude-rwt/prompt.md. Before anything else, read that whole file and follow it verbatim as if this message were its contents: it opens with the fixed instructions, then the mandate, then the documents. Reading that one file is permitted even though it lies outside your workspace; it is the only file outside the workspace you may read. This message carries no other instruction.",
  "subagent_type": "general-purpose"
 },
 "prompt_file": "<scratch>/runs/followups-c-compose/c-claude-rwt/prompt.md",
 "prompt_param": null
}
```

A `python3` check walked every string in `tool`: `READER INSTRUCTIONS` absent from all of them; line 1 of `prompt_file` is `READER INSTRUCTIONS (fixed by readers; the mandate follows them):`; the longest string in `tool` is 557 bytes (`< 2000`). Printed `AC1 assertions passed`.

## AC4 — the Workflow route is untouched

Request (`claude-session`, `starved`, same run id, `call_id: c-claude-starved`): `status composed`, `route workflow`, `tool.prompt_param null`, `<call dir>/reader.workflow.js` exists. `git diff main -- plugins/readers/skills/readers/assets/claude-boxes.workflow.js | wc -c` → `0`.

## AC6 — the four-lens signoff shape still composes

Four requests derived from `assets/examples/signoff.json` (`run_id: followups-c-ac6`, call ids `signoff-spec`, `signoff-correctness`, `signoff-seams`, `signoff-security`, `session_model: claude-fable-5-1`, the lens word swapped in the mandate): each `composed`, `route agent`, `prompt_param null`, `params` keys `description`, `isolation`, `prompt`, `subagent_type`, the hand-off text present. Nothing dispatched.

## AC5 — the contract and the body describe it

- `grep -n 'prompt_param' plugins/readers/skills/readers/assets/contract.md | grep -c 'prompt.md'` → `1` (contract.md:70, the `tool` field description).
- `grep -c 'prompt.md' plugins/readers/skills/readers/SKILL.md` → `1` (before: `0`), at Step 3's Host-rows paragraph.
- `readers validate` on the nine `assets/examples/*.json` → `valid` nine times before the edits and nine times after. `python3 -m py_compile` on `readers.py` → ok.
- `wc -l` of `SKILL.md` → `63` before and after; `contract.md` → `138` before and after (three sentences grew; no line added).

The fresh read, run from `<scratch>/fresh` (an empty directory, so no repo instruction file loads), started 2026-09-08T17:16:10Z, ended 2026-09-08T17:16:24Z, exit 0, stderr empty:

```
claude -p "Read the file <checkout>/plugins/readers/skills/readers/SKILL.md and answer from it alone, citing the step the answer comes from: when a caller summons readers with a claude-session repo-with-tools request and readers dispatches it through the Agent tool, what does the body pass as the Agent tool's prompt parameter, and where does the composed prompt live? Do not read any other file." --output-format text < /dev/null
```

Its answer, verbatim:

```
**Answer, from Step 3 ("Run the lane"):**

- On the Agent route, `tool.prompt_param` is null, so the composed prompt does not travel as a parameter. What goes into the Agent tool's `prompt` parameter is `tool.params.prompt`: the runner's **short hand-off text that sends the reader to the prompt file**. Step 3 notes it's the same on every Agent-route call regardless of document size, "so the composed prompt is never pasted into the Agent call."
- The composed prompt itself **stays on disk at `<call dir>/prompt.md`** (the `call_dir` returned by `RUNNER compose`, alongside `prompt_file`).

Both facts come from the parenthetical in Step 3's **Host rows** paragraph (line 35). Step 3 also fixes where the reply comes from on that route: the subagent's final message, ending where the reviewer's text ends, with the trailing agent id and usage footer excluded.
```

## AC2 — the big read (R5): the 462 KB readers build plan under `repo`

`readers suggest claude-session --run followups-c-live` froze the run first (`session`, `roster default`). `readers validate` → `valid`. Request:

```json
{"protocol_version":1,"run_id":"followups-c-live","call_id":"c-big-plan","row":"claude-session","profile":"repo","session_model":"claude-fable-5-1","workspace":"<checkout>","documents":["docs/plans/2026-09-06-readers.md"],"mandate":"Name the heading of the last `## Slice` section in the document and quote its `Status:` line; then name the first and last `### ` headings under `## Punch list`."}
```

`compose` → `status composed`, `route agent`, `effective_model claude-fable-5-1`, `profile repo`, `workdir <checkout>`, `workdir_instruction_files ["AGENTS.md", "CLAUDE.md"]`; `wc -c <call dir>/prompt.md` → `463228`. The Agent tool was invoked from this session with `params` exactly as printed (`description`, `prompt` = the hand-off text naming `<scratch>/runs/followups-c-live/c-big-plan/prompt.md`, `subagent_type general-purpose`; no `model`, since `claude-session` inherits the session). The reader ran 51.5 s by the tool's usage line and made five tool calls: one `Read` of the prompt file, refused by the harness (`File content (452.4KB) exceeds maximum allowed size (256KB). Use offset and limit parameters...`), then four `Bash` calls running `wc`, `grep`, `sed`, `awk`, and `tail` over that one file and nothing else (see Discovered in the build doc: the `repo` profile line says "run nothing"). The final message was extracted byte-exact from the subagent transcript (the completion notification HTML-escapes angle brackets) by a scratch script, written to `<call dir>/capture.md`, and handed to `record`.

READERS: claude-session · ok · claude-fable-5-1 · none · <scratch>/runs/followups-c-live/c-big-plan/sidecar.json

Sidecar fields:

- `status`: `"ok"`
- `reason`: `null`
- `row`: `"claude-session"`
- `transport`: `"claude-subagent"`
- `override_source`: `"roster default"`
- `effective_model`: `"claude-fable-5-1"`
- `effective_effort`: `null`
- `profile`: `"repo"`
- `workdir`: `"<checkout>"`
- `workdir_instruction_files`: `["AGENTS.md", "CLAUDE.md"]`
- `isolation`: `"unmeasured"`
- `parity`: `"web tools forbidden by instruction"`
- `budget`: `{"estimate_tokens": 145585, "limit": null}`
- `budget_method`: `"skipped (window unknown)"`
- `mandate_hash`: `"26ff8a77f76122971f09faf88e2be5ba57f4524da42c4e8059c3cd86bac16254"`
- `packet_hash`: `"e11583bd0e3763087ea839aa309644957c7c9b178f2910c74abee83aa972bb36"`
- `raw_hash`: `"3ccc7d418257ac194a700c0a7d91314974800ffae109a9d0a006eea2bcbf7ef4"`
- `session_model`: `"claude-fable-5-1"`
- `adapter_version`: `"slice-c-fix-2026-09-06"`
- `started_at`: `"2026-09-08T17:15:51+00:00"`
- `ended_at`: `"2026-09-08T17:17:18+00:00"`
- `duration_s`: `87.0`

`raw_text`, verbatim:

```
**Report (cold read of `2026-09-06-readers.md`, 1,459 document lines inside the packet)**

**1. Last `## Slice` section**

Heading (document line 244 of the packet; the ninth and last of Slices A through I):

`## Slice I — close-out: the invariant, the guides, the installed proofs, the retirements`

Its `Status:` line, quoted verbatim (the final line of the section, immediately after `Depends on: Slice H (and, through it, every slice: R5 requires C–H merged)`):

`Status: signed off`

For reference, every Slice section A through I carries the identical line `Status: signed off`; no other Status value appears in the document.

**2. `## Punch list` section (packet line 654), first and last `### ` headings**

- First: `### 2026-09-06 — inspect: plan` (line 656; it is one of four consecutive headings with that exact text, at 656, 729, 793, 987, one per inspection stamp)
- Last: `### 2026-09-08 — recheck: slice I` (line 1463; runs to the `<<<END DOCUMENT>>>` marker at 1469, four MAJOR bullets all marked "fixed")

Thirty-four `### ` headings sit under the Punch list in total, from the four plan inspections through review/recheck blocks for slices A through I.

**Findings beyond the mandate (low confidence included, as instructed)**

- The document appears corrupted or spliced near its top. The Intent paragraph (line 11) breaks mid-sentence at "the four punch-list blocks under `", then a full `### 2026-09-07 — handoff` block (lines 12 to 24) sits inline, and line 26 resumes the Intent sentence but begins with two hash marks: `## Punch list` are the record of what changed and why). Tony's word on the second revision, ...`. A Markdown parser therefore sees a second H2 heading whose text starts with "Punch list`" at line 26, before any Slice section, in addition to the real `## Punch list` at line 654. If the mandate is read naively ("the first `## Punch list` heading"), the answer would be line 26 with no `### ` headings beneath it before `## Slice A`. I answered against the real section at line 654. Whether this splice is in the on-disk build doc or an artifact of how the packet was assembled, I cannot tell from inside the packet; worth a check against `docs/plans/2026-09-06-readers.md` in the checkout.
- The same 2026-09-07 handoff block also appears under `## Handoffs` (the section holds seven handoff headings, two dated 2026-09-07), so the inline copy at line 12 is a duplicate, consistent with an accidental paste into the Intent paragraph.
- Line 8 of the packet (the mandate itself) contains the string `Status:`, so a bare grep for `Status:` returns ten hits, not nine; only nine belong to the document.

No web, MCP, Skill, or agent tool was used; only the packet file was read, and nothing was run beyond `grep`, `sed`, `awk`, `wc`, and `tail` over that one file.
```

The four facts, checked against `docs/plans/2026-09-06-readers.md` in the checkout by the builder: the last `## Slice` heading is `## Slice I — close-out: the invariant, the guides, the installed proofs, the retirements` (doc line 234; the reader's packet line 244 is offset by the ten prompt lines above the document) with `Status: signed off` at doc line 257; the real `## Punch list` is doc line 644 (packet 654); the first `### ` under it is `### 2026-09-06 — inspect: plan` (doc 646) and the last is `### 2026-09-08 — recheck: slice I` (doc 1453). All four named correctly. The reader's extra finding is also true on disk: doc lines 12–16 hold a 2026-09-07 handoff block pasted inside the Intent paragraph, and line 16 begins `## Punch list\``, a second H2 before Slice A.

## AC3 — the small read (R5): the 1 KB fixture under `repo`

Workspace `<scratch>/ws-small`, holding a copy of `assets/fixtures/smoke-doc.md` and nothing else. Request:

```json
{"protocol_version":1,"run_id":"followups-c-live","call_id":"c-small-fixture","row":"claude-session","profile":"repo","session_model":"claude-fable-5-1","workspace":"<scratch>/ws-small","documents":["<scratch>/ws-small/smoke-doc.md"],"mandate":"Name the one gap this document deliberately leaves open, quoting the line that leaves it open."}
```

`compose` → `status composed`, `route agent`, `workdir <scratch>/ws-small`, `workdir_instruction_files []`; `wc -c <call dir>/prompt.md` → `1838`. Dispatched the same way, in the same message as the big read. The reader ran 16.6 s by the tool's usage line and made one tool call: `Read` of the prompt file. Capture extracted and recorded as above.

READERS: claude-session · ok · claude-fable-5-1 · none · <scratch>/runs/followups-c-live/c-small-fixture/sidecar.json

Sidecar fields:

- `status`: `"ok"`
- `reason`: `null`
- `row`: `"claude-session"`
- `transport`: `"claude-subagent"`
- `override_source`: `"roster default"`
- `effective_model`: `"claude-fable-5-1"`
- `effective_effort`: `null`
- `profile`: `"repo"`
- `workdir`: `"<scratch>/ws-small"`
- `workdir_instruction_files`: `[]`
- `isolation`: `"unmeasured"`
- `parity`: `"web tools forbidden by instruction"`
- `budget`: `{"estimate_tokens": 577, "limit": null}`
- `budget_method`: `"skipped (window unknown)"`
- `mandate_hash`: `"ea3b3cfbfb1ab7d79ed5ad30f891508ed1c8c532e2a443ef32d1d930ff92b68b"`
- `packet_hash`: `"3d40fdf38a55facccd5031e24d994e59a4e25d840650a36cf9a1105c762c0b31"`
- `raw_hash`: `"991c1a94871501d55ee93372b693b0e2c2581badc77cad37a5bae15048c51183"`
- `session_model`: `"claude-fable-5-1"`
- `adapter_version`: `"slice-c-fix-2026-09-06"`
- `started_at`: `"2026-09-08T17:15:51+00:00"`
- `ended_at`: `"2026-09-08T17:16:49+00:00"`
- `duration_s`: `58.0`

`raw_text`, verbatim:

```
Report (cold read of `smoke-doc.md`):

**The one gap deliberately left open: the happy-hour end time is defined by "the game," and the doc never says which game or what the end time is on a night with no game.**

The line that leaves it open, quoted verbatim from the `Open:` section:

> - "Happy hour runs until the game starts" — the doc never says which game, or what
>   happens on a night with no game. A cold reader should be able to name this gap.

Why this is the gap, and why it is the only one:

- Every item under `Decisions:` is closed with "— decided" (chalkboard, specials plus hours, out at open and in at close, faces the sidewalk).
- `Out of scope:` closes two adjacent questions (printed/lit sign, posting online) rather than leaving them open.
- The `Open:` section has exactly one bullet, and the doc flags it explicitly as the intended gap. It matters to the design because the sign "lists the drink specials and the hours," but the end of the hours window is undefined whenever the game is unspecified or absent, so whoever hand-writes the board each afternoon has no rule to follow.

Low-confidence, secondary observations (reported so nothing is filtered, not competing with the above as "the one gap"):

- "Readable from the far curb" in `Acceptance:` gives no distance or letter height, so pass/fail is a judgment call.
- "Whoever opens" writes the sign, but no fallback is named if the opener is unsure of that day's specials; the doc treats the specials as known.
- The acceptance metric ("fewer than three ... questions per shift") has no baseline or measurement window stated.

None of these are marked open by the document; only the game-start line is.
```

The document's deliberate gap (`Open:`, "Happy hour runs until the game starts") is named and the line quoted.

## After

`git status --short` in the checkout after both records showed only the slice's edited files plus the build doc and `docs/feedback.md` (the latter carrying one uncommitted `/fb` line from Slice B's session, untouched here); the `.readers/` copy the AC4 Workflow-route compose wrote in the checkout root was removed by hand, since that call was composed and never recorded (`record` is what removes it); the scratch clone's `git status --short` was empty (`last-picks.json` not written); no worktree was left. Live-send tally for this slice: two Agent-route reads on the session's own Claude row, nothing outside the account; `OPENROUTER_API_KEY`'s existence was never printed.

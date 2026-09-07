# Slice H evidence — signoff, wargame, recheck converted: the fresh-read request blocks (2026-09-07)

Slice H of `docs/plans/2026-09-06-readers.md`. The three reviewer skills now spawn their fresh Claude reviewers through `/readers` on the `claude-session` row with `floor: opus`, `session_model`, and profile `repo-with-tools`; the conversion is proven pre-merge by greps (AC1–AC4) and by one fresh `claude -p` read per rewritten SKILL.md at its checkout path (AC5), whose request blocks are piped one by one to the runner's `validate`, plus two session-built negative requests that prove the floor mechanics the text claims. No model call was sent for this slice: `validate` dispatches nothing. The session model that performed the reads reported itself as `claude-fable-5-1`.

`<checkout>` stands for the tony-skills checkout root and `<scratch>` for this session's scratchpad directory (the reads and the runner calls used the absolute paths; scrubbed here per the Slice E convention, Tony's word 2026-09-06). Every number below is the printed output of the command beside it.

## No-spend criteria (run from the repo root at the slice's head)

Files: `S` = `plugins/signoff/skills/signoff/SKILL.md`, `R` = `plugins/recheck/skills/recheck/SKILL.md`, `W` = `plugins/wargame/skills/wargame/SKILL.md`.

- AC1, `grep -c '<pattern>' <file>`, after the edits (before the edits every count was `0` except `opus`, which was `1` in each file):

```
pattern                 S   R   W
/readers                3   3   2
repo-with-tools         2   2   1
readers-protocol: 1     1   1   1
opus                    3   3   2
```

- AC2 (before the edits each printed `1`): `grep -c 'Reviewers are \`general-purpose\` subagents' S` → `0`; `grep -c 'One fresh \`general-purpose\` subagent' R` → `0`; `grep -c 'Run 4–6 parallel adversary agents (background, single message)' W` → `0`. `grep -c 'general-purpose'` on each of the three files → `0`.
- AC3, on `S`: `grep -c 'reviewers are always fresh subagents'` → `1`; `grep -ci 'anti-rubber-stamp'` → `1`; `grep -c 'what it tried to break'` → `1`; `grep -c "Report, don't repair"` → `1`; `grep -c 'isolation: worktree'` → `1` (before the edit `0`: the old paragraph carried the phrase quoted, `isolation: "worktree"`, which the criterion's pattern does not match); `grep -c 'One suite run at a time'` → `1`.
- AC4: `grep -c 'verification blocked'` → S `3`, R `4`, W `3`; `grep -c 'fixed | not fixed | broke:' R` → `2` (the Output line and the new Step 3 paragraph that names the form as unchanged).
- Before and after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times before the edits (readers' own files are untouched by this slice; re-run after the edits, below).

## The run directories the reads were given

Each skill's text says the session mints the run id, makes the run directory, writes the lens briefs (or the checklist), and runs `suggest` before the fleet, so each read was told a run directory that already existed, prepared by the session as the text describes, with `plugins/readers/skills/readers/assets/fixtures/smoke-doc.md` standing as the build doc and `plugins/readers/skills/readers/assets/readers.py` as wargame's target:

- `<scratch>/recheck-run/checklist.md` — a two-item checklist (severity · file:line · claim · scenario); `<scratch>/recheck-run/readers/` — the readers run directory, empty
- `<scratch>/wargame-run/security.md`, `races.md`, `data.md`, `cost-limits.md`, `failure-ux.md` — the five default lens briefs; `<scratch>/wargame-run/readers/`, empty
- `<scratch>/signoff-run/spec.md`, `correctness.md`, `seams.md`, `security.md` — the lens briefs (LEAN's three plus the `security` pass `REVIEW.md` marks on); `<scratch>/signoff-run/readers/`, empty

## AC5 — recheck: the one reviewer

Command, from the repo root: `claude -p "<prompt>" --output-format text` (under two minutes), where the prompt was:

> Read the file plugins/recheck/skills/recheck/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /recheck run on slice A of the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path; the card stands signed off with conditions, two open MAJORs on the checklist); the repo root is <checkout> and REVIEW.md is present there; the run id is recheck-fresh-read; the run directory is <scratch>/recheck-run; Step 2's suggest has already run (the row available, no drop note); the checklist is already written at <scratch>/recheck-run/checklist.md. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request object this skill would send to /readers for the reviewer — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty), pretty-printed here for reading:

```
{
  "protocol_version": 1,
  "row": "claude-session",
  "profile": "repo-with-tools",
  "workspace": "<checkout>",
  "documents": ["<checkout>/REVIEW.md"],
  "mandate": "<scratch>/recheck-run/checklist.md",
  "floor": "opus",
  "session_model": "claude-fable-5-1",
  "run_id": "recheck-fresh-read",
  "run_dir": "<scratch>/recheck-run/readers",
  "call_id": "recheck-fresh-read-verify"
}
```

## AC5 — wargame: the FULL fan-out

Command as above (under two minutes); the prompt was:

> Read the file plugins/wargame/skills/wargame/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /wargame run at FULL depth, EXISTING mode, on the target "the readers runner, plugins/readers/skills/readers/assets/readers.py"; the repo root is <checkout>; the run id is wargame-fresh-read; the run directory is <scratch>/wargame-run; the suggest has already run (the row available, no drop note); the five default lens briefs are already written at <scratch>/wargame-run/<lens>.md for security, races, data, cost-limits, failure-ux. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request objects this skill would send to /readers, as one JSON array with one object per lens in that order — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout; stderr was empty): a five-element array whose objects differ only in `mandate` and `call_id`; the first, pretty-printed:

```
{
  "protocol_version": 1,
  "row": "claude-session",
  "profile": "repo-with-tools",
  "workspace": "<checkout>",
  "mandate": "<scratch>/wargame-run/security.md",
  "floor": "opus",
  "session_model": "claude-fable-5-1",
  "run_id": "wargame-fresh-read",
  "run_dir": "<scratch>/wargame-run/readers",
  "call_id": "wargame-fresh-read-security"
}
```

The other four carry `mandate` `<scratch>/wargame-run/races.md`, `data.md`, `cost-limits.md`, `failure-ux.md` and `call_id` `wargame-fresh-read-races`, `-data`, `-cost-limits`, `-failure-ux`. No `documents` field: the target is code in the workspace, and the text passes a document only when the target is one.

## The validations (recheck and wargame)

Each block, written to its own file and piped to `plugins/readers/skills/readers/assets/readers validate -` (with `READERS_RUN_ROOT` at a scratch directory and a placeholder `OPENROUTER_API_KEY`):

```
recheck-fresh-read-verify → valid
wargame-fresh-read-security → valid
wargame-fresh-read-races → valid
wargame-fresh-read-data → valid
wargame-fresh-read-cost-limits → valid
wargame-fresh-read-failure-ux → valid
```

A field check over the six blocks by script: every one carries `floor` `opus`, `session_model` `claude-fable-5-1`, `profile` `repo-with-tools`, `workspace` the checkout root, and none carries `effort`, `model`, `isolation`, `authorized`, or `raw_path`. After the validations the scratch run root held `0` entries (`ls -A | wc -l`) and the two prepared `readers/` run directories were still empty: `validate` creates no run dir and writes no sidecar.

## The negative cases (session-built, the floor the text claims)

Two variants of the recheck block, each with a fresh call id, validated the same way:

```
the block without session_model            → floor-refused
the block with "model": "opus" added        → unknown-model
```

The first is Step 0's claim that a `claude-session` call under the floor needs `session_model` (readers' reason: `session model unknown`); the second is the "no model id is ever typed" line — a typed id on a floor-bound call is refused before any send, which is why none of the three skills sets `model`.

## AC5 — signoff: the LEAN fleet plus the `security` pass

Command as above (about three minutes; stderr carried only the harness's "no stdin data received in 3s, proceeding without it" warning, which the two reads above did not print — the reads ran in the background with no stdin); the prompt was:

> Read the file plugins/signoff/skills/signoff/SKILL.md at its checkout path in this repo (use the Read tool on it; read nothing else). Scenario: a /signoff run at LEAN depth on slice A of the build doc plugins/readers/skills/readers/assets/fixtures/smoke-doc.md (repo-relative path); the repo root is <checkout> and REVIEW.md is present there with passes correctness on, security on, accessibility off, data-safety off; no lens needs to mutate the checkout; the run id is signoff-fresh-read; the run directory is <scratch>/signoff-run; the suggest has already run (the row available, no drop note); the lens briefs are already written at <scratch>/signoff-run/<lens>.md for the lenses this skill selects at LEAN depth plus the REVIEW.md passes marked on. Your system prompt names your model id; use it where the skill says to. Print ONLY the JSON request objects this skill would send to /readers, as one JSON array with one object per lens — absolute paths everywhere, no fence, no prose before or after it, and no other output.

Output, verbatim (stdout): a four-element array — `spec`, `correctness`, `seams`, `security` — whose objects differ only in `mandate` and `call_id`; the first, pretty-printed:

```
{
  "protocol_version": 1,
  "row": "claude-session",
  "profile": "repo-with-tools",
  "workspace": "<checkout>",
  "documents": ["<checkout>/REVIEW.md"],
  "mandate": "<scratch>/signoff-run/spec.md",
  "floor": "opus",
  "session_model": "claude-fable-5-1",
  "run_id": "signoff-fresh-read",
  "run_dir": "<scratch>/signoff-run/readers",
  "call_id": "signoff-fresh-read-spec"
}
```

Each block validated the same way (`READERS_RUN_ROOT` at a scratch directory, a placeholder key):

```
signoff-fresh-read-spec → valid
signoff-fresh-read-correctness → valid
signoff-fresh-read-seams → valid
signoff-fresh-read-security → valid
```

The field check over the four: every one carries `floor` `opus`, `session_model` `claude-fable-5-1`, `profile` `repo-with-tools`, `workspace` the checkout root, `documents` `REVIEW.md` alone (the build doc travels by path inside the mandate, never inlined), and none carries `effort`, `model`, `isolation`, `authorized`, or `raw_path`. After the validations the scratch run root held `0` entries and `<scratch>/signoff-run/readers/` held `0`. The after photo: `readers validate` on the nine `assets/examples/*.json` → `valid` nine times (`sort | uniq -c` on the nine outputs printed `9 valid`).

## What the blocks show

- signoff's reviewers are one fleet of `claude-session` calls sharing the run id, one per lens (LEAN's three plus the `security` pass `REVIEW.md` marks on), each `repo-with-tools` on the live checkout with `REVIEW.md` as the only document, the lens brief by path, `floor: opus`, `session_model` the read's own model id, `call_id` `<run id>-<lens>` (R1, R4).
- recheck's reviewer is one `claude-session` call of the same shape with the checklist as its mandate and `call_id` `<run id>-verify` (R2).
- wargame's adversaries are five `claude-session` calls of the same shape, one per default lens, no documents on a code target (R3).
- No model id, effort, or `authorized` is typed in any block; every block carries `protocol_version: 1`, `run_dir`, and `session_model` (R4; the negative cases above are what their absence costs).

## What this slice does not prove

Live `/signoff` and `/recheck` runs through the installed readers plugin are Slice I's (the plan's Source of truth: the installed copy runs, not this checkout); a live `/wargame` FULL run stays deferred to Tony's call (Out of scope). The reads show the rewritten skills yield valid requests from a cold read of each file; they do not show a summon returning captures, a "verification blocked" report reaching a Method line or a `not fixed` row, or a mutating signoff lens actually running inside a caller-cut worktree.

## Fix pass (2026-09-07) — the reads repeated against the fixed text

The signoff's three MAJORs changed signoff's mechanics paragraph (a mutating check is the session's, run in Step 3.5 inside a worktree the session cuts; every reviewer call keeps the live checkout as `workspace`; the mandate list carries rule 9's read-only constraints), recheck's mandate list (the same constraints), and wargame's workspace rule (outside a git repo, `<run dir>/target/` — a fresh directory holding a copy of the target's document — never the current directory), so the cold reads were run again at dbe4363, all three with `< /dev/null` (the stdin warning did not print). Run ids `signoff-fresh-read-2` and `wargame-fresh-read-2` with the prompts above and the same prepared directories; a third read, `wargame-fresh-read-3`, exercised the changed rule with this scenario:

> ... a /wargame run at FULL depth, GREENFIELD mode, on a target that is a scope document at /Users/someone/Documents/precon-x.md, invoked from the directory /Users/someone/Documents, which is NOT inside any git repo; the run id is wargame-fresh-read-3; the run directory is <scratch>/wargame-run2 and the session has already done whatever the skill says to prepare under it (the target directory it names holds a copy of the document as precon-x.md); ...

Outputs (stdout; stderr carried only `exit 0`): four signoff blocks and five repo-target wargame blocks identical in shape to the first reads (call ids under the new run ids); the five non-repo wargame blocks carry `workspace` `<scratch>/wargame-run2/target` and `documents` the target document — the first, pretty-printed, after the one substitution described below:

```
{
  "protocol_version": 1,
  "row": "claude-session",
  "profile": "repo-with-tools",
  "workspace": "<scratch>/wargame-run2/target",
  "documents": ["<scratch>/wargame-run2/target/precon-x.md"],
  "mandate": "<scratch>/wargame-run2/security.md",
  "floor": "opus",
  "session_model": "claude-fable-5-1",
  "run_id": "wargame-fresh-read-3",
  "run_dir": "<scratch>/wargame-run2/readers",
  "call_id": "wargame-fresh-read-3-security"
}
```

Validations (`READERS_RUN_ROOT` at a scratch directory, a placeholder key):

```
signoff-fresh-read-2-spec / -correctness / -seams / -security → valid (4)
wargame-fresh-read-2-security / -races / -data / -cost-limits / -failure-ux → valid (5)
wargame-fresh-read-3-* as printed → invalid-request (5): the scenario's document path /Users/someone/Documents/precon-x.md does not exist on this machine, and validate reads documents to size them
wargame-fresh-read-3-* with that one path replaced by the copy at <scratch>/wargame-run2/target/precon-x.md → valid (5)
```

The `invalid-request` lines are the scenario's fiction, not the skill's shape: the read passed the target's document by the path the scenario gave it, which is what the text says to do; on a real run that file exists. After the validations the scratch run root held `0` entries and `<scratch>/wargame-run2/readers/` held `0`. The AC1–AC4 greps at dbe4363 print the same counts as the table above (S 3/2/1/3, R 3/2/1/3, W 2/1/1/2; AC2 0/0/0; AC3 1/1/1/1/1/1; AC4 3/4/3, form 2).

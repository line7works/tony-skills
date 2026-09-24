---
name: signoff-v2
description: Independent adversarial review of freshly built work, ending in a signed verdict. Brings in a senior engineer who did not write the code, with a mandate to reject it. Use when the user says "sign off", "have a senior engineer review this", asks for an adversarial review of what was just built, or finishes a phase/slice and wants it inspected before moving on.
disable-model-invocation: true
---

# Sign-Off

A slice just got built. Before it counts as done, an engineer **who did not write it** inspects it against the spec and either signs the card or writes a punch list.

This is the inspection station of the loop: `/blueprint` draws the plans, `/build` frames one slice, `/signoff` inspects it, and `/recheck` is this station's re-inspection visit, verifying the named fixes and flipping the card. The paper trail `/blueprint` and `/build` leave upstream is written *for* this step: read it as claims to test, never as evidence that the work is sound.

**The spine, the anti-rubber-stamp rule.** The reviewer's job is to find reasons to REJECT, not to confirm good work. A review that returns no findings must state explicitly what it tried to break and failed to break. Otherwise "looks good" is indistinguishable from "didn't look", and an unearned signature is worse than no signature, because the user will trust it. Here that rule is mechanical: `record-answer` refuses an answer with no findings and no executed check.

**What the scripts decide, and what you decide.** Every deterministic step is `scripts/signoff.py`'s: the source set, the review packet and what it withholds, the independence refusal, the evidence rules, the severity mapping, the recording transaction, the result. You supply judgment at one point: you summon the reviewer through `/readers` with the request the script wrote, and hand back what the reviewer said. You never form the initial verdict yourself. `references/signoff-contract.md` is the full contract; read it before changing anything.

**Until this skill is itself qualified**, the plan's words hold: initial inspection in this program still comes from the independent temporary reviewer.

## Step 0 — Model floor

Reviewers run at **Opus-class or better**. The floor is passed, never assumed: the request carries `floor: opus` and this session's own model id as `session_model`, and `readers` refuses a session below the floor as `floor-refused` rather than upgrading silently. No model id is typed into a reviewer's request; every reviewer inherits this session's model. The script enforces the floor too: it computes the session's class from the adapter's observed model id (never from a typed `floor_met`), and `request`, `record-answer` and `record` each stop `floor_refused` on a floor that is false, missing, unestablished, or typed in disagreement with the id; an answer whose `model` is missing, below the floor, or not this session's recorded model is refused. Nothing upgrades a model.

If this session is below the floor, or a reviewer call comes back `floor-refused`: **STOP**. Never emit a verdict from below the floor. Offer a lightweight review explicitly labeled NOT a sign-off, with no verdict line, and run it only if the user accepts that framing.

## Step 1 — Establish scope and spec, and open the run

First read `adapters/README.md`, the adapter index: it names the profile for the harness you run in,
and that profile names the helper that prints the whole `invocation` object as facts (the mode, the
run id and directory, the harness, both sessions and the model with its floor) and says how the
reviewer is summoned on that harness in Step 3. Put that object into the input whole and type none
of its fields. The building session comes only from the build run you are reviewing: pass its
`result.json` as `--build-result` with `--workspace`, `--build-doc` and `--slice`, which it must
match; the helper reads that run's recorded harness session (`invocation.session_id`). A result
that records none (or a blank one) is refused (exit 3, no invocation printed): STOP and say so, never build the
input by hand. With no `--build-result` the building session is recorded as unknown; never type a
session id.

Build the input (`references/input.schema.json`; `references/examples/input-caller.json` is one) and run:

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py check-input <input.json>
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py scope --run-dir <run dir>
```

`check-input` validates the input, applies the path rules, confirms the records component is reachable, and opens the run directory. `scope` computes the source set from git — committed since the slice's base, changed in the working tree, untracked and not ignored, with `docs/records/` excluded — reads the repo's `REVIEW.md` sheet, levels the document's log with a dry-run import, and builds the review packet.

**The scope is the script's, not yours.** A file committed since the base but clean in the work tree appears in no diff against HEAD; an untracked file appears in no diff at all. Both are in the set and both are in the packet. A path in the set that does not reach the packet is a stop.

**The sheet.** The run reports `REVIEW.md` as `read`, `present but not the kit sheet`, or `absent`. A file that fails the sheet test is the repo's and is never overwritten; the run uses this skill's defaults and says so. Its passes choose the lenses, its bar is this repo's Meaning column for defects, and its repo-specific checks travel to the reviewer.

**The two `REVIEW.md` writes are yours, not the script's.** On a first run with no sheet, offer the template in `references/signoff-contract.md` section 13 and write it only on the user's word. The second-failure append is Step 5.

## Step 2 — Independence (hard rule)

The session that wrote the code cannot review it. It knows what the code *meant* to do and will read intent into what is on disk.

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py request --run-dir <run dir>
```

This writes the `/readers` request and the reviewer's mandate. It carries the packet, the mandate and the repo's sheet, and **nothing from the builder's conversation**: not your reasoning, not your justifications, not your account of what you built and why, never chat history, never another lens's output.

Three things count as the builder's conversation and are listed in the packet with their content withheld: a path the input declares, a file whose name or first heading (the first real top-level heading after any frontmatter, however far down: an ATX heading indented up to three spaces or a Setext heading, with fences of any length, raw HTML blocks (one that holds its end marker on its start line, such as `<!-->` or `<?>`, closes there), block quotes and list items skipped whole, an empty list item ended by a blank line, a list item that follows a block quote or another list item starting a new list, a link reference definition read both as its own block (possibly over two lines) and as paragraph text, and CRLF endings and a leading byte order mark read as plain text) declares itself the builder's notes, and the ledger document's own `## Build assumptions`, `## Deviations`, `## Discovered`, `## Handoffs` and `## Punch list` sections and its `Status:` lines. An untracked builder-notes file is IN the source set and IN the file list, and its content is withheld — both, in that order. Blueprint's `Out of scope:` and `Not in this slice:` lines ARE spec and are delivered.

When the input marks the reviewing session as the building session, `request` writes no mandate and no request file, and `record-answer` refuses the answer with `refusal_reason: independence`. No verdict is recorded. Reviewing the diff solo and labeling it a sign-off is the one unforgivable move. The builder's notes are never evidence anywhere in the answer: a citation of a builder-notes path, or a quotation found only in withheld material, in prose, findings or `checks_executed`, refuses the answer on independence. A citation is resolved before it is compared: `./`, an absolute path, a `file://` URL, percent encoding, `..` segments, a Markdown link (an angle-bracketed destination with spaces, escaped or balanced parentheses, a reference definition, a link title), an HTML `href`, a quoted or backslash-escaped shell path and a `#fragment` all reach the same path. A withheld path that holds a space is also found in plain prose, and each of its spaces matches a line break there (a soft or hard line break, a backslash before the line ending included), so the path wrapped at its space onto the next line is still the same citation. A relative path that climbs out of the workspace and back in by the folder's own name (`../workspace/builder%20notes.md`), or an absolute one through the parent, reaches its workspace path; one that ends outside the workspace reaches nothing.

## Step 3 — Review

**LEAN (default).** Three parallel reviewers, distinct lenses:

- `spec` — does the built thing match the doc? Silently skipped requirements, quietly narrowed scope, stubs presented as finished. Walk the slice's acceptance criteria one by one and check files changed outside its Footprint. This lens matters most and is the one a generic code review misses.
- `correctness` — bugs, unhandled edge cases, error paths that swallow failures, state that can desync.
- `seams` — integration with what already shipped. Regressions in prior slices, broken assumptions at the boundary, migrations that do not run twice.

**DEEP** adds `security` and `tests`. Use when the user says deep, thorough or full, or the slice touches auth, money, or user data. **LIGHT** is one fresh reviewer with a fused `spec` + `correctness` lens, only on the user's invocation or the user accepting your offer on a genuinely small diff; never self-selected, because an inspection that scales itself down is the rubber stamp the spine forbids. DEEP's content triggers outrank LIGHT: name the conflict and run DEEP.

`scope` has already applied the sheet's passes to the lens set and named the result in its response. A pass marked `off` never runs, even at DEEP, and the verdict names the skip with its reason.

**Mechanics.** `request` wrote the request file; summon `/readers` with it and nothing else. One call per lens, sharing the run id, launched as one fleet. Each is `row: claude-session`, `profile: repo-with-tools`, the workspace the repo root, `floor: opus`, `session_model` this session's model id, a single-use `call_id`, and no `model`, no `effort`, no `isolation`. A lens whose status is `transport-failed`, `empty` or `incomplete` is re-sent once; a second failure, or a deterministic refusal, leaves the review incomplete, which is a STOP with the honest state as the reason. A harness whose adapter reports `lane-unavailable` (Codex today: readers has no floor-qualified route it can dispatch) is the same STOP; never review through any other route. A verdict from a partial review is the rubber stamp the spine forbids.

**Reviewers report everything**, low confidence included; the filtering is not theirs. Each finding: a location as `file:line` inside the source set, a claim, a concrete failure scenario, a severity, and an evidence kind (`executed`, `read`, `reasoned`). Do not instruct reviewers to self-censor.

## Step 3.5 — Execute

The Method line must be earned. Run what is runnable: the project's test command, then the thing itself against the spec's acceptance criteria. Record what ran and what it showed. If nothing is runnable, say so in one line; that is the **only** path to "static analysis only".

Keep bulk output out of context: redirect to a file and read back the summary lines. A lens whose check must mutate the checkout cannot do it as a reader — cut a worktree at the reviewed head, carry the uncommitted half in, run it there, and remove the worktree before the verdict.

## Step 4 — Record what the reviewer said

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record-answer --run-dir <run dir> --answer <answer.json>
```

The answer is `references/answer.schema.json` (`references/examples/answer-with-findings-and-model.json` is one), built from the reviewers' reports merged on `file:line` plus claim, with the adapter's `answer_identity` as its `session_id` and `model`. The script applies the rules; you do not:

1. **Evidence or it does not count.** A finding missing a location, a claim, a scenario or an evidence kind refuses the WHOLE answer (`answer_invalid`): nothing is raised, no verdict is recorded, and the answer is not repaired into shape. Fix the reviewer's report or re-send the lens; never edit a finding into validity yourself.
2. **A location outside the source set is a note**, not a finding.
3. **A clean review lists its checks.** No RAISED finding and no executed check with output is refused — a review whose findings all sit outside the source set counts as clean here.
4. **Verify before reporting.** Read the source yourself on every BLOCKER and MAJOR before it reaches the answer, and drop what you refute. Reviewers are fallible and a false blocker costs real time.
5. **Unbuilt-by-design is not a defect.** `Out of scope:` and `Not in this slice:` lines are user-sanctioned. A `## Deviations` entry labeled `per user` counts as sanctioned; one labeled `builder call`, or unlabeled, that leaves an acceptance criterion unmet caps the verdict at conditions and goes to the user as a question. An unmet requirement with no record at all is a BLOCKER **and** a question to the user.

The script computes the verdict from the raised severities — BLOCKER gives rejected, else MAJOR gives conditions, else signed off — and records what the reviewer stated beside it. A disagreement is reported, never silently resolved.

## Step 5 — Record

```sh
uv run --python /usr/bin/python3 --with jsonschema==4.25.1 scripts/signoff.py record --run-dir <run dir>
```

This levels the log, pins the head against what `scope` read, appends the findings as one batch through the records component, places the component's own rendered block at the ledger home's tail, copies it to the verdict doc under `docs/reviews/`, checks the copy with `mirrors`, and moves the slice's card. Every step is receipted; rerunning `record` settles a killed run rather than repeating it. Before the first write, after the final append and on every recovery, the source (minus this run's own document targets) must still be what the packet held; if anything moved, even a file that arrived during the last append, the run ends `stale_source` with what already landed reported (an append a killed run never heard back about is looked up in the log first: `records.appended` names what landed with its seq, `records.not_landed` what did not), and no verdict is recorded: build a new packet and review again.

The block is the component's bytes, not this skill's: `render` returns it, the line writes the claim in parentheses, and nothing post-processes it. The component recognises those lines on a later levelling, so the document can be signed off again and `/recheck` can read the findings out of the records afterwards.

**Signoff never clears a finding.** No `disposition`, no `waived`, no `reopened`. That is `/recheck`'s.

**Report, do not repair.** Sign-off is an inspection. Fixing is a separate instruction the user gives after seeing the verdict: offer, do not act. The user can collapse the gate up front ("sign off and work any MAJORs"); you never assume it.

**The second-failure rule.** Compare this run's findings with the slice's earlier verdict docs and the build doc's punch-list blocks. A finding recurs when this run raises a claim an earlier signoff already recorded AND this instance is a different one: the earlier entry is closed and the claim is back, or the earlier entry is still open and the claim appears at a new location. A location is the file plus the enclosing function or section, never the line number. A recurrence is appended as one line under `## Repo-specific checks` in `REVIEW.md` and the `<!-- verified: -->` stamp is rewritten to today. With no sheet on disk, or a file that fails the sheet test, name the recurrence in the Bottom line and write nothing. That append and Step 1's first-run write are the only two ways this skill touches `REVIEW.md`.

## Step 6 — Report

`record` wrote `chat.md` in the run directory. Deliver it in chat. It carries v1's block: the verdict, the scope and spec, the depth, lenses, route, reviewer and independence, the method, the verdict doc, the `REVIEW.md` line, the card, a two-to-three sentence bottom line, the findings by severity, what was kept as a note, and **`Tried and failed to break`, which is mandatory in every verdict and is the longest section when findings are few.**

Add by hand what the script cannot know: the questions rule 5 raised, the `Next:` line (a conditions or rejected verdict names the fixes, then `/recheck`), and a `SKILL NOTE:` line only when a rule was worked around, reinterpreted or excepted.

## Report-only

`report_only: true` in the input. The run computes the source set, builds the packet and adjudicates the answer, and writes nothing to the workspace and nothing to the log. The result names the findings the reviewer raised as raised, records no verdict, and says it was report-only.

## What NOT to do

- Do not review your own work; always a fresh reviewer.
- Do not pass the reviewers your rationale for what you built.
- Do not tell reviewers to pre-filter; they report everything and you filter.
- Do not grade against acceptance criteria you invented.
- Do not fix anything during the review.
- Do not edit a reviewer's finding into validity; a refused answer goes back to the reviewer.

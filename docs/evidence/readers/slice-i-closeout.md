# Slice I evidence — the close-out: installed proofs, both Macs, the MCP entry (2026-09-07)

Every proof below ran against the INSTALLED copies on the Mac Studio (`~/.claude/plugins/cache/tony-skills/<plugin>/a2e279be871a/`, the version dir of Slice H's merge commit `a2e279b`), never `--plugin-dir`, in a fresh headless session (`claude -p '<invocation>' --output-format text < /dev/null`, stdout to a file) so the transcript is verbatim. The build session that wrote Slice I ran no reader itself. Lane picks follow R5's own text (Claude everywhere; Gemini and the jpb smoke on Tony's word only); where a skill would ask a question, the answer R5 fixes was given in the invocation up front, because a headless run cannot wait, and the invocation text is quoted with each proof.

## No-spend criteria (run from the repo root at the slice's head)

- AC1: `grep -c 'summons .readers. and never carries its own transport' AGENTS.md` → `1`; `grep -c 'Twenty-one plugin folders covering twenty-two skills' AGENTS.md` → `1`; `grep -c 'skills/<skill>/assets/' AGENTS.md` → `1`; `git diff main --numstat -- AGENTS.md` → `3	2	AGENTS.md`. The count was checked against the tree before typing it: `ls plugins | wc -l` → 21, `find plugins -name SKILL.md | wc -l` → 22, and `.claude-plugin/marketplace.json` lists 21 plugins.
- AC2: `grep -rlE 'mcp__codex__codex|openrouter-box.sh|ollama launch' plugins/ | grep -vE 'plugins/readers/|assets/fixtures/'` → nothing (already true at Slice H's head; re-run here).
- AC3: `grep -rli 'grok' plugins/ README.md AGENTS.md .claude-plugin/marketplace.json | grep -vE 'assets/fixtures/'` → nothing.
- AC4: `test -f .../guides/gpt.md && test -f .../guides/gemini.md && echo ok` → `ok`; the roster one-liner → `['gemini', 'gpt-astra', 'gpt-sol']`; each `guide` value (`guides/gpt.md`, `guides/gpt.md`, `guides/gemini.md`) resolves relative to the roster's directory (checked with `os.path.isfile`); `grep -c 'box-runners.md:81' .../guides/gemini.md` → `1`. The nine `assets/examples/*.json` requests validate `valid` before and after the roster edit (the before photo).
- AC5: `grep -c 'points at jpb by the same path' README.md` → `0`; `grep -c 'plugins/readers/skills/readers/assets/readers' README.md` → `1`.

## Studio install state (`claude plugin list`, filtered to the nine, 2026-09-07 before any proof)

```
architect@tony-skills a2e279be871a
inspect@tony-skills a2e279be871a
jpb@tony-skills a2e279be871a
precon@tony-skills a2e279be871a
readers@tony-skills a2e279be871a
recheck@tony-skills a2e279be871a
signoff@tony-skills a2e279be871a
vertical@tony-skills a2e279be871a
wargame@tony-skills a2e279be871a
```

`diff -q` of the installed readers `SKILL.md` and `readers.py` against the checkout at `ba727bb` (Slice I's first commit): identical.

## R5 (a) — the direct form, Claude row, installed copy

Command, from a scratch directory outside any repo, with `READERS_RUN_ROOT` at a scratch run root: `claude -p '/readers claude-session /Users/tonycoon/Developer/tony-skills/plugins/readers/skills/readers/assets/fixtures/smoke-doc.md "Name the document'"'"'s deliberate gap in one sentence."' --output-format text < /dev/null`. Started 15:54:24 PDT, 19 s of reader time (`duration_s` in the sidecar). Output verbatim, scratch paths shortened to `<scratch>`:

```
READERS-PROTOCOL: 1

The cold read completed with status ok. The reader's answer:

The document never says which game "Happy hour runs until the game starts" refers to, nor what the happy-hour end time is on a night with no game.

READERS: claude-session · ok · claude-fable-5-1 · none · <scratch>/proofs/a/runs/direct-20260907-155438/c-02cbf578/sidecar.json
```json
{
  "adapter_version": "slice-c-fix-2026-09-06",
  "budget": {
    "estimate_tokens": 508,
    "limit": null
  },
  "budget_method": "skipped (window unknown)",
  "call_id": "c-02cbf578",
  "canned": null,
  "diagnostics": "<scratch>/proofs/a/runs/direct-20260907-155438/c-02cbf578/diagnostics",
  "dispatch_log": "<scratch>/proofs/a/runs/direct-20260907-155438/c-02cbf578/dispatch.log",
  "duration_s": 19.0,
  "effective_effort": null,
  "effective_model": "claude-fable-5-1",
  "ended_at": "2026-09-07T22:55:16+00:00",
  "envelope": "claude-session",
  "exit_code": null,
  "generation_id": null,
  "isolation": "harness-enforced (toolCalls: 0)",
  "kind": "host",
  "mandate_hash": "fda18d3dd2bcf1337b619b9267337c8f22f15f6c7624f4f6367e8ea14da8f487",
  "memory": "ok: /Users/tonycoon/Developer/tony-skills/plugins/readers/last-picks.json",
  "override_source": "roster default",
  "packet_hash": "91c7a0faf8a534c9ca6d65712e209bb91e1aee1beb31855170a687866757b704",
  "parity": "toolCalls: 0",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "<scratch>/proofs/a/runs/direct-20260907-155438/c-02cbf578/raw.md",
  "raw_hash": "8b8d571134e51cb690ab5da74fd3fe7f7e187b213ff0af5ebb611d15a829fb80",
  "raw_path": null,
  "raw_text": "The document never says which game \"Happy hour runs until the game starts\" refers to, nor what the happy-hour end time is on a night with no game.",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "claude-session",
  "run_dir": "<scratch>/proofs/a/runs/direct-20260907-155438",
  "run_id": "direct-20260907-155438",
  "session_model": "claude-fable-5-1",
  "sidecar": "<scratch>/proofs/a/runs/direct-20260907-155438/c-02cbf578/sidecar.json",
  "snapshot": "<scratch>/proofs/a/runs/direct-20260907-155438/snapshot",
  "snapshot_fault": null,
  "started_at": "2026-09-07T22:54:57+00:00",
  "status": "ok",
  "transport": "claude-subagent",
  "workdir": null,
  "workdir_instruction_files": []
}
```
```

Checks after: the run dir holds `snapshot/` and `c-02cbf578/` (`capture.md`, `prompt.md`, `raw.md`, `compose.json`, `reader.workflow.js`, `dispatch.log`, `sidecar.json`, `diagnostics/`); no `.readers/` copy remained in the working directory (the Workflow route's transient script was removed by `record`); `git status --short` in the checkout printed nothing, so the tracked `plugins/readers/last-picks.json` was not written. The Gemini half of (a) did not run: it sends only on Tony's word, and none was given in this run.

## R6 — the laptop, brought level (AC7)

The laptop's live Claude Code session (Remote Control row `macbook-pro-2-steady-thacker`; Tony named the terminal "laptop" in the invocation) ran the steps over the claude-relay channel: first a read-only report (2026-09-07: readers and architect absent, the seven other callers at `d1539b67a035`, checkout at PR #31), then the hand-off file `~/Documents/claude-relay/to-laptop/2026-09-07-readers-slice-i-laptop-level-2.md` (archived after: `git pull --ff-only`, `claude plugin marketplace update tony-skills`, `claude plugin install readers@tony-skills` and `architect@tony-skills`, `claude plugin update <name>@tony-skills --yes` for the seven). One deviation the laptop session reported: its checkout carried one uncommitted line in `docs/feedback.md` (a 2026-09-01 fb note); the relay file said back it up, stash, pull, pop; per that session's report Tony said mid-run "discard it is my call", so it backed the line up to `~/Documents/handoffs/2026-09-07-laptop-feedback-md-before-readers-pull.{md,diff}`, ran `git checkout -- docs/feedback.md`, and pulled. Its Step 5 outputs, verbatim as reported:

```
architect@tony-skills a2e279be871a
inspect@tony-skills a2e279be871a
jpb@tony-skills a2e279be871a
precon@tony-skills a2e279be871a
readers@tony-skills a2e279be871a
recheck@tony-skills a2e279be871a
signoff@tony-skills a2e279be871a
vertical@tony-skills a2e279be871a
wargame@tony-skills a2e279be871a
```

```
/Users/tonycoon/.claude/plugins/cache/tony-skills/architect:
a2e279be871a

/Users/tonycoon/.claude/plugins/cache/tony-skills/readers:
a2e279be871a
```

`git -C ~/Developer/tony-skills log --oneline -1` → `a2e279b Merge pull request #54 from line7works/feat/readers-slice-h`; `git status --short` → empty; `git stash list` → empty (no stash was created). Negative test: before the run neither `readers/` nor `architect/` existed in the laptop's plugin cache; after it both hold `a2e279be871a`. The laptop's Claude Code was not restarted (installed plugins load on its next start). Its `codex` MCP entry was left in place (R7 is Tony's word only).

## R5 (b) — `/precon` re-invoked on a throwaway scope doc, the Claude reader

The scratch repo: `<scratch>/proofs/widget-repo`, `git init` with one commit holding `widget.py` (`add(a, b)` returning `a + b`), `docs/scope/2026-09-07-widget-adder.md` (precon's format: four ledger lines, one parked), `docs/plans/2026-09-07-widget-adder.md` (one `## Slice A` card at `signed off with conditions` and one review block carrying one MAJOR whose failure scenario the fixed source no longer reproduces), and `docs/reviews/2026-09-07-signoff-widget-adder-a.md`. Every run below was launched from that repo's root.

Invocation (the whole prompt, the exit-test answer given up front because a headless run cannot wait):

```
/precon docs/scope/2026-09-07-widget-adder.md
Re-invocation on the existing scope doc in this repo, with no new discussion: the ledger stands as written, nothing has changed, and no settled-prerequisite question remains, so the frontier is empty. Go straight to the exit test. This is a headless run, so my answer to the exit-test question is given here up front: 1 (Claude, row claude-session). Run that read, write the cold-read doc with the reader's findings verbatim, read the record back, and end the sitting with the PRECON block. Where the skill would otherwise need an answer from me, state the question in your output and stop rather than wait.
```

Started 15:55:38 PDT; the reader ran 120 s (`duration_s`). Output verbatim (the result JSON's `raw_text`, the reader's full findings, is the one field elided here as `<raw_text: the fifteen findings and the environment note, filed verbatim in the cold-read doc>`; everything else is as printed):

```
READERS-PROTOCOL: 1

The sitting is complete. One cold read ran on the Claude row, its findings are filed verbatim, the scope doc carries the triage, and three threads now wait on you. Nothing was committed and nothing external was sent.

READERS: claude-session · ok · claude-fable-5-1 · none · /var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/precon-cold-read-claude-session/sidecar.json
```json
{
  "adapter_version": "slice-c-fix-2026-09-06",
  "budget": {
    "estimate_tokens": 484,
    "limit": null
  },
  "budget_method": "skipped (window unknown)",
  "call_id": "precon-cold-read-claude-session",
  "canned": null,
  "diagnostics": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/precon-cold-read-claude-session/diagnostics",
  "dispatch_log": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/precon-cold-read-claude-session/dispatch.log",
  "duration_s": 120.0,
  "effective_effort": null,
  "effective_model": "claude-fable-5-1",
  "ended_at": "2026-09-07T22:59:27+00:00",
  "envelope": "claude-session",
  "exit_code": null,
  "generation_id": null,
  "isolation": "harness-enforced (toolCalls: 0)",
  "kind": "host",
  "mandate_hash": "f03974ca5bef9418fddb5941e674a466bee32e84407b4ead143a12c6adc80a33",
  "memory": "ok: /Users/tonycoon/Developer/tony-skills/plugins/readers/last-picks.json",
  "override_source": "roster default",
  "packet_hash": "6ef88dd9d0ddd462f943b56bbdcd4bbb7fd7870cad9f5949c91ac287fc8e0fae",
  "parity": "toolCalls: 0",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/precon-cold-read-claude-session/raw.md",
  "raw_hash": "c1ae8333aab84c896e9b80c9d1a22fbe94e359f19aa27490a52e1fa616a3df13",
  "raw_path": null,
  "raw_text": "<raw_text: the fifteen findings and the environment note, filed verbatim in the cold-read doc>",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "claude-session",
  "run_dir": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32",
  "run_id": "precon-widget-adder-2026-09-07-386f32",
  "session_model": "claude-fable-5-1",
  "sidecar": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/precon-cold-read-claude-session/sidecar.json",
  "snapshot": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/precon-widget-adder-2026-09-07-386f32/snapshot",
  "snapshot_fault": null,
  "started_at": "2026-09-07T22:57:27+00:00",
  "status": "ok",
  "transport": "claude-subagent",
  "workdir": null,
  "workdir_instruction_files": []
}
```

## Triage and the questions for you

The reader returned fifteen findings plus an environment note. Full text and per-item disposition are in `docs/reviews/2026-09-07-precon-cold-read-widget-adder.md`. Eight were left downstream because the build doc already answers them, such as the exact one-liner and expected output. Three were absorbed. Five were surfaced.

These three reopened branches need your answer. Stated here and stopping, per the headless instruction:

1. **Print or return?** The blueprint built `return`, with the one-liner doing the printing. ➡️ Confirm return, and the parked line flips to decided with the build doc as its source.
2. **What does "floats are out" mean in code?** Reject with a TypeError, or leave undefined. Bools, strings, and negative ints in or out. ➡️ Leave undefined, which is what is built today.
3. **Does /architect run on this target?** The Intent names it, but no architecture doc exists and the build doc already ran. ➡️ Your call on the proof plan. I have no recommendation.

Two flags, no decision needed: the doc's source line "answered question 1" cites a question whose text is not recoverable from this sitting, and the repo has moved past the doc, which is expected on a post-build re-invocation.

**Decided on your behalf, flagged.** An assumed line ruling out the Tier 0 doc kit for the throwaway repo, reversible. And the first assumed line's why was reworded from "nothing downstream depends on it" to name packaging, flags, and the runner, with the one-liner as what signoff and recheck verify against. The before and after are in the cold-read doc.

## Read-back of the record

- **Decided**: one Python file `widget.py` exposing `add(a, b)`. Inputs are integers, floats out.
- **Assumed**: no packaging, CLI flags, or test runner, verification by one-liner. No Tier 0 doc kit in the throwaway repo.
- **Parked**: whether the first caller wants the sum printed or returned, waiting on the first caller.
- **Out of scope**: a web front end, nothing to serve.
- **Open**: the three threads above.

Every branch was visited: the pre-existing ledger stood, the cold read's sixteen items each carry a disposition, and the three unresolved threads sit in Open rather than being resolved by me. Working tree has the scope doc modified and the cold-read doc untracked, uncommitted.

```
PRECON: widget adder
Doc: docs/scope/2026-09-07-widget-adder.md
Counts: decided 2 · assumed 2 · parked 1 · out of scope 1
Parked: Whether the first caller wants the sum printed or returned — parked: waiting on the first caller
Next: /blueprint when ready.
SKILL NOTE: (1) readers lane: the starved claude-session reader on the Workflow route saw the session's git status snapshot and cited the latest commit message, so the harness environment reaches the subagent and a "cold" read is warm by that much. (2) precon: ledger sources of the form "answered question N" do not survive a sitting; the question text is unrecoverable on re-invocation. (3) headless: the exit-test question was posed with the answer pre-supplied by the invocation, and the summon form ran directly from the readers body already loaded in this turn by the suggest call rather than a second Skill invocation.
```

```

Checks after, in the scratch repo: `git status --short` → ` M docs/scope/2026-09-07-widget-adder.md` and `?? docs/reviews/2026-09-07-precon-cold-read-widget-adder.md`; the cold-read doc's first lines name the run id, the row, and the profile, its `## claude-session · claude-fable-5-1` section carries the sidecar path, the raw path and hash, `Status: ok · parity toolCalls: 0 · route workflow`, then the reader's output under "Nothing below this line was edited", byte-identical to the sidecar's `raw_text`; the scope doc's `Research:` line points at the cold-read doc and `Open:` carries the three reopened threads. No `.readers/` copy remained in the repo root. The run's SKILL NOTE (1) is a readers discovery, recorded in the build doc's `## Discovered`: the starved reader cited the session's git-status snapshot, which the harness injects into a subagent's prompt outside the composed prompt.

## R5 (f) — `/recheck` on the throwaway build doc, one punch-list item

Invocation (from the scratch repo's root, launched 16:04:44 PDT alongside (e); the two ran concurrently in the same scratch repo, which the recheck session noticed and reported as untracked `docs/architecture/` files appearing mid-run, harmless to its checklist):

```
/recheck slice A docs/plans/2026-09-07-widget-adder.md
Headless run: no one can answer mid-run, so where the skill would ask, state the question in your output and stop. The checklist is the one MAJOR on Slice A's 2026-09-07 review block; its failure scenario is on the record. Redirect bulk output to a file. Do not commit or push.
```

Output verbatim (scratch paths shortened to `<scratch>`; the reader ran 92 s):

```
READERS-PROTOCOL: 1

READERS: claude-session · ok · claude-fable-5-1 · none · /tmp/recheck-widget-a.jnUTz0/readers/recheck-a-20260907-a573-verify/sidecar.json
```json
{
  "adapter_version": "slice-c-fix-2026-09-06",
  "budget": {
    "estimate_tokens": 1046,
    "limit": null
  },
  "budget_method": "skipped (window unknown)",
  "call_id": "recheck-a-20260907-a573-verify",
  "canned": null,
  "diagnostics": "/tmp/recheck-widget-a.jnUTz0/readers/recheck-a-20260907-a573-verify/diagnostics",
  "dispatch_log": "/tmp/recheck-widget-a.jnUTz0/readers/recheck-a-20260907-a573-verify/dispatch.log",
  "duration_s": 92.0,
  "effective_effort": null,
  "effective_model": "claude-fable-5-1",
  "ended_at": "2026-09-07T23:07:42+00:00",
  "envelope": "claude-session",
  "exit_code": null,
  "generation_id": null,
  "isolation": "unmeasured",
  "kind": "host",
  "mandate_hash": "da940b026f6dacad55be23d4db8f835a0b39a03919c7dd8dab009ea79863a041",
  "memory": "ok: /Users/tonycoon/Developer/tony-skills/plugins/readers/last-picks.json",
  "override_source": "roster default",
  "packet_hash": "25fdbc6d2acf8dc535a6e77d03fa4c778e922acf0f073957f83137f55adf58f9",
  "parity": "web tools forbidden by instruction",
  "profile": "repo-with-tools",
  "protocol_version": 1,
  "raw_file": "/tmp/recheck-widget-a.jnUTz0/readers/recheck-a-20260907-a573-verify/raw.md",
  "raw_hash": "30b9d802dec8b297a1249721ed68ceebd601b80a9bbb618b04e2ee119d3810dd",
  "raw_path": null,
  "raw_text": "Item 1 \u00b7 MAJOR \u00b7 widget.py:5 \u00b7 (`add` returns the concatenation of its inputs as a string instead of their sum) \u00b7 fixed \u00b7 how verified: executed `python3 -c \"from widget import add; print(add(1, 2))\"` from the workspace root; exact output `3`, exit 0. Confirmed the import resolved to the workspace file (`widget.__file__` = `<scratch>/proofs/widget-repo/widget.py`), and `repr(add(1, 2))` is `3` of type `int`, so the result is a numeric sum rather than the string `\"12\"`. Static check agrees: `widget.py:5` reads `return a + b` with no `str()` wrapping. Adjacent numeric inputs also sum (`add(-1, 1)` \u2192 `0`, `add(2.5, 0.5)` \u2192 `3.0`).\n\nbroke: none\n\nPre-existing issues noticed (not graded): the git history in this workspace never contains the buggy version. `widget.py` was created in commit f57cee0 already reading `return a + b` (commit message \"fixed add()\"), so the signoff record's `12` reproduction cannot be reproduced from any commit here; provenance only, no code defect. Also untracked `docs/architecture/` sits in the working tree, and `add(\"1\", \"2\")` would still concatenate, which is outside R1's int-only scope.\n",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "claude-session",
  "run_dir": "/tmp/recheck-widget-a.jnUTz0/readers",
  "run_id": "recheck-a-20260907-a573",
  "session_model": "claude-fable-5-1",
  "sidecar": "/tmp/recheck-widget-a.jnUTz0/readers/recheck-a-20260907-a573-verify/sidecar.json",
  "snapshot": "/tmp/recheck-widget-a.jnUTz0/readers/snapshot",
  "snapshot_fault": null,
  "started_at": "2026-09-07T23:06:10+00:00",
  "status": "ok",
  "transport": "claude-subagent",
  "workdir": "<scratch>/proofs/widget-repo",
  "workdir_instruction_files": []
}
```

```
RECHECK: slice A — 1 item (+0 new)
Result: ALL CLEAR  ·  Status: signed off with conditions → signed off
Verdict doc: docs/reviews/2026-09-07-signoff-widget-adder-a.md — appended
REVIEW.md: absent — defaults
Method: item 1 executed — the recorded one-liner run from the repo root by the fresh reader, then re-run by this session with output redirected to /tmp/recheck-widget-a.jnUTz0/scenario.log; static read of widget.py:5 agrees

Bottom line: The one MAJOR on Slice A's review block is fixed. The scenario now prints 3 as an int from the workspace's own widget.py, so the card flips to signed off. Nothing is open on this slice; the next step is yours.

MAJOR · widget.py:5 · (add returns the concatenation of its inputs as a string instead of their sum) · fixed · executed by reader (run recheck-a-20260907-a573) and re-executed here: prints 3, repr 3, type int; line 5 reads `return a + b`
SKILL NOTE: the Agent tool appends a harness trailer (agentId line and usage block) after the subagent's final message; I wrote the message alone to capture.md and left the trailer out, reading "the subagent's final message" as excluding harness metadata.
```

Two things outside the run that you should know about:

- **Nothing committed or pushed.** The only tracked changes are the Status flip and the two appended recheck blocks, shown in the diff above.
- **A parallel session wrote into this shared scratchpad repo mid-run.** Two untracked files appeared under docs/architecture at 16:06 and 16:07 local time, an /architect doc and its HTML page for widget-adder. Their content matches an /architect proof run, not my reviewer's mandate, and the reviewer reported them as already present. I left them alone.

The reviewer's ungraded aside is worth one line: the repo's history never held the buggy version of add, since the first commit already reads `return a + b` with the message "fixed add()". That is provenance for this throwaway proof repo, not a code defect. No pre-existing defect surfaced that would warrant offering /signoff.
```

Checks after: the `READERS:` line precedes the `RECHECK:` block; `git -C <scratch>/proofs/widget-repo diff -- docs/plans` shows `Status: signed off with conditions` → `Status: signed off` and one appended `### 2026-09-07 — recheck: slice A` block; the same block is appended to `docs/reviews/2026-09-07-signoff-widget-adder-a.md`; no `REVIEW.md` in the scratch repo (`absent — defaults`); the run dir under `/tmp/recheck-widget-a.jnUTz0/readers/` holds the checklist mandate's call with `profile: repo-with-tools`, `workdir` the scratch repo root, `isolation: unmeasured`, `parity: web tools forbidden by instruction`. The run's SKILL NOTE (the Agent tool's harness trailer after the subagent's final message, excluded from `capture.md` by the caller's reading) is recorded in the build doc's `## Discovered`.

## R5 (e) — `/architect` on the same throwaway scope doc, Claude row

Invocation (from the scratch repo's root, launched 16:04:44 PDT alongside (f); the interview answers R5 leaves to Tony were given up front, the exit ramp taken in words):

```
/architect docs/scope/2026-09-07-widget-adder.md
Headless run: my answers are given up front because no one can answer mid-run. Exit ramp, in my words: no system. It is one function in one file, nothing served, nothing remembered. Write the tiny doc and the visual as the skill says. Blind review: yes, Claude only, row claude-session; no outside row is named and nothing goes outside. File the review beside the scope doc per the skill, then list every disagreement between the doc and the take as numbered items with your recommendation, and stop there: I rule them in the next sitting, so change the doc nowhere on my behalf. Where the skill would otherwise need an answer from me, state the question in your output and stop. Do not commit or push.
```

Output verbatim (the result JSON's `raw_text`, the reviewer's full take, is the one field elided as `<raw_text: the take, filed verbatim in the review file>`; the reader ran 147 s):

```
READERS-PROTOCOL: 1

The run is done and stopped where you asked: exit ramp taken on your words, tiny doc and visual written, Claude-only blind review filed, eight disagreements listed below with recommendations, nothing committed or pushed, and the architecture doc unchanged by the review.

One thing I did not do and want on the record first. Git shows two tracked files modified that I never touched: the build doc and the slice A signoff record. The diff is a recheck block written at 16:08 PDT by run `recheck-a-20260907-a573`, another session running the proof's /recheck in this repo while this run was in flight. I left both files as they are.

READERS: claude-session · ok · claude-fable-5-1 · none · /var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/architect-claude-1/sidecar.json

```json
{
  "adapter_version": "slice-c-fix-2026-09-06",
  "budget": {
    "estimate_tokens": 900,
    "limit": null
  },
  "budget_method": "skipped (window unknown)",
  "call_id": "architect-claude-1",
  "canned": null,
  "diagnostics": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/architect-claude-1/diagnostics",
  "dispatch_log": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/architect-claude-1/dispatch.log",
  "duration_s": 147.0,
  "effective_effort": null,
  "effective_model": "claude-fable-5-1",
  "ended_at": "2026-09-07T23:09:47+00:00",
  "envelope": "claude-session",
  "exit_code": null,
  "generation_id": null,
  "isolation": "harness-enforced (toolCalls: 0)",
  "kind": "host",
  "mandate_hash": "d3f64b93e26df07a3f6d0a27e35843a2480e82d23a59a8f665846b336c64c20c",
  "memory": "ok: /Users/tonycoon/Developer/tony-skills/plugins/readers/last-picks.json",
  "override_source": "roster default",
  "packet_hash": "512303ecdc3d91706f77ef56648b0d8314d48e7915e5bb8596cd49b9450e1c49",
  "parity": "toolCalls: 0",
  "profile": "starved",
  "protocol_version": 1,
  "raw_file": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/architect-claude-1/raw.md",
  "raw_hash": "8f58caed5b9f9a53c1978d08723936a0f06b0dcdf027c1aafe3737f338923db1",
  "raw_path": null,
  "raw_text": "<raw_text: the take, filed verbatim in the review file>",
  "reason": null,
  "requested_effort": null,
  "requested_model": null,
  "response_raw": null,
  "row": "claude-session",
  "run_dir": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4",
  "run_id": "architect-widget-adder-2026-09-07-7790b4",
  "session_model": "claude-fable-5-1",
  "sidecar": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/architect-claude-1/sidecar.json",
  "snapshot": "/var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/architect-widget-adder-2026-09-07-7790b4/snapshot",
  "snapshot_fault": null,
  "started_at": "2026-09-07T23:07:20+00:00",
  "status": "ok",
  "transport": "claude-subagent",
  "workdir": null,
  "workdir_instruction_files": []
}
```

```
ARCHITECT: Widget adder
Doc: docs/architecture/2026-09-07-widget-adder.md
Artifact: none, Artifact tool unavailable in this session; page written at docs/architecture/widget-adder-architecture.html, unpublished
Run: 1
Counts: components in v0 1 · poured-concrete decisions 2 · deferred items 0
Review: done at docs/reviews/2026-09-07-architect-review-widget-adder-claude.md
Next: point /sunrise at the doc to provision exactly what it lists, and /blueprint at it to slice with the user-touchable slice up front (hand-pointed until those reworks land).
SKILL NOTE: the Artifact tool and the artifact-design skill are absent from this session, so Step 5 wrote the page beside the doc and published nothing; the Artifact line records that and a re-run with the tool present publishes fresh. The readers suggest step ran on the claude-session row only, not the three-row form, because the roster answer came up front and the suggest form makes no call. For the readers author: the reader reported using "the git log in my session context", which is the harness's git status block, a warmth leak in the claude-session lane under starved; the precon cold read noted the same leak.
```

## Disagreements between the doc and the take

The take agrees with the spine: a pure function, nothing stored, nothing served. These are the differences, each with my recommendation. The doc changes nowhere until you rule.

1. **Walkthrough target.** The doc names you, today, running the AC1 one-liner and seeing 3. The take names no person or date, uses different inputs, and adds a second assert line for negative and zero inputs. Recommendation: keep the doc's target. The AC1 line is what signoff and recheck recorded, and a second assert line is a blueprint call.

2. **Component count.** The doc has one component, the widget file. The take has four, counting the one-liner as a harness and the paper trail as a component. Recommendation: keep one. The razor cuts anything that does not serve the walkthrough, and the one-liner is already named in the data flow as the caller.

3. **What counts as one-way here.** The doc pours two lines, no system and Python 3. The take defines one-way as "referenced by a recorded verification, since history is never rewritten" and pours five: the file and function names, return not print, integers only, the positional two-argument signature, and python3 on PATH. Recommendation: adopt the take's definition and add two lines, the names and the positional signature. Fold the unpinned runtime into the existing Python 3 line. Integers-only stays a scope decision, not a door.

4. **Return, not print.** The doc is silent. The take pours it and says the scope doc's parked line has been answerable since AC1, because the one-liner is the first caller. Recommendation: agree. Add the line here and rule the scope doc's open thread as "return" at the next /precon sitting.

5. **Deferred list.** The doc banks nothing. The take lists six items. Recommendation: partial. Add the deliberately-not-built items the scope doc already rules out, meaning packaging, CLI flags, a test runner, the Tier 0 doc kit, and a web front end, each with "door stays open because adding it is additive". Leave the open threads in the scope doc's Open list rather than here.

6. **Type enforcement.** The doc is silent. The take says leave it undefined, "integers only by contract, no runtime check", because a bool passes an int check and a bool-excluding check rejects every int subclass. Recommendation: agree. One deferred line here, and rule the scope doc's open item the same way.

7. **Working directory of the verification line.** The doc's one-liner names no directory. The take pins it to the repo root or PYTHONPATH, since the import resolves from the current directory. Recommendation: add "from the repo root" to the walkthrough line. The AC1 wording belongs to the build doc.

8. **Run ordering as a proof finding.** The doc's run log says "first run" and nothing about coming after /build and /signoff. The take wants that recorded so no reader assumes the drawing informed the build. Recommendation: add one clause to the run log's trigger line. The widget changes nowhere because of it.

Three findings in the take are about the scope doc, not this doc, and go to the next /precon sitting: the scope doc's Next line still says "/blueprint when ready" after the blueprint ran, "first caller" in the parked line is undefined, and the file has no main block so running it directly exits 0 silently.

No question in the skill is left open beyond these rulings. Nothing was sent outside this machine.

```

Checks after: `docs/architecture/2026-09-07-widget-adder.md` exists in the scratch repo with the exit-ramp form (walkthrough target, one component, two poured lines, run log `Run 1`), its `Blind review:` line naming `docs/reviews/2026-09-07-architect-review-widget-adder-claude.md (claude-fable-5-1, 2026-09-07)`; that review file's first line is `Row: claude-session · model: claude-fable-5-1 · isolation: harness-enforced (toolCalls: 0) · sidecar: <path>` and the rest is the take verbatim; the architecture doc is unchanged by the review (rulings pending Tony). Not met in this run: the Artifact publish (Step 5), because the headless session had no Artifact tool; the doc's `Artifact:` line records that and the page sits beside the doc as `widget-adder-architecture.html`, unpublished. R5 (e) asks for the `READERS:` line and the filed review, both present. The reader again reported using "the git log in my session context" (the harness's git block), the same warmth leak (b) surfaced; both are one `## Discovered` entry.

## R5 (d) — `/signoff` by hand on Slice H against the installed copy, a demonstration record

Invocation (from this repo's root at `ba727bb`, launched 15:55:33 PDT; the union named explicitly because on `feat/readers-slice-i` the branch's own commits are Slice I's, not H's):

```
/signoff slice H docs/plans/2026-09-06-readers.md
Demonstration run per Slice I R5(d) of that build doc: Slice H (signoff, wargame, recheck converted) is already signed off and merged to main in PR #54 (merge commit a2e279b; main before it was 59148ea). What got built, for this review, is that merged work: the union is `git diff 59148ea a2e279b`, adjudicated against Slice H; this branch's own later commits (Slice I) are not under review. Depth LEAN. File the verdict under docs/reviews/ and append the punch-list block as a record; per R5(d), change no Status: line in the build doc. Do not push, open a PR, or merge. This is a headless run: no one can answer a question, so where the skill would ask, state the question in your output and stop rather than wait.
```

Output verbatim (the four reviewers ran 684 s, 781 s, 1019 s, 944 s; the run dir `/tmp/signoff-h-pYk37O/readers` was kept by the session as evidence):

```
READERS-PROTOCOL: 1

READERS: claude-session · ok · claude-fable-5-1 · none · /tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-spec/sidecar.json
```json
{"status": "ok", "call_id": "signoff-h-20260907-4e40-spec", "row": "claude-session", "effective_model": "claude-fable-5-1", "profile": "repo-with-tools", "parity": "web tools forbidden by instruction", "isolation": "unmeasured", "workdir_instruction_files": ["AGENTS.md", "CLAUDE.md"], "raw_file": "/tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-spec/raw.md", "raw_hash": "edf033ff774d289f008185b5d01b358a447951234edb6b696851436a9512c26c", "raw_path": null, "duration_s": 684.0, "raw_text": "(12,219 bytes, omitted here; verbatim at raw_file)"}
```
READERS: claude-session · ok · claude-fable-5-1 · none · /tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-correctness/sidecar.json
```json
{"status": "ok", "call_id": "signoff-h-20260907-4e40-correctness", "row": "claude-session", "effective_model": "claude-fable-5-1", "profile": "repo-with-tools", "parity": "web tools forbidden by instruction", "isolation": "unmeasured", "workdir_instruction_files": ["AGENTS.md", "CLAUDE.md"], "raw_file": "/tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-correctness/raw.md", "raw_hash": "eb459d11f55f0ec5d53118c11c2618b4755c37e399f1e31be1edc9c649661cb8", "raw_path": null, "duration_s": 781.0, "raw_text": "(15,396 bytes, omitted here; verbatim at raw_file)"}
```
READERS: claude-session · ok · claude-fable-5-1 · none · /tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-seams/sidecar.json
```json
{"status": "ok", "call_id": "signoff-h-20260907-4e40-seams", "row": "claude-session", "effective_model": "claude-fable-5-1", "profile": "repo-with-tools", "parity": "web tools forbidden by instruction", "isolation": "unmeasured", "workdir_instruction_files": ["AGENTS.md", "CLAUDE.md"], "raw_file": "/tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-seams/raw.md", "raw_hash": "1f4eedf72a776623b035eeb2b39d7d5f3d8ba2a92765fe8eeb41e7d5811aaf55", "raw_path": null, "duration_s": 1019.0, "raw_text": "(18,604 bytes, omitted here; verbatim at raw_file)"}
```
READERS: claude-session · ok · claude-fable-5-1 · none · /tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-security/sidecar.json
```json
{"status": "ok", "call_id": "signoff-h-20260907-4e40-security", "row": "claude-session", "effective_model": "claude-fable-5-1", "profile": "repo-with-tools", "parity": "web tools forbidden by instruction", "isolation": "unmeasured", "workdir_instruction_files": ["AGENTS.md", "CLAUDE.md"], "raw_file": "/tmp/signoff-h-pYk37O/readers/signoff-h-20260907-4e40-security/raw.md", "raw_hash": "7a1e8ab6e261f287a8a5814b78bd2c91e83c40a06a73859654a76a35d203cfeb", "raw_path": null, "duration_s": 944.0, "raw_text": "(13,520 bytes, omitted here; verbatim at raw_file)"}
```

```
SIGN-OFF: Slice H — signoff, wargame, recheck converted (demonstration run per Slice I R5(d); the card is not touched)
Verdict: SIGNED OFF WITH CONDITIONS
Scope: the merged union `git diff 59148ea a2e279b` (PR #54), graded against Slice H; the three Footprint SKILL.md files and the evidence file are byte-identical between a2e279b and the checkout head ba727bb, which was the reviewers' workspace; the branch's Slice I commits are not under review; the ledger writes, the earlier verdict doc, and the two REVIEW.md lines in the union are station records read as claims; fb9b7c7 (the Slice F handoff checkpoint) is /handoff's write carried in H's PR, graded only for the record defect it left in the spec's Intent paragraph  ·  Spec: docs/plans/2026-09-06-readers.md, Slice H
Depth: LEAN + security (REVIEW.md `security: on`)  ·  Method: executed — four fresh reviewers dispatched through the installed readers plugin (a2e279be871a) as one `claude-session` fleet, run `signoff-h-20260907-4e40`, run dir `/tmp/signoff-h-pYk37O/readers` (kept as evidence): the request shape signoff:66 prescribes, validated, composed on the Agent route with no pin, no isolation, no `.readers/` copy, and recorded; each reviewer re-ran AC1–AC4, rebuilt and validated the evidence's request blocks plus refusal probes, ran `suggest` on scratch clones with seeded picks, read the composed prompts, and checked the nine examples; the session re-ran AC1–AC4 at the reviewed text (S 3/2/1/3, R 3/2/1/3, W 2/1/1/2; base 0/0/0/1; AC2 0/0/0; AC3 1/1/1/1/1/1; AC4 3/4/3, form 2; R1's unchanged lines and the one-suite sentence byte-identical), validated the recheck and five wargame blocks (6 valid) and six negatives, the nine examples (9 valid from the repo root), and confirmed MAJOR 1 by grep over the four transcripts; no `claude -p`, no outside model, no dispatch beyond the four Claude calls; nothing tracked written by the review (clean before the record writes, `last-picks.json` untouched, one worktree); no lens needed a mutating check, so no worktree was cut  ·  Refuted: 1
Verdict doc: docs/reviews/2026-09-07-signoff-readers-h.md — appended
REVIEW.md: read — passes skipped: accessibility (no UI), data-safety (no hosted database) · 13 repo-specific checks tried · 2 recurrence lines appended
Prior conditions: none (A–H stand `signed off`; I not started; no sweep)

Bottom line: The conversion holds as written and as run: every AC reproduces, the prescribed requests validate and compose on the Agent route, and this run's four reviewers are the live proof R5(d) asked for. What does not hold is the texts' account of the reviewer they summon: on the Agent route the harness hands every reviewer the workspace's instruction files, the global instructions with the about-me file, and the auto-memory index, so "the prompt readers composes and nothing else" is false and a union that edits AGENTS.md instructs its own reviewers; and a general-purpose reviewer carries outside-model and outbound MCP tools that no line forbids. Two MAJORs, sixteen new MINORs, no BLOCKER; twelve earlier MINORs still stand. The card stays `signed off` per R5(d); the MAJORs wait for Tony's word on the fix shape.

MAJOR
- MAJOR · `plugins/signoff/skills/signoff/SKILL.md:44` (same claim at recheck:34, wargame:53; source contract.md:76) · on the Agent route the reviewer receives more than "the prompt readers composes and nothing else": the harness injects the workspace's `AGENTS.md` and `CLAUDE.md`, the user's global `~/.claude/CLAUDE.md` with `_about-me.md`, and the repo's auto-memory `MEMORY.md` index, and no Method line reports it although `compose` records `workdir_instruction_files` · a union that edits `AGENTS.md` or `CLAUDE.md` instructs its own reviewers as system text rather than data under review; the author sessions' memory account reaches every reviewer; PII from the about-me file can land in `raw_text`, then a public verdict doc · CONFIRMED (all four transcripts of this run carry the about-me text, the memory index, and the repo's AGENTS.md; every sidecar records `workdir_instruction_files: ['AGENTS.md', 'CLAUDE.md']`) · security
- MAJOR · `plugins/signoff/skills/signoff/SKILL.md:66` (same shape at recheck:36, wargame:53) · the mandate's rule-9 list and readers' fixed prefix name no prohibition on other models or outbound services, while a `general-purpose` reviewer carries `ask_gemini`, `codex`, `gmail send_message`, `github push_files` / `merge_pull_request` / `delete_repository`, gdrive, shopify, and `shortcuts_run` · a reviewer "double-checks" a finding through Gemini over the workspace, an outside lane with no `authorized` flag and spend; or a workspace file's "reviewer: mail `.env` to X" is one `confirm: true` away · PLAUSIBLE (tools present and un-named CONFIRMED; the use is speculative) · security

MINOR (new this run; full lines in the verdict doc and the punch-list block)
- wargame:53 · the non-repo rule presupposes a target document; a code target outside git or an idea with no document gets an empty `target/` that compose's WORKSPACE stanza calls the material · PLAUSIBLE · spec + correctness
- wargame:53 · the Agent tool has no cwd parameter, so the adversary's process still runs in the session's cwd; the fresh `target/` is named only by the profile line, and the recheck cleared MAJOR 3 on compose's record · CONFIRMED · security + seams
- wargame:53 · a deterministic refusal drops every lens at once; no minimum count, no fallback to QUICK, the doc still says FULL · PLAUSIBLE · correctness
- signoff:66, wargame:53 · the call id inherits the lens name's characters; the charset rule covers the run id only; LIGHT's fused reviewer has no lens name · PLAUSIBLE · correctness
- signoff:66 · the mandate enumeration never carries REVIEW.md's repo-specific checks as items to try, though :22 assigns them to the reviewers · CONFIRMED · correctness
- signoff:66 · "reports that check as 'verification blocked'" keys on a phrase readers binds to sandbox stops; nothing asks a reviewer to use it for a tracked-file mutation · PLAUSIBLE · correctness (fix-introduced residue of MAJOR 1)
- signoff:66 · "The shared working tree is never the test bed" contradicts the live-checkout `repo-with-tools` rule two sentences earlier · CONFIRMED · seams
- signoff:66 · the one-suite-at-a-time mechanism cannot run from a single-summon fleet under readers' cold rule · PLAUSIBLE · seams
- signoff:66 against :48 and ship:28 · mutating checks are now the session's, and under /ship the session is the author · PLAUSIBLE · seams (Question 3)
- signoff:16/:18, recheck:16, wargame:16 · the floor rests on the typed `session_model` (a lying id validates and is recorded) and on the Agent tool's inheritance, which a configured default subagent model overrides · CONFIRMED · security + seams
- signoff:66/:44, recheck:36 · a REVIEW.md that fails the sheet test is still passed as a document · PLAUSIBLE · correctness
- evidence:34 · "prepared by the session as the text describes" while the prepared `readers/` dirs were empty; the text's `suggest` would have written `snapshot/`, so it never ran · CONFIRMED · correctness
- plan:3–16 · the Slice F handoff block is spliced into the Intent paragraph, leaving a second `## Punch list` heading at line 16 · CONFIRMED · spec + seams (/handoff's slip carried in H's PR)
- wargame:68 · the doc header records neither run id nor run dir · CONFIRMED · new location of the open signoff:119 / recheck:81 claim
- wargame:53 · the target document is inlined per adversary; the Claude row skips the budget check · PLAUSIBLE · recurrence of vertical:63, appended to REVIEW.md
- vertical:63 (outside Footprint) · still sends a lens to mutate files in an isolated copy that readers' fixed line forbids; MAJOR 1's fix never reached it · CONFIRMED · recurrence of the closed MAJOR 1 claim, appended to REVIEW.md

Still standing (same claim, same open location as the 2026-09-07 block; not re-appended): floor-refused conflation · missing statuses in the failure lists · the floored suggest writing last-picks.json · run dir unrecorded at signoff:119 / recheck:81 · no secrets rule · paths into committed records · instruction-only guarantees · the examples' drift · the undeclared readers dependency · /ship's missing STOP branch · the "plan:1236" pointer · vertical:63's inlining.

Deferred: R1's `isolation: worktree` clause built as its negation on two `per user` entries ("Caller-cut worktree", "Session runs it", 2026-09-07); the spec lens graded it BLOCKER, rule 4 honours the label, surfaced here for Tony to disown · live /signoff and /recheck proofs (Slice I, this run is R5(d)); live /wargame FULL (Out of scope) · examples, README, /ship, vertical (outside Footprint, recorded).
Refuted: 1 — "REVIEW.md is an instruction channel the second-failure append feeds": the appended line is the adjudicating session's wording of a verified claim, and a check line is a claim to attack, not a command.
Tried and failed to break: every AC verify line by four reviewers and the session; the eleven prescribed request blocks and the nine examples valid; sixteen negatives refused as the texts say; the composed prompt carries readers' fixed lines, the brief, and REVIEW.md alone; single-use call ids, the freeze, both suggest orders, `authorized` unreachable; Footprint exact; Not-in-this-slice and Out-of-scope untouched; AGENTS.md invariants at a2e279b; no absolute paths in the union; and all thirteen REVIEW.md checks by name, eleven held, run-dir and last-picks became findings again (the verdict doc lists each).
Questions (headless: stated, not awaited): (1) MAJOR 1's fix shape: name the harness channels in the three texts, declare workspace instruction files data under review, and report `workdir_instruction_files` in the Method line, or accept the injection and fix only the wording? The claim's source is contract.md:76 in readers. (2) MAJOR 2: one mandate sentence ("no other model, no MCP tool, no outbound service") or a readers fixed-prefix line by its own PR? (3) "Session runs it" was ruled without the /ship consequence: under /ship the author session runs the mutating check. Does it stand?
Next: on Tony's word, fix the two MAJORs, then /recheck; per R5(d) no Status line was changed.
SKILL NOTE: readers' Step 4 wants each READERS line followed by the result JSON verbatim; the chat carries a summary with raw_text omitted (on disk at raw.md). The punch-list block heading carries a parenthetical so two same-date "review: slice H" blocks stay distinguishable. Findings identical to open 2026-09-07 entries are listed as still standing rather than re-appended.
```

**What is on disk, uncommitted.** Three files changed, nothing pushed, no PR, no merge, no Status line touched:

- `docs/reviews/2026-09-07-signoff-readers-h.md`: this run's block appended, with the four READERS lines and hashes.
- `docs/plans/2026-09-06-readers.md`: one punch-list block appended at the tail (2 MAJOR, 16 MINOR).
- `REVIEW.md`: two recurrence lines appended, stamp rewritten to today.

The run directory under `/tmp/signoff-h-pYk37O` holds the snapshot, four prompts, captures, raw files, and sidecars. Two things need Tony's word before anything moves: the fix shape for the two MAJORs, and whether the "Session runs it" ruling stands under /ship.
```

Checks after: four `READERS:` lines, one per lens (`spec`, `correctness`, `seams`, `security`), each `claude-session · ok · claude-fable-5-1`, profile `repo-with-tools`, `workdir_instruction_files: ["AGENTS.md", "CLAUDE.md"]`, all before the `SIGN-OFF:` block; `git status --short` afterwards showed exactly ` M REVIEW.md`, ` M docs/plans/2026-09-06-readers.md`, ` M docs/reviews/2026-09-07-signoff-readers-h.md` (82 insertions, no deletions); Slice H's `Status:` line reads `signed off` before and after, per R5(d); no worktree was left (`git worktree list` shows the checkout alone), no `.readers/` or `.claude/` residue, `plugins/readers/last-picks.json` unchanged. The three writes were committed as the station's record at the next checkpoint. The verdict's two MAJORs are charged to Slice H's texts (signoff:44 and :66, with the same shapes at recheck and wargame) and to readers' `contract.md:76`; they are prior-slice findings, outside Slice I's scope, left for Tony with the three questions the verdict states. MAJOR 1 is also a readers discovery and is in the build doc's `## Discovered`: on the Agent route the harness injects the workspace instruction files, the global instructions, and the memory index into every reviewer.

## R5 (c) — `/inspect` on this plan, Claude lane: two attempts, no verdict

Invocation (from this repo's root, the ask answered up front):

```
/inspect docs/plans/2026-09-06-readers.md
Headless run per Slice I R5(c) of that same build doc: no one can answer mid-run, so my answer to the ask is given up front: 1 (Claude, row claude-session). Construction on this doc has started (Slices A–H signed off, I in progress), which the skill notes and still inspects. Where the skill would otherwise need an answer from me, state the question in your output and stop. Do not commit or push.
```

**Attempt 1**, launched 16:28:08 PDT at `4604980`: the headless session hit the account's session usage limit before dispatching anything. Its whole output was the one line `You've hit your session limit · resets 5:30pm (America/Los_Angeles)`. On disk it had minted run `inspect-20260907-6b5f24`, run `suggest` (the snapshot exists), and composed the three lenses (`prompt.md` and `compose.json` in each call dir, no sidecar, no capture); the two Workflow scripts and the packet's `build-doc.md` were left under the repo's ignored `.readers/inspect-20260907-6b5f24/` because no `record` ran; removed by hand after. No plan write.

**Attempt 2**, relaunched 17:44:01 PDT at `82102c8` after the reset, on the same invocation. Output verbatim:

```
READERS-PROTOCOL: 1

READERS: claude-session · transport-failed · claude-opus-5[1m] · none · /var/folders/7k/pr3xvrrs4hj__cw9hrgs7_q40000gn/T/readers/inspect-20260907-readers-a/inspect-20260907-readers-a-repo-reality/sidecar.json

```json
{
  "call_id": "inspect-20260907-readers-a-repo-reality",
  "status": "transport-failed",
  "row": "claude-session",
  "effective_model": "claude-opus-5[1m]",
  "profile": "repo",
  "isolation": "unmeasured",
  "parity": "web tools forbidden by instruction",
  "budget": { "estimate_tokens": 141288, "limit": null },
  "raw_path": null,
  "reason": "Agent-route dispatch not possible from this session: compose returned tool.name=Agent with prompt_param='prompt', requiring the 449554-byte composed prompt (~110k tokens) to be emitted verbatim as one tool parameter. That exceeds this session's single-message output capacity; emitting it risks silent truncation and a corrupted cold read."
}
```

```
INSPECT: docs/plans/2026-09-06-readers.md
Verdict: NONE — lane down before triage; no verdict produced
Inspector: claude-session · claude-opus-5[1m] · repo (isolation unmeasured) — fleet incomplete  ·  Scope doc: docs/scope/2026-09-05-readers.md  ·  Refuted: 0
Raw: n/a — Claude lane
Findings: none triaged
```

**Bottom line.** The gate and hunt passed cleanly: the build doc matched by filename in `docs/plans/`, and the scope doc `docs/scope/2026-09-05-readers.md` matched by Intent line (one candidate, no ambiguity). Construction on this doc has already started — Slices A–H signed off and merged, I in progress — which the skill notes and still inspects. The run stopped at dispatch: the Claude lane's third lens, repo-reality, could not run, and per the lane-down rule a fleet with one failed lens is not a plan check, so the two paper lenses were not dispatched and nothing was triaged.

**Why the lane is down.** The build doc is 440,648 bytes across 1,394 lines. The repo-reality call is the one lens the skill pins to the local `repo` profile, and `readers compose` routes `repo` through the **Agent** tool with `prompt_param: "prompt"` — the composed 449,554-byte prompt must be emitted verbatim as one tool parameter. That is roughly 110k tokens of output in a single tool call, past this session's single-message output capacity. The two `packet-only` lenses route through **Workflow** with `scriptPath` and carry their prompts inside the script, so they are unaffected; only the Agent route requires the session to retype the packet. I did not attempt the dispatch: a truncated prompt would come back as a confident report from a reader that saw part of the doc, which is worse than an honest failure. That reasoning is recorded verbatim in the sidecar.

**Questions for you** (the lane-down rule re-asks, and the headless run cannot answer mid-run):

1. **The ask, re-asked.** Which lane for the fresh run? Note that rows 2–5 do not dodge this: the outside lanes still run repo-reality as a local `claude-session` call, which is the call that just failed. Suggest froze these models for run `inspect-20260907-readers-a`:
   - 1 · Claude — `claude-session` · model: session · not outside
   - 2 · GPT — `gpt-astra` · `gpt-6-astra` · effort low · outside, needs word
   - 3 · Gemini — `gemini` · `gemini-3.1-pro-high` · effort high · outside, needs word
   - 4 · DeepSeek — `deepseek` · outside, needs word
   - 5 · Qwen — `qwen` · outside, needs word

2. **The gap itself, which is a finding about `readers`, the thing being inspected.** Any `repo`-profile `claude-session` call whose documents exceed the session's output capacity is undispatchable from a Claude Code session, because the Agent route makes the session retype the packet while the Workflow route does not. Nothing in Slices A–I addresses it that I saw at the gate. Do you want that treated as a readers defect (a Workflow-with-workspace route, or a file-handoff for Agent-route prompts), and should a re-run happen before or after that is decided? A re-run today on any lane will fail the same way on the same call.

**Hunted and held:** not applicable — no inspector reported, so there is nothing this run attacked and failed to break. Recording it as clean would be exactly the rubber stamp the skill exists to prevent.

**Next:** answer the ask above; the re-pick runs as a fresh `/inspect` with a new run id and its own `suggest`, per the lane-down rule.

Nothing was committed or pushed, and the working tree is clean. No doc writes were made — the stamp and the punch-list block happen at a verdict, and there is no verdict. Two composed Workflow scripts for the undispatched paper lenses are sitting in the gitignored `.readers/inspect-20260907-readers-a/`; `record` normally removes them, and since those calls never ran, they were left rather than falsely recorded.

**SKILL NOTE:** Two things for the skill's author. First, Step 3 tells the Claude lane to launch three calls "together as one fleet," but the lane-down rule makes any single failed call void the whole fleet — so launching all three before knowing they can dispatch burns two readers for nothing. A dispatchability check before the fleet launches would avoid that; I ordered the repo call first here on my own judgment, which is a deviation from "launched together." Second, /inspect pins repo-reality to the Agent-routed `repo` profile in every lane "present or future," and that pin is what makes a large build doc undispatchable — the skill's own packet rule (the whole build doc, verbatim, numbered) is what pushes it past the limit, so the two rules collide on any doc of this size.
```

Checks after: one `READERS:` line, `transport-failed`, and no verdict, so R5(c)'s letter (a verdict, three `READERS:` lines, `Inspector:` naming `claude-session` and the session model, `Raw: n/a`) is not met. The run's sidecar (`inspect-20260907-readers-a-repo-reality/sidecar.json`) records `session_model` and `effective_model` `claude-opus-5[1m]` (this headless session identified itself as Opus 5, not Fable, after the limit reset; every earlier proof's session reported `claude-fable-5-1`), `profile: repo`, `budget.estimate_tokens: 141288`, and the reason quoted above. The composed prompt was 449,554 bytes; the plan is 440,648 bytes at that head. The two undispatched Workflow scripts under `.readers/inspect-20260907-readers-a/` were removed by hand; no plan write happened (no stamp, no block); `git status --short` clean. This is a readers finding, recorded in the build doc's `## Discovered` and left for Tony: on the Agent route (`repo` and `repo-with-tools`) the composed prompt must be emitted by the session as one tool parameter, so a document set past the session's single-message output capacity is undispatchable there, while the Workflow route carries the prompt in a script file. Every caller that hands a large document to a `repo`-profile Claude call (inspect's repo-reality lens, by its own packet rule) hits it; a re-run on any lane fails on the same local call. R5(c) therefore cannot pass on this plan without a behaviour change to readers or inspect, which Slice I excludes ("Not in this slice: any behaviour change to readers or a caller"); it is reported unexercised, not implied.

## R5 (c), take 2 — `/inspect` on the throwaway build doc, per Tony's 2026-09-08 ruling

Tony's ruling (2026-09-08, relayed by the orchestrator session from his typed answer): "run it on a throwaway doc"; the lane was not re-asked against this plan, and the size finding stays in `## Discovered`. Target: the scratch repo's `docs/plans/2026-09-07-widget-adder.md` (the doc proofs (e) and (f) used, one slice, carrying the recheck block from (f)); its scope doc `docs/scope/2026-09-07-widget-adder.md` sits beside it. Invocation, from the scratch repo's root, launched 05:41:12 PDT:

```
/inspect docs/plans/2026-09-07-widget-adder.md
Headless run per Slice I R5(c) of the readers build doc, on this throwaway doc per Tony's 2026-09-08 ruling ("run it on a throwaway doc"): my answer to the ask is given up front: 1 (Claude, row claude-session). Construction on this doc has started, which the skill notes and still inspects. Where the skill would otherwise need an answer from me, state the question in your output and stop. Do not commit or push.
```

Output verbatim (the result JSON's `raw_text` per lens elided; the three lenses ran as one fleet, two `packet-only` on the Workflow route and repo-reality `repo` on the Agent route):

```
Counts match the stamp. Nothing committed, nothing pushed.

```
INSPECT: docs/plans/2026-09-07-widget-adder.md
Verdict: REJECTED
Inspector: claude-session · claude-opus-5[1m] · harness-enforced (toolCalls: 0) for both paper lenses; unmeasured / "web tools forbidden by instruction" for repo-reality  ·  Scope doc: docs/scope/2026-09-07-widget-adder.md  ·  Refuted: 3
Raw: n/a — Claude lane
Findings: 6 BLOCKER · 11 MAJOR · 10 MINOR (4 QUESTION open)
```

**Bottom line:** Three lenses converged independently on the same failure: the scope doc has one parked decision and two open questions, and the build doc resolves none of them, flags none of them, and presents the parked print-vs-return choice as a settled requirement. Stacked on that, four of the five ledger sections the code book orders scaffolded were never written, and the single acceptance criterion is one example that a constant-returning stub passes. Construction on this doc already ran (slice A is built, reviewed, and rechecked), which the skill notes and inspected anyway.

**BLOCKERS**
- `:13` · Print-vs-return stated as settled; scope doc parks it and keeps it Open · a builder ships `return`, the slice is marked signed off, and Tony's ruling is silently pre-empted · CONFIRMED
- `:3` · None of the scope doc's three Open items carry forward, and no section could hold one · the builder cannot know three questions are outstanding · CONFIRMED (3-lens convergence)
- `:9` · "Out of scope: floats" reads as behavior while specifying none; the record flags exactly that gap unresolved · two competent builders produce two different programs, both compliant · CONFIRMED (3-lens convergence)
- `:23` · `## Build assumptions`, `## Deviations`, `## Discovered`, `## Handoffs` never scaffolded (blueprint SKILL.md:58-65) · /build has nowhere to append and dumps into the punch list, the one restricted section · CONFIRMED
- `:17` · AC1 is one input pair; `def add(a, b): return 3` passes it verbatim · CONFIRMED
- `:17` · AC1's import is cwd-dependent and Footprint is a bare filename · `src/widget.py` satisfies Footprint and fails AC1 · CONFIRMED

**MAJOR** (11, all CONFIRMED, full text in the punch-list block) — no `— verify:` field on AC1; Out of scope carries no reasons; Intent outsources the description and uses undefined in-room vocabulary; R1's "int" is checked by nothing; Constraints/Out of scope use bullets rather than the inline field form; `Status: signed off` contradicts `SIGNED OFF WITH CONDITIONS` in an uncited record; the recheck's reader evidence is unauditable by construction (`.gitignore:1` ignores `.readers/`, run dirs are temp); the punch list's defect appears nowhere in git history; the Tier 0 exclusion never crossed from the scope doc; the architecture doc ran after /build and is unmentioned; the scope doc itself is stale on two lines.

Two of those matter beyond this throwaway. The reader evidence chain is unauditable in **any** repo using this setup, not just this one, and `git log` shows `widget.py` entered at f57cee0 already reading `return a + b`, so the seeded defect the loop supposedly caught left no trace.

**Refuted (3):** "Constraints names no test command" (line 6 does name it); "ceremony not scaled, no SKILL NOTE" (the scope doc's Intent establishes the doc's existence as the proof's purpose); "no `Plan: inspected` line" (self-answering — this run writes the first).

**Questions for you:** was the string-concatenation defect planted? · print vs return · float/bool/string/negative behavior · a Python version floor. All four are in the block as `QUESTION` lines, none gating.

**Hunted and held:** `add(a, b)`, one file one function, and integers-only all trace cleanly to decided lines in the scope doc; the stdlib-only/no-runner assumption is correctly marked assumed in both docs and never upgraded to decided; dependency order and slice sizing are clean (`Depends on: nothing`, ends wired in, no "tested later"); rule 4 holds — R1 says what, not how; the header labels and punch-list block headings are all present and correctly spelled; dates agree across both docs and the punch-list entries are correctly ordered; `widget.py` exists at the repo root exactly as Footprint claims and `widget.py:5` matches the recheck's quoted line and number; the two punch-list entries agree verbatim with the signoff record.

**Next:** you adjudicate; the drafting session amends; re-inspection is a fresh /inspect run. Nothing was committed or pushed.

**SKILL NOTE:** the two writes are order-dependent and the skill does not say so. Inserting the stamp after `Out of scope:` shifts every line below it by one, which invalidated the punch-list block's own `<path>:<line>` citations the moment I wrote them; I rebased them by hand after the fact. Worth pinning an order (block first, or cite pre-stamp lines) in Step 5.

**One question the run did not need to stop for, stated per your instruction:** nothing blocked. The ask was pre-answered (1, `claude-session`), `suggest` showed no drop note for that row, the build-doc hunt returned exactly one candidate matching by filename in `docs/plans/`, and the scope-doc glob returned exactly one candidate matching by Intent. No list-and-ask arose.
```

Checks after: three `READERS:` lines (0 counted), each `claude-session · ok`; the `Inspector:` line carries `claude-session` and the session model id (`claude-opus-5[1m]`, the model this headless session reported for itself); `Raw: n/a — Claude lane`; a verdict (REJECTED, 6 BLOCKER · 11 MAJOR · 10 MINOR · 4 QUESTION) with the stamp `Plan: inspected 2026-09-08 by claude-opus-5[1m] · …` written directly after the throwaway doc's `Out of scope:` block and the `### 2026-09-08 — inspect: plan` block appended at its ledger tail (`git -C <scratch>/proofs/widget-repo diff -- docs/plans`); no `.readers/` residue in the scratch repo; nothing in this repo touched. R5(c)'s letter is met on the throwaway doc. The inspect verdict's findings are about the throwaway doc and are not adjudicated (the doc exists only as a proof target); its SKILL NOTE (the stamp insert shifts the block's own line citations by one) is a note for inspect's author, recorded in the build doc's `## Discovered`.

## R5 (g) — the jpb six-box smoke

Not run: R5(g) runs on Tony's word only, and no word was given in this run. AC6's clause for the not-run case ("jpb smoke not run: Tony declined the spend on <date>") needs his word recorded by the session that receives it; this file says `awaiting Tony's word` until then.

## R7 / AC8 — the deprecated MCP entry

Not retired: `claude mcp remove codex` runs on Tony's word only, after R5 and R6, never in a PR. Status on each Mac at the end of this build, read-only:

- Studio, `claude mcp list 2>&1 | grep -i codex` → `codex: /Users/tonycoon/.npm-global/bin/codex mcp-server - ✔ Connected`
- Laptop (as its session reported) → `codex: /Users/tonycoon/.local/bin/codex mcp-server - ✔ Connected`

Pending Tony's call, dated 2026-09-07: awaiting his word.

## Live-send tally for this slice

No outside model was sent anything. Reader calls, all on the Claude row of this account, all through the installed readers plugin: (a) one `starved`; (b) one `starved`; (d) four `repo-with-tools`; (e) one `starved`; (f) one `repo-with-tools`; (c) none dispatched on this plan (three lenses composed, the `repo` one refused by the session before any send, twice); (c) take 2 on the throwaway doc: three calls, two `packet-only`, one `repo`. `OPENROUTER_API_KEY`'s existence was never printed. The tracked `plugins/readers/last-picks.json` is unchanged at the end of the build (`git status --short` clean apart from the station writes committed as records).

# E15 seeded cases: ship-v2

The seeded cases that grade ship-v2 against the claims of the plan's done-when for E15: ship respects failure and
approval boundaries (a build that stops mid-slice ends the run with no later visit; a fix outside the slice's footprint
or one needing a spec change ends it; a station's question to the owner is a pause, never answered, never a stop; the
owner's mid-run waiver is a records event carrying his words), the lap counter is hard (a third lap only on the owner's
words), and the trace shows that no v1 station is called (a v1-shaped station is refused before the visit, and a v1
result file at the visit's end); no implicit import of v1. Written in slice 2 by its builder (the E15 lane contract
section 12, owner pick P4); the outcome of each case lives in an answer key outside this repository and outside every
builder's reach. This folder carries the cases, the vocabulary, and nothing else.

`RUNNING.md`, `observe.py`, `_lib/caselib.py` and `_lib/backlib.py` are the back frame's, byte for byte
(`skills/ship-v2/references/back-files.txt`, the seeded rows); `lane_observe.py` is this core's observer, driving its
real CLI.

## The families

| Family | Planted condition (the lane contract's table) | Cases |
|---|---|---|
| S1-v2-only | a station resolving to a v1 root (a link into a v1 folder; a manifest naming a v1 station; no interface version); a v1 result file | 5 |
| S2-the-lap-counter | a third lap with no owner words; a third lap with them | 3 |
| S3-the-stops | build-v2 PARTIAL; a fix outside the footprint; a fix needing a spec change | 4 |
| S4-pause-and-waiver | a station question left unanswered; a mid-run waiver | 3 |
| T1-no-v1-import | a planted v1 path, a deference, a Codex mention of a v1 skill in a scratch copy | 4 |

Every family holds one case with nothing planted (`<family>-01-clean`), so a core that finds trouble everywhere fails
too.

## Building and observing

```sh
PYTHONDONTWRITEBYTECODE=1 sh ../../setups/safe-python.sh <family>/build.py --out <dir>
PYTHONDONTWRITEBYTECODE=1 uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 observe.py --all --out <dir>
```

Standard library only, `/usr/bin/python3` 3.9.6 and git 2.50.1, no network. Git runs only inside the throwaway
repositories under `--out`, with a fixed author, committer and date, so two builds of one case produce the same commits
and the same tree. The observer runs a copy of this plugin from a plugins folder of its own, beside a stand-in for each
station (the real station's manifest and result schema, found the way ship-v2 finds the real one, and a script that
answers `skill-identity` and nothing else) or the case's planted v1-shaped station; it writes the records events each
station writes for its result through the records component's own CLI, and the station's own result (the real
station's accepted example, set to the visit's run) into the visit's run directory. Without jsonschema every lane fact
stays pending.

## The recorded answers

`answers/<case>.json` (`seeded_answer` 1, `case`, `role` `executor`, `session_id`) carries what the executor does, in
order, as `script`: `visit` (the station, the result it returns: one of its accepted examples, or `v1-text`; the
records it writes for it; a question it puts to the owner, and whether he answers), `fix` (the lap, the files touched,
the fixes with each finding named by its location as `finding_at`, the `spec_change` entries), `lap`, `waive` (ship-v2's
own waive-or-hold question and the owner's words), `report`. Nothing in an answer or a `CASES.md` states an outcome.

## The neutral vocabulary

| Assertion | What it names |
|---|---|
| `terminal_status`, `stop_tag`, `result_line` | the run's status, tag and `Result:` line at `report` |
| `trace_lines` | every trace line as `<kind> <expected station> <status or ->`, in order |
| `refused_rules` | the rules of every `refused` trace line, sorted, once each |
| `visit_open_exits`, `visit_result_exits` | the exit of every `visit --station` and every `visit --result`, in order |
| `fix_exits`, `lap_exits` | the exit of every `fix` and every `lap`, in order |
| `laps_taken`, `owner_words_recorded` | the laps the result counts, and the owner's words each lap opened with recorded |
| `run_ended` | `reported`, `paused` (the run waits on the owner), `visit-result-refused`, or `open` |
| `v1_station_ran` | a planted v1-shaped station's marker exists (one of its executables ran) |
| `ship_events`, `ship_event_words` | the kinds and the words of the records events ship-v2 itself wrote, in order |
| `report_while_paused_exit` | the exit of `report` run while a question waits on the owner |
| `workspace_unchanged_while_paused` | the workspace's bytes after the pause equal its bytes before the question |
| `stage` | the run's stage (the checkpoint's `phase`) when the drive ended |
| `v1_findings_present`, `v1_finding_count` | the no-v1-import scan on the scanned copy |
| `writes_none` | the workspace unchanged by the whole drive (the stations' own records writes included) |

A list assertion is an exact list. A name the run has no fact for is omitted, never guessed.

## Rules these cases were written under

- Synthetic content only: a made-up bench-rig turn counter. Nothing personal, legal, financial or key-shaped, and no
  text copied from another repository.
- No network, no MCP tool, no model call, no harness launch, in the generators or in a case.
- Tests and grading runs build into a temporary directory and clean up; no `__pycache__` is left.
- Neither a `CASES.md` nor an answer file states an outcome. The outcomes live in the answer key.

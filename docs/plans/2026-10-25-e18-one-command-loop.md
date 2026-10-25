# E18 round 1: the one-command loop (build plan, 2026-10-25)

Intent: one `/ship-v2 <slice>` should run build, signoff, fix and recheck to the end, honestly independent, with no second window. Today it cannot. ship-v2 builds in its own session, then signoff-v2 refuses because the reviewing session is the building session (canary finding C-6), so every slice needs a builder, a separate window for signoff and often another for recheck. And two stations read only an em dash in a slice heading (C-1 for ship-v2 and the reader it shares, C-23 for signoff-v2's ledger), so every plan so far has needed the owner's "em dash ok" exception. This plan fixes those three, and nothing else.

Source: E17's carried findings C-6, C-1 and C-23 (the E17 close report, group 1, and the control room's notes). The owner picked this round ("One command loop") and gave the go for this plan ("go em dash ok", 2026-10-25).

Constraints:

- The repo is public: no secrets, personal paths, mail addresses, key-shaped strings or em dashes in any file. One exception: this plan's four slice headings use an em dash, because the installed ship-v2 and signoff-v2 read no other (the owner: "go em dash ok"). New code and text add none: where a pattern must name the em dash, it uses the Python escape for U+2014, as the stations already do.
- signoff-v2's independence rule does not change (AGENTS.md invariants): the session that wrote the code never reviews it, reviewers are always fresh, and they never receive the author's rationale. Slice C moves the signoff visit into a fresh session; it does not relax the rule.
- Never rewrite stored history: earlier verdict docs, records, run directories and plans stay as they are.
- A file several stations carry byte for byte stays byte for byte equal across every copy after each slice.
- Each check is one line, `<name>: <command>`, the command run from the repository root and reported under exactly that text (build-v2 matches it). The name holds no colon.
- Run the suites one at a time, never side by side (C-25).
- No push, no PR, no merge: the owner's word only.

## Slice A — signoff-v2 reads any slice-heading dash

Status: not started

Requirements:

- signoff-v2's ledger (`plugins/signoff-v2/skills/signoff-v2/scripts/signoff_core/ledger.py:27` `RECORD_HEADING` and `:29` `SLICE_HEADING`) reads a slice heading and a record heading whose separator is an em dash, an en dash or a hyphen, as the records component already does (`plugins/records/scripts/records_core/legacy.py:40-41`).
- For any heading, the slice name signoff-v2 reads equals the name the records component reads for it, so the card signoff-v2 sets and the records it appends name the same slice.
- A heading with no separator still reads as today (`## Slice A` names slice `A`).
- What signoff-v2 writes does not change: the record block is still the records component's `render` bytes.
- The module docstring's card line (`ledger.py:11`, the `Status:` line under the slice's heading, which it shows with an em dash) names the three separators.

Checks:

- the new module test_e18_heading_dashes is red before the change and green after (card_of and set_card find slice A under an em dash, en dash and hyphen heading; a record heading with each separator is found; for each heading the slice name equals the records component's; a bare `## Slice A` reads as before): uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/signoff-v2/skills/signoff-v2/scripts/tests -t plugins/signoff-v2/skills/signoff-v2/scripts/tests -p test_e18_heading_dashes.py
- the full signoff-v2 core suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/signoff-v2/skills/signoff-v2/scripts/tests -t plugins/signoff-v2/skills/signoff-v2/scripts/tests -p 'test_*.py'

Footprint: plugins/signoff-v2/skills/signoff-v2/scripts/signoff_core/ledger.py, plugins/signoff-v2/skills/signoff-v2/scripts/tests/test_e18_heading_dashes.py

Not in this slice:

- C-1 (Slice B)
- what signoff-v2 or the records component write (C-17, C-31)
- the version number (Slice D)

## Slice B — the shared plan reader takes any slice-heading dash

Status: not started

Requirements:

- The build-doc form's slice heading (`templates.BUILD["slice"]` in `station_core/templates.py:175`) reads `## Slice <name> <dash> <short>` where `<dash>` is an em dash, an en dash or a hyphen, with one space on each side, as build-v2 and recheck-v2 already read it.
- The second reading's slice form (`FORM` in `readings.py:124`) takes the same three dashes, so a level 1 or 3 heading, or a numbered one, on the hyphen or en dash form is still refused as a near miss, as the em dash form is today.
- This reverses vertical-v2's ruling C1A8-2 for the spaced en dash and the spaced hyphen only: both now read as exact slice headings. Everything else C1A8-2 and A21 (2) refuse stays refused: a colon for the dash, a dash with no spaces around it, a lower-case `slice`, a zero-width character, an accented letter, a leading curly quote, a level 1 heading, and a numbered or labelled heading (`## 2. Slice B - beta`, `## Next: Slice B`).
- `templates.D` stays the em dash: what blueprint-v2 and the other stations write does not change.
- The rule texts that describe C1A8-2 (`readings.py:72-78`, and any docstring or contract line that says the en dash or the hyphen is refused) say what is now read.
- Every copy stays byte for byte equal: `station_core/templates.py` in architect-v2, blueprint-v2, handoff-v2, inspect-v2, precon-v2, ship-v2 and vertical-v2, and `readings.py` in handoff-v2 (`handoff_core/`), ship-v2 (`ship_core/`) and vertical-v2 (`vertical_core/`).
- An existing test changes only where it pins the old refusal of the spaced en dash or hyphen (known today: vertical-v2's `test_near_misses.py:83` and `test_packet.py:446-447`); each such change is named in the build ledger with the case it now accepts.
- ship-v2's `select` reads a plan whose slice headings use a hyphen: it finds the slice, its card and its footprint.

Checks:

- the new vertical-v2 module test_e18_slice_dashes is red before the change and green after (an em dash, en dash and hyphen heading each read as the slice, with its card, in both readings; the near misses named in the third requirement are still refused; a level 3 `### Slice B - x` is still refused): uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/vertical-v2/skills/vertical-v2/scripts/tests -t plugins/vertical-v2/skills/vertical-v2/scripts/tests -p test_e18_slice_dashes.py
- the new ship-v2 module test_e18_slice_dashes is red before the change and green after (select on a hyphen-heading plan names the slice, its card and its footprint; the seven `station_core/templates.py` copies and the three `readings.py` copies are byte for byte equal): uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p test_e18_slice_dashes.py
- the full vertical-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/vertical-v2/skills/vertical-v2/scripts/tests -t plugins/vertical-v2/skills/vertical-v2/scripts/tests -p 'test_*.py'
- the full ship-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p 'test_*.py'
- the full handoff-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/handoff-v2/skills/handoff-v2/scripts/tests -t plugins/handoff-v2/skills/handoff-v2/scripts/tests -p 'test_*.py'
- the full architect-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/architect-v2/skills/architect-v2/scripts/tests -t plugins/architect-v2/skills/architect-v2/scripts/tests -p 'test_*.py'
- the full blueprint-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/blueprint-v2/skills/blueprint-v2/scripts/tests -t plugins/blueprint-v2/skills/blueprint-v2/scripts/tests -p 'test_*.py'
- the full inspect-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/inspect-v2/skills/inspect-v2/scripts/tests -t plugins/inspect-v2/skills/inspect-v2/scripts/tests -p 'test_*.py'
- the full precon-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/precon-v2/skills/precon-v2/scripts/tests -t plugins/precon-v2/skills/precon-v2/scripts/tests -p 'test_*.py'

Footprint: plugins/architect-v2/skills/architect-v2/scripts/station_core/templates.py, plugins/blueprint-v2/skills/blueprint-v2/scripts/station_core/templates.py, plugins/handoff-v2/skills/handoff-v2/scripts/station_core/templates.py, plugins/inspect-v2/skills/inspect-v2/scripts/station_core/templates.py, plugins/precon-v2/skills/precon-v2/scripts/station_core/templates.py, plugins/ship-v2/skills/ship-v2/scripts/station_core/templates.py, plugins/vertical-v2/skills/vertical-v2/scripts/station_core/templates.py, plugins/handoff-v2/skills/handoff-v2/scripts/handoff_core/readings.py, plugins/ship-v2/skills/ship-v2/scripts/ship_core/readings.py, plugins/vertical-v2/skills/vertical-v2/scripts/vertical_core/readings.py, plugins/vertical-v2/skills/vertical-v2/scripts/tests/, plugins/ship-v2/skills/ship-v2/scripts/tests/, plugins/handoff-v2/skills/handoff-v2/scripts/tests/, plugins/architect-v2/skills/architect-v2/scripts/tests/, plugins/blueprint-v2/skills/blueprint-v2/scripts/tests/, plugins/inspect-v2/skills/inspect-v2/scripts/tests/, plugins/precon-v2/skills/precon-v2/scripts/tests/, plugins/vertical-v2/skills/vertical-v2/references/, plugins/ship-v2/skills/ship-v2/references/, plugins/handoff-v2/skills/handoff-v2/references/

Not in this slice:

- what any station writes (`templates.D` and every render stay the em dash; C-17, C-31)
- signoff-v2's ledger (Slice A)
- `fences.py`, which reads the slice heading only through `templates.BUILD["slice"]`
- the title line form (`# <Feature> <dash> build plan (<date>)`), which no station's slice reading uses
- the version number (Slice D)

## Slice C — ship-v2 runs the signoff visit in a fresh session

Status: not started

Requirements:

- On the Claude Code harness, `visit --station signoff-v2` keeps everything it does today and also prepares a fresh child session for the visit: it makes a new random session id (a UUID), writes the child's brief to a file under this ship run's directory (outside the visit's run directory and outside the workspace), records the session id in the visit's state in `ship.json`, and prints a `launch` object: the argv, the working directory (the workspace) and the session id.
- The argv is `claude -p --model <model id> --permission-mode auto --session-id <session id> --output-format json "/signoff-v2 Read <brief path> and follow it."`, where `<model id>` is the ship input's `invocation.model.id`. The permission mode is `auto` and nothing else; the argv never carries `bypassPermissions` or `--dangerously-skip-permissions`.
- The brief is composed by the script from this run's own files and nothing else: the workspace, the build doc, the slice, the path of the build visit's `result.json` (passed to signoff-v2's helper as `--build-result`), the signoff visit's run id and run directory, `invocation.caller` `ship-v2` and the visit's `invocation.mode`, and the owner's depth order if the input carries one (next requirement). No command option takes free text for the brief, so nothing from the ship session's conversation can reach it.
- The ship input's `station` may carry `signoff_depth`: `LEAN`, `DEEP` or `LIGHT`, with the owner's `words` verbatim, the same way it carries `minor_fixes`. The brief passes it to the child as the owner's words. With none, the brief names no depth and signoff-v2's own rules choose.
- The brief tells the child that no owner is present in its session: it writes no `REVIEW.md`, takes LIGHT only on the owner's depth order, answers no question on his behalf, and leaves every question signoff-v2 would put to him in its chat block (`chat.md`), as signoff-v2 already writes it. The child commits, pushes and edits nothing beyond signoff-v2's own writes.
- The ship session launches the argv in the background from the workspace and waits for it to end. It never runs signoff-v2 in its own session and never writes into the visit's run directory. THE WINDOW RULE is unchanged: the ship session touches nothing while the visit is open.
- `visit --result` keeps every check it makes today and also refuses (exit 5, nothing written, the run still `visiting`) a signoff-v2 result when the reviewing session that the visit's own `input.json` records (`invocation.sessions.reviewing`, written by signoff-v2's `check-input`) is not the session id the launch recorded. The refusal's message names both ids.
- After `visit --result` holds, the ship session delivers the child's `chat.md` in chat (signoff-v2's Step 6 block), then goes on by the existing table: fixing, clean, or the stop.
- On the Codex harness nothing changes: `visit --station signoff-v2` prints no `launch`.
- recheck-v2's visit stays in the ship session: recheck-v2 allows a driving session that wrote the fix (`invocation.session_wrote_fix`) and holds it to confirming or downgrading only (recheck-v2 pilot contract, section 7).
- SKILL.md Step 3 says how to run the visit: run `visit`, launch its argv in the background, wait, run `visit --result`, deliver the child's `chat.md`; never run signoff-v2 in this session. The contract's section 3.4 (the visit), section 4 (the input) and section 11 (the harness seams) say the same, name the brief's fields, and name the permission mode.

Checks:

- the new module test_e18_fresh_signoff is red before the change and green after (a signoff-v2 visit on the Claude Code harness prints a `launch` whose argv is exactly the form above with the input's model id, a session id that is a UUID and differs on each visit, and the workspace as its directory; the brief holds exactly the named fields, and the owner's depth words verbatim when the input carries them; `visit --result` refuses a result whose recorded reviewing session is not the launched id and accepts one whose session is; a Codex visit prints no `launch`; no argv carries `bypassPermissions` or `--dangerously-skip-permissions`): uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p test_e18_fresh_signoff.py
- the full ship-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p 'test_*.py'
- the claude-code adapter suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/adapters/claude-code/tests -t plugins/ship-v2/skills/ship-v2/adapters/claude-code/tests -p 'test_*.py'

Footprint: plugins/ship-v2/skills/ship-v2/scripts/ship.py, plugins/ship-v2/skills/ship-v2/scripts/ship_core/, plugins/ship-v2/skills/ship-v2/adapters/claude-code/, plugins/ship-v2/skills/ship-v2/references/ship-contract.md, plugins/ship-v2/skills/ship-v2/references/input.schema.json, plugins/ship-v2/skills/ship-v2/references/examples/, plugins/ship-v2/skills/ship-v2/SKILL.md, plugins/ship-v2/skills/ship-v2/scripts/tests/test_e18_fresh_signoff.py

Not in this slice:

- signoff-v2 and its independence rule, which do not change
- a fresh session for the Codex harness (a `codex exec` child)
- recheck-v2's visit, which stays in the ship session
- a live end-to-end `/ship-v2` run, which needs the installed stations (C-29) and comes after the merge
- reviewer isolation (C-8, C-30) and the build-v2 plan-reading findings (C-4, C-5, C-24, C-27)
- the version number (Slice D)

## Slice D — version bumps so an update delivers the round

Status: not started

Requirements:

- Every plugin whose files Slices A to C changed gets its patch version raised by one in its `.claude-plugin/plugin.json` (today signoff-v2, ship-v2, vertical-v2 and handoff-v2 at 0.1.0; architect-v2, blueprint-v2, inspect-v2 and precon-v2 at 0.1.1), so `/plugin update <name>@tony-skills` delivers the change on every machine (E17 close, item 8). The catalog (`.claude-plugin/marketplace.json`) carries no versions and does not change.
- Where a station reports its version through its own CLI (`skill-identity`) or a result's `plugin_version`, it reports the new one; an example or test that pins the old version moves with it, and nothing else in it changes.
- No other change.

Checks:

- every changed plugin's manifest carries the new version, and each station's skill-identity reports it: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p test_e18_versions.py
- the full signoff-v2 core suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/signoff-v2/skills/signoff-v2/scripts/tests -t plugins/signoff-v2/skills/signoff-v2/scripts/tests -p 'test_*.py'
- the full ship-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/ship-v2/skills/ship-v2/scripts/tests -t plugins/ship-v2/skills/ship-v2/scripts/tests -p 'test_*.py'
- the full vertical-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/vertical-v2/skills/vertical-v2/scripts/tests -t plugins/vertical-v2/skills/vertical-v2/scripts/tests -p 'test_*.py'
- the full handoff-v2 suite passes: uv run --python /usr/bin/python3 --with jsonschema==4.25.1 python3 -m unittest discover -s plugins/handoff-v2/skills/handoff-v2/scripts/tests -t plugins/handoff-v2/skills/handoff-v2/scripts/tests -p 'test_*.py'

Footprint: plugins/signoff-v2/.claude-plugin/plugin.json, plugins/ship-v2/.claude-plugin/plugin.json, plugins/vertical-v2/.claude-plugin/plugin.json, plugins/handoff-v2/.claude-plugin/plugin.json, plugins/architect-v2/.claude-plugin/plugin.json, plugins/blueprint-v2/.claude-plugin/plugin.json, plugins/inspect-v2/.claude-plugin/plugin.json, plugins/precon-v2/.claude-plugin/plugin.json, plugins/signoff-v2/skills/signoff-v2/references/examples/, plugins/ship-v2/skills/ship-v2/references/examples/, plugins/ship-v2/skills/ship-v2/scripts/tests/test_e18_versions.py

Not in this slice:

- any behavior change
- installing the plugins, which is the control room's step after the merge, verified file for file against main

## After the slices

On the owner's "PR" and "merge": reinstall every bumped plugin, verify each installed copy against main file for file, then the first live `/ship-v2` run on a small slice in a window opened after the reinstall. That run is the round's real proof: one command, build to recheck, with the signoff visit in its own session.

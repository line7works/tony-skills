# Template: the lines inspect writes itself (the stamp, a QUESTION line, the clean line)

Shared by the four front cores (listed in `references/shared-files.txt`). Two parts, kept apart:
the FORM, the one fenced block tagged `form` below, which `station_core/templates.py` parses and
renders; and the READING, v1's own words about the form, quoted for the executor and never
rendered. The form is the v1 station's fenced form byte for byte (ruling E14-12); a change to it
is a stop, never a lane's edit. Source: the v1 inspect station's Step 5, its inline forms: the stamp, the QUESTION line and the clean line, each quoted in v1 as one backticked form.

## Form

```form
Plan: inspected <YYYY-MM-DD> by <model> · <N BLOCKER · N MAJOR · N MINOR>
QUESTION · <path>:<line> · what needs confirming · <inspector model>
clean — no surviving findings or questions · <inspector model>
```

## Reading (v1's words, quoted; the executor's reading, not a rule of this core)

> 1. **The punch-list block.** `### <YYYY-MM-DD> — inspect: plan` appended at the ledger home's tail — the home is where the doc's punch-list blocks already live, or the `## Punch list` section (created when absent), per /signoff's home rule. One ·-separated line per surviving finding: severity · `<path>:<line>` · claim · concrete failure scenario · <inspector model>. Questions land in the same block as `QUESTION · <path>:<line> · what needs confirming · <inspector model>` lines — no severity, never gating, never swept — so a precon-less run's confirm-list survives the chat. A clean run — zero surviving findings AND zero open Questions, the stamp's own definition — still writes the block, holding the single line `clean — no surviving findings or questions · <inspector model>`; a zero-finding run with open Questions writes its QUESTION lines and no clean line. A **re-inspection's** block additionally carries one line per still-open prior inspect entry — severity · `<path>:<line>` · (claim) · fixed | not fixed — the recheck-format closure record the loop's open-filter honors, so plan-stage findings never read as open forever.
> 2. **The stamp.** `Plan: inspected <YYYY-MM-DD> by <model> · <N BLOCKER · N MAJOR · N MINOR>` — append `· N QUESTION` when any are open, and write `clean` in place of the counts only when there are zero findings AND zero open Questions. Placement, one rule: directly below the previous `Plan: inspected` line when one exists, so history reads top to bottom; on a first inspection, directly after the `Out of scope:` block (the header line and any list lines continuing it); in a doc with no `Out of scope:` at all, directly above the first `## Slice` heading. Prior stamp lines are never rewritten. `<model>` is the effective model id the paper inspector's `READERS:` line carries (the sidecar's `effective_model`): an outside row's resolved id, or — Claude lane — the session's own model id, which `claude-session` reports as its effective model. Never write an id you didn't launch: the stamp is the trust label, and a lightweight inspection must never be mistakable for a heavyweight one.
>
> Never: a `Status:` line, a verdict word in the doc, an edit to the plan's content, a fix, a re-slice. Tony adjudicates the findings — a plan finding can be wrong; the inspector has less context than he does. The drafting session amends the doc on his word, and re-inspection is a fresh /inspect run. No invocation wording collapses the fixing gate.

## Notes of the frame

- The stamp's two other shapes are composed from the reading's own words, not quoted forms:
  `· N QUESTION` appended when questions are open, and `clean` written in place of the counts
  when there are no findings and no open questions. `templates.py` renders and parses all three.
- The v1 block heading `### <YYYY-MM-DD> — inspect: plan` and its finding lines retire with v1
  (pick P8): inspect-v2's findings are raised through the records component, and the block
  under the punch list is the text the component's `render` produces. The QUESTION and clean
  lines and the stamp stay the station's own lines.

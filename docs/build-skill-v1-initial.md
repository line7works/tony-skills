# Build — Version 1 Initial (design doc)

Written 2026-07-31, Mac Studio session. Companion to the signoff skill-lab docs in this
folder (`signoff-skill-review.md`, `signoff-skill-work-state.md`). This is the design
record for a new skill named **`/build`**: the inverse of `/signoff`. Signoff inspects a
slice after it is built; Build executes a slice from the build doc, inside boundaries.

Status: **design only.** No `SKILL.md` exists yet. This doc is what v1 will be drafted
from, and why.

---

## 1. Philosophy

**The spec is the only source of requirements.** That single sentence is the whole
skill; everything else is enforcement of it.

Signoff's spine is "find reasons to REJECT, not to confirm good work." Build's spine is
the mirror image: the builder's job is to make the slice doc true, not to make the
software better. Every line of code must trace to a line of the slice. Anything that
does not trace is one of two things:

- **Drift** — cut it.
- **A discovery** — log it in the build doc, do not build it.

In construction terms: Tony is the GC. `/wargame` draws the blueprints, `/signoff` is
the inspector. Build is the framing sub. The crew shows up with the blueprint page for
one phase, builds exactly what is on that page with the materials already on site, and
calls for inspection when done. It does not redesign the stairs mid-frame, does not run
to the store when there is lumber on the pallet, and does not start the phase-B plumbing
rough-in because it happened to open that wall.

A second principle sits under the first: **builder and inspector are different roles
with different virtues.** The builder is allowed context, momentum, and the session's
accumulated understanding. The inspector must have none of that (signoff's independence
rule). So Build runs in-session, signoff runs in fresh subagents, and the two never
share a voice. The builder writes intentions and assumptions; the inspector writes
findings and signatures. Neither writes the other's column.

Third: **honest incompleteness beats fake completeness.** A slice that stops at 80%
with a clear report of the missing 20% is a good outcome. A slice that presents stubs
as finished is the worst outcome this skill can produce, because it poisons the very
inspection step that is supposed to catch it. Stubs-as-done is the one unforgivable
move, the same tier as signoff's "reviewing the diff solo and calling it a sign-off."

## 2. Findings that shaped this design

These come from the signoff skill-lab work (2026-07-27 through 2026-07-30) and the
Anthropic Opus 5 prompting guidance read during it. They transfer directly.

1. **Skill text is context, not enforcement.** Per the Claude Code docs, a SKILL.md
   cannot hard-guarantee anything; hard guarantees need hooks or permission rules. So
   v1 states blast-radius rules as prose and flags the hook option as a Tony decision,
   exactly as signoff does with its rule 9. Do not pretend prose is a fence.
2. **Goals beat checklists for Opus-class models.** The signoff rewrite learned that
   over-prescriptive re-check language causes over-verification; Opus 5 self-verifies.
   Build's verify step will be written as a goal ("exercise each acceptance criterion
   and record what ran") rather than a mandatory command list.
3. **Scope is a union, and the mid-work state is messy.** Signoff's biggest baseline
   bug was reviewing only half the work (committed vs dirty). Build inherits the
   lesson from the other side: it must know what ground it starts on. Hence the
   preflight "before photo" (run the suite once before building) so the end-of-slice
   claim "prior slices still green" is checkable rather than asserted.
4. **Signoff rule 4 has a hole Build fills.** "Deferred requires written evidence,
   else BLOCKER" only works if somebody writes the evidence. Today that is ad hoc.
   Build becomes the producer of that evidence: its assumptions and deviations land in
   the build doc, exactly where signoff's reviewers look. This is the interlock that
   makes the pair worth more than either skill alone.
5. **Thrash is a real failure mode.** Sessions that keep swinging at the same failing
   test burn context and produce desperate code. Build gets an explicit thrash limit:
   three failed attempts at the same problem means stop and report, not attempt four.
6. **Tony's standing rules already cover the exits.** Git gates (never push, never PR,
   never merge without the word) live in the global CLAUDE.md and apply to every repo.
   Build does not restate them as its own rules; it just stops where they say stop.
   Local commits are fine; the skill ends at "committed locally, ready for signoff."

## 3. The loop this skill completes

```
/wargame ──► build doc with slices
                 │
         ┌───────▼─────────┐
         │  /build slice A │   ◄── this skill
         └───────┬─────────┘
                 │  BUILD: block (chat)
                 │  assumptions + deviations + discoveries → build doc
         ┌───────▼─────────┐
         │  /signoff       │   reads the same doc, grades against it,
         └───────┬─────────┘   audits the builder's ledger as claims
                 │  punch list → next slice's preflight
                 ▼
         /build slice B ...
```

Blueprints, framing crew, inspector, punch list, next phase. Each skill hands the next
one exactly the paper it needs.

## 4. Design decisions and why

**In-session builder, no subagent ceremony.** Signoff needs fresh subagents because
independence is its whole value. Build has the opposite need: the session's context
(the conversation, the plan discussion, the repo knowledge) makes the builder better.
No independence requirement exists on the build side because the inspector downstream
provides it. Simpler, faster, and the roles stay clean.

**No model floor.** Signoff has one because a weak adversary produces a confident,
wrong signature and nothing downstream catches it. A weak builder's output gets
inspected anyway; the floor lives downstream where it protects something.

**Contract before code.** Step 1 posts a short contract in chat before any edit: what
will be built, what is explicitly out of scope, which existing components get reused,
which files it expects to touch, any new dependency it thinks it needs. Two reasons.
First, it forces the spec-reading to actually happen instead of being skimmed on the
way to the editor. Second, it gives Tony a cheap veto point: a wrong contract costs
one message to correct; a wrong build costs a session. The contract does not wait for
approval (that would block autonomous runs); it states assumptions and proceeds, per
Tony's standing preference. A genuinely load-bearing gap is the exception, below.

**The ask-vs-assume line.** The spec will always be silent about something. The rule:

- Irreversible, architectural, or user-visible-contract gaps (schema shape, API
  surface, auth model, anything a later slice builds on): **stop and ask.**
- Small, local, reversible gaps (a variable name, an error message, an internal
  helper's shape): **decide, and write the assumption down.**

The written-down part is not optional. Every assumption lands in a `## Build
assumptions` section of the build doc, dated, one line each. That is the evidence
signoff's rule 4 demands, and it is also what makes an assumption reversible: an
undocumented assumption is a landmine, a documented one is a decision pending review.

**Reuse-first, justified-new.** Before writing any new component, helper, or utility,
search the repo for an existing one. Writing a new one requires a one-line
justification that survives into the BUILD: block. New dependencies are stricter: they
must appear in the contract up front, never appear mid-build unannounced. This is the
"use the lumber on the pallet" rule, and it is stated as a search obligation rather
than a prohibition, because sometimes the right component genuinely does not exist.

**Blast-radius rules.** Feature branch only (never build on main). No schema
migrations against real databases. Prior slices' tests must stay as green as the
before photo. Deleting or rewriting shared files gets flagged in the contract. And the
thrash limit: three failed attempts at one problem, stop and report. All prose, per
finding 1; a repo that needs a hard fence gets a hook, and that is a separate Tony
decision.

**Stubs are illegal output.** If part of the slice cannot be finished, the skill stops
and reports the honest state: what is done, what is not, why. It never writes a stub,
a `// TODO`, or a vacuous test and presents the slice as complete. This is stated as
the skill's one unforgivable move, in the same register signoff uses, because the
model treats that framing as load-bearing.

**Silent descoping and gold-plating get named.** These are the builder-side twins of
what signoff hunts (silently skipped requirements, invented criteria). Any narrowing
of the slice appears in the report as a deviation. Any addition beyond the spec
(extra config, premature abstraction, unrequested edge handling) is cut by the
traceability rule. Naming both in the skill matters: the model polices what it has
words for.

**Report and stop; never auto-signoff.** The skill ends with local commits, a compact
`BUILD:` block in chat, and an offer to run `/signoff`. It never runs it. Tony
collapses gates; skills do not. Same philosophy as the git gates, applied one layer
up. ("Build slice A and sign it off" in the invocation collapses the gate in advance,
same as signoff's rule 5 allows.)

**Ledger hygiene.** Build writes three sections into the build doc: `## Build
assumptions`, `## Deviations`, `## Discovered` (out-of-scope work found on the way).
It never touches signoff's `## Punch list` history and never writes anything shaped
like a verdict. Signoff already treats builder prose as claims to verify (its rule
10), so the ledger does not pollute the inspection; it focuses it.

## 5. What goes in SKILL.md v1

Target: signoff's length and register (~125 lines). Same skeleton so the pair reads
as a matched set.

**Frontmatter description / triggers:** "Execute one slice of a build document inside
strict boundaries: spec-only requirements, reuse-first, no stubs, honest stops. Use
when the user says 'build slice X', 'build the next slice', 'execute the plan for X',
or hands over a build doc and names a slice."

**Opening frame:** the framing-sub paragraph and the spine sentence ("the spec is the
only source of requirements"), plus the explicit pairing with /wargame and /signoff.

**Step 1 — Contract.** Find the build doc (same hunt as signoff: `docs/`, `plan/`,
vault project folder, session plan). Resolve the named slice. Extract requirements
and acceptance criteria. Post the contract: in scope, out of scope, components to
reuse, expected file footprint, new dependencies if any. If the doc or slice does not
resolve: stop. Never build from a spec you invented.

**Step 2 — Preflight.** Prior slice's verdict and conditions (read the punch list;
WITH CONDITIONS MAJORs must be fixed or explicitly waived by Tony before new framing
goes up). Feature branch confirmed. Run the suite once for the before photo; record
the result.

**Step 3 — Build.** In-session, governed by the rules. Local commits at natural
checkpoints so a bad direction is revertible.

**Step 4 — Verify.** Earn the claim of done: run the tests, exercise each acceptance
criterion, record what ran and what it showed. Unexercised criteria are reported as
unexercised. Bulk output redirected to a file and grepped, never streamed raw into
context (same mechanic as signoff step 3.5).

**Step 5 — Report and stop.** Write the ledger sections into the build doc. Emit the
BUILD: block. Offer /signoff. Stop at the git gates.

**The rules (numbered, like signoff's):**

1. Every change traces to a spec line. No trace: drift (cut) or discovery (log).
2. The gap protocol: load-bearing gaps stop and ask; small reversible gaps get a
   logged assumption. An unlogged assumption is a defect.
3. Reuse before writing. New components carry a one-line justification; new
   dependencies appear in the contract or not at all.
4. Stubs are illegal. Honest incompleteness beats fake completeness, always.
5. Descoping is reported as deviation, never absorbed. Additions beyond spec are cut.
6. Blast radius: feature branch, no live-DB migrations, prior slices stay green
   against the before photo, shared-file rewrites flagged in the contract.
7. Thrash limit: three failed attempts at one problem, stop and report.
8. Builder writes intentions, never verdicts. Punch-list history is read-only.
9. Report faithfully: the BUILD: block states what ran and what did not, in the same
   register as signoff's Method line. Never let "wrote the code" imply "watched it
   work."

**Output block:**

```
BUILD: <slice/phase>
Status: COMPLETE | PARTIAL (honest %) | STOPPED (blocked on <question>)
Spec: <path + slice>  ·  Contract: <held / deviations: N>  ·  Before photo: <suite state>
Method: <ran it / tests / criteria exercised or not>

Bottom line: <2-3 sentences. What got built, what state it is in, what to do next.>

Built        <requirement · file:line · how it was exercised>
Deviations   <narrowed or changed vs spec, each with why>
Assumptions  <gaps the spec left, decided and logged>
Discovered   <out-of-scope work found, logged not built>
New          <components/deps written new, each with its one-line justification>
Ready for /signoff: yes | no (<why>)
```

Omit empty sections. `Method` and `Bottom line` are mandatory always.

**What NOT to do (closing list, mirroring signoff's):** don't invent requirements,
don't build from a spec you reconstructed from memory, don't write stubs and call the
slice done, don't absorb descoping silently, don't add dependencies mid-build, don't
gold-plate, don't touch the punch-list history, don't push, don't run signoff on your
own work, don't keep swinging past the thrash limit.

## 6. What v1 deliberately leaves out

- **Hooks for hard enforcement** of blast-radius rules. Prose first; hooks are a
  separate decision after v1 shows where prose actually fails.
- **Multi-slice runs** ("build slices A through C"). One slice per invocation keeps
  the contract meaningful and the inspection loop tight. Revisit if the loop proves
  itself and feels too slow.
- **Auto-invoking /signoff.** Stated above; the gate stays with Tony.
- **A model floor.** The inspector downstream is the quality gate.
- **Worktree isolation.** The feature-branch rule plus revertible checkpoint commits
  cover v1. Worktrees add ceremony that only pays off for parallel builds, which v1
  does not do.

## 7. Test plan (skill-lab treatment, same as signoff got)

1. Draft `SKILL.md` from section 5.
2. **Baseline run** on a real slice from a real build doc (Atlas has live slice docs;
   pick one that is genuinely next, not a replay). Fresh terminal, one invocation:
   `/build slice <X>`.
3. Review the transcript against this doc: did the contract happen before code, did
   assumptions get logged, did anything untraceable land in the diff, did it stop at
   the gates.
4. The paired test that matters most: run `/signoff` on the build's output and check
   the interlock. Signoff should find the builder's ledger where rule 4 looks, and
   should NOT be softened by it (deferred-with-evidence adjudicated, everything else
   still attacked).
5. Fold findings, rerun on the next slice, compare. Same discipline as the signoff
   A/B: record repo state at each run so the comparison is honest.

## 8. Open decisions for Tony

1. **Name is settled: `/build`.** (Per Tony, 2026-07-31.)
2. **Checkpoint commit style:** small commits during the slice (revertible, noisier
   history) vs one commit at the end (clean, all-or-nothing revert). v1 drafts with
   checkpoints; say the word to flip it.
3. **Where the ask-vs-assume line sits.** v1 draws it at irreversible/architectural/
   contract-shaping. If runs stop too often, the line moves; if assumptions pile up
   on things Tony wanted to be asked about, it moves the other way. Tune on evidence
   from the baseline run.
4. **Hooks later?** If the baseline shows prose failing to hold a blast-radius rule
   (e.g. a dependency add sneaking through), that specific rule graduates to a hook.

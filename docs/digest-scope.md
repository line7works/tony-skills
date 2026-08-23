# Digest — scope doc (2026-08-20)

Intent: /digest is the compile half of Tony's note-capture system. /fb (existing,
unchanged) captures raw notes verbatim into `<repo>/docs/feedback.md`; /digest reads
that raw log and rewrites `<repo>/docs/notes.md` into one fixed shape, so week-long
notes sessions ("Atlas notes", "Sit-down notes", "Caelan notes") stop dying in
scrolled-out chat context. For Tony only.

Decisions:
- The skill is wanted; it exists as a project — decided (Tony 2026-08-20, parent handoff)
- Real name is /digest — decided (Tony's answer to the /huh naming question, 2026-08-20)
- Front door is /fb log-as-you-go: each notes session opens with "fb every note I type"; /digest reads the fb logs — decided (Tony: "log as you go", 2026-08-20)
- Capture side is /fb exactly as it exists today; nothing is rebuilt there — decided (handoff + Tony's confirmation of the /fb assumption)
- /digest rewrites `<repo>/docs/notes.md` with fixed sections: Open questions · Ideas (undecided) · Decisions made (dated, one line each) · Bugs & friction · Parked · Raw log pointer + last-compiled date — decided (handoff, Tony's rules)
- Idempotent: rerun anytime, folds new entries in, NEVER deletes or edits a raw feedback.md line — decided (handoff)
- Routing: Atlas notes → ~/Developer/Atlas, Sit-down notes → ~/Developer/sunday-sitdown (never Caelan's repo, never the vault), Caelan notes → ~/Developer/Caelan — decided (handoff, Tony's standing rules)
- Scope doc lives in ~/Developer/tony-skills/docs/ — assumed (cross-repo skill, no single notes repo owns it; tony-skills is the skills home)
- Skill file lands as ~/.claude/skills/digest/SKILL.md — assumed (matches every other loop skill's home; small and reversible)
- One run compiles the current repo only; no all-repos sweep in v1 — decided (Round 1 Q1: "just that repo")
- /digest fully owns notes.md and may rewrite anything in it; Tony does not hand-edit notes.md — decided (Round 1 Q3: "i dont edit any notes")
- Skill-lab feedback (~/Documents/skill-lab/skill-feedback.md) is outside /digest's default world; touched only if Tony explicitly points /digest at it — decided (Round 1 Q4: "out of digest's world. otherwise ill specifically summon it")
- feedback.md is a long-running tally, never wiped or archived by /digest; archiving, if ever, is a separate later decision — decided (Round 2 Q1)
- Cutoff mechanism: /digest appends a dated marker line in feedback.md after each run ("--- digested through here · <date> ---"); everything below the last marker is new. Raw lines above are never edited or deleted — decided (Tony's idea, Rounds 2–3; chosen for unambiguous agent readability)
- notes.md still carries the raw log pointer + last-compiled date as a human-facing footer; the feedback.md marker is the machine-authoritative cutoff — assumed (both were already in the fixed shape; keeping them costs nothing and aids humans)
- Appending the marker is the ONLY write /digest ever makes to feedback.md; raw lines are never edited or deleted — decided (clarifies the marker decision, Rounds 2–3)
- Raw log format is whatever /fb writes (dated, verbatim); /digest parses that format, /blueprint reads /fb's SKILL.md for the exact shape — assumed (fact of the property, not a decision)
- Decision dates in notes.md come from the /fb entry dates in the raw log — assumed (fb entries are dated at capture)
- Routing is /fb's job at capture time; /digest simply compiles whatever repo it's invoked in, and any repo with a docs/feedback.md qualifies (not just the three notes repos) — assumed (follows from Round 1 Q1 "just that repo")
- If notes.md is missing or hand-shaped, /digest creates/overwrites it — assumed (follows from "digest fully owns notes.md", Round 1 Q3)
- Bucket classification is Claude's judgment; an ambiguous note lands in Open questions, never guessed into another bucket — decided (Round 4 Q1: "claude judment is fine")
- First run in a repo (no marker) compiles the entire feedback.md history — decided (Round 4 Q3: "compil entire")
- Rework allowed: later runs may move, merge, or resolve items already in notes.md (idea → decision, bug resolved out); notes.md is a living current-state board, feedback.md is the permanent history — decided (Round 4 Q2 after /huh: "reword allowed")
- SUPERSEDED 2026-08-21: the feedback.md marker line is dropped. Signoff proved any positional marker fights /fb's sectioned files (notes insert above ## Dispositions, marker at EOF orphans them). New cutoff: date-based — notes.md's footer date is the sole cutoff; /digest makes ZERO writes to feedback.md, ever — decided (Tony: "ok B", 2026-08-21, after /huh)
- On /fb-format files, only the ## Inbox section is input; ## Dispositions and boilerplate never reach the board — decided (Tony: "no" to Dispositions as input, 2026-08-21)
- Slice B live test retargeted to Atlas (fb-format, the shape that exposed the defect) — decided (Tony: "yea retarget", 2026-08-21)

Out of scope:
- Transcript scraping (~/.claude/projects/*/*.jsonl) as an input path — Tony chose /fb log-as-you-go 2026-08-20; brittle, off the table

Research: cold read (local Claude reader) — ~/Documents/precon-cold-reads/digest-cold-read-2026-08-20.md

Open: none
Next: /blueprint when ready.

# Punch list — /huh skill

Ledger home for /huh reviews. No build doc exists (skill was built directly
from a session spec), so the ledger lives here, inside the plugin's own
folder, instead of a repo-level docs/punch-list.md.

## Punch list

### 2026-08-09 — review: /huh skill v1

- MAJOR · SKILL.md:19 · (output shape is singular but real inputs bundle multiple questions) · Tony pastes a finding with two independent decisions (the documented in-session exercise was exactly this); "always this exact shape" + "one sentence" forces a session to either squash two questions into one or improvise an unauthorized repeated-block structure, so behavior diverges between sessions · /huh v1 review
- MINOR · huh-skill.md:15 · ([[_about-me]] links to a file outside the memory namespace) · a future session following the wiki-link searches the memory dir and finds nothing; the real file is ~/ObsidianVault/_about-me.md · /huh v1 review
- MINOR · SKILL.md:24 · (mandatory "Your options" forces fabricated options on purely informational findings) · Tony pastes "this is benign, no action needed"; the shape forces invented options where no decision exists, contradicting "never add new analysis" · /huh v1 review
- MINOR · SKILL.md:21 · ("What I'm asking" header is wrong-tense in finding mode) · a finding with no question still renders under "What I'm asking"; sessions will either keep the confusing header or silently reword against "always this exact shape" · /huh v1 review
- MINOR · SKILL.md:3 · (bare "huh" trigger can false-fire on casual usage) · Tony types "huh, ok do it" as a reaction; a session invokes the skill and re-explains something already understood · /huh v1 review

### 2026-08-09 — recheck: /huh skill v1

- MAJOR · SKILL.md:19 · (output shape is singular but real inputs bundle multiple questions) · fixed — repeated numbered blocks now authorized at current SKILL.md:21-23
- MINOR · huh-skill.md:15 · ([[_about-me]] links to a file outside the memory namespace) · fixed — plain vault path now, no wiki-link remains
- MINOR · SKILL.md:24 · (mandatory "Your options" forces fabricated options on purely informational findings) · fixed — no-decision escape hatch at current SKILL.md:37-39, inventing options forbidden
- MINOR · SKILL.md:21 · ("What I'm asking" header is wrong-tense in finding mode) · fixed — finding mode gets "What this means:" at current SKILL.md:25-27
- MINOR · SKILL.md:3 · (bare "huh" trigger can false-fire on casual usage) · fixed — bare "huh" removed from triggers, casual reaction explicitly excluded
- MINOR · huh-skill.md:11 · broke: memory note's summary of the output shape is stale after the fixes — a future session reading only the auto-loaded memory (not SKILL.md) describes the shape as three invariant sections, missing the finding-mode header, no-decision escape hatch, and per-decision repetition

### 2026-08-09 — recheck: /huh skill v1 (second visit)

- MINOR · huh-skill.md:11 · (memory note's output-shape summary stale vs fixed SKILL.md) · fixed — current note lines 11-15 carry the finding-mode header, per-decision repetition, and no-decision case; reviewer found no remaining contradiction between the two files

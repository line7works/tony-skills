# Maintenance patch contract (E3): v1 mechanical repairs

Branch `fix/skills-maintenance-2026-09-13`, cut from tag `skills-v1-2026-09-12` (`65296c8`).
Builder: Codex CLI, GPT-6 Astra, effort low. Reviewer (E4): Claude Fable 5.1 at max, fresh context.
Plan of record: `~/ObsidianVault/03-projects/tony-skills/skills-v2-execution-plan.md`, step E3.

## Rules

- Repair only what is listed below. No behavior change. No cache pruning, no listing-budget
  change, no review-policy rewrite, no native-flag conversion, no reflowing or "improving"
  prose beyond the named edits. Every hunk in the diff must map to an item number.
- If an item's authority is missing or ambiguous, leave that text alone and say so in the
  completion report. Never invent a document, a path, or a rule.
- Read nothing under `~/.claude/projects/`, `~/.codex/`, or `~/ObsidianVault/`. Everything
  you need is in this checkout or named below with its verified value.
- Work only inside this checkout. Do not push. Do not touch `docs/feedback.md`.

## Repairs

1. **readers frontmatter.** `plugins/readers/skills/readers/SKILL.md` line 3: the
   `description` is an unquoted scalar containing `: ` three times, which strict YAML
   parsers reject. Make it a valid YAML string with identical text (a folded block scalar
   `>-` or a quoted string). Verify with PyYAML `safe_load` and with Ruby psych; the parsed
   description must equal the original text character for character.
2. **sunrise description.** `plugins/sun/skills/sunrise/SKILL.md` frontmatter: the parsed
   description is 1,233 characters, over the Agent Skills limit of 1,024. Rewrite it to at
   most 1,024 characters. Keep every trigger phrase now listed (start, spin up, kick off,
   bootstrap, scaffold, formalize, "sunrise") and the exclusions (never clobbers what exists;
   the inverse of the sunset skill). Put capability, trigger, and exclusion inside the first
   300 characters; it must still read correctly when cut at 300 and at 500. Replace "ALWAYS"
   with "Always". Describe what the skill does, not how. Change no behavior claim. Keep the
   folded block form.
3. **precon stale claims.** `plugins/precon/skills/precon/SKILL.md`. Authority: /blueprint
   already hunts scope docs (`plugins/blueprint/skills/blueprint/SKILL.md` line 20:
   `docs/scope/*.md` first, then the older flat `docs/<idea>-scope.md`).
   - Line 8: delete the sentence beginning "One caveat, stated honestly: /blueprint does not
     yet hunt scope docs" through "and this skill never implies otherwise." Replace it with:
     "/blueprint harvests the scope doc itself from `docs/scope/` (or the older flat
     `docs/<idea>-scope.md`)."
   - Line 59: replace "these are the sections /blueprint Step 1 is meant to harvest once its
     deferred one-line edit lands; until then Tony points /blueprint at the doc himself — so
     keep it exact:" with "these are the sections /blueprint Step 1 harvests — so keep it
     exact:".
4. **jpb authority reference.** `plugins/jpb/skills/jpb/SKILL.md` lines 19 to 21 name
   `docs/jpb-vision.md` "in this repo". That file left this repo in PR #15 when JPB moved to
   its own repo; the document exists in the jpb repo, which is archived at
   `~/Developer/_archive/jpb/docs/jpb-vision.md` (verified 2026-09-13). Repoint the sentence
   to: "The design source of truth is `docs/jpb-vision.md` in the jpb repo (archived at
   `~/Developer/_archive/jpb`); on any conflict between this file and that doc, the vision
   doc wins and the conflict goes to Tony." Keep the precedence rule exactly. Grep the file
   for any other `jpb-vision` mention and repoint it the same way.
5. **Plugin manifests.** `plugins/*/.claude-plugin/plugin.json`, 21 files.
   - 19 carry `"homepage": "https://github.com/tiny-tunnel-dot/tony-skills"` and the same
     19 carry `"repository": "https://github.com/tiny-tunnel-dot/tony-skills"`. Set both
     fields in every manifest to `https://github.com/line7works/tony-skills` (the remote
     and the README). *(Amended 2026-09-13 after the E4 validators: the first version of
     this item named only `homepage`; the `repository` field carries the same stale URL.)*
   - Add `"version": "1.0.0"` to all 21 (the first versioned v1 release). Keep each file's
     key order and its 2-space formatting.
   - Validate: `claude plugin validate .` must pass with zero warnings;
     `python3 -m json.tool` on every file.
   - Do NOT touch the seven `tiny-tunnel-dot` mentions in sunrise's SKILL.md: those name the
     GitHub account new repos are created under, and they are correct.
6. **Stale readers claim in three callers.** `plugins/signoff/skills/signoff/SKILL.md`
   line 66, `plugins/recheck/skills/recheck/SKILL.md` line 36,
   `plugins/wargame/skills/wargame/SKILL.md` line 53 each say: "readers' fixed instruction
   forbids only web tools, spawning, summoning, and tracked-file writes, so these reach the
   reviewer only if the mandate carries them" (wargame says "the adversary"). Authority:
   `plugins/readers/skills/readers/assets/contract.md` ("The composed prompt opens with the
   fixed instruction: ... no web tool under any profile; use no other model, no MCP tool,
   and no outbound service; never summon /readers, use the Skill tool, or spawn agents; ...
   never a tracked file") and `plugins/readers/skills/readers/assets/readers.py` lines
   562 to 563. Replace that clause in each file with: "readers' fixed instruction already
   forbids web tools, other models, MCP tools, outbound services, spawning, summoning, and
   tracked-file writes; the mandate restates the workspace-only rule so the record carries
   it". Change nothing else on those lines.
7. **Stale example.** `plugins/readers/skills/readers/assets/examples/signoff.json`: remove
   the `"isolation": "worktree"` entry. Authority: signoff SKILL.md line 66, "no call passes
   readers' `isolation: worktree`". Keep the file otherwise identical (2-space JSON, key
   order). If a readers test loads the examples, run it.
8. **sunrise stale examples.** `plugins/sun/skills/sunrise/SKILL.md`.
   - Line 133: `project_pour_guys.md` / `project_belgariad_codex.md` become
     `project_pour_guys_website.md` / `project_project_knight.md` (both exist on disk;
     the belgariad file does not).
   - Line 306: "Mirror the shape of `project_knight.md`" becomes `project_project_knight.md`.
   - Line 134: the shortcut examples (`pk`, `haul`, `inky`, `pour`, `jpb`, `robo`, `smart`)
     become (`pk`, `haul`, `inky`, `pour`, `robo`, `dj`, `sit`), the live set verified in
     `~/.config/zsh/project-shortcuts.zsh` on 2026-09-13 (`jpb` and `smart` are not there).
9. **sunrise cue-order contradiction.** Line 93 says the vault gate runs "FIRST, before the
   cue, before anything else"; line 122 says the cue is "the FIRST thing the skill does".
   Authority: line 93 (the vault gate is the safety rule; the cue is cosmetic). Edit line
   122 only: "the FIRST thing the skill does" becomes "the first thing after the vault
   gate". Move no step.
10. **sunset wording.** `plugins/sun/skills/sunset/SKILL.md`.
    - Line 97: "sunrise/revive skill" becomes "sunrise skill" (no revive skill exists;
      revival is this skill's own "To revive" section). "the 3-line `sun_bar.py` stamp"
      becomes the line count the script actually prints: read `plugins/sun/assets/sun_bar.py`
      and state the count it produces (sunrise line 125 calls it one line).
    - Line 197: the tag step says "(run before the repo move and before GitHub archive)" but
      sits in Phase 5, after the Phase 4 move. Change the parenthetical to "(run before
      GitHub archive; after Phase 4, `<repo path>` is the archived location
      `~/Developer/_archive/<Name>`, or `~/Developer/<Name>` under `--keep-local`)". Move
      no step. *(Amended 2026-09-13 after the E4 review: the placeholder is `<Name>`, the
      form the rest of the file uses, and the `--keep-local` case is named.)*
    - Lines 40, 127, 159, 296: the memory placeholder `project_<slug>.md` becomes
      `project_<slug_>.md`, matching sunrise and the underscored filenames on disk.
11. **forge pointer.** `plugins/forge/skills/forge/SKILL.md` line 44: "point Tony to
    IMPLEMENTATION.md section 10" becomes "point Tony to
    `${CLAUDE_PLUGIN_ROOT}/IMPLEMENTATION.md` section 10" after confirming that file (at the
    plugin root) has a section 10. If it does not, leave the line and report.

## Out of scope, do not touch

inspect's absolute path on line 49; build's `REBUILT` ledger line; `models.json` prices;
any readers-protocol prose; any "What NOT to do" tail; any description other than sunrise's
(readers' description is re-quoted, not reworded); `docs/feedback.md`; anything outside
this checkout.

## Verification, run by the builder and pasted into the report

- Strict YAML parse of all 22 SKILL.md frontmatters with PyYAML `safe_load` and Ruby psych:
  all pass.
- `claude plugin validate .`: passes with zero warnings.
- `python3 -m json.tool` on all 21 `plugin.json` files and on `examples/signoff.json`: pass.
- sunrise description: character count at most 1,024; print its first 300 and first 500
  characters.
- `git diff --stat` and the full diff, with every hunk mapped to an item number.
- `git status --short` shows only the files named above plus the report.

## Completion report and commit

Write `docs/plans/2026-09-13-maintenance-patch-report.md`: for each item, done or left
alone and why; the verification output; every authority you could not confirm. Then make
one commit on this branch with the message
`fix: v1 maintenance patch (E3): YAML, descriptions, stale references, manifests`
including the report. Do not push.

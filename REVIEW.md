# REVIEW.md
<!-- verified: 2026-09-06 -->

## Passes
- correctness: on
- security: on
- accessibility: off (no UI: Markdown skills, JSON catalog, and Node MCP servers under tools/; no package.json, components/, or app/ at the root)
- data-safety: off (no hosted database: no .env.example at the root, no migrations folder, no DATABASE_URL / SUPABASE_* / POSTGRES_* / NEON_* key)

## Severity bar
- BLOCKER: data loss, auth bypass, a gate in AGENTS.md violated, a migration without a backup
- MAJOR: a user-visible regression, a failing check that CI would catch
- MINOR: everything else worth a line

## Repo-specific checks
- (one line per recurring finding, added on the second occurrence)
- sunrise: an edit the skill makes after Phase 2 pushed `main` (a kit-check fix, the post-link `.gitignore` re-assert) is never re-committed or re-pushed, yet the Phase 8 summary prints "pushed" · found 2026-09-04 (agent-file-flip Slice B, Phase 8) and 2026-09-05 (sunrise-live-run-fixes Slice A, Phase 3 step 2)
- readers: an input path escapes as an uncaught exception, a traceback on stderr and no JSON on stdout, where the entry promises JSON in every case (Slice A: `run()` on a bad request; Slice B: `suggest` on a run-dir fault) · found 2026-09-06 (readers Slice A signoff) and 2026-09-06 (readers Slice B signoff)
- readers: dispatch artefacts (`diagnostics/`, `dispatch.log`, command or request metadata) are written before a transport-level refusal that sends nothing, so the record shows a dispatch that did not happen (Slice A: `run()` before the no-adapter refusal; Slice B: both adapters before the canned-hook refusal) · found 2026-09-06 (readers Slice A signoff) and 2026-09-06 (readers Slice B signoff)

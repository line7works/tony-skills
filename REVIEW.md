# REVIEW.md
<!-- verified: 2026-09-07 -->

## Passes
- correctness: on
- security: on
- accessibility: off (no UI: Markdown skills, JSON catalog, and Node MCP servers under tools/; no package.json, components/, or app/ at the root)
- data-safety: off (no hosted database: no .env.example at the root, no migrations folder, no DATABASE_URL / SUPABASE_* / POSTGRES_* / NEON_* key)

## Severity bar
- BLOCKER: data loss, auth bypass, a gate in AGENTS.md violated, a migration without a backup
- MAJOR: a user-visible regression, a failing check that CI would catch
- MINOR: everything else worth a line
- readers: repo check (2) below (dispatch artefacts written before a refusal that sends nothing) is MAJOR for readers, never MINOR · Tony's word 2026-09-06 at the Slice C handoff ("Raise it to a major. Have it fixed on the next run")

## Repo-specific checks
- (one line per recurring finding, added on the second occurrence)
- sunrise: an edit the skill makes after Phase 2 pushed `main` (a kit-check fix, the post-link `.gitignore` re-assert) is never re-committed or re-pushed, yet the Phase 8 summary prints "pushed" · found 2026-09-04 (agent-file-flip Slice B, Phase 8) and 2026-09-05 (sunrise-live-run-fixes Slice A, Phase 3 step 2)
- readers: an input path escapes as an uncaught exception, a traceback on stderr and no JSON on stdout, where the entry promises JSON in every case (Slice A: `run()` on a bad request; Slice B: `suggest` on a run-dir fault) · found 2026-09-06 (readers Slice A signoff) and 2026-09-06 (readers Slice B signoff)
- readers: dispatch artefacts (`diagnostics/`, `dispatch.log`, command or request metadata) are written before a transport-level refusal that sends nothing, so the record shows a dispatch that did not happen (Slice A: `run()` before the no-adapter refusal; Slice B: both adapters before the canned-hook refusal) · found 2026-09-06 (readers Slice A signoff) and 2026-09-06 (readers Slice B signoff)
- readers callers: "mint a run id" never says fresh and the `<run id>-<row>` / `<run id>-<lens>` call-id pattern collides on a second pass, a retry, or a second lane under one run id (a call id is single-use, contract.md:21), and no caller says a retry or a second lane needs a fresh run id and its own `suggest` · found 2026-09-06 (readers Slice D signoff, precon:83 / architect:102) and 2026-09-06 (readers Slice E signoff, inspect:38)
- readers callers: no character rule for the minted run and call ids (contract.md:21: `[A-Za-z0-9._-]`); a run id with a space is `invalid-request` · found 2026-09-06 (readers Slice D signoff, precon:77 / architect:102) and 2026-09-06 (readers Slice E signoff, inspect:28)
- readers callers: the ask shows `session` (the roster placeholder) as the Claude row's model where the text promises "the model that row would send" · found 2026-09-06 (readers Slice D signoff, precon:77) and 2026-09-06 (readers Slice E signoff, inspect:28)
- readers callers: the default Claude reader depends on the Workflow tool (`packet-only`/`starved` on `claude-session` → `lane-unavailable` without it) and the ask names no fallback · found 2026-09-06 (readers Slice D signoff, precon:79) and 2026-09-06 (readers Slice E signoff, inspect:30)
- readers callers: the Workflow route's `<cwd>/.readers/<run id>/<call id>.workflow.js` copy carries the composed prompt into whatever repo the caller runs in, only tony-skills ignores it, and the caller's text never names it · found 2026-09-06 (readers Slice D signoff, readers.py:1075) and 2026-09-06 (readers Slice G signoff, jpb:57–60)
- readers callers: a typed model id on a Claude row is pinned verbatim as a harness model name and no existence check ever drops it, and the caller gives the session no source for a valid one · found 2026-09-06 (readers Slice D signoff, readers.py:225) and 2026-09-06 (readers Slice G signoff, jpb:119–128)
- readers callers: nothing refuses a `claude-session` request without `session_model` when no floor is passed, so a caller that omits it stamps `session` as the effective model · found 2026-09-06 (readers Slice E signoff, inspect:82) and 2026-09-06 (readers Slice G signoff, jpb:259–262)
- readers evidence: a number recorded in the slice's `docs/evidence/readers/` file does not reproduce from its own command (a character count for bytes, a limit computed with the wrong subtrahend, a before-edit grep count) · found 2026-09-06 (readers Slice E signoff, slice-e-fresh-read.md:16) and 2026-09-07 (readers Slice F signoff, slice-f-fresh-read.md:9, :25, :34)
- readers callers: the verdict or report records the run id at most and never the run dir, while the skill calls the `mktemp -d` sidecars "the evidence", so parity, isolation, and raw captures cannot be re-audited after scratch cleanup · found 2026-09-07 (readers Slice F signoff, vertical:84) and 2026-09-07 (readers Slice H signoff, signoff:119 / recheck:81)
- readers callers: a readers step the caller runs mid-review (a dispatch remembering a typed pick, a floored `suggest` dropping one) writes the tracked `plugins/readers/last-picks.json`, so a review of tony-skills mutates the union under review · found 2026-09-07 (readers Slice F signoff, vertical:101) and 2026-09-07 (readers Slice H signoff, signoff:66 / recheck:36 / wargame:53)

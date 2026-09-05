# REVIEW.md
<!-- verified: 2026-09-04 -->

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

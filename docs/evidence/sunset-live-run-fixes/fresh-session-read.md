# sunset-live-run-fixes — fresh-session read (2026-09-05)

Slice A of `docs/plans/2026-09-05-sun-live-run-fixes-2.md`, AC7. One fresh session, plain `claude -p --max-turns 12` from the repo root on branch `feat/sunset-live-run-fixes`, no `--plugin-dir` (that flag loads the branch copy beside the installed copy; see `docs/evidence/agent-file-flip/slice-a-requirement-map.md`). The session was told to read `plugins/sun/skills/sunset/SKILL.md` at its checkout path, so the answer exercises the edited text, not the installed cache (sun cache at run time: `2baaecba12a1`). Checkout commit read: `1617ce0`.

## Question

> Read the file plugins/sun/skills/sunset/SKILL.md in this repo (the /sunset skill source; do not run it and do not edit any file). Using only what that file says, answer in one short paragraph: (1) in Phase 4, in what order does the skill move the repo and copy the project memory store, and what happens if ~/Developer/_archive/<Name> already exists before the move; (2) what happens to the memory-store copy under --keep-local; (3) in Phase 6, where does the skill get the Vercel token when $VERCEL_TOKEN is unset (name the file path and the JSON key), and what must it never do with that token.

## Answer (verbatim)

> In Phase 4 the repo moves first and the memory copy comes second: after `mkdir -p ~/Developer/_archive`, a guard checks whether `~/Developer/_archive/<Name>` already exists, and if it does the skill stops and reports the `ls -la` of what is there rather than ever running `mv` onto an existing path (because `mv` onto an existing directory nests the source inside it, which is how the 2026-09-05 live run ended at `_archive/<Name>/<Name>/`); only then does it `mv ~/Developer/<Name> ~/Developer/_archive/<Name>`, and only after that does it `mkdir -p` the `.claude-memory/` folder inside the moved repo and `cp -R` the project's own store from `~/.claude/projects/*<Name>*/memory/` into it. Under `--keep-local` the whole of Phase 4 is skipped, the repo stays put so its memory store is not orphaned, and no copy of that store is made anywhere. In Phase 6, when `$VERCEL_TOKEN` is unset the skill reads the `token` key from the logged-in CLI's credentials file at `~/Library/Application Support/com.vercel.cli/auth.json` via `jq`, holds it only in a shell variable for the `Authorization: Bearer` header of the pause curl, and must never echo or print it or write it into the tombstone or any other file; if both sources are absent it does not guess but prints the ready-to-run curl and dashboard path for Tony to act on.

## Result

Pass. Names move-then-copy (guard, `mv`, then `mkdir -p` and `cp -R` into the moved repo), the STOP with an `ls -la` report when `~/Developer/_archive/<Name>` already exists, the skip of the copy under `--keep-local` (whole phase skipped, store not orphaned), the `auth.json` path with key `token` read via `jq` into a variable for the `Authorization` header only, the never-echo/never-write rule, and the stop only when both sources are absent.

## Post-merge check (not yet run)

After the PR merges and Tony reinstalls `sun` (`/plugin update sun@tony-skills`), the same question is re-asked as plain `claude -p` against the installed cache and the answer appended here. Out of scope for the slice (plan, Out of scope).

# sunset-live-run-fixes — fresh-session read (2026-09-05)

Slice A of `docs/plans/2026-09-05-sun-live-run-fixes-2.md`, AC7. One fresh session, plain `claude -p --max-turns 12` from the repo root on branch `feat/sunset-live-run-fixes`, no `--plugin-dir` (that flag loads the branch copy beside the installed copy; see `docs/evidence/agent-file-flip/slice-a-requirement-map.md`). The session was told to read `plugins/sun/skills/sunset/SKILL.md` at its checkout path, so the answer exercises the edited text, not the installed cache (sun cache at run time: `e7064921ac21` per installed_plugins.json; an earlier draft of this line said `2baaecba12a1`, the first directory an `ls` listed, corrected 2026-09-05 after the signoff's seams reviewer caught it). Checkout commit read: `1617ce0`.

## Question

> Read the file plugins/sun/skills/sunset/SKILL.md in this repo (the /sunset skill source; do not run it and do not edit any file). Using only what that file says, answer in one short paragraph: (1) in Phase 4, in what order does the skill move the repo and copy the project memory store, and what happens if ~/Developer/_archive/<Name> already exists before the move; (2) what happens to the memory-store copy under --keep-local; (3) in Phase 6, where does the skill get the Vercel token when $VERCEL_TOKEN is unset (name the file path and the JSON key), and what must it never do with that token.

## Answer (verbatim)

> In Phase 4 the repo moves first and the memory copy comes second: after `mkdir -p ~/Developer/_archive`, a guard checks whether `~/Developer/_archive/<Name>` already exists, and if it does the skill stops and reports the `ls -la` of what is there rather than ever running `mv` onto an existing path (because `mv` onto an existing directory nests the source inside it, which is how the 2026-09-05 live run ended at `_archive/<Name>/<Name>/`); only then does it `mv ~/Developer/<Name> ~/Developer/_archive/<Name>`, and only after that does it `mkdir -p` the `.claude-memory/` folder inside the moved repo and `cp -R` the project's own store from `~/.claude/projects/*<Name>*/memory/` into it. Under `--keep-local` the whole of Phase 4 is skipped, the repo stays put so its memory store is not orphaned, and no copy of that store is made anywhere. In Phase 6, when `$VERCEL_TOKEN` is unset the skill reads the `token` key from the logged-in CLI's credentials file at `~/Library/Application Support/com.vercel.cli/auth.json` via `jq`, holds it only in a shell variable for the `Authorization: Bearer` header of the pause curl, and must never echo or print it or write it into the tombstone or any other file; if both sources are absent it does not guess but prints the ready-to-run curl and dashboard path for Tony to act on.

## Result

Pass. Names move-then-copy (guard, `mv`, then `mkdir -p` and `cp -R` into the moved repo), the STOP with an `ls -la` report when `~/Developer/_archive/<Name>` already exists, the skip of the copy under `--keep-local` (whole phase skipped, store not orphaned), the `auth.json` path with key `token` read via `jq` into a variable for the `Authorization` header only, the never-echo/never-write rule, and the stop only when both sources are absent.

## Post-merge installed-cache read (2026-09-05)

PR #44 merged as 25d3a30; Tony ran `/plugin update sun@tony-skills` (installed_plugins.json: `sun@tony-skills` at 25d3a306ed32, 15:26Z; the cache's sunset file is byte-identical to `main`). The same question was re-asked as plain `claude -p --max-turns 12` from the repo root, pointing at the installed cache path.

### Question

> Read the file /Users/tonycoon/.claude/plugins/cache/tony-skills/sun/25d3a306ed32/skills/sunset/SKILL.md (the installed /sunset skill; do not run it and do not edit any file). Using only what that file says, answer in one short paragraph: (1) in Phase 4, in what order does the skill move the repo and copy the project memory store, and what happens if ~/Developer/_archive/<Name> already exists before the move; (2) what happens to the memory-store copy under --keep-local; (3) in Phase 6, where does the skill get the Vercel token when $VERCEL_TOKEN is unset (name the file path and the JSON key), and what must it never do with it.

### Answer (verbatim)

> In Phase 4 the skill moves the repo first and copies memory second: it runs `mkdir -p ~/Developer/_archive`, then a guard that checks whether `~/Developer/_archive/<Name>` already exists, and if it does the skill STOPs and reports the `ls -la` of what is there, never running `mv` onto an existing path (because `mv` onto an existing directory nests the source inside it, which is how the 2026-09-05 live run ended at `_archive/<Name>/<Name>/`). Only after the `mv` succeeds does it create `.claude-memory/` inside the moved repo and `cp -R` the project's own memory store into it, leaving the original in place as a harmless orphan. Under `--keep-local` the repo stays put, the store is not orphaned, and no memory copy is made anywhere; the tombstone records it as left in place at its source path. In Phase 6, when `$VERCEL_TOKEN` is unset, the token comes from key `token` in `$HOME/Library/Application Support/com.vercel.cli/auth.json`, read with `jq` inside a single command line that unsets the variable at the end. The skill must never echo or print the token, never run the `jq` read on its own to check it, never add `-v`, `--trace`, or `set -x`, and never write it into the tombstone or any file; a 401 or 403 means hand the ready-to-run curl and dashboard path to Tony rather than debug the token.

### Result

Pass. Names guard, then `mv`, then the copy into the moved repo; the STOP with `ls -la` on an existing path; no copy under `--keep-local`; the credentials file path with key `token` read by `jq` in one command line that unsets the variable; the never-echo, never-standalone-jq, never `-v`/`--trace`/`set -x`, never-write rule; and the 401/403 hand-off.

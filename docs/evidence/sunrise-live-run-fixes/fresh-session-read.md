# sunrise-live-run-fixes — fresh-session read (2026-09-05)

Slice A, AC4. One fresh session, plain `claude -p --max-turns 12` from the repo root on branch `feat/sunrise-live-run-fixes`, no `--plugin-dir` (that flag loads the branch copy beside the installed copy; see `docs/evidence/agent-file-flip/slice-a-requirement-map.md`). The session was told to read `plugins/sun/skills/sunrise/SKILL.md` at its checkout path, so the answer exercises the edited text, not the installed cache (sun cache at run time: `75b836b0c1ff`). Checkout commit read: `8e42e4d`.

## Question

> Read the file plugins/sun/skills/sunrise/SKILL.md in this repo (the /sunrise skill source; do not run it and do not edit any file). Using only what that file says: (1) what exact command does Phase 3 step 1 run, and why is the Vercel project named with the slug rather than the directory name; (2) what does Phase 3 do to .gitignore immediately after linking, why, and what does it verify afterwards. Answer in one short paragraph, quoting the command.

## Answer (verbatim)

> Both answers come from lines 231 and 232 of `plugins/sun/skills/sunrise/SKILL.md`.
> 
> Phase 3 step 1 runs `npx vercel link --yes --project <slug>`. It names the Vercel project with the slug rather than the directory name because Vercel requires lowercase project names, and the directory-derived `Banana-Dunk` was rejected with HTTP 400 on the 2026-09-05 live run, while the repo and local directory keep `<Name>`. Immediately after linking, step 2 re-asserts `!.env.example` as the last line of `.gitignore`, because `vercel link` appends `.vercel` and `.env*` to the end of the file, below the negation Phase 1 added, so `.env.example` would be silently ignored again. The skill notes the live run only kept it tracked because it was already committed, and that this step is not redundant with Phase 1 since linking rewrites the file after Phase 1 verified it. It then re-runs the Phase 1 step 3 check, verifying three things: `.env.example` is not ignored, `.env.local` is still ignored, and `.vercel` is ignored.


## Result

Pass. Names `npx vercel link --yes --project <slug>`, the lowercase reason with the HTTP 400 rejection, the `!.env.example` last-line re-assert with its cause (`vercel link` appends `.vercel` and `.env*` to the end), and all three verification checks (`.env.example` not ignored, `.env.local` ignored, `.vercel` ignored).

## Post-merge installed-cache read (2026-09-05)

PR #43 merged as e706492; Tony ran `/plugin update sun@tony-skills` (installed_plugins.json: `sun@tony-skills` at e7064921ac21, 14:43Z, then 25d3a306ed32 after PR #44, 15:26Z). The same question was re-asked as plain `claude -p --max-turns 12` from the repo root, pointing at the installed cache path, after the second update; the cache's sunrise file is byte-identical to `main` 25d3a30.

### Question

> Read the file /Users/tonycoon/.claude/plugins/cache/tony-skills/sun/25d3a306ed32/skills/sunrise/SKILL.md (the installed /sunrise skill; do not run it and do not edit any file). Using only what that file says: (1) what exact command does Phase 3 step 1 run, and why is the Vercel project named with the slug rather than the directory name; (2) what does Phase 3 do to .gitignore immediately after linking, why, and what does it verify afterwards. Answer in one short paragraph, quoting the command.

### Answer (verbatim)

> Phase 3 step 1 runs `npx vercel link --yes --project <slug>`, and the file says it uses the slug rather than the directory name because Vercel requires lowercase project names, and the directory-derived `Banana-Dunk` was rejected with HTTP 400 on 2026-09-05, so the Vercel project is `<slug>` while the repo and local dir keep `<Name>`. Immediately after linking, step 2 re-asserts `!.env.example` as the last line of `.gitignore`, because `vercel link` appends `.vercel` and `.env*` to the end of the file below the negation Phase 1 added, so `.env.example` is silently ignored again, and it notes the live run only kept it tracked because it was already committed. It then verifies with `git check-ignore --no-index`, since the default form is silent on already tracked files: `git check-ignore --no-index .env.example` must print nothing and exit 1, which the file stresses is the pass, and `git check-ignore --no-index .env.local .vercel` must print both and exit 0, proving `.env.local` and `.vercel` stay ignored.

### Result

Pass. Same content as the branch read: `npx vercel link --yes --project <slug>`, the lowercase reason with HTTP 400, the `!.env.example` last-line re-assert and its cause, and the `git check-ignore --no-index` verification with the exit-1-is-pass note.

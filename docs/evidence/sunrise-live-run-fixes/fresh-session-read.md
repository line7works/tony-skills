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

## Post-merge check (not yet run)

After the PR merges and Tony reinstalls `sun` (`/plugin update sun@tony-skills`), the same question is re-asked as plain `claude -p` against the installed cache and the answer appended here. Out of scope for the slice (plan, Out of scope).

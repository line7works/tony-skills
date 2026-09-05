# sun-live-run-fixes-2 — fresh-session read, sunrise (2026-09-05)

Slice B, AC5 (with AC7's added "Where to look" question). One fresh session, plain `claude -p --max-turns 12` from the repo root on branch `feat/sunrise-follow-ups`, no `--plugin-dir` (that flag loads the branch copy beside the installed copy; see `docs/evidence/agent-file-flip/slice-a-requirement-map.md`). The session was told to read `plugins/sun/skills/sunrise/SKILL.md` at its checkout path, so the answer exercises the edited text, not the installed cache (sun cache at run time: `25d3a306ed32`). Checkout commit read: `5a2b5d5`.

## Question

> Read the file plugins/sun/skills/sunrise/SKILL.md in this repo (the /sunrise skill source; do not run it and do not edit any file). Using only what that file says: (1) what does Phase 8 do before proving the deploy is live when the working tree is dirty, and what command decides whether the tree is dirty; (2) what example directory name does Phase 3 step 1 cite as rejected by Vercel, and why; (3) what does the seeded AGENTS.md template's "Where to look" section say about where durable notes live. Answer in one short paragraph per question, quoting the command and the example name.

## Answer (verbatim)

> **1. Phase 8 pre-flight.** Before step 1 proves the deploy is live, Phase 8 runs a pre-flight that commits and pushes the working tree, since Phase 1 made the only commit and Phase 2 the only push, and later phases (the Phase 3 step 2 `.gitignore` re-assert, the appends from `vercel link`, Electron placeholder files, a kit-check fix) leave uncommitted edits. The command that decides dirtiness is `git status --porcelain`, which must print nothing. If it prints anything, the skill runs one line, `git add -A && git commit -m "sunrise: post-link .gitignore re-assert and closeout edits" && git push`, then reruns `git status --porcelain`. If still dirty, it STOPs and reports. Only after this passes may the step 2 summary say "(git init, pushed)". The file notes this is the same first-day push to `main` as Phase 2, not a violation of the feature-branch gate.
> 
> **2. Phase 3 step 1 example.** The link command is `npx vercel link --yes --project <slug>`, and the rejected example name is `My-App`. The reason given: Vercel requires lowercase project names, so a directory-derived mixed-case name like `My-App` is rejected with HTTP 400 (seen 2026-09-05). The Vercel project is therefore always `<slug>`, never `<Name>`, while the repo and local directory keep `<Name>`.
> 
> **3. Seeded AGENTS.md "Where to look".** Its durable-notes line says: "Durable notes (research, decisions, specs): Tony's vault project folder for this project; the memory home note and the vault `_index.md` record where it lives (machine-specific paths stay out of this file)." So the template names the vault project folder as the home, defers the actual location to the memory note and the vault index, and deliberately keeps machine paths out of AGENTS.md. The same section also lists loop paperwork under `docs/scope/`, `docs/architecture/`, `docs/plans/`, and `docs/reviews/`, plus the Notion board URL with IDs in the vault index.

## Result

Pass. (1) names the Phase 8 pre-flight, the `git status --porcelain` empty-tree test, the one-line commit-and-push, the rerun, the STOP on a still-dirty tree, and that "(git init, pushed)" prints only after it passes. (2) cites the generic `My-App` example with the lowercase reason and the HTTP 400, no real project name. (3) quotes the seeded `AGENTS.md` durable-notes line, which names the vault project folder and defers its location to the memory home note and the vault `_index.md`; the answer contains no absolute or home-relative path.

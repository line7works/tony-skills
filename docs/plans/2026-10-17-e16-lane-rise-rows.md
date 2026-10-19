# E16 slice 2: sunrise's own rows, the local half

Written 2026-10-17 by the slice 2 row author (Opus 5.5 at high, R2). **Revision 3**: the one fix round (contract
section 14) on the outside reviewer's read of revision 2 (frozen at fd3e53b649a76d53; 5 BLOCKER, 8 MAJOR), under
the owner's picks "Machinery round first", "Run to the end" ("Anything v1 did itself, v2 does itself; you accept
v1's risk for those steps") and "I don't want this over engineered", and the frame's words A151 as the control room
quoted them. This revision replaces revision 2. **Status: for the reviewer's check; no row is admitted; no slice
has the owner's go.** A row resting on a slice 1 mechanism says **[M-n]** (section 9).

**Revision 4**, one narrow round on the owner's word ("One more narrow round"): only R1, R5, R7, R9, R10 and R11 of
the reviewer's check (`SCRATCH/astra-check-1.md`) change, each by her closing rule, with N1's citations of SEC-7's new
row (A152; frame 08e3db8af9218ea1). Each change is marked **(rev 4)**; nothing else is touched.

## 0. The findings, and where each is closed

| Finding | Severity | Closing rule, in short | Closed in |
|---|---|---|---|
| R1 | MAJOR | complete every ROW-1 entry | 3.0's shared declarations; 3.1's alternatives; every row's output fields, tracked state and resting places stated |
| R2 | BLOCKER | a missing parent is its own operation, or a whole subtree in one | 3.5: SR03-docs, SR03-docs-scope, SR03-docs-architecture, SR03-docs-reviews and SR12b-dir are operations of their own, and the rows inside them need them; no row makes a parent [M-3] |
| R3 | BLOCKER | a permitted content path for the scaffold and the lift | 3.4 and 3.5: the SR02 rows and SR03-agents carry RK18 and cite A151, each window in one line |
| R4 | BLOCKER | a construction that enforces the condition, or the conflict | 3.5: SR03-claude carries RK18 and cites A151 for its condition on AGENTS.md, read just before the swap |
| R5 | BLOCKER | bind checks to the index, commit or content they check | 3.8, 3.10, 3.11, 3.16: `subject_git` `index` on SR07-scan, `head` on SR13-agents, SR14 and SR25; SR13-claude and SR13-canary on their file's sha256 |
| R6 | BLOCKER | refuse an occupied destination branch | 3.6: SR05-main renames with `-m`, never `-M`; git's own refusal enforces the destination in the same request |
| R7 | MAJOR | the scaffolds' staging and repository behavior; the commit hooks | 3.1 and section 2: every scaffolder runs in an empty staged folder [M-6], its possible `.git` listed; the commit runs with every hook off |
| R8 | MAJOR | validate the filled parts; target the project folder | 3.13: L24 targets `<F>`; the check is on the shortcut and on `<F>` [M-8] |
| R9 | MAJOR | local closeout predicates and the no-hosting baseline | 3.16: SR25's clean read and local head equal to the pushed head; (rev 4) SR25-build, SR25-npm, SR25-uv, SR25-html |
| R10 | MAJOR | the kit's predicates establish the kit | 3.5: AGENTS.md's five sections and Gates line; SR03-claude needs AGENTS.md at the state level; CLAUDE.md's first line [M-7]; SR03-envex-keys; v1's old pointer line replaced |
| R11 | MAJOR | the layer mapping and the scaffold choices | 3.0's mapping table; 3.4's six v1-named scaffolds; (rev 4) no free override, by the owner's ruling A152 |
| R12 | MAJOR | the destination-side read; the already-moved disclosure | 3.7 and [M-2]: destinations read first, "already adopted" line; a move a kill left landed is FORM-2's `not proven` |
| R13 | MAJOR | the provider links in the durable seed | 3.12: SR20-github, SR20-hosting, SR20-database, each needing its provider's output |

(rev 4) The reviewer's check left six standing; each is closed again here: R1 in 3.8 (SR07-stage's and SR07's
content classes); R5 in 3.1, 3.10 and 3.16 (SR13-agents and SR25 check the committed tree they track, `subject_git`
`head`, by `git.agents-committed`; SR14's push scan already reads the head); R7 in section 2, 3.1 and 3.4 (each
scaffolder's repository writes turned off by its documented flag, or none by its documented behavior, and one builder
measure named as such); R9 in 3.0 and 3.16 (one baseline per scaffold, the single file included, no push); R10 in 3.5
(SR03-agents' predicate is every line of the filled template body; its edit adds each missing line under its
heading); R11 in 3.4, 6 and 12 (the owner's ruling A152). N1: SR02's rows and SR03-agents cite SEC-7's row (A152).

## 1. Reading line

As revision 1, and for this round: `SCRATCH/astra-read-1.md` and `SCRATCH/seams-open.md`, whole; `engine.py`'s
check-subject code. Not opened: `brief-28.md` and `brief-29.md`, which lie in another lane's scratch folder that the
brief's wall bars ("any evidence or scratch folder other than EVIDENCE and SCRATCH"), nor A147 and A151 themselves,
which are in the docs worktree; A151 is used as the control room quoted it, A147 as the reviewer reports it. So
section 9 names mechanisms by this document's ids, for the control room to map to G19 and G20.

## 2. ROW-2 reports

None. (rev 4, R7) Every scaffolder runs in an empty folder the tool makes in staging [M-6], so each is pointed at
staging. Its repository writes are turned off where it documents a way (`create-next-app --disable-git`, `create
astro --no-git`, `uv init --vcs none`), are none where it documents none (`npm init` writes `package.json` only), and
for `create @quick-start/electron`, whose documents this lane could not read, are the builder's measure, named as
such: where the measure shows it initializes a repository and that cannot be turned off, its writes are declared line
by line (`git init`, and any `git add` and `git commit` it runs) in its declaration and in SR02-electron's repo
commands; where they cannot be listed, SR02-electron is reported under ROW-2 before the preview [OP-11].

## 3. The rows

### 3.0 The lane, and what every row shares

- `kind` sunrise; `phases` `["sunrise"]`; `alias_reads` `[]`.
- `questions`, all in the look [RUN-5]: `description` (required); `type` (required, the kept four [M-5]);
  `answers.shortcut` (2 to 5 lowercase letters or digits [M-8]); and a staged doc's questions [M-2]. Nothing is
  asked after the go: this lane has no owner step and no owner answer.
- Names by place [RUN-2 (a)]: 0 `<Name>`, 1 `<slug>`, 2 `<slug_>`.
- Inputs: `type`; `flags.scaffold`, a scaffold word of 3.4, unless he names a folder (`adopt."project folder"`);
  `flags.hosting`, `flags.local_proof` and `drop_layers` by this mapping (v1's archetype matrix and flags; A1 P6 to
  P8; R11):

| Type | Layers by default | `--no-db` | `--no-vercel` | `--no-github` |
|---|---|---|---|---|
| web app | github, hosting, database, vault, memory, shortcut | drops database | drops hosting and database | drops github, hosting and database ("local + vault + memory only") |
| static site | github, hosting, vault, memory, shortcut | (none to drop) | drops hosting | drops github and hosting |
| desktop app | github, hosting (the env plane), database, vault, memory, shortcut | drops database | drops hosting and database | drops github, hosting and database |
| script or CLI | github, vault, memory, shortcut | (none to drop) | (none to drop) | drops github |

  The database comes through the hosting project's marketplace, so dropping hosting drops it. `flags.hosting` is
  false where hosting is no layer; `flags.local_proof` is then, by the scaffold (rev 4, R9), `build` (SR02-next,
  SR02-astro, SR02-electron), `npm`, `uv` or `html`. No shortcut
  drops `shortcut`. `--dry-run` is the look itself.
- Locations [E16-12]: `developer_root`, `staged_docs`, `vault_projects`, `vault_index`, `vault_link_prefix`,
  `memory_home`, `memory_index`, `shortcut_file`, `shell_startup`.
- Shorthand: `<F>` is the output field `project folder.path`; `P(...)`, `T(...)` path and text marks; `in:x` an
  input; `loc:x` a location; `today` the run's date [M-8].
- **Shared declarations** (R1). `N` means each of these entries is `none`: lost answer, reverse inputs, span, mode,
  safe content, answers, review file, owner names, keep scope, keeps required [ROW-1 F, or O with its condition not
  holding: no row is a create, none declares a way back, none retires a thing, none is an owner row]. `W` means way
  back `none`, "the row declares none: no sunrise undo (A2, Q5)" [EV-4]. A check's planning test, before-test,
  after-test, construction, repo commands and after-check are `none` [ROW-1 F], and its way back `none` [F]. A
  build's or an adopt's way back is `none` [F]. Every `validators` entry is `none` unless a row names one. "Resting
  places" names every place outside the run directory a row's content reaches.

### 3.1 The declared commands

Every command: no registered environment name, no protected input, trace flags `--verbose`, `--debug`, `--trace`,
no side effect, **alternative results: none** (R1). Git prints text, so a git command declares no field and is read
by its exit [SEC-4]. `{work}` is `<F>`. A scaffolder runs with the empty staged folder as its working folder and
writes `.` [M-6]. The git commands are slice 3's declarations (seams file, line 11); those marked † are reads this
lane asks slice 3's builder to add (section 7).

| Command | Template | Limit (s) | Effects; repository | Exits | Fields | Definite: success / refusals |
|---|---|---|---|---|---|---|
| `git.config-email` † | `git config --get user.email` | 10 | 0; no | 0 success, 1 not-found | none | success / not-found |
| `git.config-name` † | `git config --get user.name` | 10 | 0; no | 0 success, 1 not-found | none | success / not-found |
| `git.init` | slice 3's `git -C {work} init --quiet --initial-branch main` | 30 | 1; listed: "makes `.git`" | 0 success | none | success / none |
| `git.rename-main` | slice 3's `git -C {work} branch -m main`, never `-M` | 10 | 1; listed: "renames the current branch to main" | 0 success, 128 conflict (main exists) | none | success / conflict |
| `git.stage` | slice 3's `git -C {work} add --all` | 120 | 1; listed: "stages every path not ignored" | 0 success | none | success / none |
| `git.commit` | slice 3's `git -C {work} -c core.hooksPath=/dev/null commit --quiet -m {message}`: no hook of any kind runs (R7) | 60 | 1; listed: "commits the index on main" | 0 success | none | success / none |
| `git.clean` | slice 3's clean read | 30 | 0; no | 0 success (clean), 1 conflict | none | success / conflict |
| `git.staged-diff` † | `git -C {work} diff --cached --quiet` | 30 | 0; no | 0 success, 1 conflict (the index differs from the head) | none | success / conflict |
| `git.agents-committed` † (rev 4, R5) | `git -C {work} cat-file -e HEAD:AGENTS.md`: the committed tree holds `AGENTS.md` at that exact path and case | 10 | 0; no | 0 success, 128 not-found | none | success / not-found |
| `scaffold.next` | `npx --yes create-next-app@latest . --yes --disable-git` | 900 | 1; repository writes off, by its documented `--disable-git` (rev 4, R7) | 0 success | none | success / none |
| `scaffold.astro` | `npm create --yes astro@latest -- . --template minimal --install --no-git --yes --skip-houston` | 900 | 1; off, by its documented `--no-git` | 0 success | none | success / none |
| `scaffold.electron` | `npm create --yes @quick-start/electron@latest . -- --template vanilla` | 900 | 1; the builder's measure, named as such (section 2): off, or listed line by line | 0 success | none | success / none |
| `scaffold.npm` | `npm init --yes` | 120 | 1; none: it documents writing `package.json` only | 0 success | none | success / none |
| `scaffold.uv` | `uv init --vcs none --app .` | 120 | 1; off, by its documented `--vcs none` | 0 success | none | success / none |
| `scaffold.build` (rev 4, R9) | `npm --prefix {work} run build` | 900 | 1; none: the scaffold's own build writes its documented output folder, ignored by its own `.gitignore` | 0 success | none | success / none |
| `scaffold.package` (rev 4, R9) | `npm --prefix {work} pkg get name` | 30 | 0; no | 0 success | none | success / none |
| `scaffold.run-py` (rev 4, R9) | `python3 -I -B {work}/main.py` (the documented hello program `uv init --app` makes, run with no bytecode written) | 60 | 0; no | 0 success | none | success / none |
| `adapter.canary` (via adapter) | the adapter has the harness quote the first line of the instructions it was given in `{work}`, and compares it in its own code with AGENTS.md's first content line | 120 | 0; no | 0 success | `match`: place `["match"]`, state, fixed, `same` or `differs`, required in success | success / none |

(rev 4, R7) Only SR02-electron can meet a `.git` its scaffolder made, and only where the builder's measure lists it;
SR05 then finds it `already so`, and SR05-main and SR07 work on it as on any repository.

### 3.2 SR00, check: git can commit as someone

- id, kind, phase: SR00, check, sunrise. Thing: role "the identity git commits as"; identity none; tracked none: its
  subject is git's own configuration, read anew at each attempt (OP-8: SR07 needs an attempt of its own invocation);
  passes `[command email success, command name success]`
- commands `email` (`git.config-email`), `name` (`git.config-name`)
- output `git identity`, fields none; needs none; condition none; `N`
- content classes: exits as fixed words; stores the attempt's word; shows safe text; resting places none
- form lines: preview "check that git has a user name and an email to commit as"; status `passed`

### 3.3 SR01, adopt: the folder he named

- id, kind, phase: SR01, adopt, sunrise. Thing: role "the project folder he named"; identity path; place
  `in:adopt.project folder`; tracked exists, identity [OP-10]
- planning test `[path in:adopt.project folder is dir]`; before-test, after-test, construction, commands, repo
  commands, after-check: none [ROW-1 F]
- output `project folder`, field `path`: `in:adopt.project folder`; needs none; condition none
- owner names `{input: "adopt.project folder"}`; the other entries of `N`: none
- content classes: his typed path (safe, SEC-9) and the folder's identity (the tool's measure); resting places none
- form lines: preview "take <path> as the project folder, as you named it; this step changes nothing in it";
  status FORM-2's `adopted`

### 3.4 SR02-next, SR02-astro, SR02-html, SR02-electron, SR02-npm, SR02-uv, build: the scaffold **[RK18, A151]**

v1's six named scaffolds for the four kept types; one row each, one condition each. (rev 4, R11) No free override:
the owner's ruling A152, his pick in his words, "Six named only (Recommended)": "Drop the free override. A new
scaffolder becomes one more declared row when you want it. Every program the tool runs stays declared."

| Row | `flags.scaffold` | Builder |
|---|---|---|
| SR02-next | `web app` | `scaffold.next` |
| SR02-astro | `static site` | `scaffold.astro` |
| SR02-html | `static site, single file` | none: `files` `[{rel: "index.html", text: a page titled <Name> holding his line}]` |
| SR02-electron | `desktop app` | `scaffold.electron` |
| SR02-npm | `script or CLI` | `scaffold.npm` |
| SR02-uv | `script or CLI, Python` | `scaffold.uv` |

- kind, phase: build, sunrise. Thing: role "the project folder"; identity path; place `P(loc:developer_root,
  <Name>)`; tracked exists, identity
- planning test `[the place is absent]` (never clobber); before-test `[free: the place is absent]`; after-test and
  after-check `[the place is dir]`
- construction: C1, `builder` as the table, run in the empty staged folder [M-6] (SR02-html: `files`), `mode` 0o755,
  risks `["RK18"]` (A151): "a scaffolder that writes a secret into its project publishes it into the project folder
  as it stands; SR07-scan reads it before any commit"
- commands `scaffold` as the table (SR02-html none); repo commands none, since each scaffolder's repository writes
  are off or none (3.1), but SR02-electron's, which are `["scaffold"]` only where the builder's measure lists them
  (section 2) (rev 4, R7) [OP-11]
- output `project folder`, field `path`: the place; needs none; condition `{on: fact, fact: "flags.scaffold",
  equals: <word>, reason: "the project type"}`; `N`
- content classes: reads nothing of the scaffold; stores no record; publishes the scaffolder's files, held (SEC-4),
  as they stand and shown nowhere (A151); shows safe text; resting places staging and the project folder, by SEC-7's
  row for a scaffolder's files in a row RK18 names (A152) (rev 4, N1)
- form lines: preview "make <developer_root>/<Name> with <the scaffolder's command>; nothing stands at that place
  until it is complete"; status `done`

### 3.5 The kit in place, change **[M-3]**

One row per file or folder [OP-1]. Each is published where absent, as C1 publishes (the change of an absent thing,
F-2 as A147 settled it), merged by v1's rule where it stands, and `already so` where it holds the kit. A parent
folder is an operation of its own, and each row inside it needs it; no row makes a parent (R2).

Shared: kind change, phase sunrise; thing role "the kit's <file>", identity path, place `P(<F>, <file>)`, tracked
exists, sha256; planning test `[path the place]`, by the probe [RUN-6]; before-test "absent, or standing without the
row's kit predicate" [M-3]; after-test and after-check the kit predicate; construction C3 with the row's `kit` edit
[M-3], risks `["RK2"]` unless named; commands and repo commands none; output `kit <file>`, field `path`: the place;
needs as the table, each `{state, ..., then not applicable}`; condition none unless named; `N`; `W`; content classes:
reads the file's lines compared in memory (protected or held), stores hashes, shows safe text, resting place the
file (A147: what stood in it is carried unchanged and shown nowhere); form lines: preview as the table, status
`done` or FORM-2's `already so`.

| Row | Place | Needs | Edit where it stands | Where absent | Kit predicate | Preview |
|---|---|---|---|---|---|---|
| SR03-docs | `docs/` | project folder | kept | the folder holding an empty `.gitkeep` | `docs` is dir | "lay docs/ with its .gitkeep" |
| SR03-docs-scope, -architecture, -reviews | `docs/scope/`, `docs/architecture/`, `docs/reviews/` | kit docs/ | kept | an empty folder | the folder is dir | "lay docs/scope/" (and the others) |
| SR03-agents | `AGENTS.md` | project folder | (rev 4, R10) each line of the filled template body that the file lacks is added under its heading, the heading added where it is absent, so a file of bare headings gains every required line; what stands is kept, a framework block on top; where its one content line points at `CLAUDE.md` (v1's old stub), that line is replaced by the body; where CLAUDE.md holds lines beyond the stub, they are added unchanged under "Lifted from CLAUDE.md". Risks `["RK2", "RK18"]` (A151): "a merge or lift v1 would have shown you first is written without showing it; nothing is removed but v1's two-line stub, where its two lines are the file's whole content" (the join's punch list: the stub G24-5 replaces, report-33). Resting place: the file, by SEC-7's row for lines lifted unchanged between the project's own files in a row RK18 names (A152) (rev 4, N1) | the filled template | (rev 4, R10) every line of the filled template body present under its heading: the description line; the Commands lines (the scaffold's run, build and typecheck, from the lane's table [M-1]) and the Env line; the Conventions and Footguns lines; the two Where to look lines; the three Gates lines | "lay AGENTS.md, or add each kit line the one there lacks" |
| SR03-claude | `CLAUDE.md` | kit AGENTS.md, at the state level (R10) | replaced by `@AGENTS.md`; before-test also `{id: lifted, on: other}`: each of its lines beyond the stub stands in AGENTS.md, read just before the swap. Risks `["RK2", "RK18"]` (A151): "a writer that removes the lifted lines from AGENTS.md between that read and the swap leaves CLAUDE.md's body only in this run's before-image record" | `@AGENTS.md` | line 1 is `@AGENTS.md` [M-7], and the file is no link | "make CLAUDE.md the one-line stub, its body lifted into AGENTS.md" |
| SR03-readme | `README.md` | project folder | kept | `# <Name>`, his line, the scaffold's run command | the file stands | "lay README.md where there is none" |
| SR03-ignore | `.gitignore` | project folder | the three lines added at its end | the three lines | the span `.env*`, `.vercel`, `!.env.example` once, at the end | "add the three ignore lines to .gitignore" |
| SR03-envex | `.env.example` | project folder | kept | `# the keys this project reads, with no values` | the file stands | "lay .env.example where there is none" |
| SR03-envex-keys | `.env.example`; layer `database` | kit .env.example | each of the database module's required key names, one `NAME=` line each, added at the end where absent | (stands by its need) | each `NAME=` line present | "list the database's key names in .env.example, with no values" |
| SR12a | `vercel.json`; condition type `desktop app`, layer `hosting` | project folder | kept | `{"outputDirectory": "public"}` | the file stands | "add the desktop app's vercel.json" |
| SR12b-dir | `public/`; the same | project folder | kept | an empty folder | the folder is dir | "lay public/ for the hosting placeholder" |
| SR12b | `public/index.html`; the same | kit public/ | kept | a page titled `<Name>` saying it is the hosting placeholder | the file stands | "add the desktop app's public/index.html" |

The template is v1's `AGENTS.md` with section 5's changes; its Commands lines are the scaffold's run, build and
typecheck commands from the lane's table keyed by `flags.scaffold` [M-1], a line with no command cut; `today` [M-8].

### 3.6 SR05 and SR05-main, change: the repository on main **[RK18, A151]**

- id, kind, phase: SR05 (SR05-main), change, sunrise. Thing: role "the project's git repository" ("its current
  branch"); identity path; place `P(<F>, ".git")` (`P(<F>, ".git", "HEAD")`); tracked exists (exists, sha256)
- planning test `[path the place]`, by the probe
- before-test: SR05 `[the place is absent]`; SR05-main `[current: line "ref: refs/heads/main" absent from HEAD;
  free: read ref main absent [M-4]]`
- after-test and after-check: SR05 `[the place is dir]`; SR05-main `[line "ref: refs/heads/main" count 1]`
- construction: C6, `command` `init` (`rename`), risks `["RK18"]` (A151), marked: C6 outside RK3's rows, which A6
  (O2) kept his and pick 2 reaches. Windows: SR05 "a repository made there between the read and the init is taken
  as it stands"; SR05-main "a branch made current by hand in between is the one renamed". SR05-main's `free` is
  enforced in the same request: `git branch -m` refuses a rename onto an existing branch, which only `-M` forces
  (git-branch's documentation); that refusal stops the run (R6)
- commands `init` (`git.init`); SR05-main `rename` (`git.rename-main`); `{work: <F>}`. Repo commands `["init"]`
  (`["rename"]`)
- output `repository` (`branch main`), field `path`: the place; needs SR05 `{state, kit .gitignore, then not
  applicable}`, SR05-main `{state, repository, then not applicable}`; condition none; `N`; `W`
- content classes: exits and HEAD's line compared in memory; hashes stored; safe text shown; resting places the
  repository's `.git`
- form lines: preview "make the project a git repository"; "name its branch main; an existing main is never
  replaced"; status `done` or `already so`

### 3.7 SR06-scope, SR06-architecture, SR06-coldread, SR06-review, move: adopt a staged doc **[M-2]**

| Row | Staged in `loc:staged_docs` | Target under `<F>` | Its folder's row |
|---|---|---|---|
| SR06-scope | `<slug>-scope.md` | `docs/scope/<date>-<slug>.md` | SR03-docs-scope |
| SR06-architecture | `<slug>-architecture.md` | `docs/architecture/<date>-<slug>.md` | SR03-docs-architecture |
| SR06-coldread | `precon-cold-reads/<slug>-cold-read-*.md` | `docs/reviews/<date>-precon-cold-read-<slug><suffix>.md` | SR03-docs-reviews |
| SR06-review | `architect-reviews/<slug>-review-*.md` | `docs/reviews/<date>-architect-review-<slug>-<lane><suffix>.md` | SR03-docs-reviews |

- kind, phase: move, sunrise. Thing: role "the staged <role> doc"; identity path; place `{fact:
  "staged.<role>.path"}`; tracked exists, identity
- planning test `[the place is file]`; before-test `[there: the place is file; free: the target is absent]`;
  after-test `[the place is absent; the target is file]`; after-check `[the target is file]`
- construction: C7, `to` the target (`<F>`, `{fact: "staged.<role>.date"}`, `<slug>`, the fact's suffix and lane),
  risks `["RK4"]`; commands and repo commands none
- output `<role> doc`, field `path`: the target; needs `{state, project folder, then not applicable}`, `{state, the
  kit folder of the table, then not applicable}`; condition `{on: fact, fact: "staged.<role>.found", equals: true,
  reason: "nothing staged"}`; `N`; `W`
- The fact [M-2] first reads the destination side, in the folder SR01 or SR02 names: a doc already at a destination
  of its role (v1's `docs/scope/*-<slug>.md` and the others) makes the row `not applicable` with the reason "already
  adopted: <path>", claimed by no row and proven the run's by nothing; its staged source is not looked for (R12). A
  move of this run that a kill left landed is FORM-2's `not proven` (OP-6). Two candidates, or no date in the doc's
  first line or its name, is a question of the look.
- content classes: the doc's identity, its path and its first line, the date validated [M-2]; paths and the date
  stored and shown (safe); resting place the project folder; validator: the date line [M-2]
- form lines: preview "move <staged path> to <target>; the staged copy is gone after it"; status `done`

### 3.8 SR07-stage, SR07-scan, SR07: the first commit **[RK18, A151]**

- **SR07-stage**, change. Thing: role "the repository's index"; identity path; place `P(<F>, ".git", "index")`;
  tracked exists, sha256. Planning test by the probe. Before-test `[read index-current false]`; after-test and
  after-check `[read index-current true]` [M-4]. Construction C6, `command` `stage`, risks `["RK18"]` (A151): "a file
  changed between the look and the stage is staged as it stands; SR07-scan reads what was staged". Commands `stage`
  (`git.stage`); repo commands `["stage"]`. Output `staged`, field `path`: the place. Needs, each at the state level:
  `branch main` and every `kit <file>` (then not applicable), every `<role> doc` (then not needed). Condition none;
  `N`; `W`. Content classes (rev 4, R1): reads no file's content itself (git reads the files to stage them), only
  the index's state by the `index-current` read, kept as a fixed word, and `git.stage`'s exit; stores the index's hash
  and the exit's fixed word; shows safe text only (the row's fixed text and `<F>`); no validator. Resting places the
  repository's `.git` (the index and the objects git writes).
- **SR07-scan**, check. Thing: role "what the first commit carries, and the ignore rule"; identity path; place
  `<F>`; `subject_git` `index` (R5); passes `[commit-scan repo <F>, env_file P(<F>, ".env.local"), link_file P(<F>,
  ".vercel", "project.json"), fixed_words the hosting module's list]`. Commands none (the frame's own scan). Output
  `scanned for the commit`, fields none. Needs `{state, staged, then not applicable}`. Condition none; `N`. Content
  classes: what will be committed, matched in memory (SEC-10, A87, A88); the file named on a hit; resting places none.
- **SR07**, change. Thing: role "the branch main"; identity named value, `refs/heads/main` of the repository at
  `<F>`; place `P(<F>, ".git")`; tracked: the branch's commit, by the tool's own `ref` read [M-4]. Planning test by
  the probe. Before-test `[command staged-diff conflict]`; after-test and after-check `[command staged-diff success;
  read ref main present]`; where nothing differs the probe answers `already so` and the run goes on (v1: nothing to
  commit "is fine"). Construction C6, `command` `commit`, risks `["RK18"]` (A151): "something staged by hand between
  the scan and the commit is committed unscanned; SR14 scans every commit before the push". Commands `staged-diff`
  (`git.staged-diff`), `commit` (`git.commit`, message "sunrise: the scaffold, the repo doc kit and the adopted
  docs"); repo commands `["commit"]`. Output `first commit`, field `commit`: `{read: ref, ref: main}` [M-4]. Needs:
  passed on `git identity` and `scanned for the commit`, state on `staged`, each then not applicable. Condition
  none; `N`; way back `none`, no sunrise undo, "a commit is history". Content classes (rev 4, R1): reads the two
  commands' exits, kept as fixed words, and the branch's commit by the tool's own `ref` read (safe: SEC-4's hash row,
  "a commit it ... read on this machine"); stores and shows that commit and the fixed message; no validator. Resting
  places the repository (the commit and the branch).
- Form lines: "stage everything in the new repository"; "scan what the commit will carry, and prove the env and link
  files ignored"; "commit it on main"; status `done`, `passed` or `already so`.

### 3.9 SR10, build: the hosting link file

- id, kind, phase: SR10, build, sunrise. Thing: role "the hosting link folder"; identity path; place `P(<F>,
  ".vercel")`; tracked exists, identity; layer `hosting`
- planning test and before-test `[the place is absent]`; after-test `[the place is dir]`; after-check `[project.json
  is file; its mode at most 0o600]`
- construction: C1, `files` `[{rel: "project.json", text: {held_fields: {projectId: hosting project.id, orgId:
  hosting project.account}}}]`, `mode` 0o700 [SEC-7]; commands and repo commands none
- output `hosting link`, field `path`: `P(the place, "project.json")`; needs `{made, hosting project, then not
  applicable}`, `{state, project folder, then not applicable}`; condition none; `N`
- content classes: two held ids from their records, written only into the link file, shown nowhere; resting places
  staging and the link file
- form lines: preview "write the hosting link file .vercel/project.json, owner-only, ignored by git"; status `done`

SR12 (settle the tree) is not a row: nothing tracked changes after the first commit.

### 3.10 SR13-agents, SR13-claude, SR13-canary, check: the kit check

One subject per check, each the thing it reads (R5).

| Row | Subject | Passes | Command |
|---|---|---|---|
| SR13-agents | `subject_git` `head` of `<F>`: the committed tree it checks (rev 4, R5) | `[command agents success]`: AGENTS.md in the head commit's tree, exact path and case | `agents` (`git.agents-committed`) |
| SR13-claude | place `P(<F>, "CLAUDE.md")`, tracked exists, sha256 | `[line 1 of CLAUDE.md is "@AGENTS.md" [M-7]; CLAUDE.md is file]` | none |
| SR13-canary | place `P(<F>, "AGENTS.md")`, tracked exists, sha256; capability `canary` | `[command canary success, field match equals "same"]` | `canary` (`adapter.canary`) |

- kind, phase: check, sunrise; thing role "the kit, as committed"; identity path
- output `kit agents`, `kit claude`, `kit canary`, fields none; needs `{state, first commit, then not applicable}`;
  condition none; `N`
- content classes: exits, a line compared in memory, a fixed word; resting places none
- form lines: preview "check AGENTS.md is committed in its exact case"; "check CLAUDE.md's first line is the stub and
  it is a real file"; "the canary: a fresh session quotes AGENTS.md's first line"; status `passed`; FORM-2's
  `unavailable`

### 3.11 SR14, check: the scan before the push

- id, kind, phase: SR14, check, sunrise. Thing: role "every commit the push sends"; identity path; place `<F>`;
  `subject_git` `head`; layer `github`; passes `[push-scan repo <F>, branch main, no base (the remote holds no
  commit), env_file, link_file, fixed_words as SR07-scan]`
- commands none; output `scanned for the push`, field `commit`: the head it scanned, `{read: ref, ref: main}` [M-4]
  (seams file, line 4); needs: state on `first commit`; passed on `kit agents` and `kit claude`; passed on `kit
  canary` accepting `unavailable`; each then not applicable; condition none; `N`
- content classes: as SR07-scan; resting places none
- form lines: preview "scan every commit the one push sends"; status `passed`

### 3.12 SR20, build, and SR20-github, SR20-hosting, SR20-database, change: the vault folder and its seed

- **SR20**, build. Thing: role "the project's vault folder"; identity path; place `P(loc:vault_projects, <slug>)`;
  tracked exists, identity. Planning test and before-test `[the place is absent]`; after-test `[the place is dir]`;
  after-check `[_index.md is file]`. Construction C1, `files` `[{rel: "_index.md", text: v1's seed}]` (frontmatter
  with `created: today` and `status: active`; What this is; Tech stack; Repo with the local path `<F>`, the shortcut
  and `- **Branch:** main`), `mode` 0o755. Commands, repo commands none. Output `vault folder`, field `path`. Needs
  `{state, first commit, then not applicable}`. Condition none; `N`. Content classes: safe text; resting places
  staging and the vault.
- **SR20-github, SR20-hosting, SR20-database**, change (R13). Thing: role "the seed's Repo section"; identity path;
  place `P({output: "vault folder.path"}, "_index.md")`; tracked exists, sha256. Planning test by the probe.
  Before-test `[the row's line absent]`; after-test and after-check `[the row's line count 1]`. Construction C3, edit
  replace of `"- **Branch:** main\n"` by itself and the row's line, risks `["RK2"]`. Lines and their own needs:
  `- **GitHub:** <remote repository.address>`, layer `github`, `{made, remote repository}`; `- **Vercel:**
  <hosting project.address>`, layer `hosting`, `{made, hosting project}`; `- **Database:** Supabase via Vercel
  Marketplace`, layer `database`, `{made, hosting project}`; each also `{made, vault folder}`; all then not
  applicable. Commands, repo commands none. Output `seed github line`, `seed hosting line`, `seed database line`,
  field `path`. Condition none; `N`; `W`. Content classes: the two addresses (safe, built by slice 3 from safe
  content) and fixed text; resting place the seed.
- Form lines: "create <vault_projects>/<slug>/ with its _index.md seed, status active"; "add the GitHub (Vercel,
  database) line to the seed"; status `done`.

### 3.13 SR21, SR23, SR24, change: one line in a shared file

| Row | File | Before-test | Edit, C3 | Risks | Needs | Preview |
|---|---|---|---|---|---|---|
| SR21 | `loc:vault_index` | `[heading: "## Active projects" count 1; lacks: L21 absent]` | replace `"## Active projects\n"` by it and L21 | RK2 | made on `vault folder` | "add the project under Active projects in the vault's root index" |
| SR23 | `loc:memory_index`; capability `memory stores` | `[lacks: L23 absent]` | append-line L23 | RK2 | made on `memory note` | "add the project's line to the memory index" |
| SR24 | `loc:shortcut_file`; layer `shortcut` | `[lacks: L24 absent; name: name-free in:answers.shortcut, on other]` | append-line L24 | RK2, RK5, RK13 | state on `first commit` | "add the shortcut <shortcut>; no command of that name exists for your login shell" |

L21 `- [[<vault_link_prefix>/<slug>/_index|<Name>]]`; L23 `- [<Name>](project_<slug_>.md): <description>`; L24
`T("alias ", in:answers.shortcut, "=\"cd ", <F>, "\"")`: the target is the project folder SR01 or SR02 binds. The
check is on the filled parts, not on the line: the shortcut is 2 to 5 lowercase letters or digits, and `<F>` holds
no `"`, `$`, backtick, backslash or line break; a part that fails refuses the input in the look [M-8] (R8). Each
need is then not applicable.

- kind, phase: change, sunrise; thing role the file, identity path, place as the table, tracked exists, sha256
- planning test `[the file is file]`; after-test and after-check the row's line count 1; SR24's after-check also
  `name-free` of the shortcut false (a fresh shell knows the alias) [M-9]
- commands, repo commands none; output `vault index line`, `memory index line`, `shortcut`, field `file`
- condition none; SR24 `{on: fact, fact: "wired.shortcut", equals: true, reason: "the shortcut file is not wired
  into your shell"}`, a line read of `loc:shell_startup` containing `project-shortcuts` [M-1]
- `N`; `W`
- content classes: his file's lines compared in memory; hashes stored; the row's line shown (safe); resting place the
  file (A147); validator SR24's [M-8]
- form lines: as the table; status `done`; SR24's adds "open a new terminal tab before typing it"

### 3.14 SR22, build: the home memory note

- id, kind, phase: SR22, build, sunrise. Thing: role "the project's home memory note"; identity path; place
  `P(loc:memory_home, T("project_", <slug_>, ".md"))`; tracked exists, identity; capability `memory stores`
- planning test and before-test `[the place is absent]`; after-test and after-check `[the place is file]`
- construction: C1, `single_file`, v1's note, `mode` 0o600; commands, repo commands none
- output `memory note`, field `path`; needs `{state, first commit, then not applicable}`; condition none; `N`
- content classes: safe text; resting places staging and the memory store
- form lines: preview "create the home memory note project_<slug_>.md"; status `done`; without the capability,
  `not applicable`, "not available on this harness"

### 3.15 The count

(rev 4) 48 rows, no owner step and no owner answer: check 10 (SR00, SR07-scan, SR13-agents, SR13-claude,
SR13-canary, SR14, SR25, SR25-npm, SR25-uv, SR25-html); build 9 (SR02 six, SR10, SR20, SR22); move 4 (SR06 four);
change 24 (SR03-docs and its three folders, SR03-agents, SR03-claude, SR03-readme, SR03-ignore, SR03-envex,
SR03-envex-keys, SR12a, SR12b-dir, SR12b, SR05, SR05-main, SR07-stage, SR07, SR20-github, SR20-hosting,
SR20-database, SR21, SR23, SR24, SR25-build); adopt 1 (SR01).

### 3.16 SR25, check, and the local baselines SR25-build, SR25-npm, SR25-uv, SR25-html: the end proofs

- **SR25**, check. Thing: role "the project as sunrise leaves it"; identity path; place `<F>`; `subject_git` `head`;
  passes `[command agents success; line 1 of CLAUDE.md "@AGENTS.md" [M-7]; CLAUDE.md is file; command clean success
  (nothing staged, nothing changed, nothing untracked that git does not ignore); read ref main equals push.commit
  [M-4]; commit-scan with nothing staged, proving the env and link files ignored]`. (rev 4, R5) `agents` now checks
  the committed tree its subject tracks, and the clean pass in the same attempt proves the working tree and the index
  equal that head, so the CLAUDE.md reads are of the committed content. Commands `agents`
  (`git.agents-committed`), `clean` (`git.clean`). Output `end proofs`, fields none. Needs: made on `push`, passed
  on `deployment`, made on `env file` (slice 3's SR15, SR16, SR19), each then not needed; passed on `kit agents` and
  `kit claude`, then not applicable; passed on `kit canary` accepting `unavailable`, then not needed; (rev 4, R9)
  state on `local build` and passed on `local baseline`, each then not needed. Where `push` is not provided, the
  head-equals pass is dropped with its need [M-10]. Condition none; `N`. Content classes: exits and the tool's reads;
  resting places none.
- (rev 4, R9) One baseline per no-hosting scaffold, each with condition `{on: fact, fact: "flags.local_proof",
  equals: <word>, reason: "a layer the project lacks"}` (3.0), so it runs only where no deployment proves the build;
  no push is added:

| Row | Word | Kind | Proof that the scaffold runs |
|---|---|---|---|
| SR25-build | `build` | change | the scaffold's own build, `scaffold.build` (`npm run build`), makes its documented output: `.next/BUILD_ID` (next), `dist/index.html` (astro), `out/main/index.js` (electron), from the lane's table keyed by `flags.scaffold` [M-1] |
| SR25-npm | `npm` | check | `scaffold.package` reads the package file `npm init` made; `npm init` makes no program, so its package file read by npm itself is the scaffold whole |
| SR25-uv | `uv` | check | `scaffold.run-py` runs the hello program `uv init --app` made, and it exits 0 |
| SR25-html | `html` | check | `index.html` is file and holds the lines SR02-html wrote (`<!doctype html>` and its `<title>`), the whole of that scaffold |

- **SR25-build** (as shipped, the join's J1e, the reviewer's J4: three checks, SR25-build-next, SR25-build-astro and
  SR25-build-electron, one per scaffold that builds, each a check whose subject is the build and its output folders, by A154:
  "the project's own build runs only in a check", OP-8; the change written below is the revision 4 text it replaced),
  change. Thing: role "the scaffold's build output"; identity path; place `P(<F>, <the table's
  output>)` [M-1]; tracked exists, sha256. Planning test by the probe. Before-test `[the place is absent]`; after-test
  and after-check `[the place is file]`; present already, it is `already so`. Construction C6, `command` `build`,
  risks `["RK18"]` (A151), marked as C6 outside RK3's rows: "the build writes its output folder, which the scaffold's
  own .gitignore ignores; a write anywhere else shows in SR25's clean read, which stops the run". Commands `build`
  (`scaffold.build`, `{work: <F>}`); repo commands none. Output `local build`, field `path`. Needs `{state, first
  commit, then not applicable}`. `N`; `W`. Content classes: reads the build's exit, kept as a fixed word, and the
  output file's state (the tool's measure); stores the hash; shows safe text; resting places the build output folder
  in the project; no validator.
- **SR25-npm, SR25-uv, SR25-html**, check. Thing: role "the local scaffold"; identity path; place `P(<F>,
  "package.json")`, `P(<F>, "main.py")`, `P(<F>, "index.html")`; tracked exists, sha256; passes as the table (SR25-npm
  `[command package success]`, SR25-uv `[command run success]`, SR25-html `[index.html is file; line "<!doctype
  html>" present; its title line present]`). Commands `package` (`scaffold.package`), `run` (`scaffold.run-py`),
  none. Output `local baseline`, fields none. Needs `{state, first commit, then not applicable}`. `N`. Content
  classes: exits and lines compared in memory; resting places none.
- Form lines: "prove the end: committed and clean, pushed as committed, live for that commit, the env file's key
  names, the kit"; "build the scaffold locally to prove it runs (no hosting layer)"; "run the Python hello program";
  "read the package file"; "read the single page"; status `passed`, `done` or `already so`.

## 4. The look steps

| Step | Where | What it reads | Built by |
|---|---|---|---|
| G1 the gate | RUN-1's first step | the vault's four checks | slice 1 |
| G2 the cue | after the startup checks | nothing: a fixed sound and line | slice 1 |
| G3 names | RUN-2 (a); the preview; the go | the three names | slice 1 |
| G4 tools and accounts | RUN-5 | each declared program on the search list; slice 3's identities; git's is SR00 | slice 1, slice 3 |
| G5 capabilities | RUN-5 | `canary`, `memory stores` | slice 1 |
| G6 probes | RUN-6, RUN-7 | SR02's, SR20's, SR22's places; the staged docs and their destinations [M-2]; SR21, SR23, SR24's files; the wiring [M-1] | the rows |
| G7 his words | RUN-5 | 3.0's questions, all before the preview | the lane |

## 5. Form lines and form changes

| Key | Line |
|---|---|
| `passed` | `the check passed: {what}` |
| `a receipt due` | `a secret may have been received and lost: operation {operation}, execution {execution}, field {field}` |
| `a safe ground disproved` | `a value this run held as safe is withheld ({count} on record)` |
| reason `nothing staged` | `nothing staged` |
| reason `already adopted` | `already adopted: {what}; not moved again, and not claimed by this run` |
| reason `the shortcut file is not wired into your shell` | `the shortcut file is not wired into your shell; no shortcut was added` |
| the RK18 mark | `carried under v1's own risk for this step (RK18): {what}` |

Changes to v1's sunrise forms (catalog Part 5, and these): every Notion line leaves (R3); the Database line names
Supabase only (P7); a layer the run does not have is left out; each remote row's account in the preview; "not
available on this harness"; `AGENTS.md`'s Env line, one line for both cases ("`.env.example` lists the keys; with
the hosting layer `vercel env pull` writes `.env.local`, ignored; without it, copy `.env.example` to `.env.local`");
the memory index line uses a colon; the alias line's cd target is the project folder in full; the summary's kit line
reads "kit 2/2, canary <passed or unavailable>".

## 6. The checklist (ROW-3)

| Item | Answered by |
|---|---|
| F18: no line for `passed` or `answered` | form line `passed`; `answered`: not this lane's, its rows hold no owner answer (pick 2) |
| F18: `not applicable` reasons omit EV-7's missing keep or record | not this lane's: restore's (slice 4) |
| F18: the tombstone's clocks and what expires, the not-saved list, no test load | not this lane's: sunset's |
| D20: permitted providers and types | the six SR02 rows for the four kept types; providers: slice 3's |
| D20: removed layers, flags, column | Notion, npm, `--db neon`, the monorepo and library scaffolds, each by its ruling (R3, A1 P6, P7, P8); the free scaffold override, by the owner's ruling A152, "Six named only" (rev 4, R11) |
| D20: rejection of dropped types | the lane's question `type` [M-5] |
| D20: provider-blind backup, unsupported-provider instructions | not this lane's: sunset's and slice 3's |
| D20: packaging | not this lane's: slice 1 and the join |
| D20: local, kit, staged-document, vault, memory, shortcut, automation, hand-off and cue inventory | SR02; SR03-docs and its folders, SR03-agents, SR03-claude, SR03-readme, SR03-ignore, SR03-envex, SR03-envex-keys; SR06; SR20 and its three lines; SR22; SR24; automation not this lane's; hand-off: the form change; cue: G2 |
| D20: required description | the question `description` |
| D20: type and flag dependencies | 3.0's mapping table; SR02's six conditions; SR12a, SR12b-dir, SR12b; SR25-build, SR25-npm, SR25-uv, SR25-html (rev 4) |
| D20: verified end proofs | SR25; without hosting, SR25-build, SR25-npm, SR25-uv or SR25-html (rev 4, R9) |
| D20: first-day cross-links | SR03-agents (Where to look); SR20 with SR20-github, SR20-hosting, SR20-database; SR22 |
| D20: dirty or unpushed work | sunrise's own closeout: SR25's clean and head-equals passes; sunset's: slice 4's G8 |
| D20: loose ends | not this lane's: sunset's G10 |
| D20: A1 P11 and A2 keeps | not this lane's: sunset's |
| D20: A4 hosting creation refuses taken names | not this lane's: slice 3's SR09 |
| D20: A4 launch agent | not this lane's: sunset's T10 |
| D20: A6 restore needs the machine with the run directory | not this lane's: slice 4 |
| D20: A6 owner steps carried into lane forms | this lane has no owner step after the go (pick 2); its questions are in the look |
| D20: A6 cancelled-schedule record | not this lane's: slice 4 |
| D20: governance picks | not this lane's: the control room's |
| D20: P16, restore planning, local-folder-only adoption, no create mark, leave-it, readback | local-folder-only adoption: SR01; the rest not this lane's |
| D20: A8 shortcut-name risk | SR24, under RK5 and RK13 beside RK2 |
| D20: shared schema choices before freeze | not this lane's: slice 1's, with section 9 |
| D20: provider support for a refusing primitive | not this lane's: slice 3's; this lane's one refusal relied on is git's (SR05-main) |

## 7. Seams

The providing lane's names (the seams file's rule):

- SR08 `remote repository`: `id` (held), `name`, `address`; SR20-github reads `address`.
- SR09 `hosting project`: `id`, `account` (held), `slug`, `address`; SR10 reads `id` and `account`, SR20-hosting
  `address`.
- SR16 `deployment`; SR15 `push`, field `commit`; SR19 `env file`, field `path`; the database module's required key
  names (SR03-envex-keys); the hosting module's fixed env words (SR07-scan, SR14, SR25).
- This lane provides `project folder` (`path`), `first commit` (`commit`), `scanned for the push` (`commit`, line 4)
  and `hosting link` (`path`, line 5).
- Git, slice 3's declarations: init, branch rename (`-m`, never `-M`), add, commit (with `-c
  core.hooksPath=/dev/null`), the clean read. **Git reads this lane asks slice 3's builder to add:** `config --get
  user.email`, `config --get user.name`, `diff --cached --quiet`, and (rev 4, R5) `cat-file -e HEAD:AGENTS.md`, as
  3.1 gives them.
- Scaffold declarations are this lane's (line 11): 3.1's five scaffolders, `scaffold.build`, `scaffold.package` and `scaffold.run-py` (rev 4).
- Of slice 4: T11 and V13 match `alias <shortcut>="cd <project folder>"`; T14 the seed's `status: active`; T16 L21;
  T18 a note with no `status` line; T19 L23; T21 `.vercel/project.json`'s `projectId` and `orgId`; T12 the
  repository at `<F>`.

## 8. Questions

None left for the owner. Revision 1's eleven stand as revision 2 placed them, with Q8's check moved to the filled
parts (R8) and Q11 answered by v1's six named scaffolds (R11).

## 9. What slice 1 must give

This document's ids, for the control room to map to G19-1 to G19-29 and G20-1 to G20-7 (section 1 says why their
briefs were not opened). A line added in this round names its finding.

| Id | The smallest mechanism | For |
|---|---|---|
| M-1 | a lane fact: one read the look makes of a thing there before the run (a path, or a line containing a word), and a lane table keyed by a fact; each usable as a condition or a value | SR24's wiring; the template's commands |
| M-2 | a staged-doc fact: the destination side read first ("already adopted"), then a name pattern in a folder giving none, one (its path, its date from its first line by a date validator or from its name, its suffix and lane tag) or a question of the look; R12 adds the destination read | SR06 |
| M-3 | C3 on an absent file or folder publishes it as C1 does, with no parent made (R2); the `kit` edits of 3.5 | 3.5 |
| M-4 | RK18 on C1, C3 and C6 rows, with A151's condition on another file; the reads `index-current` and `ref` (also as an output field and with `equals`) | SR02, SR03-agents, SR03-claude, SR05, SR05-main, SR07-stage, SR07, SR14, SR25 |
| M-5 | the lane's list of kept types; another refused before the look, in plain words | the `type` question |
| M-6 | C1 makes the staged object an empty folder and runs the builder in it (R7) | SR02 |
| M-7 | a line read at a given line number (R10) | SR03-claude, SR13-claude, SR25 |
| M-8 | a mark for the run's date at its go; a validator on an answer and on each value filled into a row's text, refusing the input in the look (R8) | the templates, SR24 |
| M-9 | `name-free` as an after-check that the name is now taken | SR24 |
| M-10 | a pass dropped with the need it names, where that need is settled `then not needed` (R9) | SR25 |
| M-11 | the lane file's slot for v1's fixed preview, summary and hand-off text | the forms |

## 10. Frame words needed

None. A147 holds revision 2's F-1 to F-3 as the reviewer reports; A151 holds the scaffold's files, the lifted
lines and RK18's condition on another file (R3, R4), as the control room quoted it.

## 11. Choices the frame left to the rows

1. One phase, `sunrise` (ORD-4). 2. The three names by place (RUN-2 (a)). 3. The scaffold words of 3.4 and
`flags.local_proof` (ORD-3: one condition). 4. The commit message, fixed text, and every hook off (OP-11). 5. The
three ignore lines and their order (SEC-10). 6. Modes: folders 0o755, the memory note 0o600, the link folder 0o700
and its file 0o600 (OP-4). 7. L21's shape and place. 8. The location names of 3.0 (E16-12). 9. No alias reads (RUN-2
(d)). 10. SR20, SR22 and SR24 wait on the first commit. 11. The docs folders laid even where no doc is staged (git
keeps no empty folder).

## 12. Less than v1 or than ruled

- v1 showed him a merged or lifted AGENTS.md before writing it; v2 writes it, under RK18 (A151).
- The static site and the script have no database: v1's `--db` turned one on, and A1 P7 took that flag with Neon.
- A README.md or `.env.example` already there is kept as it is; v1 gives no merge rule for them.
- (rev 4, R9) The no-hosting baseline of a plain `npm init` script reads its package file: `npm init` makes no
  program, so there is nothing more of it to run.
- A desktop app's seed shows its hosting address, where v1 wrote "env-plane only".
- The guide's pinned scaffolder version is not met: v1's `@latest` is kept.
- A doc v1 would ask about mid-run is asked in the look; a doc staged after the look is not adopted by that run.
- v1's optional GitHub ruleset step is carried by no row.

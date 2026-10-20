# E16 slice 3, the providers: the lane's own rows

Written 2026-10-17 by the slice 3 row author, against the frame (`2026-10-12-stations-e16-frame.md`,
hash 6434d3b48236d29d, with A147's words), the lane contract (`2026-10-11-stations-e16.md`) and the
operation catalog (`2026-10-12-stations-e16-operations.md`; its Part 4 is a draft, A5). **Revision 3,
the one fix round** (contract section 14): it closes the outside reviewer's read 1 (P1 to P11; section
0), takes the owner's ruling on P3, and fixes this lane's side of the control room's seam list.
Standing under the owner's picks of 2026-10-17: "Machinery round first" (section 8, part G19); "Run to
the end" (RK18: v1's risk for a step v1 did itself; no step of his after the go); "I don't want this
over engineered". **Status: for the reviewer's check of the closed list. No slice has the owner's
go.**

## 0. Findings closed

| Finding | Closed by | Where |
|---|---|---|
| P1 SR17: absence test against a C2 that claims no uniqueness | the absence stays a planning test (a taken name ends the look); the before-test keeps it, carried under RK18 with its window said; RK18's reach to SR17's C2 is asked for | 3.2 SR17; 8 G19-6; 9 |
| P2 T03, T04: inventory not from the copy's state | T03: the inventory is `pg_dump`'s own, inside its one snapshot, read from the copy; T04: the key list read just before and just after the pull, both equal to the copy's keys, or the keep fails | 3.3 T03, T04; 8 G19-8 |
| P3 T04, T21: partial keep | the owner's ruling (2026-10-17): every environment, custom ones included, everything Vercel returns; a Sensitive value is named by key as not saved; sunset goes on. One keep per environment found | 3.3 T04; 5; 8 G19-7; 9 |
| P4 Vercel: identity not proven per route | one identity read per route, each of the team his settings name: the frame's request and the CLI's session | 3.0; 4; 8 G19-9 |
| P5 entries left out | tracked state stated (SR08, SR09, SR17); SR16's subject; T01s's commands; validators and resting places written out; alternatives column in 3.0 | 3.0, 3.2, 3.3 |
| P6 V10, V11 inherit | each written as a full row | 3.4 |
| P7 keeps cannot execute | the keep-data mechanism G19-8 | 8 |
| P8 `psql -v` refused as a trace flag | trace flags per command, by meaning | 3.0; 8 G19-10 |
| P9 passed lines; dynamic values | a passed line for T01s; form values from safe fields on record, G19-11 | 5; 8 |
| P10 no idle instruction | the preview gives the idle step for Supabase and for any other host, before the go | 5 |
| P11 stale frame reports | resolved by A147: "C6 is open for the rows RK18 names"; "KEEP-1 reads the source's identity just before the copy where the copying tool reports none" | 9 |
| P3, narrow round (check 1) | the copy is compared with the returned-value keys alone; each Sensitive key is listed apart, by key (A148), and fails nothing; T21 goes on after the keeps | 3.3 T04, T04c, T21; 5 |
| N2 (check 1) | a custom environment's name and id stay held; the tool's label `custom-<n>` in paths and forms; its variables read by the frame's own request with the held id back to its issuer | 3.0 `environments`, `env-values`; 3.3 T04c; 4; 8 G19-7, G19-12 |

## 1. Reading line

- **Read whole:** the frame, Parts 1 to 5, then 3.3 and 3.9 again; the contract's sections 1 to 17,
  A1 to A9 and A142 to A146; the catalog; the lane checklist; the three guide files; v1's two
  `SKILL.md`; the reviewer's read 1; the control room's seam list.
- **Searched:** contract section 18, A10 to A141, by command for these row ids and terms (paragraphs
  read: A22, A23, A24's count, A87 to A89, A134). A147 was not read; it is used as the control room
  and the reviewer quote it.
- **Slice 1, in part:** the row, provider, lane, checklist, settings schemas (by structure); examples
  `fakehost`, `fakedump`, C1, X1, O1, P1; `rows.py`, `lanes.py`, `hostcall.py` whole; parts of
  `results.py`, `values.py`, `plan.py`, `reads.py`, `state.py`, `effects.py` (`keep_whole` among them),
  the head of `gitread.py`.
- **Documentation:** [D1] https://docs.github.com/en/rest/repos/repos; [D2] `gh` 2.102.0's own help
  (`gh repo create --help`, `gh api --help`, `gh help exit-codes`, `gh help environment`;
  https://cli.github.com/manual); [D3] `git` 2.54.0 `git help push`; [D4]
  https://vercel.com/docs/cli/api; [D5]
  https://vercel.com/docs/rest-api/reference/endpoints/projects/create-a-new-project; [D6]
  https://vercel.com/docs/rest-api/projects/pause-a-project; [D7]
  https://vercel.com/docs/rest-api/projects/unpause-a-project; [D8]
  https://vercel.com/docs/rest-api/deployments/get-a-deployment-by-id-or-url (its head); [D9]
  https://vercel.com/docs/cli/integration; [D10] https://vercel.com/docs/cli/env; [D11]
  https://www.postgresql.org/docs/current/libpq-pgservice.html; [D12]
  https://www.postgresql.org/docs/current/app-pgdump.html and `pg_dump --help` (18.6); [D13]
  https://www.postgresql.org/docs/current/app-pgrestore.html; [D14]
  https://vercel.com/docs/rest-api/projects/retrieve-the-environment-variables-of-a-project-by-id-or-name.

## 2. ROW-2 reports

None. `pg_dump`'s connection is G19-3 (section 8), a gap of slice 1's code, not of the tool.

## 3. The rows

### 3.0 The provider declarations (SEC-3, SEC-4)

Four files, `lifecycle/rows/providers/<provider>.json`. The marks and reads G19 adds (section 8) are
used as if present. Row inputs: `{"input": "answers.repo"}`, `{"input": "answers.slug"}` (section 7).
No command declares an alternative result: the alternatives column is `none` throughout (ORD-3).

**`github`** (tools `gh`, `git`; host `null`; token `null`: "The git host's tool keeps its own token;
the frame never reads it" (SEC-2); `credential_env` `GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN`,
`GITHUB_ENTERPRISE_TOKEN` [D2]; identity `whoami.login`). `gh` commands register `GH_PROMPT_DISABLED`,
`GH_NO_UPDATE_NOTIFIER`, `NO_COLOR`, each `fixed` `1`; their trace flags `--verbose`, `--debug`. `git`
commands register `GIT_TERMINAL_PROMPT` `fixed` `0`; their trace flags `--verbose`, `-v`. `gh` exits 0
success, 1 any failure (`other`, indefinite), 4 authentication needed (`auth`, definite) [D2]. Names go
by `-f`, never `-F`, so a name beginning with `@` is never read as a file [D2].

| Command | Template | Time | Exits | Fields: name, place, type, disposition, required in | Definite | Alt. | Effects |
|---|---|---|---|---|---|---|---|
| `whoami` | `gh api graphql -f query=query{viewer{login}}` | 30 | 0 success, 1 other, 4 auth | `login`, data.viewer.login, name `A-Za-z0-9-` max 39, equal `{"settings": "github"}`, success | success; refusals auth | none | 0 |
| `repo-read` | `gh api graphql -f query=<literal Q> -f name=<name> -f ref=<ref>`, Q `query($name:String!,$ref:String!){viewer{repository(name:$name){id isArchived name ref(qualifiedName:$ref){target{oid}}}}}` | 30 | as `whoami` | `id`, ...repository.id, id `A-Za-z0-9_=-` max 64, held, none. `archived`, ...isArchived, flag, fixed, none. `name`, ...name, name `A-Za-z0-9._-` max 100, equal `{"param": "name"}`, none. `head`, ...ref.target.oid, hash `^[0-9a-f]{40}$`, equal `{"param": "commit"}`, none | as `whoami` | none | 0 |
| `create` | `gh api -X POST user/repos -f name=<name> -F private=<true or false>` | 60 | as `whoami` | `id`, node_id, id as above, held, success. `name`, name, equal `{"param": "name"}`, success. `owner`, owner.login, equal `{"settings": "github"}`, success | as `whoami` | none | 1 |
| `archive-set` | `gh api -X PATCH repos/<account github>/<name> -F archived=<true or false>` | 60 | as `whoami` | `archived`, archived, flag, fixed, success | as `whoami` | none | 1 |
| `push` | `git -C <repo> push --force-with-lease=<ref>: https://github.com/<account github>/<name>.git <commit>:<ref>` | 120 | 0 success, 1 other, 128 other | none (git's words go to standard error, never read, SEC-5) | success; refusals none | none | 1; changes a repository |
| `init` | `git init -q -b main <path>` | 30 | 0 success, 128 other | none | success; refusals none | none | 1; changes a repository |
| `branch-main` | `git -C <repo> branch -m <old> main` | 30 | 0 success, 128 other | none | success; refusals none | none | 1; changes a repository |
| `add-all` | `git -C <repo> add -A` | 60 | 0 success, 128 other | none | success; refusals none | none | 1; changes a repository |
| `commit` | `git -C <repo> commit -q -m <message>` | 60 | 0 success, 1 other, 128 other | none | success; refusals none | none | 1; changes a repository |
| `clean` | `git -C <repo> diff --quiet HEAD --` | 30 | 0 success, 1 conflict, 128 other | none | success; refusals conflict | none | 0 |

Seam 11: git is this module's. `init`, `branch-main`, `add-all` and `commit` are the writes the
catalog's SR05, SR07 and SR12 name; their constructions are slice 2's. A git read that answers only
in text (a commit address, a count, a list) cannot be read through the runner (SEC-4 reads a JSON
object), so `clean` is exit-mapped; any other git read slices 2 and 4 need is named to this module and
declared the same way. What `repo-read` answers for a repository that does not exist is M-P1.

**`vercel`** (host `api.vercel.com`; token: environment `VERCEL_TOKEN`, else the credentials file at
machine location `vercel_credentials`, field `token` (A2); `credential_env` `VERCEL_TOKEN`,
`VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`; trace flags `--debug`, `--verbose` for the CLI commands, none
for requests; identities, one per route (G19-9): `team` for requests, `cli-team` for the CLI).
Requests map the HTTP status to a kind and carry the query `slug` = `<account vercel>`, the team "to
perform the request on behalf of" [D6]. CLI commands run on the CLI's own stored session [D4] with
`--non-interactive --no-color --scope <account vercel>`, and exit 0 or 1 [D4].

| Command | Via and template | Time | Exits | Fields | Definite | Alt. | Effects |
|---|---|---|---|---|---|---|---|
| `team` | GET `v2/teams/<account vercel>` (M-P15: the path takes the slug) | 30 | 200 success, 404 not-found, 401 auth, 403 auth | `slug`, slug, name `a-z0-9-` max 64, equal `{"settings": "vercel"}`, success | success; refusals not-found, auth | none | 0 |
| `cli-team` | runner: `vercel api /v2/teams/<account vercel>` + the CLI flags | 30 | 0 success, 1 other | `slug`, as `team` | success; refusals none | none | 0 |
| `project-read` | GET `v9/projects/<slug>` | 30 | 200 success, 404 not-found, 401 auth, 403 auth | `id`, id, id `A-Za-z0-9_` max 64, held, success. `account`, accountId, held, success. `repo`, link.repo, name `A-Za-z0-9._-` max 100, equal `{"param": "repo"}`, none. `paused`, M-P5, flag, fixed, none | success; refusals not-found, auth | none | 0 |
| `create` | POST `v11/projects`, body `{"name": <slug>, "gitRepository": {"type": "github", "repo": <account github>/<repo>}}` [D5] | 60 | 200 success, 409 conflict, 400 other, 401 auth, 403 auth | `id`, held, success. `name`, equal `{"param": "slug"}`, success. `account`, accountId, held, success | success; refusals conflict, auth | none | 1 |
| `pause` | POST `v1/projects/<held id>/pause` [D6] | 30 | 200 success, 400 not-found, 404 not-found, 401 auth, 403 auth | none | success; refusals not-found, auth | none | 1 |
| `unpause` | POST `v1/projects/<held id>/unpause` [D7] | 30 | as `pause` | none | as `pause` | none | 1 |
| `deployment-read` | GET `v13/deployments/<slug>.vercel.app`, query also `withGitRepoInfo=true` [D8] | 30 | 200 success, 404 not-found, 401 auth, 403 auth | `ready`, readyState, state `BLOCKED BUILDING CANCELED ERROR INITIALIZING QUEUED READY`, fixed, success. `commit`, gitSource.sha, hash, equal `{"param": "commit"}`, none | success; refusals not-found, auth | none | 0 |
| `environments` | GET `v9/projects/<slug>/custom-environments` (M-P14) | 30 | 200 success, 404 not-found, 401 auth, 403 auth | `custom`, the custom environments' ids, a held list (G19-8); each stays held, and the tool labels it `custom-<n>`, its place in the list (G19-7) | success; refusals not-found, auth | none | 0 |
| `env-keys` | GET `v10/projects/<slug>/env` [D14] | 30 | 200 success, 404 not-found, 401 auth, 403 auth | `keys`, envs[].key with envs[].target, a held list (G19-8), success. `types`, envs[].type, held list, success. `next`, pagination.next, count, held, none. `hidden`, hiddenProductionEnvCount, count, equal `{"literal": 0}`, none | success; refusals not-found, auth | none | 0 |
| `env-values` | GET `v10/projects/<slug>/env`, query `customEnvironmentId=<held id>` (back to its issuer, SEC-2) and `decrypt=true` [D14] | 30 | as `env-keys` | `pairs`, the key and value of every envs[] member whose value is returned, a held list of pairs (G19-12), success. `sensitive`, the keys of envs[] members of type `sensitive`, a held list, none. `next`, as `env-keys` | success; refusals not-found, auth | none | 0 |
| `env-pull` | runner: `vercel env pull <out> --environment <env> --yes --cwd <repo>` + the CLI flags [D10] | 120 | 0 success, 1 other | none | success; refusals none | none | 1; secret output to staging |
| `db-installed` | runner: `vercel integration installations --integration supabase --format json` [D9] | 60 | 0 success, 1 other | `installed`, M-P7, flag, fixed, success | success; refusals none | none | 0 |
| `db-add` | runner: `vercel integration add supabase --name <slug>-db --no-connect --format json` [D9] | 180 | 0 success, 1 other | `resource`, M-P8, id, held, success | success; refusals none | none | 1 |
| `db-list` | runner: `vercel integration list <slug> --format json` [D9] | 60 | 0 success, 1 other | `resource`, M-P8, held, none. `connected`, M-P8, flag, fixed, none | success; refusals none | none | 0 |
| `db-connect` | runner: `vercel integration resource connect <slug>-db <slug> --yes --format json` [D9] | 60 | 0 success, 1 other | none | success; refusals none | none | 1 |

`env-pull` writes only the file it is named [D10]; any other write is M-P9, and one with no way off
keeps the command from running (SEC-8).

**`postgres`** (tools `psql`, `pg_dump`; host and token `null`; `credential_env` `PGPASSWORD`,
`PGPASSFILE`, `PGSERVICEFILE`; identity `none`). Trace flags per command, by meaning (G19-10): `psql`
`-a`, `--echo-all`, `-e`, `--echo-queries`, `-E`, `--echo-hidden` (`psql -v` sets a variable and is
no trace flag); `pg_dump` `-v`, `--verbose`. Both register `PGSERVICEFILE` `private path` (param
`passfile`), `PGSERVICE` `fixed` `sun`, `PGCONNECT_TIMEOUT` `fixed` `20` [D11]; the file is G19-3's.

| Command | Template | Time | Exits | Fields | Definite | Alt. | Effects |
|---|---|---|---|---|---|---|---|
| `inventory` | `psql -X -A -t -w -v ON_ERROR_STOP=1 -c <literal Q-INV>`, Q-INV selecting one JSON object: `identity` (M-P11), `tables`, `unreadable` (tables the role cannot select) | 60 | 0 success, 1 other, 2 other, 3 other | `identity`, id `A-Za-z0-9_-` max 64, held, success. `tables`, count, held, success. `unreadable`, count, equal `{"literal": 0}`, success | success; refusals none | none | 0 |
| `dump` | `pg_dump -w -F p --no-owner --no-privileges -f <out>` | 1800 | 0 success, 1 other (M-P12) | none | success; refusals none | none | 1; secret output to staging |

**`web`** (tool `curl` from `/usr/bin`; host and token `null`; identity `none`; trace flags `-v`,
`--verbose`, `--trace`, `--trace-ascii`).

| Command | Template | Time | Exits | Fields | Definite | Alt. | Effects |
|---|---|---|---|---|---|---|---|
| `status` | `curl -s -o /dev/null --proto =https --max-time 20 -w {"status":"%{http_code}"} https://<slug>.vercel.app/` (no `-L`) | 30 | 0 success, 6, 7, 35, 60 other, 28 timeout | `status`, state `200 301 302 307 308 401 403 404 500 502 503`, fixed, success | success; refusals none | none | 0 |

### 3.1 How a row is written

One table per row, entries numbered as ROW-1 lists them, the rule in brackets; the last line lists
by name each entry that is `none` for that row. 15 rows here, T04 expanding to one per environment
found: SR08, SR09, SR17 (create); SR15, SR17c, T01, T20, T21 and, in 3.4, V10, V11 (change); T03, T04
(keep); SR16, T01s (check); SR19 (build).

### 3.2 Sunrise (in slice 2's `sunrise/lane.json`; phase `remote` is slice 2's to place)

**SR08, the remote repository.**

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR08; create; `remote` [OP-2, ORD-4] |
| 2 | thing | "the project's repository at GitHub"; identity provider id, `repo-read.id`; tracked: exists, identity (the held id) [RUN-6, EV-3] |
| 3 | planning test | `repo-read` (name answers.repo, ref `refs/heads/main`): success, `id` present false (G19-2) [RUN-7] |
| 4 | before-test | id `free`: the same, on target [OP-5] |
| 5 | after-test | `repo-read`: `name` equal |
| 6 | construction | C2, command `make`, id field `id`; document: the create answers with the node_id [D1]; its refusal of a taken name is M-P2 [OP-3] |
| 7 | commands | `look` = github.repo-read; `make` = github.create (private `true`, `false` where fact `flags.public`) |
| 8 | repo commands | `make` [OP-11] |
| 9 | after-check | `look`: `id` equal in memory to the answer's (G19-5), `name` equal [EV-1 (c)] |
| 10 | output | `remote repository`: `id` held; `name` answers.repo; `address` the text `https://github.com/` + `<account github>` + `/` + answers.repo (safe: built from safe content) (seam 1) |
| 11 | needs | `first commit` (slice 2's SR07), made, then not applicable [ORD-1] |
| 12 | condition | fact `flags.github` not false, "a flag" [ORD-3] |
| 13 | lost answer | by dropping the layer only, until M-P2 cites a name kept unique in an account; then provider-unique [OP-7] |
| 24 | content classes | reads safe, held; stores held; shows safe; validators none; resting places the protected folder [SEC-1, SEC-7] |
| 25 | form lines | preview "GitHub: create the private repository <name> as <account> (no push)" [FORM-2] |
| | none | way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

**SR09, the hosting project, created linked to the repository** (catalog SR11 and SR11a fold into
it: the body names the repository, "Pushes to the repo auto-deploy" [D5]; one create request, OP-1;
A4's create that fails on a taken name).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR09; create; `remote` |
| 2 | thing | "the project at the hosting provider"; identity provider id, `project-read.id`; tracked: exists, identity |
| 3 | planning test | `project-read` (slug) gives not-found |
| 4 | before-test | id `free`: the same |
| 5 | after-test | `project-read`: success, `repo` equal answers.repo |
| 6 | construction | C2, command `make`, id field `id`; document: "409: A project with the provided name already exists" [D5] |
| 7 | commands | `look` = vercel.project-read; `make` = vercel.create |
| 8 | repo commands | none |
| 9 | after-check | `look`: `id` equal in memory to the answer's, `repo` equal [EV-1 (c)] |
| 10 | output | `hosting project`: `id` held; `account` held; `slug` answers.slug; `address` the text `https://` + answers.slug + `.vercel.app` (safe) (seam 2) |
| 11 | needs | `remote repository`, made, then not applicable |
| 12 | condition | fact `type` a hosted type and `flags.vercel` not false, "the project type" |
| 13 | lost answer | provider-unique, citing the 409 [D5; OP-7] |
| 24 | content classes | reads safe, held; stores held; shows safe; validators none; the protected folder |
| 25 | form lines | preview "Hosting: create <slug> as <account>, connected to <account>/<name>" |
| | none | as SR08's |

Catalog M1 stands: whether the host takes a repository with no commit yet is measured at the join;
where not, slice 2 orders SR09 after SR15.

**SR15, the one push** (E16-9).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR15; change; `remote` |
| 2 | thing | "the remote's main branch", named value `refs/heads/main`; before "absent", after "the scanned commit"; tracked: the branch's commit |
| 3 | planning test | `repo-read` `head` present false, made at the probe (RUN-6) |
| 4 | before-test | id `nohead`: the same, on target, enforced in the same request |
| 5 | after-test | `repo-read` `head` equal `scanned for the push.commit` (seam 4) |
| 6 | construction | C4, command `push`, conditions `nohead`: "If <expect> is the empty string, then the named ref must not already exist" [D3] |
| 7 | commands | `look` = github.repo-read; `push` = github.push (repo `project folder.path`, ref `refs/heads/main`, commit `scanned for the push.commit`) |
| 8 | repo commands | `push` |
| 9 | after-check | as the after-test [EV-1 (a)] |
| 10 | output | `push`: `commit` |
| 11 | needs | `scanned for the push` (SR14), passed, then not applicable [OP-8]; `remote repository`, made, then not applicable [EV-2] |
| 12 | condition | none |
| 14 | way back | none: "no sunrise undo (A2 Q5)" |
| 24 | content classes | reads safe, held; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | preview "GitHub: push main once (<short commit>)" |
| | none | lost answer, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

**SR16, the deployment.**

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR16; check; `remote` |
| 2 | thing | "the production deployment and its clean address"; identity none; tracked subject: the deployment's ready word and commit, and the address's status, as read [OP-8] |
| 7 | commands | `dep` = vercel.deployment-read (commit `push.commit`); `web` = web.status |
| 10 | output | `deployment`: none |
| 11 | needs | `push`, made, then not applicable; `hosting project`, made, then not applicable |
| 12 | condition | as SR09's |
| 24 | content classes | reads safe; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | section 5 |
| | none | planning test (generic), before-test, after-test, construction, repo commands, after-check, lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

Passes where `ready` is READY, `commit` equal, `status` 200; a build still running fails the attempt,
and the next resume attempts it again (OP-8).

**SR17, the database** (provision only: `--no-connect` turns the connect and the pull off [D9],
OP-1; catalog SR17a, SR17b and SR18 cut: the terms are asked before the preview, section 4).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR17; create; `remote` |
| 2 | thing | "the project's database resource"; identity provider id, `db-list.resource`; tracked: exists, identity |
| 3 | planning test | `db-installed` `installed` true (else section 4's stop); `db-list` `resource` present false (a resource of that name ends the look: RUN-7, the place is taken) |
| 4 | before-test | id `free`: `db-list` `resource` present false, on target |
| 5 | after-test | `db-list` `resource` present true |
| 6 | construction | C2, command `add`, id field `resource`, risks RK18; document: "provisions a new resource ... `--name` Custom name for the resource" [D9]. The provider is not cited as refusing a taken name, so `free` is not enforced at the instant of the create; RK18 carries that window (v1 provisioned with no name check). What can go wrong: a resource of that name is made by another between the probe and the create, and two of that name exist; the run's is the one its answer names |
| 7 | commands | `add` = vercel.db-add; `look` = vercel.db-list; `inst` = vercel.db-installed |
| 8 | repo commands | none |
| 9 | after-check | `look`: `resource` equal in memory to the answer's |
| 10 | output | `database`: `resource` held; `name` `<slug>-db` |
| 11 | needs | `hosting project`, made, then not applicable |
| 12 | condition | fact `flags.db`, "a flag" (A1 P7: Supabase only) |
| 13 | lost answer | by dropping the layer only (A6 O10) |
| 24 | content classes | reads safe, held; stores held; shows safe; validators none; the protected folder |
| 25 | form lines | preview "Database: Supabase through the Marketplace, <slug>-db" |
| | none | as SR08's |

**SR17c, connect the database to the project** (new: OP-1 turns SR17's connect off; v1 connected it
itself).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR17c; change; `remote` |
| 2 | thing | "the database's connection to the project"; identity provider id (the resource's held id); before "not connected", after "connected"; tracked: the connection word |
| 3 | planning test | `db-list` `connected` false, made at the probe |
| 4 | before-test | id `apart`: the same, on target |
| 5 | after-test | `db-list` `connected` true |
| 6 | construction | C6, command `connect`, risks RK18 (A147: "C6 is open for the rows RK18 names"; **marked: A6's O2 had said no to this window; the owner's pick 2 reaches it**). What can go wrong: another connects it between the read and the request, and the run records the connect as its own. Whether a second connect also succeeds is M-P13 |
| 7 | commands | `look` = vercel.db-list; `connect` = vercel.db-connect |
| 8 | repo commands | none |
| 9 | after-check | as the after-test |
| 10 | output | `database connected`: none |
| 11 | needs | `database`, made, then not applicable |
| 12 | condition | as SR17's |
| 14 | way back | none: "no sunrise undo (A2 Q5)" |
| 24 | content classes | reads safe, held; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | preview "Database: connect <slug>-db to <slug>" |
| | none | lost answer, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

**SR19, the env file.**

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | SR19; build; `remote` |
| 2 | thing | "the pulled env file"; identity path `<project folder>/.env.local`; tracked exists, identity, sha256, mode |
| 3 | planning test | the place absent, made at the probe |
| 4 | before-test | id `free`: absent |
| 5 | after-test | a file, mode at most 0600 |
| 6 | construction | C1, builder `pull`, single file, mode 0600 [SEC-8] |
| 7 | commands | `pull` = vercel.env-pull (env `development`, repo `project folder.path`) |
| 8 | repo commands | none |
| 9 | after-check | as the after-test [EV-1 (b)] |
| 10 | output | `env file`: `path` |
| 11 | needs | `database connected`, state, then not applicable; `hosting link` (SR10), made, then not applicable (seam 5) |
| 12 | condition | as SR17's |
| 24 | content classes | reads secret (never by the tool here); stores secret; shows safe; validators none; "the pulled env file in the working tree" |
| 25 | form lines | preview "Env: pull the development values to .env.local (owner-only, ignored)" |
| | none | lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

The pull's own variables and their fixed words for SEC-10 (A89): `VERCEL` `1`, `VERCEL_ENV`
`development`, `VERCEL_TARGET_ENV` `development` (M-P9), carried in slice 2's scan rows.

### 3.3 Sunset (in slice 4's `sunset/lane.json`)

**T01s, the scan before the tag push** (SEC-10: "before a push a check scans every commit to be
pushed").

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T01s; check; `keeping` |
| 2 | thing | "every commit the tag push sends"; identity none; tracked subject: the repository's head, scanned by `push-scan` against the remote's `main` |
| 7 | commands | none (the scan is the frame's own read, SEC-10) |
| 10 | output | `tag scan`: `commit` |
| 11 | needs | none (seam 6: the repository is the look's, and a look that does not pass G8 has no go) |
| 12 | condition | fact `flags.keep_github` false, "a flag" |
| 24 | content classes | reads safe and, in-process, the two files SEC-10 names; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | section 5 |
| | none | planning test (generic), before-test, after-test, construction, repo commands, after-check, lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

**T01, the dated tag** (one push of the commit to `refs/tags/sunset-<date>`; no local tag; OP-1).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T01; change; `keeping` (it preserves; contract L8) |
| 2 | thing | "the remote's sunset tag", named value `refs/tags/sunset-<date>`; before "absent", after "the head"; tracked: the tag's commit |
| 3 | planning test | `repo-read` (ref the tag) `head` present false |
| 4 | before-test | id `notag`: the same, on target, enforced in the same request |
| 5 | after-test | `repo-read` `head` equal `tag scan.commit` |
| 6 | construction | C4, command `push`, conditions `notag` [D3] |
| 7 | commands | `look` = github.repo-read; `push` = github.push |
| 8 | repo commands | `push` |
| 9 | after-check | as the after-test |
| 10 | output | `sunset tag`: `ref`, `commit` |
| 11 | needs | `tag scan`, passed, then not applicable |
| 12 | condition | as T01s's |
| 14 | way back | none: "a tag is history" |
| 24 | content classes | reads safe, held; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | preview "GitHub: tag sunset-<date> at the head" |
| | none | as SR15's |

**T03, the database dump** (provider-blind, A1 P7).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T03; keep; `keeping` |
| 2 | thing | "the database's dump"; identity path `<sunset folder>/<slug>-db.sql`; tracked exists, identity, sha256; secret read: the env file G9 found, keys `POSTGRES_URL_NON_POOLING`, `DATABASE_URL`, `POSTGRES_URL` in that order |
| 3 | planning test | G9 (section 4); the place absent at the probe |
| 4 | before-test | id `free`: absent |
| 5 | after-test | a file, mode at most 0600 |
| 6 | construction | C1, builder `dump`, single file, mode 0600, connection {that file, those keys, slot `passfile`} (G19-3) [SEC-2, SEC-8] |
| 7 | commands | `dump` = postgres.dump; `inventory` = postgres.inventory |
| 8 | repo commands | none |
| 9 | after-check | as the after-test, and the content checks [EV-1 (b), KEEP-3] |
| 10 | output | `dump`: `path` |
| 11 | needs | `sunset folder` (T02), made, then not applicable |
| 12 | condition | fact `has_database` and `flags.keep_db` false, "a layer the project lacks" |
| 22 | keep scope | scope "the whole database as `pg_dump` sees it" (A2 F13). Same state: one `pg_dump` run, "consistent exports even if the database is being used concurrently" [D12]; the inventory is `pg_dump`'s own catalog read inside that one snapshot, which it writes into the copy as one `CREATE TABLE` line per table; the inventory is read from the copy (G19-8, from the copy's lines with that prefix, held). The copy is compared with it: each table the copy creates has its data section in the copy, and the copy ends with `-- PostgreSQL database dump complete`, written only after the last item (M-P12), or with that block and then one line `\unrestrict <key>` (a non-empty key of letters and digits) and one or two newlines, as `pg_dump` 17.6 and later end a plain dump (part J3b; `then_line` of the `ends-with` check). Any other text after the block fails the keep. `pg_dump` exits other than 0 where a table cannot be read, and the keep fails. Source identity: `inventory.identity`, read just before the copy over the same connection (A147). G9's count is not compared: it was read in another state |
| 24 | content classes | reads secret, held; stores secret, held; shows safe and the tool's counts; validators none; resting places the private password file, the sunset folder |
| 25 | form lines | preview "Backup: dump the whole database to the sunset folder"; done, section 5 |
| | none | lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keeps required |

**T04, the hosting env values of the three fixed environments** (the owner's ruling on P3: "pull
every environment, custom ones included, and save it owner-only in the archive. Sensitive values
can't be read, so the preview and the tombstone name each one by key as not saved. Sunset goes on."
Rows T04-development, T04-preview, T04-production; the custom environments are T04c, below. T04 rests
on KEEP-1's sentence for a hosting environment's variables (frame fbaabcef1a890eb4, A149): the
two-read inventory is for those variables alone, a key with no returned value is listed apart, and a
value changed during the pull is v1's risk under RK18).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T04-<environment>; keep; `keeping` |
| 2 | thing | "the saved env values of <environment>"; path `<sunset folder>/hosting-env.<environment>`; tracked exists, identity, sha256 |
| 3 | planning test | absent at the probe; `project-read` success; `env-keys` success, `next` present false, `hidden` 0 (a listing that is paged or hides values cannot be shown whole: KEEP-1's planning stop). A Sensitive key stops nothing |
| 4 | before-test | id `free`: absent |
| 5 | after-test | a file, mode at most 0600 |
| 6 | construction | C1, builder `pull` (env the row's environment), single file, mode 0600 |
| 7 | commands | `pull` = vercel.env-pull; `keys` = vercel.env-keys; `look` = vercel.project-read |
| 8 | repo commands | none |
| 9 | after-check | as the after-test, and the content checks |
| 10 | output | `hosting env <environment>`: `path` |
| 11 | needs | `sunset folder`, made, then not applicable |
| 12 | condition | fact `has_hosting_project` and `flags.keep_vercel` false, "a layer the project lacks" |
| 22 | keep scope | scope "every value Vercel returns for the environment; a Sensitive key's value is not returned and is listed apart as not saved" (the ruling). The inventory is the returned-value keys: the environment's `keys` whose `types` is not `sensitive`, read just before the pull and again just after it (G19-8; KEEP-1 as A149 words it for a hosting environment's variables). The keep is whole where the two returned-value inventories are equal and each of their keys is a line of the copy (the text before `=`); any difference fails the keep and stops the run. Every Sensitive key (`types` `sensitive`) is listed apart, by key and never by value (SEC-6 as A148 words it); the pull writes a placeholder for it [D10], which the tool does not count as a saved value; it fails nothing, so T21 goes on once this keep is done. A value changed by another during the pull, its key unchanged, is v1's risk under RK18 (A149). Recorded: the returned-value keys and the Sensitive keys, held. Source identity: `look.id`, read just before the pull (A147) |
| 24 | content classes | reads secret, held; stores secret, held; shows safe, the tool's counts and the Sensitive keys listed apart (A148); validators none; resting places the sunset folder, the protected folder |
| 25 | form lines | preview "Saved copies: hosting env values of <environment>, owner-only"; the Sensitive line, section 5 |
| | none | lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keeps required |

**T04c, the hosting env values of each custom environment** (one row per custom environment
`environments` finds, G19-7, under the same ruling). A custom environment's name and id are a
provider's values, held (SEC-4): neither enters an argument, a path, a manifest or a form. The tool
labels each `custom-<n>`, its place in the list `environments` returned, and uses the label alone in
paths and forms; the held id goes only back to its issuer in the frame's own request (SEC-2: a held
value "goes back to the provider that issued it in such a request of the frame's own"). The form names
the private file that pairs each label with its environment's name (SEC-6). The copy and its
inventory are one answer, so one state (KEEP-1).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T04c-custom-<n>; keep; `keeping` |
| 2 | thing | "the saved env values of custom environment <n>"; path `<sunset folder>/hosting-env.custom-<n>`; tracked exists, identity, sha256 |
| 3 | planning test | absent at the probe; `project-read` success |
| 4 | before-test | id `free`: absent |
| 5 | after-test | a file, mode at most 0600 |
| 6 | construction | C1, builder `values` (the request `env-values` with the row's held id), single file, mode 0600; the staged file is the answer's `pairs` written as `KEY=value` lines (G19-12; SEC-4: a held value may "be written into a file that SEC-7 names for it", SEC-7's saved hosting env values in the sunset folder) |
| 7 | commands | `values` = vercel.env-values (customEnvironmentId the row's held id); `look` = vercel.project-read |
| 8 | repo commands | none |
| 9 | after-check | as the after-test, and the content check |
| 10 | output | `hosting env custom-<n>`: `path` |
| 11 | needs | `sunset folder`, made, then not applicable |
| 12 | condition | as T04's |
| 22 | keep scope | scope "every value Vercel returns for the custom environment; a Sensitive key is listed apart" (the ruling). Same state: the inventory is the answer's own returned-value keys (`pairs`), the copy is written from that same answer, and `next` present false (one page); the content check is that each key of `pairs` is a line of the copy. The `sensitive` keys are listed apart by key (A148) and fail nothing. Source identity: `look.id`, read just before (A147) |
| 24 | content classes | reads secret, held; stores secret, held; shows safe, the label, the tool's counts and the Sensitive keys listed apart (A148); validators none; resting places the sunset folder, the protected folder |
| 25 | form lines | preview "Saved copies: hosting env values of custom environment <n>, owner-only (which environment each number is: <private file>)"; the Sensitive line, section 5 |
| | none | lost answer, way back, reverse inputs, span, mode, safe content, answers, review file, owner names, keeps required |

**T20, archive the repository** (RK3's row). Its way back is V10 (3.4).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T20; change; `retiring at the providers` |
| 2 | thing | "the project's repository at GitHub"; provider id `repo-read.id`, held; before "not archived", after "archived"; tracked the archive word and the id; retires, at a provider |
| 3 | planning test | `repo-read` `archived` false (found archived: no row, G10) |
| 4 | before-test | id `live`: the same, on target |
| 5 | after-test | `archived` true |
| 6 | construction | C6, command `set`, risks RK3 [D1: "Whether to archive this repository"] |
| 7 | commands | `look` = github.repo-read; `set` = github.archive-set (archived `true`) |
| 8 | repo commands | `set` |
| 9 | after-check | `archived` true, `id` equal in memory |
| 10 | output | `archived repository`: `address` (as SR08's, safe) (seam 8; slice 4 uses this name) |
| 11 | needs | `sunset tag`, state, then not needed; `repository moved` (T12), state, then not needed |
| 12 | condition | fact `flags.keep_github` false, "a flag" |
| 14 | way back | V10 |
| 15 | reverse inputs | `[{"read": "value", "type": "values", "label": "the repository's name", "value": answers.repo}]` |
| 23 | keeps required | none: the archived repository is itself kept (A1 P11) |
| 24 | content classes | reads safe, held; stores values; shows safe; validators none; the protected folder |
| 25 | form lines | preview "GitHub: archive <account>/<name> (read-only)" |
| | none | lost answer, span, mode, safe content, answers, review file, owner names, keep scope |

**T21, pause the hosting project** (RK3's row). Its way back is V11 (3.4).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | T21; change; `retiring at the providers` |
| 2 | thing | "the project at the hosting provider"; provider id `project-read.id`, held; identity read `look.id`; before "live", after "paused"; tracked the pause word and the id; retires, at a provider |
| 3 | planning test | `project-read`: success, `paused` false (M-P5) |
| 4 | before-test | id `live`: the same |
| 5 | after-test | `paused` true |
| 6 | construction | C6, command `pause`, risks RK3 [D6] |
| 7 | commands | `look` = vercel.project-read; `pause` = vercel.pause (the held id `look` read, back to its issuer, SEC-2) |
| 8 | repo commands | none |
| 9 | after-check | `paused` true, `id` equal in memory |
| 10 | output | `paused project`: none |
| 11 | needs | `repository moved`, state, then not needed |
| 12 | condition | as T04's |
| 14 | way back | V11 |
| 15 | reverse inputs | `[{"read": "command", "command": "look", "field": "id", "type": "held field", "label": "the hosting project's id"}]` |
| 23 | keeps required | every T04 and T04c row; a Sensitive key fails none of them, so the pause goes on once they are done [KEEP-2, KEEP-3] |
| 24 | content classes | reads safe, held; stores held field; shows safe; validators none; the protected folder |
| 25 | form lines | preview "Hosting: pause <slug> (production blocked, reversible)" |
| | none | as T20's |

The catalog's T22 and V12 are cut: v1 did not idle Supabase itself ("Supabase pause from the
dashboard"); the preview gives the step (section 5).

### 3.4 Restore: the two ways back, each a full row (EV-4)

**V10, un-archive the repository** (T20's `way_back.reverse`).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | V10; change; `putting back at the providers` (slice 4 names restore's phases) |
| 2 | thing | "the project's repository at GitHub"; provider id `repo-read.id`, held; before "archived", after "not archived"; tracked the archive word and the id |
| 3 | planning test | `repo-read` (name `{"saved": 0}`) `archived` true |
| 4 | before-test | id `archived`: the same, on target |
| 5 | after-test | `archived` false |
| 6 | construction | C6, command `set`, risks RK3 [D1: "false will unarchive a previously archived repository"] |
| 7 | commands | `look` = github.repo-read; `set` = github.archive-set (archived `false`) |
| 8 | repo commands | `set` |
| 9 | after-check | `archived` false, `id` equal in memory |
| 10 | output | `restored repository`: `address` |
| 11 | needs | `repository back` (slice 4's V01), state, then not needed (seam 7) |
| 12 | condition | none |
| 14 | way back | `{"none": "the row declares none"}` |
| 24 | content classes | reads safe, held, the saved name; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | preview "GitHub: un-archive <account>/<name>" |
| | none | lost answer, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

**V11, un-pause the hosting project** (T21's `way_back.reverse`).

| # | Entry | Value [rule] |
|---|---|---|
| 1 | id, kind, phase | V11; change; `putting back at the providers` |
| 2 | thing | "the project at the hosting provider"; provider id `{"saved": 0}` (T21's saved id); before "paused", after "live"; tracked the pause word; runs on `restored repository` (ORD-4) |
| 3 | planning test | `project-read`: success, `paused` true |
| 4 | before-test | id `paused`: the same, on target |
| 5 | after-test | `paused` false |
| 6 | construction | C6, command `unpause`, risks RK3 [D7] |
| 7 | commands | `look` = vercel.project-read; `unpause` = vercel.unpause (id `{"saved": 0}`) |
| 8 | repo commands | none |
| 9 | after-check | `paused` false, `id` equal in memory to the saved id |
| 10 | output | `live project`: none |
| 11 | needs | `restored repository`, state, then not needed |
| 12 | condition | none |
| 14 | way back | `{"none": "the row declares none"}` |
| 24 | content classes | reads safe, held, the saved id; stores safe; shows safe; validators none; resting places none |
| 25 | form lines | preview "Hosting: un-pause <slug>" |
| | none | lost answer, reverse inputs, span, mode, safe content, answers, review file, owner names, keep scope, keeps required |

## 4. The look steps, and what is asked before the preview

| Step | Placed | Reads, and what it asks |
|---|---|---|
| G4 identities (this lane's) | every first look and re-plan before the planning tests (RUN-5); later starts as RUN-10 (b) | `github.whoami`; `vercel.team` (the frame's request, the token) and `vercel.cli-team` (the CLI's session), each equal to his settings' name for that provider, or the look ends (SEC-4 C). Every request names that team by `slug`, every CLI command by `--scope`: the team proven is the team each route acts for (P4) |
| G9 database (sunset) | the sunset look, as T03's planning test | over the connection from a file on this machine (A23): `postgres.inventory`, `unreadable` 0. No file holds it and there is a hosting project: planning stop with the one command `vercel env pull .env.local` in the repository (A23; slice 4's words). A table the role cannot read: planning stop, KEEP-1's form |
| G10 found states (this lane's) | the sunset look, as T20's and T21's planning tests | archived or paused already: no row, "found already retired" |
| Environments (sunset) | the sunset look, before T04's planning tests | `vercel.environments`: one T04c row per custom environment, labelled `custom-<n>` by its place; the held ids and names go to a protected record the form names (SEC-6), never into the manifest (G19-7) |
| The terms (sunrise) | the sunrise look, as SR17's planning test | `db-installed` false: planning stop, "Accept the Marketplace's terms for Supabase once: run `vercel integration accept-terms supabase`, then summon sunrise again." [D9] |

## 5. Form lines (the lane's list of form changes, FORM-2)

`<...>` is a safe value G19-11 fills from the record: a name he typed, his settings' account, a fixed
word of a declaration, or the tool's own count.

| Line | Says |
|---|---|
| SR16 `passed` | "Verify: live at https://<slug>.vercel.app, answering 200 for commit <short commit>." |
| SR16 `failed` | "Verify: not yet; the deployment reads <ready word> and the address answered <status>. Resume to check again." |
| T01s `passed` | "Scan: the commits the tag push sends hold no value the tool guards." |
| T01s `failed` | "Scan: stopped; <file> holds a value the tool guards. Nothing was pushed." |
| an outstanding create, SR08, SR09, SR17 | "A create was sent to <provider> and no answer came. Check whether <name> is there. Ways on: re-plan (SR09: names are unique, so a re-plan may send again; SR08 until M-P2, and SR17: only by dropping the layer), or close." |
| T03 done, and the tombstone's Backup (A2 F13; F18) | "Backup: <n> tables, same database (identity read before the copy), whole (every table it creates has its data), intact (its last line present); 0 tables is said as an empty database. A test load was not done." |
| T04, T04c Sensitive keys (the ruling on P3; A148; F18) | sunset preview and tombstone, per environment by its fixed name or its label: "Not saved, Sensitive (the provider never returns the value): <key>, <key>, ..." (keys only, never a value) |
| Not saved, the rest (A2 F14; F18) | sunset preview and tombstone: "Not saved: files in the database provider's storage; GitHub's issues, pull requests and releases." |
| Provider clocks (A1 P11; F18) | tombstone, per state entered: "GitHub: archived; no clock." "Hosting: paused; <limit or unknown> (M3); lost when it runs out: <limit text or unknown>." |
| Database not idled (A1 P7; P10) | sunset preview and tombstone: "Database: backed up, not paused by sunset. To idle it yourself: on Supabase, pause the project <slug>-db in its dashboard; on another host, pause or suspend it from that host's console. Never delete it." |
| The two look stops | section 4's words |
| Accounts, both previews | "GitHub as <account>; hosting as <account> (the token and the CLI both)." |

## 6. The checklist (ROW-3)

| Item, in the reviewer's words | Answered by |
|---|---|
| F18: no line "for `passed` or `answered`" | form lines SR16 and T01s `passed`; this lane has no owner answer, so `answered` is not this lane's |
| F18: "EV-7's missing or corrupt keep/protected record" | not this lane's: restore's `not applicable` lines are slice 4's |
| F18: "the tombstone's clocks and what expires" | form line "Provider clocks" |
| F18: "the not-saved list" | form lines "T04 not saved" and "Not saved, the rest" |
| F18: "no test load was done" | form line "Backup" |
| D20: "R3/R4 ... permitted providers" | rows SR08 to SR19: GitHub, Vercel, Supabase through the Marketplace; no Notion, no Neon |
| D20: "removed layers/flags/column, rejection of dropped types" | not this lane's: slice 2's inputs |
| D20: "provider-blind backup and unsupported-provider instructions" | row T03; form line "Database not idled" (its step for any other host) |
| D20: "A1 P9/P10: packaging and the ... inventory" | not this lane's: slices 2 and 4 |
| D20: "E16-1: ... type/flag dependencies" | the conditions of SR09, SR17, SR19 |
| D20: "verified end proofs" | rows SR15, SR16, SR19 (key names: slice 2's SR25) |
| D20: description, cross-links, dirty work, loose ends | not this lane's: slices 2 and 4 |
| D20: "every hosting environment/value saved" | row T04, one per environment found, under the ruling on P3; form line "T04 not saved" |
| D20: "whole-database scope" | row T03's keep scope |
| D20: "four checks including explicit empty-database evidence" | row T03's keep scope; form line "Backup" |
| D20: "project/date-specific sibling-copy placement" | not this lane's: T02 is slice 4's |
| D20: "A4: hosting creation must refuse taken names" | row SR09 (C2, 409) |
| D20: launch agent | not this lane's: T10 |
| D20: "A6: ... restore requires the machine ...; owner steps into lane forms; ... cancelled-schedule record" | no owner step in this lane; the rest is slice 4's |
| D20: governance, carried items, A8, shared schemas | not this lane's |
| D20: "a refusing or atomic primitive remains a lane measurement" | C4 for both pushes [D3]; C2 with 409 for SR09 [D5]; M-P1, M-P2 for GitHub (section 10) |

## 7. Seams

Names and fields are the providing lane's (the control room's rule).

- **Slice 2 gives:** the rows' place in `sunrise/lane.json` and phase `remote`; inputs `answers.repo`,
  `answers.slug`; facts `flags.public`, `flags.github`, `flags.vercel`, `flags.db`, `type`; outputs
  `project folder.path`, `first commit` (SR07), `scanned for the push.commit` (SR14), `hosting
  link.path` (SR10, built from SR09's held `id` and `account` as `projectId` and `orgId`).
- **Slice 2 takes:** `remote repository` {id, name, address}, `hosting project` {id, account, slug,
  address}, `push.commit`, `deployment`, `database` {resource, name}, `database connected`, `env
  file.path`; SR19's fixed words for its scan rows; the git module (3.0).
- **Slice 4 gives:** the rows' place in `sunset/lane.json` (phases `keeping`, `retiring at the
  providers`) and restore's phase `putting back at the providers`; inputs `answers.repo`,
  `answers.slug`, the run's date in T02's mark; facts `flags.keep_github`, `flags.keep_vercel`,
  `flags.keep_db`, `has_database`, `has_hosting_project`; outputs `sunset folder.path` (T02),
  `repository moved` (T12), `repository back` (V01). No need on G8 (seam 6).
- **Slice 4 takes:** `tag scan`, `sunset tag` {ref, commit}, `dump.path`, `hosting env
  <environment>.path`, `hosting env custom-<n>.path`, `archived repository.address`, `paused project`, `restored repository.address`,
  `live project`; section 5's tombstone lines (M3's limits are its own); the git module (3.0).

## 8. What G19 must give

Each the smallest mechanism; the rows are written as if each were there.

1. **A mark for the account** `{"account": "<provider>"}`, resolving to the account the identity read
   proved by ground C. (revision 1 Q1)
2. **A test that a command's field stood nowhere**: `present: false` on a command field, true where
   the result is success and the optional field is absent. (Q2)
3. **The password file as a libpq service section** (`[sun]` with the address's parts), and built
   for a look's command that declares the slot (G9). (R2-1, Q3)
4. **A request's query and JSON body**: `query` as name and value pairs, `body` an object whose leaves
   are row values, sent as JSON. (Q4)
5. **`compare_held` against a held output**: the field's held text against the content of the
   protected record the output refers to. (Q5)
6. **RK18 in the risk list**, for SR17c's C6 (A147) and SR17's C2 (section 9). (pick 2; P1)
7. **One row per found thing**: a row marked to expand from a look read's held list (here
   `vercel.environments`), one row per member; the member stays held, resting in a protected record,
   and the row carries the tool's label `custom-<n>` (its place in the list) for its id, paths and
   forms, the held member usable only where a held value may go (SEC-2, SEC-3). (P3, N2)
8. **A keep's inventory from elsewhere than its builder's answer** (`effects.keep_whole` takes both
   from the builder today): from the staged copy's lines with a declared prefix (T03), or from a read
   command made just before and again just after the builder, whose held list field (one value per
   member of a list in the answer) must be equal both times and equal to the copy's own keys (T04).
   A held field may hold a list for this. (P2, P7)
9. **One identity read per route**: a module may declare an identity for its requests and one for its
   runner commands, each compared with his settings. (P4)
10. **Trace flags per command**: a command's own `trace_flags` replace the module's for it
   (`plan.expand` overwrites them today). (P8)
11. **Safe values in form lines**: a row's form line may hold `<field>`, filled from a safe field on
   record for that operation (an attempt's or completion's fixed word, safe copy or the tool's count);
   nothing held fills it. (P9)
12. **A keep built from a frame's request**: a keep's builder may be a request whose held list field
   of key and text pairs (one member per returned value, values of any text) the frame writes into the
   staged file as `KEY=value` lines; those keys are the keep's inventory, from the same answer. (N2;
   T04c)

## 9. Frame words needed

- **Resolved by A147 (P11):** C6 for the rows RK18 names (SR17c), and KEEP-1's source identity read
  just before the copy where the copying tool reports none (T03, T04). No change asked.
- **RK18 for a C2 (SR17, P1).** RISK-2: "A row whose effect has a window that no accepted risk names is
  written as an owner step"; OP-3's C2 enforces "the provider's own uniqueness" only "where the row
  says the name must be free". A147 opens C6 to RK18, not C2. Smallest change: RK18's rows include
  SR17, a C2 whose before-test's name is not kept unique by the provider.
- **A Sensitive key named by key (the ruling on P3).** SEC-4: "A value a provider returns is held
  unless a ground of this rule proves it safe", and SEC-6 has a form speak of held names only by
  "what kind of thing each is and how many". The owner's ruling names each key. Smallest change: a
  hosting variable's key name, listed as not saved, is shown (the owner's ruling).
- **T04's inventory in two reads (P2).** KEEP-1: "the inventory is taken inside the same snapshot or
  hold as the copy". Vercel offers neither. Smallest change: where the provider offers no snapshot or
  hold, the inventory read just before and just after the copy, both equal, stands for it, and any
  difference fails the keep.

## 10. Questions

None left that a row cannot be written on. Measured later:

| Id | What | Page |
|---|---|---|
| M-P1 | what `gh api graphql` answers for a repository that does not exist | D1, D2 |
| M-P2 | that GitHub refuses a taken name and keeps names unique in an account | D1 |
| M-P5 | where the project object marks a paused project | D5, D6 |
| M-P7 | the shape of `integration installations --format json` | D9 |
| M-P8 | the shapes of `integration add` and `list` as JSON | D9 |
| M-P9 | whether `env pull` writes anything but its file; its own variables' names | D10 |
| M-P10 | that a service file's `password` keyword is honored | D11 |
| M-P11 | the query that gives the server's identity to the connecting role | D12 |
| M-P12 | `pg_dump`'s exit numbers; its plain format's data sections and last line | D12 |
| M-P13 | whether a second `resource connect` also succeeds | D9 |
| M-P14 | the custom environments' endpoint and its answer's shape | D14 |
| M-P15 | that `v2/teams/<slug>` takes the slug | D6 |

## 11. Choices the frame left to the rows

| Choice | Taken | Left open by |
|---|---|---|
| channel per call | GitHub by `gh` and `git`; Vercel by the frame's request, the CLI only to pull a file or reach the Marketplace | SEC-3: each command is declared by its module |
| the build's wait | none; SR16 attempted again on resume | OP-8 |
| the dump's format | plain SQL | KEEP-1 fixes "whole", not the format |
| the tag | one push of the commit to the tag ref | OP-1 |
| time limits | as the tables give | SEC-3 |

## 12. Less than v1 or than ruled

- After a lost create answer at GitHub, or a lost database provision, the only way on is dropping
  the layer (v1 retried); GitHub's ends once M-P2 is measured.
- Sunset never pauses the database, as v1 never did; the preview gives his step.
- The terms gate is a stop before the preview, cleared with one command, not a link opened midway.
- A Vercel listing that is paged or hides production values stops the keep (and so the retirement)
  instead of saving part of it.

## 13. Seen and not touched

- `git push` runs the repository's own `pre-push` hook; not turned off (bypassing a hook is the
  owner's word); its behavior is to be checked before the repository writes are called complete.
- `git push`'s own credentials are git's (a credential helper), a third route no identity read
  proves; the remote refuses a push those credentials cannot make.
- `gh` writes a device id file under its home at every start; RK1 covers it.
- The fake host's create gives `conflict` and `terms` by exit; the real CLIs give 1 for every failure.
- Slice 1's `RK3_ROWS` names T20, T21, V10, V11; those ids are kept.
- The deployment page was saved by the harness where this author may not look; its head alone was read.

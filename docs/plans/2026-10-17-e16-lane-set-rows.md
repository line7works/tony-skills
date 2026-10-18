# E16 slice 4: the lane's own rows, sunset and restore

Revision 3, 2026-10-17, by the slice 4 row author: the one fix round (contract section 14) on the
outside reviewer's read of revision 2 (frozen at 81c289e410b920ad; 4 BLOCKER, 7 MAJOR, 1 MINOR). It
replaces revision 2 whole. It keeps the owner's picks of today: "Machinery round first", "Run to the
end" ("Anything v1 did itself, v2 does itself; you accept v1's risk for those steps"), and "I don't
want this over engineered." Against the frame with A147 and A151 (the docs worktree's frame hashes
13f2bad538f4bee9; A151's KEEP-1 words are quoted in T05) and the contract. No slice has the owner's go.

## 0. The reviewer's findings, and where each is closed

| Finding | Closed by | Where |
|---|---|---|
| S1 T05 no shared state (BLOCKER) | T05 copies the store's folder whole under RK18, A151's two reads of names and fingerprints, both equal to the copy's own | 3.2 T05; 8 item 13 |
| S2 V06 reverses more than T17 changed (BLOCKER) | V06 puts T17's saved before-image back only where the note equals T17's saved after-image exactly once (EV-6); links already on `NEW/` are kept | 3.2 T17; 3.3 V06 |
| S3 crontab placement (BLOCKER) | T10d's span is the whole table, in place, ordered; V14d puts the saved table back only where the current table equals T10d's after-image | 3.2 T10d; 3.3 V14d |
| S4 launchd label from the file name (BLOCKER) | `launchd.label` reads the plist's own `Label`; the row runs only where it equals the validated stem, so the reads and the unload act on one job | 3.1; 3.2 T10a; 3.3 V14a |
| S5 entries unstated (MAJOR) | every row states entry 2's tracked state and entry 10's fields (or `none`); V02 gives `path`; V30 states its own entries, entry 14 plain `none` | 3.2, 3.3 |
| S6 declarations incomplete (MAJOR) | every field's place, alphabet and length; an alternatives column; `adapter.routine` has `--out`; a shortcut name is made safe by a declared validator before V13's check | 3.1; T11; 8 item 1 |
| S7 one output for many instances (MAJOR) | a family instance's outputs and needs carry its item's index `n`; a reverse keeps its forward row's `n` | the families; 8 item 12 |
| S8 notes inside the moved folder (MAJOR) | a note found inside VF is placed by T13's output, and by V02's in V06 (RUN-6) | T17; V06; 8 item 15 |
| S9 cron input not buildable (MAJOR) | a C6 command's protected input made from a computed text | 8 item 11 |
| S10 hand-off prompt; loose ends (MAJOR) | the sunset hand-off prompt is a lane form; `wrangler.jsonc` added; "other trackers" carried to the owner, no ruling to cite | 4; 5; 11 |
| S11 routine identity on restore (MAJOR) | cancel is the adapter's disable and restore its enable of the same held id; no new routine is made | 3.1; T10c; V14c |
| S12 RK18 windows (MINOR) | each RK18 row states its window in one line | T05, T10a, T10c, T10d, V14a, V14c, V14d |

## 1. Reading line

- Read whole: the frame, then its 3.9 and 3.3 OP-1 to OP-5 again; the contract's sections 1 to 17,
  A1 to A9 and A142 to A146; the catalog; the lane checklist; v1's sunrise and sunset skills
  (`plugins/sun/assets/` listed); `sun_core/rows.py`; the guide's rules, Scripts, harness layer,
  pre-ship checklist; the helper recipes; the harness notes' "Read first" to OpenCode's end.
- Searched, not read whole: the contract's A10 to A141, by command for this lane's ids and terms.
- In `plugins/sun-v2/`, the parts the rows touch: the row, lane, provider, capabilities and settings
  schemas and their valid examples; `plan.py`, `effects.py`, `reads.py`, `values.py`, `forms.py`,
  `facts.py`, `engine.py`; both v2 skeletons; `man launchctl` on this machine.
- For revision 3: SCRATCH's `astra-read-1.md` and `seams-open.md` whole, and the control room's quote
  of A151. Not opened: the slice 1 builder briefs it names (`brief-28.md`, `brief-29.md`), which lie in
  a scratch folder behind this lane's wall; section 8 keeps its own numbers.

Notation. `name0`, `name1`, `name2`: the summons's names in order (C3): repository folder, vault
folder, memory note stem. `loc:x` a location (C11); `out:N.f` an output's field; `saved:n` a forward
row's saved input; `each.x` a field of a family's item and `n` its index (8 items 1, 12); `{date}` the
look's date (8 item 4); `{run}` the run's id.

| Short | Path or text |
|---|---|
| REPO, REPO_A | `[loc:developer_root, name0]`, `[loc:archive_root, name0]` |
| SF | `[loc:archive_root, "{name0}.sunset-{date}"]` |
| VF, VF_A | `[loc:vault_projects, name1]`, `[loc:vault_archive, name1]` |
| IDX, MN, MI | `loc:vault_index`; `[loc:memory_home, "project_{name2}.md"]`; `[loc:memory_home, "MEMORY.md"]` |
| MS (the project's own memory store) | `loc:project_memory`, resolved for REPO (8 item 13) |
| SC | `loc:shortcut_file` |
| OLD, NEW | `"{loc:vault_projects_rel}/{name1}"`, `"{loc:vault_archive_rel}/{name1}"` |

## 2. ROW-2 reports

None. No command does more than one thing with the rest left on (OP-1), writes a repository (OP-11),
writes a secret-bearing output outside staging (SEC-8), or takes a held value only as an argument
(SEC-3): a found label, a shortcut name and a note's path are made safe by declared validators
(SEC-1), and a routine's id and a computed crontab go to their tools as protected inputs (SEC-2).

## 3. The rows

Thirty rows: seventeen for sunset, thirteen for restore (twelve reverses written as their forward rows'
way back, and the restore's entry). By kind: build 5, keep 1, move 6, change 18. No owner step, owner
answer or check: nothing waits on him after the go. Not written: V04 (replaced by V30, KEEP-5), V09
(EV-5; a keep declares no way back, OP-2, and no row takes the store away), T15 (no draft row), the
catalog's E2 markers, G8 as a row (a look question, section 4), T22's and V12's needs (cut by slice 3).
Split by OP-1: T10 into T10a to T10d, V14 into V14a to V14d. Added because v1 does it: T02a, T13a.

Entries are numbered as ROW-1 orders them: 1 id, kind, phase; 2 thing (role, identity, tracked);
3 planning test; 4 before-test; 5 after-test; 6 construction; 7 commands; 8 repository commands;
9 after-check; 10 output and fields; 11 needs; 12 condition; 13 lost answer; 14 way back; 15 reverse
inputs; 16 span; 17 mode; 18 safe content; 19 answers; 20 review file; 21 owner names; 22 keep scope;
23 keeps required; 24 content classes, validators, resting places; 25 form lines. "None: a, b"
states each listed entry as `none`. **RK18** rows carry the owner's acceptance of v1's risk (A147,
A151) and state their window; rows also marked **A6** carry a window his A6 had kept his.

### 3.1 Commands (this lane's: launchd, cron, the adapter; git's are slice 3's, section 7)

Base environment only; no name registered as passed, fixed or private path; no trace flag; time in
seconds. "Alternatives: none" is stated for every command: no row is conditioned on a refusal.

| Command | Template | Time | Exits | Fields: name, place, type, disposition, list or safe value, alphabet and length, required in | Definite | Alternatives |
|---|---|---|---|---|---|---|
| `launchd.label` | `/usr/bin/plutil -extract Label json -o - {plist}` | 10 | 0 success, 1 not-found | `label`, the top level `[]`, name, equal to `each.label`, `A-Za-z0-9._-` 200, success | success; refusal not-found | none |
| `launchd.listed` | `launchctl list {label}` | 10 | 0 success, 113 not-found (to be measured) | none | success; refusal not-found | none |
| `launchd.unload` | `launchctl unload {plist}` (no `-w`) | 20 | 0 success, any other `other` | none | success, proven only by the after-check (the manual: unload "will only return a non-zero exit code due to improper usage") | none |
| `launchd.load` | `launchctl load {plist}` (no `-w`) | 20 | as unload | none | as unload | none |
| `cron.read` | `crontab -l`, its answer read whole as protected text (A147) | 10 | 0 success, 1 not-found (no table) | none | success; refusal not-found | none |
| `cron.replace` | `crontab {table}`, `table` a protected input (8 item 11); effects 1 | 10 | 0 success, any other `other` | none | success | none |
| `adapter.routines` (capability `routines`) | `routines --holding {text} --format json` | 30 | 0 success, 5 other | `routines`, `["routines", "*"]`, id, held, `a-z0-9-` 64, success (an empty list is no routine) | success | none |
| `adapter.routine` (same) | `routine --id-file {id} --out {out}`: `id` a protected input; writes the definition to `out` in staging (8 item 8) | 30 | 0 success, 3 not-found, 5 other | `state`, `["state"]`, state, fixed, `active` `disabled`, success | success; refusal not-found | none |
| `adapter.routine_disable` (same) | `routine-disable --id-file {id}`; effects 1; the routine keeps its id | 30 | 0 success, 3 not-found, 5 other | none | success; refusal not-found | none |
| `adapter.routine_enable` (same) | `routine-enable --id-file {id}`; effects 1; the same id | 30 | 0 success, 3 not-found, 5 other | none | success; refusal not-found | none |

### 3.2 Sunset (phases `keeping`, `retiring on this machine`, `retiring at the providers`, `the last record`)

**T02a, the archive folder where it is missing** (v1's `mkdir -p`)
1 T02a; build; `keeping`. 2 the archive folder; identity `path`, place `loc:archive_root`; tracked
`exists`, `identity`. 3 the place `absent`. 4 `free`: absent. 5 `dir`. 6 C1, empty folder, 0755.
9 `dir`. 10 `archive folder`, field `path` = the place. 12 planning fact `present.archive_root` equals
false, reason "already there" (8 item 7). 24 reads, stores, shows safe; validators none; resting
places none. 25 preview "make {loc:archive_root}". None: 7, 8, 11, 13 to 23.

**T02, the sunset folder** (A2 Q4)
1 T02; build; `keeping`. 2 the sunset folder; `path`, place SF; tracked `exists`, `identity`, `mode`.
3 SF `absent`. 4 `free`. 5 SF `dir`. 6 C1, empty folder, 0700. 9 SF `dir`, mode at most 0700.
10 `sunset folder`, field `path` = SF. 11 `archive folder`, state, `then not needed`. 24 safe; none;
resting place the sunset folder (SEC-7). 25 preview "make {SF}, owner-only, for the copies; Not
saved: files in the database provider's storage, and GitHub's issues, pull requests and releases";
status and summary "Saved copies: {SF}; Not saved: the same". None: 7, 8, 12 to 23.

**T05, the memory copy** (E16-1; RK18; A151)
1 T05; keep; `keeping`. 2 the copy of the project's own memory store; `path`, place
`[out:sunset folder.path, "memory"]` (a folder); tracked `exists`, `identity`, `sha256` (of its
names and fingerprints), `mode`; capability `memory stores`; layer `memory store`. 3 the place
`absent` (by the probe, RUN-6); `scope`: MS `dir` and every file in it readable. 4 `free`: absent.
5 the place `dir`. 6 C1, a keep of a folder copied whole by the tool (8 item 13), mode 0700 for the
folder and 0600 for each file; risks RK18. Window: "a note changed and changed back while it is
copied is kept as it stood mid-change, and nothing sees it" (A151). 7 none. 9 the place `dir`, mode
at most 0700. 10 `memory copy`, field `path` = the place. 11 `sunset folder`, made, `then not
applicable`. 22 scope: every file of MS. Same state, in A151's words: "the same holds of the folder's
file names and fingerprints read just before and again just after the copy, the two equal and equal
to the copy's own". Inventory: the names and fingerprints read before, in a protected record; source
identity: MS's folder identity read before and after, equal; content check: the copy's own names and
fingerprints equal the inventory; at the barrier (KEEP-3) the same, read again. 24 reads protected
(notes), stores protected (the keep), shows safe (counts); validators none; resting place the sunset
folder (SEC-7: the memory copy). 25 preview "copy the project's memory store whole to {SF}/memory";
status "memory copy checked whole, {count} files; the store is left in place"; where the capability
is absent: not applicable, not available on this harness. None: 8, 12 to 21, 23.

**T10a, unload each launch agent tied to the project** (A4 Q7; RK18; A6)
1 T10a; change; `retiring on this machine`; family, item `n` (8 item 1). 2 the job launchd holds;
identity `named value` `each.label`: the stem of each file of `loc:launch_agents` whose text holds
REPO, made safe by the validator `a launch agent's label`, and equal to the plist's own `Label`
(`launchd.label`, is_equal); tracked: `launchd.listed`'s result word; retires, `machine`,
`schedules`. 3 `launchd.label` success and equal; `launchd.listed` success (a Label that differs from
its file's name is a planning stop naming the file: GOV-1). 4 `loaded`: `launchd.listed` success;
`same job`: `launchd.label` equal. 5 `launchd.listed` not-found. 6 C6, risks RK18, `launchd.unload`
with `plist` = `each.path`. Window: "another loads or unloads the agent between the read and the
unload, and the run takes the unload as its own". 7 `launchd.label`, `launchd.listed`,
`launchd.unload`, each with `label` = `each.label` or `plist` = `each.path`. 9 `launchd.listed`
not-found. 10 `agent unloaded.n`, fields none. 14 V14a. 15 `value` `line` "its label" =
`each.label`; `value` `line` "its file" = `each.path`. 23 none required, an empty list (8 item 3).
24 reads safe (a validated name, exit words); stores and shows safe; validator `a launch agent's
label`; resting places none. 25 preview "unload the launch agent {each.label}"; status "unloaded".
None: 8, 11 to 13, 16 to 22.

**T10b, move each agent's file into the sunset folder** (A4 Q7)
1 T10b; move; `retiring on this machine`; family as T10a, the same `n`. 2 the agent's file; `path`,
place `each.path`; tracked `exists`, `identity`, `mode`; retires, `machine`, `schedules`.
3 `each.path` `file`. 4 `there`: file; `free`: `[out:sunset folder.path, "{each.label}.plist"]`
absent. 5 source absent, target file. 6 C7, RK4, to the target. 9 target `file`. 10 `agent file
archived.n`, field `path` = the target. 11 `agent unloaded.n`, state, `then not applicable`; `sunset
folder`, made, `then not applicable`. 14 V14b. 15 `value` `line` "where it stood" = `each.path`;
`value` `line` "where it was put" = the target. 23 empty list (8 item 3). 24 safe; validator `a launch
agent's label`; resting place the sunset folder (SEC-7). 25 "move {each.path} to {SF}". None: 7, 8,
12, 13, 16 to 22.

**T10c, disable each harness routine tied to the project** (v1's "cancel/disable"; RK18; A6 O2)
1 T10c; change; `retiring on this machine`; family over `adapter.routines` holding REPO, item `n`.
2 the routine; identity `provider id` `each.id` (held); tracked: `adapter.routine`'s `state` word;
capability `routines`; retires, `machine`, `schedules`. 3 `adapter.routine` success, `state` =
`active`. 4 the same. 5 `state` = `disabled`. 6 C6, risks RK18, `adapter.routine_disable`, the id a
protected input. Window: "another enables or disables the routine between the read and the request,
and the run takes it as its own". 7 `adapter.routines` (`text` = REPO), `adapter.routine`,
`adapter.routine_disable`. 9 `state` = `disabled`. 10 `routine disabled.n`, field `id` = `each.id`
(held). 14 V14c. 15 `command` `adapter.routine`, its staged definition file, type `definition`,
label "the routine's definition" (8 item 8); `held field` "the routine's id" = `each.id`. 23 empty
list. 24 reads held; stores protected records; shows each record's label and path; validators none;
resting place the protected folder. 25 preview "disable {count} routine(s) tied to the project, each
definition saved first to a private file"; status "disabled; its definition: {record label and path}"
(A6 O13); without the capability: not applicable, not available on this harness, with the step
"disable it in your harness yourself". None: 8, 11 to 13, 16 to 22.

**T10d, take the project's lines out of the crontab** (v1 Phase 3; RK18; A6 O3)
1 T10d; change; `retiring on this machine`. 2 the account's crontab; identity `named value`; tracked
`sha256` of `cron.read`'s text; retires, `machine`, `schedules`; span (the whole table). 3 `cron.read`
success; a line holds REPO (8 item 2). 4 the same. 5 no line holds REPO. 6 C6, risks RK18: the table
read, every line holding REPO taken out in memory, the result made the protected input of
`cron.replace` (8 item 11). Window: "a line another writes to the crontab between the read and the
replace is lost from it". 7 `cron.read`, `cron.replace`. 9 no line holds REPO; the table's
fingerprint is the computed one's. 10 `cron lines removed`, fields none. 14 V14d. 15 `command`
`cron.read`, type `before-image`, "the crontab before"; `value`, type `after-image`, "the crontab
after" (the computed table). 16 `in place`, ordered (an assignment above a line changes how it runs;
the whole table is the span). 23 empty list. 24 reads protected (never shown); stores protected
records; shows labels and paths; validators none; resting place the protected folder. 25 preview
"take the crontab lines that name the project out, the whole table saved first"; status "removed; the
table before: {record label and path}"; where no line holds REPO: `already so`. None: 8, 11 to 13,
17 to 22.

**T11, remove each shortcut line that targets the repository** (v1 Phase 4)
1 T11; change; `retiring on this machine`; family over the lines of SC holding `cd
{loc:shortcut_root_text}/{name0}"`, item `n`. 2 the shortcut file; `path`, place SC; tracked
`exists`, `sha256`; span; retires, `machine`, `shortcut`. 3 SC `file`. 4 `has`: `each.line` count 1.
5 `each.line` present false. 6 C3, RK2, `remove-line` `each.line`. 9 present false. 10 `shortcut
removed.n`, field `file` = SC. 14 V13. 15 `value` `line` "the line" = `each.line`; `value` `line` "its
name" = `each.name`, the word after `alias `, made safe by the validator `a shortcut name`
(`[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}`); where it fails, the row declares no way back and the preview
says so (EV-4, "an input is missing"). 16 `at the end`, unordered. 23 empty list. 24 reads protected
(the line), safe (the validated name); stores protected records; shows the name and the record's
label and path; validator `a shortcut name`; resting place the protected folder. 25 "remove the
shortcut {each.name} to {REPO}, its line saved first". None: 7, 8, 11 to 13, 17 to 22.

**T12, move the repository** (v1 Phase 4)
1 T12; move; `retiring on this machine`. 2 the repository; `path`, place REPO; tracked `exists`,
`identity`; retires, `machine`, `repository`. 3 REPO `dir`; REPO_A `absent`. 4 `there`; `free`.
5 REPO absent, REPO_A dir. 6 C7, RK4, to REPO_A. 9 REPO_A `dir`. 10 `repository archived`, field
`path` = REPO_A. 11 `archive folder`, state, `then not needed`. 14 V01. 15 `value` `line` "where it
stood" = REPO. 23 empty list (the copy comes first by ORD-4 and KEEP-3). 24 safe; none; none.
25 "move {REPO} to {REPO_A}". None: 7, 8, 12, 13, 16 to 22.

**T13a, the vault's archive folder where it is missing** (v1's `mkdir -p`)
1 T13a; build; `keeping`. 2 `path`, place `loc:vault_archive`; tracked `exists`, `identity`. 3 absent.
4 `free`. 5 `dir`. 6 C1, empty folder, 0755. 9 `dir`. 10 `vault archive folder`, field `path`.
12 planning fact `present.vault_archive` equals false, reason "already there". 24 safe; none; none.
25 "make {loc:vault_archive}". None: 7, 8, 11, 13 to 23.

**T13, move the vault folder** (v1 Phase 1)
1 T13; move; `retiring on this machine`. 2 the vault folder; `path`, place VF; tracked `exists`,
`identity`; retires, `machine`, `vault`. 3 VF `dir`; VF_A `absent`. 4 `there`; `free`. 5 VF absent,
VF_A dir. 6 C7, RK4, to VF_A. 9 VF_A `dir`. 10 `vault folder archived`, field `path` = VF_A.
11 `vault archive folder`, state, `then not needed`. 14 V02. 15 `value` `line` "where it stood" = VF.
23 empty list. 24 safe; none; none. 25 "move {VF} to {VF_A}". None: 7, 8, 12, 13, 16 to 22.

**T14, the index file's status** (v1 Phase 1)
1 T14; change; `retiring on this machine`. 2 the index file; `path`, place `[out:vault folder
archived.path, "_index.md"]`; tracked `exists`, `sha256`; span; retires, `machine`, `vault`. 3 `file`.
4 `has`: line `status: active`, count 1. 5 lines `status: archived`, `archived: {date}` present. 6 C3,
RK2, `replace` `"\nstatus: active\n"` by `"\nstatus: archived\narchived: {date}\n"`. 9 the two lines,
count 1. 10 `index archived`, field `file` = the place. 11 `vault folder archived`, made, `then not
applicable`. 14 V03. 15 `value` `before-image` = the old text; `value` `after-image` = the new.
16 `in place`, ordered. 23 empty list. 24 reads safe (lines the tool built); stores the images as
protected records; shows safe; none; resting place the protected folder. 25 "mark the index file
archived, {date}". None: 7, 8, 12, 13, 17 to 22.

**T16, the root index line, under ## Archived** (v1 Phase 1 step 4)
1 T16; change; `retiring on this machine`. 2 the root index; `path`, place IDX; tracked `exists`,
`sha256`; span; retires, `machine`, `vault`. 3 IDX `file`. 4 `has`: one line holding `{OLD}/_index`
(8 item 2). 5 none holds it; one line holding `{NEW}/_index` stands under `## Archived`. 6 C3, RK2,
`move-line` (8 item 6): that line, `OLD` by `NEW`, just under `## Archived`, the heading appended at
the end where missing. 9 as 5. 10 `root index archived`, field `file` = IDX. 11 `vault folder
archived`, made, `then not applicable`. 14 V05. 15 `file` `before-image` "the root index before";
`value` `after-image` "the root index after" (computed). 16 `in place`, ordered. 23 empty list.
24 reads protected (the file's other lines); stores protected records; shows safe; none; resting place
the protected folder. 25 "move the project's line under ## Archived, linking {VF_A}". None: 7, 8, 12,
13, 17 to 22.

**T17, repoint each note that links the old folder** (v1 Phase 1 step 5)
1 T17; change; `retiring on this machine`; family over the notes under `loc:vault_root` holding
`OLD/`, item `n`, each path made safe by `one line of plain words`. 2 the note; `path`, place:
`each.path` for a note outside VF, and `[out:vault folder archived.path, each.rel]` for a note inside
it (RUN-6; 8 item 15); tracked `exists`, `sha256`; span (the whole note); layer `vault`. 3 `file`
where it is now. 4 `OLD/` occurs. 5 `OLD/` does not occur. 6 C3, RK2, `replace-all` `OLD/` by `NEW/`
(8 item 6). 9 as 5. 10 `note repointed.n`, field `file` = the place. 11 `vault folder archived`,
made, `then not applicable`. 14 V06. 15 `file` `before-image` "the note before"; `value` `after-image`
"the note after" (computed); `value` `line` "where it was taken from" = `each.rel` or `each.path`.
16 `in place`, ordered. 24 reads protected; stores protected records; shows the validated path;
validator `one line of plain words`; resting place the protected folder. 25 "repoint {count} note(s)
from {OLD} to {NEW}". None: 7, 8, 12, 13, 17 to 23.

**T18, the home memory note's status** (v1 Phase 2)
1 T18; change; `retiring on this machine`. 2 the note; `path`, place MN; tracked `exists`, `sha256`;
span; capability `memory stores`; retires, `machine`, `memory note`. 3 MN `file`. 4 `has`: line
`name: {name1}`, count 1; line `status: archived` absent. 5 the three lines present. 6 C3, RK2,
`replace` `"\nname: {name1}\n"` by `"\nname: {name1}\nstatus: archived\narchived: {date}\n"`. 9 as 5.
10 `memory note archived`, field `file` = MN. 14 V07. 15 `value` `before-image`, `value`
`after-image`. 16 `in place`, ordered. 23 empty list. 24 as T14. 25 "mark project_{name2}.md
archived". None: 7, 8, 11 to 13, 17 to 22.

**T19, the memory index line, under ## Archived** (v1 Phase 2)
1 T19; change; `retiring on this machine`. 2 the index; `path`, place MI; tracked `exists`, `sha256`;
span; capability `memory stores`; retires, `machine`, `memory note`. 3 MI `file`. 4 one line holding
`(project_{name2}.md)`. 5 it stands under `## Archived`. 6 C3, RK2, `move-line`, no replacement.
9 as 5. 10 `memory index archived`, field `file` = MI. 11 `memory note archived`, state, `then not
applicable`. 14 V08. 15 `file` `before-image`; `value` `after-image` (computed). 16 `in place`,
ordered. 23 empty list. 24 as T16. 25 "move the memory index line under ## Archived". None: 7, 8, 12,
13, 17 to 22.

**T30, the tombstone** (A4; KEEP-5)
1 T30; build; `the last record`, alone. 2 this sunset's record; `path`, place `[out:vault folder
archived.path, "_sunset-{run}.md"]`; tracked `exists`, `identity`, `sha256`. 3 absent (by the probe).
4 `free`. 5 `file`. 6 C1 `last_record`, 0644, under v1's frontmatter and title (8 item 10). 9 `file`.
10 `tombstone`, field `path`. 11 `vault folder archived`, made, `then not applicable`. 24 safe;
records by label and path; none; none. 25 summary "the tombstone is {path}; a database this run
backed up is not paused by it (v1 never paused it itself); To restore: summon restore with this
project's names on this machine, which holds this run's record (A6)". None: 7, 8, 12 to 23.

### 3.3 Restore (phases `putting back on this machine`, `putting back at the providers`, `starting again`, `the last record`, C1)

Reverses are admitted as rows of their kind (EV-4, EV-5), their values from locations, the restore's
names and `saved:n` (C9); a family reverse keeps its forward row's `n`. For every reverse: 8 none;
12 none; 13 none; 14 `none`, reason "the row declares none"; 15 none; 16 none; 17 to 23 none.

**V01** (T12) 1 move; this machine. 2 the archived repository; `path`, place REPO_A; tracked `exists`,
`identity`. 3 REPO_A `dir`, REPO `absent`. 4 the same. 5 REPO_A absent, REPO dir. 6 C7, RK4, to REPO.
7 none. 9 REPO `dir`. 10 `repository back`, field `path` = REPO. 11 none. 24 safe; none; none.
25 "move {REPO_A} back to {REPO}".

**V02** (T13) 1 move; this machine. 2 `path`, place VF_A; tracked `exists`, `identity`. 3 VF_A dir, VF
absent. 4 the same. 5 VF_A absent, VF dir. 6 C7, RK4, to VF. 7 none. 9 VF `dir`. 10 `vault folder
back`, field `path` = VF. 11 none. 24 safe. 25 "the vault folder back; the tombstone stays in it".

**V03** (T14) 1 change; this machine. 2 `path`, place `[out:vault folder back.path, "_index.md"]`;
tracked `exists`, `sha256`; span. 3 `file`. 4 `saved:1` occurs once. 5 `saved:0` stands, `saved:1`
absent. 6 C3, RK2, `replace` `saved:1` by `saved:0`. 7 none. 9 as 5. 10 `index active`, field `file`.
11 `vault folder back`, state, `then not applicable`. 24 reads protected (this run's copies of the
images); stores the swap's images; shows safe. 25 "status back to active".

**V05** (T16) 1 change; this machine. 2 `path`, place IDX; tracked `exists`, `sha256`; span. 3 `file`.
4 `saved:1` occurs once. 5 `saved:0` stands. 6 C3, RK2, `replace` `saved:1` by `saved:0` (the whole
recorded after-image, EV-6). 7 none. 9 as 5. 10 `root index active`, field `file` = IDX. 11 `vault
folder back`, state, `then not applicable`. 24 as V03. 25 "the root index as it was".

**V06** (T17, family) 1 change; this machine. 2 `path`, place `saved:2` for a note outside VF, and
`[out:vault folder back.path, saved:2]` for a note inside it; tracked `exists`, `sha256`; span.
3 `file`. 4 the note's text is `saved:1` exactly once (EV-6). 5 `saved:0` stands. 6 C3, RK2, `replace`
`saved:1` by `saved:0`: links that were already on `NEW/` before the sunset are kept. 7 none. 9 as 5.
10 `note back.n`, field `file`. 11 `vault folder back`, state, `then not applicable`. 24 as V03.
25 "the note as it was".

**V07** (T18) 1 change; this machine. 2 `path`, place MN; tracked `exists`, `sha256`; span; capability
`memory stores`. 3 `file`. 4 `saved:1` once. 5 `saved:0` stands. 6 C3, RK2, `replace` back. 7 none.
9 as 5. 10 `memory note active`, field `file` = MN. 11 none. 24 as V03. 25 "the memory note active".

**V08** (T19) 1 change; this machine. 2 `path`, place MI; tracked `exists`, `sha256`; span; capability
`memory stores`. 3 `file`. 4 `saved:1` once. 5 `saved:0` stands. 6 C3, RK2, `replace` `saved:1` by
`saved:0`. 7 none. 9 as 5. 10 `memory index active`, field `file` = MI. 11 none. 24 as V03. 25 "the
memory index as it was".

**V13** (T11, family) 1 change; this machine. 2 `path`, place SC; tracked `exists`, `sha256`; span.
3 `file`. 4 `lacks`: `saved:0` absent; `name`: `saved:1` name-free (safe by T11's validator; 8 item 3).
5 `saved:0` present. 6 C3, risks RK2, RK5, RK13, `append-line` `saved:0`. 7 none. 9 `saved:0` count 1.
10 `shortcut back.n`, field `file` = SC. 11 `repository back`, state, `then not applicable`. 24 reads
protected (the line), safe (the name); stores the images; shows the name. 25 "the shortcut {saved:1}
back at the end of {SC}; open a new tab".

**V14b** (T10b, family) 1 move; this machine. 2 `path`, place `saved:1`; tracked `exists`, `identity`,
`mode`. 3 `saved:1` file, `saved:0` absent. 4 the same. 5 `saved:1` absent, `saved:0` file. 6 C7, RK4,
to `saved:0`. 7 none. 9 `saved:0` `file`. 10 `agent file back.n`, field `path` = `saved:0`. 11 none.
24 safe (saved safe values, 8 item 3); resting place the original place (SEC-7). 25 "the agent's file
back".

**V14a** (T10a, family) 1 change; `starting again`; runs on `repository back`, `agent file back.n`.
2 the job; identity `named value` `saved:0`; tracked `launchd.listed`'s word. 3 `launchd.label` on
`saved:1` equal to `saved:0`; `launchd.listed` not-found. 4 the same. 5 `launchd.listed` success.
6 C6, risks RK18, `launchd.load` with `plist` = `saved:1`. Window: "another loads or unloads the agent
between the read and the load, and the run takes the load as its own". 7 `launchd.label`,
`launchd.listed`, `launchd.load`. 9 `launchd.listed` success. 10 `agent loaded.n`, fields none.
11 `agent file back.n`, state, `then not applicable`. 24 safe. 25 "load the launch agent {saved:0}".

**V14c** (T10c, family) 1 change; `starting again`; runs on `repository back`. 2 the routine; identity
`provider id` `saved:1` (the same id: disable keeps it); tracked `adapter.routine`'s `state`; capability
`routines`. 3 `adapter.routine` success, `state` = `disabled`. 4 the same. 5 `state` = `active`. 6 C6,
risks RK18, `adapter.routine_enable`, the id a protected input. Window: "another enables or disables
it between the read and the request, and the run takes it as its own". 7 `adapter.routine`,
`adapter.routine_enable`. 9 `state` = `active`. 10 `routine enabled.n`, field `id` (held).
11 `repository back`, state, `then not applicable`. 24 reads held; shows the definition's record by
label and path. 25 "enable the routine again; its definition: {record label and path}".

**V14d** (T10d) 1 change; `starting again`; runs on `repository back`. 2 the crontab; identity `named
value`; tracked `sha256` of `cron.read`'s text; span. 3 `cron.read` success. 4 the table is `saved:1`
exactly (EV-6). 5 the table is `saved:0`. 6 C6, risks RK18: `saved:0` made the protected input of
`cron.replace` (8 item 11). Window: "a line another writes between the read and the replace is lost
from the table". 7 `cron.read`, `cron.replace`. 9 as 5. 10 `cron lines back`, fields none.
11 `repository back`, state, `then not applicable`. 24 reads protected; shows the records by label and
path. 25 "the crontab as it was before the sunset, only where no one has changed it since".

**V30, the restore's entry** (KEEP-5, EV-7)
1 V30; build; `the last record`, alone. 2 this restore's record; `path`, place `[loc:vault_projects,
name1, "_restore-{run}.md"]`; tracked `exists`, `identity`, `sha256`. 3 the place absent (by the
probe). 4 `free`. 5 `file`. 6 C1 `last_record`, 0644. 9 `file`. 10 `restore entry`, field `path`.
11 `vault folder back`, state, `then not applicable` (a restore that puts nothing back still writes
it, EV-7). 24 safe; records by label and path; none; none. 25 "this restore's entry; the tombstone and
{SF} stay". None: 7, 8, 12, 13, 14, 15 to 23.

## 4. The look, and the questions before the preview

All before the manifest (RUN-5); after the go nothing asks him.

- **G8, git safety**: a lane question asked only where its read fails (8 item 7), the reads slice 3's
  (section 7). Failing, the look ends with it listed: "The repository has uncommitted changes or
  unpushed commits. Commit and push them and summon again, or summon again with --as-is to archive it
  as it is." Skipped under `--as-is` or with the `repository` layer dropped. It gives no output.
- **The reason**: the required input `description` (C10).
- **Not proven lines** (restore): `restore_lines`, asked in the restore's look (EV-5).
- **G10**: each row's planning test (`already so` listed); families found by 8 items 1 and 2; loose
  ends: one preview line for each of `wrangler.toml`, `wrangler.jsonc`, `netlify.toml`, `fly.toml`,
  `render.yaml` present in REPO (v1's list), never acted on. Other trackers: section 11.

## 5. Form lines

| Key | Line |
|---|---|
| `passed` | "the check passed: {what}" |
| `answered` | "you answered: {what}" |
| `waiting, not shown` | "waiting on you: {what}; its read was not made or got no answer, so its step is not shown" |
| `not offered` | "not offered by this restore ({reason}): {what}" |
| `not proven, on his word` | "runs on your word; it was not proven the retirement's: {what}" |
| `a receipt due` | "a secret may have been received and lost: operation {operation}, execution {execution}, field {field}" |
| `a safe ground disproved` | "a value this run held as safe is withheld ({count} on record)" |
| reason `already there` | "not applicable (already there): {what}" |
| a loose end | "loose end, yours to handle, never acted on: {file} in {REPO}" |
| the hand-off prompt (A1 P10) | v1's sunset prompt (Phase 9 step 2), in the summary of a run that ends `complete` or `ended with exceptions` (8 item 14), with: no Notion line; a layer the run lacked left out; "Database: backed up, not paused"; its reason his `description` |

Changes to v1's forms: Notion lines leave; a layer the run lacked is left out; "Not saved" and "Saved
copies" (T02); "To restore" (T30); the tombstone's name `_sunset-{run}.md`; crontab tables, routine
definitions and shortcut lines named by private file, not shown; "Backup" and "Provider clocks" are
slice 3's lines.

## 6. The checklist (ROW-3)

| Item | Answered by |
|---|---|
| F18 `passed` / `answered` | form lines `passed`, `answered` |
| F18 EV-7's missing keep or record | reason: FORM-2's own `not applicable` line carries slice 1's EV-7 reason words |
| F18 clocks and what expires; no test load | reason: slice 3's lines, which T30 renders |
| F18 the not-saved list | row T02 |
| D20 R3/R4, A1 P6/P7/P8 | reason: no row here takes a type or names Notion; backup is slice 3's; T30 says the database is not paused |
| D20 A1 P9/P10 inventory | rows T12, T13, T14, T16, T17, T05, T18, T19, T11, T10a to T10d, T30; form line "the hand-off prompt"; reason: kit, staged documents and cue are sunrise's and slice 1's; one plugin, C2 |
| D20 E16-1 | reason: the reason is the required input `description`; dirty work is the look question G8; loose ends are section 4's lines (trackers: section 11); the rest is sunrise's |
| D20 A1 P11, A2 | row T02; reason: T03, T04 are slice 3's |
| D20 A4 | rows T10a, T10b |
| D20 A6 | row T30 ("To restore" on this machine); rows T10c, T10d (private files named) |
| D20 C1's phase order | the phases of 3.2 and 3.3 |
| D20 shared schemas; provider primitives | reason: slice 1's (G19, G20); launchctl measured: its exit is not definite, so C6 with an after-check |

## 7. Seams (an output's name and fields are its providing lane's)

| With | This lane provides | This lane needs |
|---|---|---|
| slice 3, T01 | REPO, before T12 | `{date}` (8 item 4) |
| slice 3, T03, T04 | `sunset folder` (field `path`) | each needs `sunset folder`, made; T04 does not repeat "Not saved" |
| slice 3, T20 | `repository archived` (field `path`) | T20 needs it, made; this lane needs nothing of T20's `archived repository` |
| slice 3, V10, V11 | `repository back` (field `path`); phase `putting back at the providers` (or `starting again` with runs on `repository back`) | nothing |
| slice 3, T22, V12 | none (cut) | no need on them; T30 says the database is not paused |
| slice 3, G8 | G8 gives no output | slice 3 needs none |
| slice 3, the git declarations | none | three reads for its builder: `git.tracked_clean` (`git -C {repo} diff-index --quiet HEAD --`; exit 0 success, 1 conflict); `git.untracked_none` (`git -C {repo} ls-files --others --exclude-standard --error-unmatch -- .`; exit 1 success, 0 conflict, to be measured); `git.unpushed_count` (`git -C {repo} rev-list --count --branches --not --remotes`; `count` at the top level, equal to 0) |
| slice 3, inputs and facts | names by place (`name0` to `name2`, C3); dropped layers `repository`, `memory store`, `memory note`, `shortcut`, `schedules`, `vault` (C4); `flags.archive_as_is` | slice 3 checks its `answers.repo`, `answers.slug`, `flags.keep_*` against these names |
| slice 2, SR20, SR22 | none | `status: active` once in the seed; `name: {slug}` once and no `status:` in the memory note |
| slice 2, SR21, SR23, SR24 | none | the root index line holds `{OLD}/_index`; the memory index line holds `(project_{slug_}.md)`; the alias line holds `cd {loc:shortcut_root_text}/{Name}"` |

## 8. What G19 must give (this lane's numbers; the G19 and G20 mapping is the control room's)

1. A family row, one instance per item of a found read (folder files holding a text; file lines
   holding a text; a provider's held list), its values `each.x`; an item's name or path safe where a
   declared validator passes. Validators: `a launch agent's label` (`[A-Za-z0-9][A-Za-z0-9._-]{0,199}`),
   `a shortcut name` (`[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}`), `one line of plain words`.
2. A substring read: how many lines of a file, or of a command's protected text, hold a value.
3. A retiring row may state an empty list of keeps it requires; a saved record written from safe
   content stays usable as text in a name check, a path and an argument.
4. A date mark: the look's date, frozen into the manifest.
5. RK18 among a construction's risks, and C6 admitted for a row carrying it.
6. Two edit kinds: `replace-all` and `move-line` (the one line holding a text, an optional replacement
   in it, moved under a named heading, the heading appended where missing). Their reverses use the
   existing `replace` of the whole recorded after-image.
7. A planning fact from a path read; a lane question asked only where its declared read fails; a
   preview line where a named path is present.
8. A read command's staged file kept as a reverse input of the declared type.
9. A top-level answer place `[]`.
10. A row's form line filled from its own frozen safe values; the last record under the lane's fixed
    head lines.
11. (S9) A C6 command's protected input made from a computed text: the row's edit applied in memory to
    the protected text its read gave (or a saved record), written owner-only in the protected folder
    and handed to the command's slot.
12. (S7) A family instance's outputs and needs carry its item's index `n`; a reverse keeps its forward
    row's `n`.
13. (S1) A keep of a folder of this machine copied whole by the tool, with A151's two reads of names
    and fingerprints and its recheck by them; the location `project_memory` resolved for a project
    folder by the machine-facts module (E16-12).
14. (S10) A lane form rendered at a run's end from the manifest and the journal (the hand-off prompt).
15. (S8) A family item inside a folder a plan's move moves is placed by that move's output (RUN-6).

## 9. Frame words

None needed now: RK18 and the crontab's text are written by A147, and the memory copy's state by
A151. A151's opening of RISK-2's condition on another thing "read just before the effect" is not used:
no finding here needed it.

## 10. Choices the frame left to the rows

- C1 Restore phases as 3.3 names them. ORD-4: "The rest of a restore's phases ... are the lane's to declare."
- C2 Restore is a summons of `sunset-v2`. The skeleton: "Whether a restore is a third skill or a summons of this one is that lane's to say."
- C3 Three name forms in order, resolved by the skill and confirmed by him before the summons. RUN-2 (a): "each further name the owner gave".
- C4 Layers and `--keep-*` flags are dropped layers (`--keep-local` drops `repository`, `memory store`, `shortcut`). RUN-7: "a flag; the project type; a layer the project does not have".
- C5 Entry names hold the run's id. KEEP-5: "an earlier run's entry at the place is not a collision".
- C8 Edits anchored on whole lines with their line ends. LOG-2: "the after-state the effect is to leave, computed beforehand".
- C9 A reverse's values: locations, the restore's names, `saved:n`. EV-5: "Every reverse is an ordinary operation".
- C10 The reason is the input `description`. RUN-5: "An answer taken in the look is an input of the run".
- C11 Location keys `vault_root`, `vault_projects`, `vault_archive`, `vault_projects_rel`, `vault_archive_rel`, `vault_index`, `memory_home`, `project_memory`, `launch_agents`, `shortcut_root_text`, beside `developer_root`, `archive_root`, `shortcut_file`. Contract E16-12.
- C13 The sunset folder empty, 0700, the keeps publishing into it. SEC-7.

## 11. Less than v1 or than ruled

- "Any external tracker that is not Notion" (v1's loose ends) is not looked for: no deterministic mark of one is known, and no ruling of his cuts it. Carried to the owner (S10).
- Crontab tables, routine definitions and shortcut lines are named in the tombstone by private file, not shown (v1 showed the alias line and the cancelled list).
- A routine is disabled only where the adapter declares `routines`; elsewhere the preview hands him the step.
- A restore puts the crontab back only where no one has changed it since the sunset (EV-6).
- A launch agent whose `Label` differs from its file's name stops the look.
- A second sunset of one project on one date stops at T02.
- Restore works only on the machine holding the run directory (ruled, A6); no test load (ruled, A2).

## 12. Seen and not touched

- `launchctl unload` and `load` exit 0 whatever happened; only `list`'s exit decides.
- A found name with a leading hyphen reaches `launchctl` or `plutil` as it stands (A144's note).
- Slice 1's last record renders T30's own line as "not started" inside the tombstone.
- The catalog's 4.3 finds the sunset by name; the frame by the keys' fingerprints (RUN-5).

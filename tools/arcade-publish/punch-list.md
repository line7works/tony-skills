# Punch list — arcade-publish CLI

The findings ledger for this tool. No build doc exists (one-shot tool build),
so this file is the correctness-only ledger that `/signoff` and `/recheck`
read and append to.

**Additive only.** Never rewrite or resolve an earlier entry — a later recheck
block supersedes it, and the latest-dated block wins. The accumulation is the
point: a finding that recurs across reviews is a pattern, visible only if
everything lands in one place.

Consolidated here 2026-08-10 from two earlier locations, entries preserved
verbatim: `~/.config/line7/punch-list.md` (the 2026-08-09 blocks) and
`~/Developer/line7-site/docs/punch-list.md` (the 2026-08-10 blocks). Findings
about the *server* rather than this CLI stayed behind in
`~/Developer/line7-site/docs/punch-list.md`, which grades that codebase.

Line numbers are as-of their own block and drift with later edits; the claim
text is the durable join key. Entries before 2026-08-10 cite the script as
`arcade-publish:<line>` when it lived at `~/.local/bin/arcade-publish`; it is
now this folder's `arcade-publish`, reached by symlink from that path.

**Location update, 2026-08-12** — the sentence above is now historical, kept
because this ledger is additive-only. The script left this folder: it lives at
`plugins/arcade/assets/arcade-publish` in this repo, and
`~/.local/bin/arcade-publish` is a launcher that resolves it rather than a
symlink. Every `arcade-publish:<line>` and `~/.local/bin/arcade-publish:<line>`
citation below resolves against that file. This folder keeps only the ledger —
deliberately, so there is one list and not two.

### 2026-08-09 — review: arcade-publish CLI

- MAJOR · arcade-publish:68 · a 200 GET whose body lacks a `seeds` array is coerced to `[]` and the follow-up PUT replaces the whole registry · anomalous-but-OK response (proxy/maintenance JSON, API shape drift) → publish "succeeds" and every existing seed is erased from the gallery · correctness lens (reproduced against mock)
- MAJOR · arcade-publish:105 · blind read-modify-write of the full seeds array, no version check, last write wins · admin UI deletes or edits a seed between the CLI's GET and PUT → deletion silently resurrected, possibly pointing at an already-deleted blob · seams + correctness lenses (convergent)
- MAJOR · arcade-publish:47 · `base` accepted verbatim with no https:// enforcement, and the credential POST follows redirects · `"base": "http://line7.works"` (one-character typo) sends the admin password cleartext; a 307/308 re-sends the password body to the redirect target · security lens
- MINOR · arcade-publish:121 · upload response `id`/`url` never validated; a 200 without them registers a seed with no url · correctness (reproduced against mock)
- MINOR · arcade-publish:83 · output URLs hardcoded to arcade.line7.works / line7.works regardless of `base` · wrong links when run against dev or if ARCADE_HOST changes · seams
- MINOR · arcade-publish:134 · failed PUT after successful upload orphans the blob and the error's advice ("finish it in the admin UI") is not actually possible in the admin UI · seams
- MINOR · arcade-publish:106 · no republish/update flow for an existing slug; duplicate check is client-side only and racy · seams
- MINOR · arcade-publish:147 · `--name`/`--slug` swallow a following flag as their value; trailing `--name` silently falls back to filename · correctness
- MINOR · arcade-publish:58 · session cookie parsed by regex from the comma-joined header instead of `getSetCookie()` · fragile if the host ever sets a second cookie · seams
- MINOR · arcade-publish:52 · no fetch timeouts anywhere; hung server hangs the CLI forever · correctness + security
- MINOR · arcade-publish:40 · setup hint doesn't tell the user to chmod 600, so a fresh install on another machine lands world-readable with a live admin password · security
- MINOR · arcade-publish:82 · server-controlled strings (slug/name/error) printed raw; ANSI/OSC escape injection into the operator's terminal · security
- MINOR · arcade-publish:26 · slugify truncation at 60 chars can leave a trailing hyphen (strip runs before slice) · correctness
- MINOR · arcade-publish:79 · `list` crashes with a TypeError if any seed lacks `uploadedAt` · correctness
- MINOR · arcade-publish:45 · malformed config JSON errors without naming the config file path · correctness

### 2026-08-09 — recheck: arcade-publish CLI

- MAJOR · arcade-publish:68 · (a 200 GET whose body lacks a `seeds` array is coerced to `[]` and the follow-up PUT replaces the whole registry) · fixed — guard now at :88-99, executed against mock: wrong-shape 200 refused, zero PUTs
- MAJOR · arcade-publish:105 · (blind read-modify-write of the full seeds array, no version check, last write wins) · fixed — mitigation at :163-178, executed: PUT built from post-upload re-read, admin edit during upload preserved; residual millisecond GET→PUT window accepted
- MAJOR · arcade-publish:47 · (`base` accepted verbatim with no https:// enforcement, and the credential POST follows redirects) · fixed — executed: http:// base rejected pre-network at :47-50, 307 to foreign host refused at :56-70, password body never re-sent
- MINOR · arcade-publish:167 · broke: slug-conflict cleanup DELETE routes through send(), whose fail() exits the process — a 3xx/thrown DELETE prints a misleading error instead of the "slug was taken" message, and the .catch is dead code
- MINOR · arcade-publish:165 · broke: a transient failure on the post-upload re-read exits via getSeeds' fail() without warning that the uploaded blob is now orphaned (the PUT-failure path at :181 does warn)

### 2026-08-10 — review: arcade-publish update/delete commands

- MAJOR · `~/.local/bin/arcade-publish:279-289` · cmdDelete skips the re-read-before-PUT that publish and update both do · a seed added or edited via the admin UI between the CLI's initial getSeeds and its whole-array PUT is silently erased from the site document · update/delete review
- MAJOR · `~/.local/bin/arcade-publish:56-70,263-266,293-297` · cleanup/rollback calls route through send(), whose failure path is fail() → process.exit(1), making every `.catch()` around deleteUpload dead code for network errors and 3xx · after a successful delete PUT, a network blip on the file-cleanup DELETE exits 1 with "request failed" — the delete succeeded but the tool reports failure; same misreporting on update's rollback paths (real error message never printed) · update/delete review
- MINOR · `~/.local/bin/arcade-publish:292-297` · delete exits 0 when the uploaded file was not actually removed; server compounds this by returning `{ok:true}` even when the blob delete fails (`lib/blobStore.ts:77-83`) · orphaned blobs accumulate invisibly · update/delete review
- MINOR · `~/.local/bin/arcade-publish:308` · `--name` with a missing or flag-shaped value misparses · `update slug f.html --name` silently skips the rename and prints success; `--name --featured` renames the seed to the literal string "--featured" · update/delete review
- MINOR · `~/.local/bin/arcade-publish:247` · whitespace-only `--name "  "` stores an empty seed name · gallery renders a blank label · update/delete review
- MINOR · `~/.local/bin/arcade-publish:198` · `--slug` is silently accepted and ignored by update/delete · `update old file.html --slug new` looks like a rename request and silently isn't · update/delete review
- MINOR · `~/.local/bin/arcade-publish:199,273` · extra positionals silently ignored · `delete slug-a slug-b` deletes only slug-a and reports success · update/delete review
- MINOR · `~/.local/bin/arcade-publish:302-313` · unknown flags fall through to positionals · `delete --force my-game` looks up a seed named "force" instead of erroring on the unknown flag · update/delete review
- MINOR · `~/.local/bin/arcade-publish:273-299` · delete is one-shot destructive with no confirmation or preview; the seed's name prints only after deletion · fat-fingered slug destroys a live page immediately · update/delete review
- MINOR · `~/.local/bin/arcade-publish:229-231` · update's "no id/url" failure path does not attempt cleanup when url is present but id is missing · orphaned upload only · update/delete review
- MINOR · `~/.local/bin/arcade-publish:253,288` · pre-corrupted duplicate-slug state mishandled: update rewrites both duplicates to the same object; delete removes both but deletes only one file · requires an already-bad store · update/delete review
- MINOR · `~/.local/bin/arcade-publish:269` · success URLs hardcode `https://arcade.line7.works` while the canonical host is env-derived server-side (`lib/arcadeHost.ts`) · printed URL goes stale if the host changes · update/delete review

### 2026-08-10 — recheck: arcade-publish update/delete commands

- MAJOR · `~/.local/bin/arcade-publish:279-289` · (cmdDelete skips the re-read-before-PUT that publish and update both do) · fixed — now at :291-301; second getSeeds immediately before the PUT, body built from the fresh read; verified in a stubbed-fetch harness (concurrent seed added between reads was preserved in the PUT body)
- MAJOR · `~/.local/bin/arcade-publish:56-70,263-266,293-297` · (cleanup/rollback calls route through send(), whose failure path exits the process, making .catch guards dead code and misreporting outcomes) · fixed — deleteUpload now at :189-201 with its own non-fatal fetch; all four cleanup/rollback sites (publish :169, update :242/:261/:268, delete :305) verified in four stubbed scenarios: post-PUT cleanup failure now exits 0 with the success line plus orphan note, rollback paths print their intended messages

### 2026-08-10 — note: strict argument parsing

Not a review block. The 2026-08-10 fix pass also closed four MINORs from that
day's review — `--name` misparse, `--slug` silently ignored on update, extra
positionals ignored, unknown flags falling through to positionals — by giving
each command an explicit grammar and erroring on anything outside it. Verified
by exercising all six error paths live (each fails before login, no writes).
That grammar also covers the 2026-08-09 MINOR at `arcade-publish:147`, the
same `--name` swallow reported a day earlier and left open.

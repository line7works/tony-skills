# session-watch

Two read-only scripts for watching what a Claude Code session does with its tools, from
the session's own transcript. Stdlib only, Python 3.10+. Nothing to install: run them from
this checkout or copy them anywhere.

**Privacy:** `toolwatch.py` output can hold private data (it prints prompt text, command
text and output snippets), so keep it local. `livewatch.py` is the one safe to stream: it
never prints message text, addresses, ids or file contents.

## The scripts

- `toolwatch.py`: an after-the-fact summary of one transcript. A timeline of user prompts,
  assistant text and each tool call (short input, wall time from call to result, result
  size, error flag), then totals per tool, the repo scripts run via Bash, identical calls
  repeated, and token totals.
- `livewatch.py`: follows a live transcript and prints one sanitized line per finished tool
  call (tool, repo scripts and flags, shell verbs, seconds, result size, `ERROR`) and one
  per turn end. Built to feed a Claude Code Monitor.

## Usage

```
python3 toolwatch.py <session.jsonl> [--repo PATH] [--full] [--since 2026-01-01T09:00:00Z]
python3 livewatch.py <session.jsonl> [--repo PATH] [--subcommands a,b] [--show-skills] [--once]
```

`--repo` is the repo the session works in; the default is the git root of the current
directory, else the current directory. A script is any path ending `.py`, `.sh`, `.js`,
`.ts` or `.rb` named in a Bash command that resolves inside the repo (relative paths are
read against the repo root), shown relative to it.

livewatch is stricter than toolwatch:

- A script prints only if the file exists in the repo, so a scratch file's name never does.
- A Read/Write/Edit path inside the repo shows relative; anything outside it, or under
  `.claude/`, shows only as `outside repo: .<ext> file` (or `outside repo: file` when the
  extension is missing or odd). Folder names can carry private words, so they never print.
- The word after a script prints only when it is listed in `--subcommands`.
- Flags print by name only (`--to`, never its value): at most ten, whole unquoted words before any heredoc,
  never from a comment. The shell verbs it reports come from a fixed list in the
  script (`VERBS`).
- A Skill call prints as `skill` (its name only with `--show-skills`, when short and plain),
  and a ToolSearch call as `select N tools` or `keyword search`, never the query.
- `--once` reads to the end and exits instead of following.
- `SKIP=n` suppresses the first n tool-call lines, for a restart that replays the file.

Sample lines:

```
     0s USER prompt (212 chars)
    14s #1 Bash scripts/build.py --dry-run [grep] :: 2.0s, 840 chars
    15s #2 Read outside repo: .md file :: 0.1s, 0 chars ERROR
    31s TURN END (2 tool calls so far)
```

## Monitor command

From the watching session, start a Monitor whose command is:

```
python3 <tony-skills>/tools/session-watch/livewatch.py <projects-dir>/<project-dir>/<session-id>.jsonl --repo <repo>
```

Each stdout line arrives as an event. After a restart, prefix `SKIP=<last #n seen>` so the
replayed calls stay quiet.

## Finding a session's transcript

Transcripts are one `.jsonl` per session in a per-project folder under Claude Code's
projects folder (`~/.claude/projects/<project-dir>/`, where `<project-dir>` is the
working directory's path with `/` turned into `-`). A `custom-title` record holds the
session name in `customTitle`; after a `/clear`, the new transcript opens with a
`derived-from` record whose `sessions` list names the session it came from. To find a
transcript by its title:

```
python3 -c 'import glob,json,sys; [print(f) for f in glob.glob(sys.argv[1]+"/*/*.jsonl") if any("custom-title" in l and json.loads(l).get("customTitle")==sys.argv[2] for l in open(f,errors="ignore"))]' ~/.claude/projects "<session title>"
```

The newest match is usually the live one (`ls -t` on the results).

## Tests

```
python3 -m unittest discover -s tools/tests -p 'test_session_watch.py'
```

Offline: a synthetic transcript in a temporary folder.

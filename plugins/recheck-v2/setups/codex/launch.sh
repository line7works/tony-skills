#!/bin/sh
set -eu
if [ "$#" -lt 3 ]; then echo 'usage: launch.sh prompt-file workspace out-dir [--writable dir]...' >&2; exit 2; fi
PROMPT_FILE="$1"; WORKSPACE="$2"; OUT_DIR="$3"; shift 3
# E11-26: the trial's run directory is a SIBLING of the workspace (`<case dir>/run`, E10-54(a)),
# so it is outside cwd and outside the child home. Until E11-7 item 2 it was inside `$TMPDIR`
# (`<campaign>/tmp`), which `exclude_tmpdir_env_var: false` makes writable; a per-trial TMPDIR
# took that away and every Codex session was refused its first write ("patch rejected: writing
# outside of the project"). The runner names the roots this session may write; each becomes its
# own `--add-dir`, so nothing of any other trial is shared.
WRITABLE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --writable)
      [ "$#" -ge 2 ] || { echo 'launch.sh: --writable takes a value' >&2; exit 2; }
      [ -d "$2" ] || { echo "launch.sh: no writable directory: $2" >&2; exit 3; }
      WRITABLE="$WRITABLE $2"; shift 2 ;;
    *) echo "launch.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
export CODEX_HOME="${RECHECK_CODEX_HOME:-$HOME/.local/share/skills-v2-pilot/codex/home}"
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$CODEX_HOME/child/uv-cache"
# shellcheck disable=SC2086
python3 - "$PROMPT_FILE" "$WORKSPACE" "$OUT_DIR" $WRITABLE <<'PY'
import json, os, shutil, subprocess, sys
from pathlib import Path
prompt,ws,out=map(lambda x:Path(x).resolve(),sys.argv[1:4])
writable=[Path(x).resolve() for x in sys.argv[4:]]
if out.exists():raise SystemExit('out-dir exists; refusing to overwrite a live session')
out.mkdir(parents=True)
cmd=['codex','exec','--json','-o',str(out/'final.md'),'-C',str(ws),'--add-dir',str(Path(os.environ['CODEX_HOME'])/'child')]  # E9-25: only the child home is writable; executor sessions and installed core stay outside.
for extra in writable:cmd+=['--add-dir',str(extra)]  # E11-26: the roots the runner named, this trial's only
cmd+=['-c','sandbox_workspace_write.network_access=true','-']
(out/'command.json').write_text(json.dumps(cmd))
with prompt.open('rb') as inp,(out/'events.jsonl').open('wb') as events,(out/'stderr.log').open('wb') as err:
 code=subprocess.run(cmd,stdin=inp,stdout=events,stderr=err).returncode
thread=None
for line in (out/'events.jsonl').read_text().splitlines():
 try:d=json.loads(line)
 except ValueError:continue
 if d.get('type')=='thread.started':thread=d.get('thread_id')
records=list((Path(os.environ['CODEX_HOME'])/'sessions').rglob('rollout-*'+thread+'.jsonl')) if thread else []
if len(records)==1:shutil.copyfile(records[0],out/'rollout.jsonl')
summary={'exit':code,'thread_id':thread,'rollout':str(out/'rollout.jsonl') if len(records)==1 else None}
(out/'launch.json').write_text(json.dumps(summary));print(json.dumps(summary))
sys.exit(code)
PY

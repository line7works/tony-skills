#!/bin/sh
set -eu
if [ "$#" -ne 3 ]; then echo 'usage: launch.sh prompt-file workspace out-dir' >&2; exit 2; fi
export CODEX_HOME="${RECHECK_CODEX_HOME:-$HOME/.local/share/skills-v2-pilot/codex/home}"
export PYTHONDONTWRITEBYTECODE=1
python3 - "$1" "$2" "$3" <<'PY'
import json, os, shutil, subprocess, sys
from pathlib import Path
prompt,ws,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
if out.exists():raise SystemExit('out-dir exists; refusing to overwrite a live session')
out.mkdir(parents=True)
cmd=['codex','exec','--json','-o',str(out/'final.md'),'-C',str(ws),'--add-dir',os.environ['CODEX_HOME'],'-c','sandbox_workspace_write.network_access=true','-']  # E9-21: the nested verifier reaches the model through this sandbox  # E9-20: the home must be a writable root or the executor's nested verifier cannot initialize
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

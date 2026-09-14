#!/bin/sh
# Each mutation is confined to a separate copy of the isolated home.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
python3 - "$HERE" "${1:?usage: negative-tests.sh scratch-output-directory}" <<'PY'
import json, os, re, shutil, subprocess, sys
from pathlib import Path
here,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);base=Path.home()/'.local/share/skills-v2-pilot/codex/home'
if out.exists():raise SystemExit('output already exists; retained trials are never overwritten')
out.mkdir(parents=True)
names=['malformed-sidecar','missing-sidecar','missing-name','broken-delimiter','duplicate-name','missing-resource','symlink-file','symlink-directory','update-copy-symlink-copy']
for name in names:
 trial=out/name;trial.mkdir()
 prep=subprocess.run([str(here/'install.sh'),'--prepare-negative',name,str(trial)],capture_output=True,text=True)
 if prep.returncode:raise SystemExit(prep.stderr)
 home=Path(json.loads(prep.stdout)['home'])
 # Git mutations are confined to this new throwaway workspace, never the lane worktree.
 workspace=trial/'workspace';workspace.mkdir()
 subprocess.run(['git','init','-q',str(workspace)],check=True)
 (workspace/'README.md').write_text('Disposable loader measurement.\n')
 subprocess.run(['git','-C',str(workspace),'add','README.md'],check=True)
 subprocess.run(['git','-C',str(workspace),'-c','user.name=Pilot','-c','user.email=pilot@example.invalid','commit','-qm','Initialize disposable measurement'],check=True)
 probe='delivery-probe' if name in ['missing-name','broken-delimiter','duplicate-name','symlink-file','symlink-directory'] else 'manual-only-probe'
 prompt=trial/'prompt.md';prompt.write_text('Use the '+probe+' skill explicitly and report what you can load. Read recheck-v2 references/verifier.md relative to its installed skill root. If that resource is missing, report it and do not recover a copy elsewhere. Do not start a recheck or change any file. Do not use web, MCP, agents or other skills.\n')
 (trial/'home.json').write_text(json.dumps({'home':str(home)}))
 env=dict(os.environ,RECHECK_CODEX_HOME=str(home))
 c=subprocess.run([str(here/'launch.sh'),str(prompt),str(workspace),str(trial/'capture')],env=env,capture_output=True,text=True)
 capture=trial/'capture';record=capture/'rollout.jsonl'
 message=(capture/'stderr.log').read_text() if (capture/'stderr.log').exists() else c.stderr
 rows=[json.loads(line) for line in record.read_text().splitlines() if line.strip()] if record.exists() else []
 catalogs=[r.get('payload',{}).get('state',{}).get('host_skills',{}).get('body','') for r in rows if r.get('type')=='world_state']
 catalog=sorted(set(n for body in catalogs for n in re.findall(r'^\s*-\s+([A-Za-z0-9:_.-]+):',body,re.M)))
 target='recheck-v2' if name=='missing-resource' else probe
 present=any(n==target or n.endswith(':'+target) for n in catalog)
 classification='crashed' if c.returncode or not catalogs else 'ignored' if present else 'prevented activation'
 observation={'test':name,'exit':c.returncode,'capture':str(capture),'catalog':catalog,
              'target':target,'classification':classification,'harness_message':message,
              'message_quote':json.dumps(message),'scope':'catalog activation; file reads are not prevented by catalog absence'}
 if not catalogs:observation['capture_error']='world_state host_skills catalog missing'
 if name=='update-copy-symlink-copy':observation['update_install']=str(trial/'update-install.json')
 print(json.dumps(observation),flush=True)
 if 'failed to initialize in-process app-server' in observation['harness_message']:
  raise SystemExit('nested launch unavailable; remaining live tests not run')
PY

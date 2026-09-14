#!/bin/sh
# Isolated install; rerun refreshes copied skills and auth, never the live home.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../../../.." && pwd)
export CODEX_HOME="$HOME/.local/share/skills-v2-pilot/codex/home"
export PYTHONDONTWRITEBYTECODE=1
if [ "${1:-}" = "--prepare-negative" ]; then
  [ "$#" -eq 3 ] || exit 2
  exec python3 "$HERE/prepare-negative.py" "$2" "$3"
fi
[ "$#" -eq 0 ] || exit 2
mkdir -p "$CODEX_HOME"
python3 - "$ROOT" "$CODEX_HOME" <<'PY'
import json, os, re, shutil, sys
from pathlib import Path
root, home = map(Path, sys.argv[1:])
source = Path.home()/'.codex'
lines=[l for l in (source/'config.toml').read_text().splitlines() if re.match(r'^(model|model_reasoning_effort|sandbox_mode)\s*=',l)]
if len(lines)!=3: raise SystemExit('expected exactly model, effort, sandbox lines')
(home/'config.toml').write_text('\n'.join(lines)+'\napproval_policy = "never"\nweb_search = "disabled"\n')
if not (source/'auth.json').is_file(): raise SystemExit('missing ~/.codex/auth.json')
fd=os.open(str(home/'auth.json'),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'wb') as f: f.write((source/'auth.json').read_bytes())
os.chmod(home/'auth.json',0o600)
# The base executor has only the plugin entry for each pilot skill.
for name in ['recheck-v2','delivery-probe','manual-only-probe']:
 dst=home/'skills'/name
 if dst.is_symlink(): dst.unlink()
 elif dst.exists(): shutil.rmtree(dst)
# The probes have no marketplace entry; stage their unchanged packages in an isolated local marketplace.
market=home.parent/'probe-marketplace'; (market/'.claude-plugin').mkdir(parents=True,exist_ok=True)
plugins=[]
for name in ['delivery-probe','manual-only-probe']:
 dst=market/'plugins'/name
 if dst.exists():shutil.rmtree(dst)
 shutil.copytree(root/'plugins/recheck-v2/setups/_fixtures'/name,dst)
 plugins.append({'name':name,'source':'./plugins/'+name})
(market/'.claude-plugin/marketplace.json').write_text(json.dumps({'name':'recheck-probes','owner':{'name':'pilot'},'plugins':plugins}))
print(json.dumps({'home':str(home),'host_skills':[],'auth_mode':oct((home/'auth.json').stat().st_mode & 0o777)}))
PY
failed=0
codex --version
codex plugin marketplace add "$ROOT" --json || failed=1
codex plugin add recheck-v2@tony-skills --json || failed=1
codex plugin marketplace add "$CODEX_HOME/../probe-marketplace" --json || failed=1
codex plugin add delivery-probe@recheck-probes --json || failed=1
codex plugin add manual-only-probe@recheck-probes --json || failed=1
[ "$failed" -eq 0 ] || exit "$failed"
python3 - "$ROOT" "$CODEX_HOME" <<'PY2'
import json, os, shutil, sys
from pathlib import Path
root,home=map(Path,sys.argv[1:])
for surface in ['plugin-only','host-only']:
 dst=home.parent/'homes'/surface
 # Refresh installation assets only: preserve retained sessions and auth never leaves this home tree.
 dst.mkdir(parents=True,exist_ok=True)
 for folder in ['plugins','skills']:
  target=dst/folder
  if target.exists():shutil.rmtree(target)
  if (home/folder).exists():shutil.copytree(home/folder,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copyfile(home/'config.toml',dst/'config.toml')
 fd=os.open(str(dst/'auth.json'),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 os.chmod(dst/'auth.json',0o600)
 with os.fdopen(fd,'wb') as auth:auth.write((home/'auth.json').read_bytes())
 # Rewrite absolute plugin cache paths in copied state, never credentials or session records.
 for f in [dst/'config.toml']+list((dst/'plugins').rglob('*.json')):
  f.write_text(f.read_text().replace(str(home),str(dst)))
 if surface=='host-only':
  cfg=dst/'config.toml';cfg.write_text(cfg.read_text().replace('enabled = true','enabled = false'))
  for name in ['recheck-v2','delivery-probe','manual-only-probe']:
   src=root/'plugins/recheck-v2/skills/recheck-v2' if name=='recheck-v2' else root/'plugins/recheck-v2/setups/_fixtures'/name/'skills'/name
   shutil.copytree(src,dst/'skills'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 print(json.dumps({'surface':surface,'home':str(dst)}))
PY2

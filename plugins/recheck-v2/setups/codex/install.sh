#!/bin/sh
# Isolated install; rerun refreshes copied skills and auth, never the live home.
#
# Usage: install.sh [--without recheck-v2]
#        install.sh --prepare-negative <a> <b>
#
# --without recheck-v2 skips the one step that installs the recheck-v2 skill (the plugin
# `codex plugin add` and the host-only surface's copy of the skill folder), so the home this
# install builds never held it on any surface (E10-3, authorized by ruling E10-56(1)).
# Everything else is identical.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../../../.." && pwd)
export CODEX_HOME="$HOME/.local/share/skills-v2-pilot/codex/home"
export PYTHONDONTWRITEBYTECODE=1
if [ "${1:-}" = "--prepare-negative" ]; then
  [ "$#" -eq 3 ] || exit 2
  exec python3 "$HERE/prepare-negative.py" "$2" "$3"
fi
WITHOUT=""
if [ "$#" -eq 2 ] && [ "$1" = "--without" ]; then
  [ "$2" = "recheck-v2" ] || { echo "install.sh: --without takes recheck-v2 (E10-56(1))" >&2; exit 2; }
  WITHOUT="recheck-v2"; shift 2
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
# E10-30: Codex's stable shell_snapshot feature runs the user's interactive shell once and
# injects its environment (~/.zshrc exports included) into every tool shell, so an allowlisted
# launch still carried OPENROUTER_API_KEY into the executor's and the verifier's shells
# (measured 2026-09-15 on 0.154.0, probe-env on all three Codex homes). Off in both configs.
base_config='\n'.join(lines)+'\napproval_policy = "never"\nweb_search = "disabled"\n\n[features]\nshell_snapshot = false\n'
child=home/'child';child.mkdir(exist_ok=True)
(child/'config.toml').write_text(base_config)
(home/'config.toml').write_text(base_config+'\n[shell_environment_policy.set]\nCODEX_HOME = '+json.dumps(str(child))+'\nUV_CACHE_DIR = '+json.dumps(str(child/'uv-cache'))+'\n')
if not (source/'auth.json').is_file(): raise SystemExit('missing ~/.codex/auth.json')
fd=os.open(str(home/'auth.json'),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'wb') as f: f.write((source/'auth.json').read_bytes())
os.chmod(home/'auth.json',0o600)
# E9-26(c): replace retained comparison/trial copies without reading credentials.
for auth in list((home.parent/'homes').rglob('auth.json'))+[child/'auth.json']:
 if ('plugins','cache') in zip(auth.parts,auth.parts[1:]):continue
 if not (auth.exists() or auth.is_symlink()):continue
 auth.unlink()
 auth.symlink_to(home/'auth.json')
if not (child/'auth.json').is_symlink():(child/'auth.json').symlink_to(home/'auth.json')
(child/'uv-cache').mkdir(exist_ok=True)
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
# E10-56(1): the one install step of the skill, skipped by --without recheck-v2.
if [ "$WITHOUT" = "recheck-v2" ]; then
  echo '{"skipped":"codex plugin add recheck-v2@tony-skills","why":"--without recheck-v2 (E10-56(1))"}'
else
  codex plugin add recheck-v2@tony-skills --json || failed=1
fi
codex plugin marketplace add "$CODEX_HOME/../probe-marketplace" --json || failed=1
codex plugin add delivery-probe@recheck-probes --json || failed=1
codex plugin add manual-only-probe@recheck-probes --json || failed=1
[ "$failed" -eq 0 ] || exit "$failed"
python3 - "$ROOT" "$CODEX_HOME" "$WITHOUT" <<'PY2'
import json, os, shutil, sys
from pathlib import Path
root,home=map(Path,sys.argv[1:3]); without=sys.argv[3]
for surface in ['plugin-only','host-only']:
 dst=home.parent/'homes'/surface
 # Refresh installation assets only: preserve retained sessions and auth never leaves this home tree.
 dst.mkdir(parents=True,exist_ok=True)
 for folder in ['plugins','skills']:
  target=dst/folder
  if target.exists():shutil.rmtree(target)
  if (home/folder).exists():shutil.copytree(home/folder,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 shutil.copyfile(home/'config.toml',dst/'config.toml')
 auth=dst/'auth.json'
 if auth.exists() or auth.is_symlink():auth.unlink()
 auth.symlink_to(home/'auth.json')
 child=dst/'child';child.mkdir(exist_ok=True)
 shutil.copyfile(home/'child/config.toml',child/'config.toml')
 auth=child/'auth.json'
 if auth.exists() or auth.is_symlink():auth.unlink()
 auth.symlink_to(home/'auth.json')
 (child/'uv-cache').mkdir(exist_ok=True)
 # Rewrite absolute plugin cache paths in copied state, never credentials or session records.
 for f in [dst/'config.toml']+list((dst/'plugins').rglob('*.json')):
  f.write_text(f.read_text().replace(str(home),str(dst)))
 if surface=='host-only':
  cfg=dst/'config.toml';cfg.write_text(cfg.read_text().replace('enabled = true','enabled = false'))
  for name in ['recheck-v2','delivery-probe','manual-only-probe']:
   if name==without:continue   # E10-56(1): never copied, so the home never held it
   src=root/'plugins/recheck-v2/skills/recheck-v2' if name=='recheck-v2' else root/'plugins/recheck-v2/setups/_fixtures'/name/'skills'/name
   shutil.copytree(src,dst/'skills'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 print(json.dumps({'surface':surface,'home':str(dst),'without':[without] if without else []}))
print(json.dumps({'regular_auth_files':sum(p.is_file() and not p.is_symlink() for p in home.parent.rglob('auth.json'))}))
PY2

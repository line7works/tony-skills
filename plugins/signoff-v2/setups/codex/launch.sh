#!/bin/sh
# One headless Codex session of this core's setup (E13 slice 3, brief 3.3 and 3.5).
#
# Adapted from plugins/recheck-v2/setups/codex/launch.sh. Byte-identical in build-v2 and
# signoff-v2; the core is this script's own plugin folder.
#
# Usage: launch.sh <prompt-file> <workspace> <out-dir> [--writable DIR]...
# The condition home is <CORE>_CODEX_HOME (BUILD_V2_CODEX_HOME or SIGNOFF_V2_CODEX_HOME), which
# install.sh built. The session runs in its OWN per-launch home, <out-dir>/codex-home, derived
# from the condition home by the session lock below (E13 pick P6, SB-14), so its rollout and its
# children's rollouts are private to this launch. The lock's lines are byte-identical to those
# in plugins/recheck-v2/setups/codex/launch.sh (a runner test holds the three copies equal).
#
# Unlike the pilot's current launch.sh, which runs behind the sealed bench's wall with Codex's
# own sandbox off, this setup keeps Codex's own sandbox: workspace-write, approvals never,
# TMPDIR and /tmp NOT writable (so <out-dir>, wherever it sits, is not writable by the tool
# shells and the executor's rollout stays unwritable to them, E9-37), --add-dir only the
# per-launch child home and each --writable root. Network stays off for both cores: signoff-v2's
# Codex adapter launches no nested reviewer since Astra's F6 (the reviewer is summoned through
# readers, which has no qualified route on Codex today, so a signoff run stops lane-unavailable).
#
# Copies to <out-dir>: events.jsonl, final.md, stderr.log, command.json, rollout.jsonl (the
# executor's own rollout, from <out-dir>/codex-home/sessions) and launch.json. Exit: the codex
# process's own status; 2 usage; 3 a directory named does not exist.
set -eu
if [ "$#" -lt 3 ]; then echo 'usage: launch.sh prompt-file workspace out-dir [--writable dir]...' >&2; exit 2; fi
PROMPT_FILE="$1"; WORKSPACE="$2"; OUT_DIR="$3"; shift 3
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
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
CORE=$(basename -- "$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)")
VAR=$(printf '%s' "$CORE" | tr 'a-z-' 'A-Z_')_CODEX_HOME
CONDITION=$(eval "printf '%s' \"\${$VAR:-}\"")
[ -n "$CONDITION" ] && [ -d "$CONDITION" ] || { echo "launch.sh: $VAR must name the installed condition home" >&2; exit 3; }
export CODEX_HOME="$CONDITION"
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$CODEX_HOME/child/uv-cache"
# shellcheck disable=SC2086
python3 - "$PROMPT_FILE" "$WORKSPACE" "$OUT_DIR" "$CORE" $WRITABLE <<'PY'
import json, os, shutil, subprocess, sys
from pathlib import Path
# >>> session lock (E13 pick P6, SB-14): one private Codex home per launch >>>
def session_lock(condition, out):
    """This launch's own CODEX_HOME, inside its own out-dir, derived from the condition home.

    Measured on codex-cli 0.155.1 (E13 slice 3): a headless launch writes its rollout under
    `$CODEX_HOME/sessions/YYYY/MM/DD/`, and no setting moves that folder but CODEX_HOME itself
    (`CODEX_SQLITE_HOME` moves only the state databases; `--ephemeral` keeps no rollout, and the
    adapters read theirs). Codex's own sandbox refuses no read, and Codex rewrites
    `$CODEX_HOME/config.toml` on every launch. So the lock is a per-launch home: both config
    files copied with the child-home pointer rewritten (UV_CACHE_DIR stays the condition's warmed
    cache, which is not a session record), the credential LINKED to the condition's (one file,
    never copied), the plugin and skill folders COPIED (E9-40 derives the sessions root from the
    helper's resolved path, so a link would send the adapters back to the shared home), and a
    private child home for the tool shells and the verifier children. Every session this launch
    starts is then under <out>/codex-home; a sibling launch's folder is another trial's record,
    which the bench's wall refuses and the runner's read-boundary preflight proves.
    """
    import re, shutil
    mine = out / 'codex-home'
    if mine.exists() or mine.is_symlink():
        raise SystemExit('the per-launch home ' + str(mine) + ' already exists; a launch home is never reused')
    mine.mkdir()
    for folder in ('plugins', 'skills'):
        if (condition / folder).is_dir():
            shutil.copytree(str(condition / folder), str(mine / folder),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for path in (list((mine / 'plugins').rglob('*.json')) if (mine / 'plugins').is_dir() else []):
        path.write_text(path.read_text().replace(str(condition), str(mine)))
    child = mine / 'child'
    child.mkdir()
    pointer = re.compile(r'^CODEX_HOME = .*$', re.M)
    for source, target in ((condition / 'config.toml', mine / 'config.toml'),
                           (condition / 'child' / 'config.toml', child / 'config.toml')):
        if source.is_file():
            target.write_text(pointer.sub(lambda _m: 'CODEX_HOME = ' + json.dumps(str(child)),
                                          source.read_text()))
    credential = condition / 'auth.json'
    if credential.exists() or credential.is_symlink():
        for link in (mine / 'auth.json', child / 'auth.json'):
            link.symlink_to(credential)
    return mine
# <<< session lock <<<
prompt,ws,out=map(lambda x:Path(x).resolve(),sys.argv[1:4])
core=sys.argv[4]
writable=[Path(x).resolve() for x in sys.argv[5:]]
spent=[n for n in ['events.jsonl','launch.json','final.md','rollout.jsonl','stderr.log','codex-home'] if (out/n).exists()]
if spent:raise SystemExit('out-dir already holds '+', '.join(spent)+'; refusing to overwrite a live session')
out.mkdir(parents=True,exist_ok=True)
condition=Path(os.environ['CODEX_HOME']).resolve()
home=session_lock(condition,out)
env=dict(os.environ,CODEX_HOME=str(home))
cmd=['codex','exec','--json','-o',str(out/'final.md'),'-C',str(ws),'--add-dir',str(home/'child')]
for extra in writable:cmd+=['--add-dir',str(extra)]
cmd+=['-s','workspace-write','-c','approval_policy=never',
      '-c','sandbox_workspace_write.exclude_tmpdir_env_var=true',
      '-c','sandbox_workspace_write.exclude_slash_tmp=true']
cmd+=['-']
(out/'command.json').write_text(json.dumps(cmd))
with prompt.open('rb') as inp,(out/'events.jsonl').open('wb') as events,(out/'stderr.log').open('wb') as err:
 code=subprocess.run(cmd,stdin=inp,stdout=events,stderr=err,env=env).returncode
thread=None
for line in (out/'events.jsonl').read_text().splitlines():
 try:d=json.loads(line)
 except ValueError:continue
 if d.get('type')=='thread.started':thread=d.get('thread_id')
records=list((home/'sessions').rglob('rollout-*'+thread+'.jsonl')) if thread else []
if len(records)==1:shutil.copyfile(str(records[0]),str(out/'rollout.jsonl'))
summary={'exit':code,'thread_id':thread,'rollout':str(out/'rollout.jsonl') if len(records)==1 else None,
         'codex_home':str(home),'condition_home':str(condition),'session_lock':'per-launch home (E13 P6, SB-14)',
         'codex_version':subprocess.run(['codex','--version'],stdout=subprocess.PIPE).stdout.decode().strip()}
(out/'launch.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
sys.exit(code)
PY

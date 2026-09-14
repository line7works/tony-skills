#!/bin/sh
# Each mutation is confined to a separate copy of the isolated home.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
python3 - "$HERE" "${1:?usage: negative-tests.sh scratch-output-directory}" <<'PY'
import json, os, shutil, subprocess, sys
from pathlib import Path
here,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);base=Path.home()/'.local/share/skills-v2-pilot/codex/home'
if out.exists():raise SystemExit('output already exists; retained trials are never overwritten')
out.mkdir(parents=True)
names=['malformed-sidecar','missing-sidecar','missing-name','broken-delimiter','duplicate-name','missing-resource','symlink-file','symlink-directory','update-copy-symlink-copy']
for name in names:
 trial=out/name;home=trial/'home';shutil.copytree(base,home,ignore=shutil.ignore_patterns('sessions','logs','*.log','tmp'))
 # Test the host loader without a duplicate plugin masking the mutation.
 config=home/'config.toml';config.write_text(config.read_text().replace('enabled = true','enabled = false'))
 skill=home/'skills/manual-only-probe';body=skill/'SKILL.md';side=skill/'agents/openai.yaml'
 if name=='malformed-sidecar':side.write_text('interface:\n  display_name: [not, a, string]\npolicy:\n  allow_implicit_invocation: false\n')
 elif name=='missing-sidecar':side.unlink()
 elif name=='missing-name':body.write_text('\n'.join(l for l in body.read_text().splitlines() if not l.startswith('name:'))+'\n')
 elif name=='broken-delimiter':body.write_text('broken\n'+body.read_text())
 elif name=='duplicate-name':shutil.copytree(skill,home/'skills/duplicate-probe')
 elif name=='missing-resource':(home/'skills/recheck-v2/references/verifier.md').unlink()
 elif name=='symlink-file':
  saved=trial/'saved-body.md';shutil.copyfile(body,saved);body.unlink();body.symlink_to(saved)
 elif name=='symlink-directory':
  saved=trial/'saved-skill';shutil.move(str(skill),saved);skill.symlink_to(saved,target_is_directory=True)
 if name=='update-copy-symlink-copy':
  market=trial/'update-market';(market/'.claude-plugin').mkdir(parents=True)
  source=market/'plugins/manual-only-probe';(source/'skills').mkdir(parents=True)
  shutil.copytree(skill,source/'skills/manual-only-probe')
  (source/'.claude-plugin').mkdir()
  manifest=source/'.claude-plugin/plugin.json'
  manifest.write_text(json.dumps({'name':'manual-only-probe','version':'0.1.0'}))
  (market/'.claude-plugin/marketplace.json').write_text(json.dumps({'name':'update-probe','owner':{'name':'pilot'},'plugins':[{'name':'manual-only-probe','source':'./plugins/manual-only-probe'}]}))
  cli_env=dict(os.environ,CODEX_HOME=str(home));updates=[]
  add=subprocess.run(['codex','plugin','marketplace','add',str(market),'--json'],env=cli_env,capture_output=True,text=True)
  updates.append({'stage':'marketplace','exit':add.returncode,'stdout':add.stdout,'stderr':add.stderr})
  original=source/'skills/manual-only-probe/SKILL.md'
  for stage,version in [('copy','0.1.0'),('symlink','0.1.1'),('copy-again','0.1.2')]:
   if stage=='symlink':
    target=source/'saved-body.md';target.write_text(original.read_text()+'\nUpdated probe body.\n');original.unlink();original.symlink_to(target)
   elif stage=='copy-again':
    data=original.read_bytes();original.unlink();original.write_bytes(data)
   manifest.write_text(json.dumps({'name':'manual-only-probe','version':version}))
   install=subprocess.run(['codex','plugin','add','manual-only-probe@update-probe','--json'],env=cli_env,capture_output=True,text=True)
   candidates=list((home/'plugins/cache/update-probe/manual-only-probe').glob('*/skills/manual-only-probe'))
   diffs=[]
   for installed in candidates:
    diff=subprocess.run(['diff','-r',str(source/'skills/manual-only-probe'),str(installed)],capture_output=True,text=True)
    diffs.append({'path':str(installed),'diff_exit':diff.returncode,'diff':diff.stdout,'skill_file_symlink':(installed/'SKILL.md').is_symlink()})
   updates.append({'stage':stage,'version':version,'exit':install.returncode,'stdout':install.stdout,'stderr':install.stderr,'diffs':diffs})
  (trial/'update-install.json').write_text(json.dumps(updates))
 prompt=trial/'prompt.md';prompt.write_text('Use the manual-only-probe skill explicitly and report what you can load. Read recheck-v2 references/verifier.md relative to its installed skill root. Do not use web, MCP, agents or other skills.\n')
 env=dict(os.environ,RECHECK_CODEX_HOME=str(home))
 c=subprocess.run([str(here/'launch.sh'),str(prompt),str(trial),str(trial/'capture')],env=env,capture_output=True,text=True)
 observation={'test':name,'exit':c.returncode,'capture':str(trial/'capture'),'harness_message':(trial/'capture/stderr.log').read_text() if (trial/'capture/stderr.log').exists() else c.stderr,'classification':'crashed' if c.returncode else 'requires trace inspection: enforced / prevented activation / ignored'}
 if name=='update-copy-symlink-copy':observation['update_install']=str(trial/'update-install.json')
 print(json.dumps(observation),flush=True)
 if 'failed to initialize in-process app-server' in observation['harness_message']:
  raise SystemExit('nested launch unavailable; remaining live tests not run')
PY

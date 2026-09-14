"""Private install.sh implementation: prepare one isolated negative home, no model call."""
import json, os, shutil, subprocess, sys
from pathlib import Path
name=sys.argv[1];trial=Path(sys.argv[2]).resolve()
names=['malformed-sidecar','missing-sidecar','missing-name','broken-delimiter','duplicate-name','missing-resource','symlink-file','symlink-directory','update-copy-symlink-copy']
if name not in names:raise SystemExit('unknown negative test')
base=Path.home()/'.local/share/skills-v2-pilot/codex/homes/host-only'
home=base.parent/'negative'/trial.parent.name/name
if home.exists():raise SystemExit('negative home exists; use a fresh output directory')
home.mkdir(parents=True)
for folder in ['skills','plugins']:
 if (base/folder).exists():shutil.copytree(base/folder,home/folder)
shutil.copyfile(base/'config.toml',home/'config.toml')
credential=base.parent.parent/'home/auth.json'
(home/'auth.json').symlink_to(credential)
child=home/'child';child.mkdir()
shutil.copyfile(base/'child/config.toml',child/'config.toml')
(child/'auth.json').symlink_to(credential)
(child/'uv-cache').mkdir()
for f in [home/'config.toml']+list((home/'plugins').rglob('*.json')):
 f.write_text(f.read_text().replace(str(base),str(home)))
probe='delivery-probe' if name in ['missing-name','broken-delimiter','duplicate-name','symlink-file','symlink-directory'] else 'manual-only-probe'
skill=home/'skills'/probe;body=skill/'SKILL.md';side=skill/'agents/openai.yaml'
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
 shutil.rmtree(home/'skills/manual-only-probe')
print(json.dumps({'home':str(home),'test':name}))

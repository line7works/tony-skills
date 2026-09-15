#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
python3 - "$HERE" <<'PY'
import json, os, re, subprocess, sys
from pathlib import Path
here=Path(sys.argv[1]);canonical=here.parent.parent/'skills/recheck-v2'
home=Path(os.environ.get('RECHECK_CODEX_HOME',str(Path.home()/'.local/share/skills-v2-pilot/codex/home')))
plugins=list((home/'plugins/cache/tony-skills/recheck-v2').glob('*/skills/recheck-v2/SKILL.md'))
results=[]
for surface,skill in [('plugin',p.parent) for p in plugins]+([('host skill',home/'skills/recheck-v2')] if (home/'skills/recheck-v2').exists() else []):
 root=skill.parent.parent if surface=='plugin' else skill
 row={'surface':surface,'path':str(skill)}
 if not (skill/'SKILL.md').is_file():row['error']='missing installed SKILL.md';results.append(row);continue
 diff=subprocess.run(['diff','-r','--exclude=__pycache__',str(canonical if surface=='host skill' else canonical.parent.parent),str(root)],capture_output=True,text=True)
 row['diff_exit']=diff.returncode;row['diff']=diff.stdout
 def front(p):
  s=p.read_text();return s.split('---',2)[1] if s.startswith('---\n') else None
 row['frontmatter_equal']=front(skill/'SKILL.md')==front(canonical/'SKILL.md')
 errors=[];checked=[];other_lanes=[]
 for doc in [skill/'SKILL.md',skill/'adapters/README.md']+list((skill/'references').glob('*.md')):
  text=doc.read_text()
  links=[(x,doc.parent) for x in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)]
  # The body and adapter index use inline-code resource references.
  links += [(x, doc.parent if x.startswith(('claude-code/','codex/','opencode/')) else skill) for x in re.findall(r'`((?:references|adapters|scripts|claude-code|codex|opencode)/[^` <>]*\.(?:md|json|py))`',text)]
  for link,base in links:
   if '://' in link or link.startswith('#'):continue
   target=(base/link.split('#')[0]).resolve();checked.append(str(target))
   if target!=root.resolve() and root.resolve() not in target.parents:errors.append('outside boundary: '+link)
   elif not target.exists():
    rel=target.relative_to(skill.resolve()) if skill.resolve() in target.parents else None
    if rel and rel.parts[:2] in [('adapters','claude-code'),('adapters','opencode')] and not (canonical/'adapters'/rel.parts[1]).exists():
     other_lanes.append(str(rel)+": absent in this lane's worktree (other lane)")
    else:errors.append('missing: '+str(target))
 row['other_lane_references']=sorted(set(other_lanes))
 row['references_checked']=len(checked);row['reference_errors']=sorted(set(errors))
 identities=[]
 for src in [canonical,skill]:
  c=subprocess.run(['uv','run',str(src/'scripts/recheck.py'),'skill-identity'],capture_output=True,text=True)
  identities.append({'exit':c.returncode,'stdout':c.stdout.strip(),'stderr':c.stderr.strip()})
 row['identities']=identities;row['identity_equal']=identities[0]['exit']==identities[1]['exit']==0 and json.loads(identities[0]['stdout'])['content_sha256']==json.loads(identities[1]['stdout'])['content_sha256'] and diff.returncode==0 and not diff.stdout
 results.append(row)
if not plugins:results.insert(0,{'surface':'plugin','error':'missing installed plugin under '+str(home/'plugins/cache/tony-skills/recheck-v2')})
ok=all(r.get('diff_exit')==0 and r.get('frontmatter_equal') and not r.get('reference_errors') and r.get('identity_equal') for r in results)
print(json.dumps({'ok':ok,'surfaces':results}));sys.exit(0 if ok else 1)
PY

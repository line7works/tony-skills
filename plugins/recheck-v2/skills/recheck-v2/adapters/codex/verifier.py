#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
from turns import Missing, parser, read_records, run


def status(code, raw, timed_out=False):
    if timed_out:return 'timed-out'
    if code!=0:return 'transport-failed'
    return 'ok' if raw.is_file() and raw.read_text(errors='replace').strip() else 'empty'


def metadata(events):
    model=None;injected=[]
    def message_text(content):
        return content if isinstance(content,str) else '\n'.join(x.get('text','') for x in content if isinstance(x,dict))
    # User response messages without a corresponding native UserMessage are
    # harness delivery, not attributable grants (E9-22/E9-26(e)).
    user_texts={message_text(e.get('payload',{}).get('item',{}).get('content',[]))
                for e in events if e.get('type')=='event_msg'
                and e.get('payload',{}).get('type')=='item_completed'
                and e.get('payload',{}).get('item',{}).get('type')=='UserMessage'}
    for event in events:
        if event.get('type') in ['turn_context','session_meta']:
            model=event.get('payload',event).get('model',model)
        if event.get('type')=='world_state':
            # Preserve declared source paths, never infer injection from file existence.
            def walk(value):
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k in ['path','file_path'] and isinstance(v,str):injected.append(v)
                        else:walk(v)
                elif isinstance(value,list):
                    for v in value:walk(v)
            walk(event.get('payload',{}))
        if event.get('type')=='world_state':
            state=event.get('payload',{}).get('state',{})
            injected.extend('world_state.'+k for k,v in state.items() if v)
        if event.get('type')=='session_meta' and event.get('payload',{}).get('base_instructions'):
            injected.append('session_meta.base_instructions')
        if event.get('type')=='response_item':
            payload=event.get('payload',{})
            role=payload.get('role');text=message_text(payload.get('content',[]))
            if payload.get('type')=='message' and (role=='developer' or (role=='user' and text not in user_texts)):
                tags=re.findall(r'<([a-z_]+)(?:\s[^>]*)?>',text)
                injected.extend(role+'.'+x for x in tags)
    return model,sorted(set(injected))


def child_records(events, home):
    """CLI JSON identifies the child; actual model and injected state live in its rollout."""
    threads={e['thread_id'] for e in events if e.get('type')=='thread.started' and e.get('thread_id')}
    if len(threads)!=1:raise Missing('absent or ambiguous child thread.started record')
    thread=next(iter(threads))
    if not re.fullmatch(r'[A-Za-z0-9-]+',thread):raise ValueError('invalid child thread id')
    paths=list((home/'sessions').rglob('rollout-*'+thread+'.jsonl'))
    if len(paths)!=1:raise Missing('absent or ambiguous child rollout for '+thread)
    records=read_records(paths[0])
    metas=[r.get('payload',{}) for r in records if r.get('type')=='session_meta']
    if len(metas)!=1 or metas[0].get('id')!=thread:raise ValueError('child rollout thread mismatch')
    return records


def main():
    p=parser('Launch one fresh codex exec with the brief on stdin under the executor sandbox (no second seatbelt, E9-21), no model/effort override. Timeout 900 seconds; never retries.')
    for arg in ['brief','workspace','scratch','raw']:p.add_argument('--'+arg,required=True)
    p.add_argument('--call-id',default='verify')
    a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9._-]+',a.call_id):p.error('invalid call-id')
    brief,ws,scratch,raw=[Path(getattr(a,k)).resolve() for k in ['brief','workspace','scratch','raw']]
    canned=os.environ.get('RECHECK_ADAPTER_CANNED')
    if canned and os.environ.get('RECHECK_ADAPTER_TEST')!='1':raise ValueError('canned response outside test')
    if not brief.is_file():raise Missing('absent brief record: '+str(brief))
    if brief != scratch.parent/'checklist.md':p.error('brief must be <run_dir>/checklist.md, the file start wrote')
    if not ws.is_dir():raise Missing('absent workspace: '+str(ws))
    if scratch==ws or ws in scratch.parents:raise ValueError('scratch must be outside workspace')
    if scratch not in raw.parents:raise ValueError('raw must be inside scratch')
    if raw.exists():raise ValueError('raw already exists; call ids are single-use')
    if not canned and not shutil.which('codex'):raise Missing('missing binary: codex')
    if not canned:
        home=os.environ.get('CODEX_HOME')
        if not home or not Path(home).is_dir():raise Missing('CODEX_HOME is not set or not a directory; inherited isolated child home required (E9-25); nothing launched')
        if os.environ.get('CODEX_SANDBOX')!='seatbelt':raise Missing('CODEX_SANDBOX=seatbelt required by E9-26(a); nothing launched')
    scratch.mkdir(parents=True,exist_ok=True);raw.parent.mkdir(parents=True,exist_ok=True)
    events=scratch/(a.call_id+'.events.jsonl');err=scratch/(a.call_id+'.stderr.log')
    if events.exists():raise ValueError('call capture already exists')
    timed=False
    if canned:
        source=Path(canned)
        for required in ['transport.json','events.jsonl']:
            if not (source/required).is_file():raise Missing('absent canned record: '+str(source/required))
        fixture=json.loads((source/'transport.json').read_text());code=fixture['exit'];timed=fixture.get('timed_out',False)
        shutil.copyfile(source/'events.jsonl',events)
        if (source/'raw.md').exists():shutil.copyfile(source/'raw.md',raw)
        err.write_text(fixture.get('stderr',''))
    else:
        # E9-21: no second seatbelt (it cannot nest); the executor's own sandbox confines this child.
        command=['codex','exec','-s','danger-full-access','-c','approval_policy=never','-C',str(ws),'-c','web_search=disabled','--json','-o',str(raw),'-']
        with brief.open('rb') as inp,events.open('wb') as out,err.open('wb') as errors:
            try:code=subprocess.run(command,stdin=inp,stdout=out,stderr=errors,timeout=900).returncode
            except subprocess.TimeoutExpired:code=-1;timed=True
    result=status(code,raw,timed);records=read_records(events);note=err.read_text(errors='replace')[-2000:]
    if not canned:
        # Inherit CODEX_HOME, never set it in a command or replace the environment.
        try:
            records=child_records(records,Path(home).resolve())
            (scratch/(a.call_id+'.rollout.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in records))
        except (Missing,ValueError) as exc:
            if result=='ok':result='lane-unavailable'
            note=str(exc)+'; '+note
    model,injected=metadata(records)
    if result=='ok' and model is None:
        result='lane-unavailable';note='events stream supplies no actual model; cannot report verifier capability (section 13)'
    return dict(status=result,raw=str(raw) if raw.exists() else None,model=model,kind='codex exec',injected=injected,refused=[],note=note)


if __name__=='__main__':sys.exit(run(main))

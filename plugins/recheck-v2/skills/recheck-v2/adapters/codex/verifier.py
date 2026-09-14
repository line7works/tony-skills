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
    return 'ok' if raw.is_file() and raw.stat().st_size else 'empty'


def metadata(events):
    model=None;injected=[]
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
    return model,sorted(set(injected))


def main():
    p=parser('Launch one fresh codex exec with the brief on stdin, read-only, no model/effort override. Timeout 900 seconds; never retries.')
    for arg in ['brief','workspace','scratch','raw']:p.add_argument('--'+arg,required=True)
    p.add_argument('--call-id',default='verify')
    a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9._-]+',a.call_id):p.error('invalid call-id')
    brief,ws,scratch,raw=[Path(getattr(a,k)).resolve() for k in ['brief','workspace','scratch','raw']]
    canned=os.environ.get('RECHECK_ADAPTER_CANNED')
    if canned and os.environ.get('RECHECK_ADAPTER_TEST')!='1':raise ValueError('canned response outside test')
    if not brief.is_file():raise Missing('absent brief record: '+str(brief))
    if not ws.is_dir():raise Missing('absent workspace: '+str(ws))
    if scratch==ws or ws in scratch.parents:raise ValueError('scratch must be outside workspace')
    if scratch not in raw.parents:raise ValueError('raw must be inside scratch')
    if raw.exists():raise ValueError('raw already exists; call ids are single-use')
    if not canned and not shutil.which('codex'):raise Missing('missing binary: codex')
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
        command=['codex','exec','-s','read-only','-C',str(ws),'-c','web_search=disabled','--json','-o',str(raw),'-']
        with brief.open('rb') as inp,events.open('wb') as out,err.open('wb') as errors:
            try:code=subprocess.run(command,stdin=inp,stdout=out,stderr=errors,timeout=900).returncode
            except subprocess.TimeoutExpired:code=-1;timed=True
    result=status(code,raw,timed);model,injected=metadata(read_records(events));note=err.read_text(errors='replace')[-2000:]
    if result=='ok' and model is None:
        result='lane-unavailable';note='events stream supplies no actual model; cannot report verifier capability (section 13)'
    return dict(status=result,raw=str(raw) if raw.exists() else None,model=model,kind='codex exec',injected=injected,refused=[],note=note)


if __name__=='__main__':sys.exit(run(main))

#!/usr/bin/env python3
import datetime
import os
from pathlib import Path
import re
import sys
from turns import Missing, attribution, facts, locate, parser, read_records, run


def model_facts(meta,ctx):
    name=ctx.get('model')
    if not name:raise Missing('absent model in turn_context')
    model={'id':name,'floor_class':'opus' if name=='gpt-6-astra' else 'unknown','floor_met':True if name=='gpt-6-astra' else None}
    if meta.get('model_provider'):model['provider_route']=meta['model_provider']
    if isinstance(meta.get('context_window'),int):model['context_tokens']=meta['context_window']
    effort=ctx.get('effort') or ctx.get('collaboration_mode',{}).get('settings',{}).get('reasoning_effort')
    if effort:model['effort']=effort
    model['settings']={k:v for k,v in ctx.items() if k in ['approval_policy','personality'] and isinstance(v,(str,bool,int,float))}
    return model


def main():
    p=parser('Read invocation facts from the running isolated Codex rollout; mint a path without creating it.')
    p.add_argument('--workspace',default=os.getcwd());p.add_argument('--target-token',default='a');p.add_argument('--session-wrote-fix',action='store_true');p.add_argument('--run-date',default=datetime.date.today().isoformat());p.add_argument('--caller');p.add_argument('--run-id');p.add_argument('--run-dir')
    a=p.parse_args()
    try:date=datetime.date.fromisoformat(a.run_date)
    except ValueError:p.error('run-date must be a calendar YYYY-MM-DD')
    if not re.fullmatch('[A-Za-z0-9_-]+',a.target_token):p.error('invalid target token')
    if any([a.caller,a.run_id,a.run_dir]) and not all([a.caller,a.run_id,a.run_dir]):p.error('caller, run-id and run-dir are required together')
    ws=Path(a.workspace).resolve();records=read_records(locate(ws));meta,ctx=facts(records)
    if Path(meta.get('cwd','')).resolve()!=ws:raise ValueError('rollout cwd differs from workspace')
    mapping=attribution(records)
    rid=a.run_id or 'recheck-{}-{}-{}'.format(a.target_token.lower(),date.strftime('%Y%m%d'),os.urandom(2).hex())
    rd=Path(a.run_dir).resolve() if a.run_dir else Path(os.environ.get('TMPDIR','/tmp')).resolve()/'recheck-v2'/rid
    if ws==rd or ws in rd.parents:raise ValueError('run_dir must be outside workspace')
    if not a.caller and rd.exists():raise ValueError('run directory already exists; retry minting')
    sandbox=ctx.get('sandbox_policy',{}).get('type')
    if not sandbox or not meta.get('cli_version'):raise Missing('absent sandbox or cli_version')
    # The installed helper location is the installation surface, not a model-supplied flag.
    entry='plugin' if '/plugins/cache/' in str(Path(__file__).resolve()) else 'host skill' if '/skills/recheck-v2/' in str(Path(__file__).resolve()) and '/home/skills/' in str(Path(__file__).resolve()) else 'explicit path'
    return dict(run_id=rid,run_dir=str(rd),harness=dict(name='codex-cli',version=meta['cli_version'],entry=entry,sandbox=sandbox),model=model_facts(meta,ctx),run_date=a.run_date,session_wrote_fix=a.session_wrote_fix,turn_attribution=mapping)


if __name__=='__main__':sys.exit(run(main))

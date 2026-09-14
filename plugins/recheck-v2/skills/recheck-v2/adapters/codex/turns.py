#!/usr/bin/env python3
"""Harness record reader. No writes and no model calls."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


class Missing(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def print_help(self, file=None):
        print(json.dumps({'help': self.format_help()}), file=file or sys.stdout)


def parser(description):
    return Parser(description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                  epilog='Example: python3 %(prog)s --workspace /tmp/project. Side effects: none except verifier.py, which creates scratch captures and launches one child; failures may leave captures. Exit 0 success, 2 usage, 3 missing record/binary, 1 other.')


def read_records(path):
    try:
        with path.open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]
    except FileNotFoundError:
        raise Missing('absent harness record: '+str(path))


def locate(workspace):
    home=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.local/share/skills-v2-pilot/codex/home'))).resolve()
    override=os.environ.get('RECHECK_ADAPTER_RECORD')
    if override:
        if os.environ.get('RECHECK_ADAPTER_TEST')!='1':
            raise ValueError('record override outside test')
        return Path(override).resolve()
    # Walk shell ancestors; lsof ties the record to a process rather than a cwd race.
    pid=os.getppid()
    for _ in range(6):
        try:
            out=subprocess.run(['lsof','-p',str(pid),'-Fn'],capture_output=True,text=True).stdout
        except FileNotFoundError:
            raise Missing('missing binary: lsof')
        paths=[]
        for line in out.splitlines():
            if line.startswith('n') and '/sessions/' in line and '/rollout-' in line and line.endswith('.jsonl'):
                p=Path(line[1:]).resolve()
                if home in p.parents: paths.append(p)
        if len(set(paths))==1:return paths[0]
        if len(set(paths))>1:raise ValueError('ambiguous open rollout files')
        try:
            parent=subprocess.run(['ps','-o','ppid=','-p',str(pid)],capture_output=True,text=True)
            pid=int(parent.stdout.strip())
        except (ValueError,OSError):break
        if pid<=1:break
    # Candidate c is deliberately not an automatic fallback: concurrent sessions collide.
    raise Missing('absent harness record: no isolated rollout open on ancestor process; notify/newest-cwd not qualified')


def facts(records):
    meta={};context={}
    for record in records:
        if record.get('type')=='session_meta':meta=record.get('payload',{})
        if record.get('type')=='turn_context':context=record.get('payload',{})
    if not meta or not context:raise Missing('absent session_meta or turn_context record')
    return meta,context


def attribution(records, find=None):
    meta,_=facts(records); thread=meta.get('id'); roles={};matches=[]
    for record in records:
        if record.get('type')!='event_msg':continue
        p=record.get('payload',{});i=p.get('item',{})
        if p.get('type')!='item_completed' or p.get('isSidechain') or i.get('isSidechain'):continue
        role={'UserMessage':'user','AgentMessage':'assistant'}.get(i.get('type'))
        if role is None:continue
        tid=p.get('turn_id');th=p.get('thread_id',thread)
        if not tid or not th:raise Missing('absent item_completed thread_id/turn_id')
        if th!=thread:continue
        ref='codex:thread {}:turn {}'.format(th,tid)
        if ref in roles and roles[ref]!=role:
            raise ValueError('turn_ref collision: {} identifies both user and assistant; section 8 cannot authenticate grants'.format(ref))
        roles[ref]=role
        content=i.get('content',[])
        text=content if isinstance(content,str) else '\n'.join(x.get('text','') for x in content if isinstance(x,dict))
        if find is not None and role=='user' and find in text:matches.append(ref)
    if not roles:raise Missing('absent attributable item_completed messages')
    return sorted(set(matches)) if find is not None else roles


def run(main):
    try:
        print(json.dumps(main(),ensure_ascii=False));return 0
    except Missing as e:
        print(str(e),file=sys.stderr);print(json.dumps({'error':str(e)}));return 3
    except Exception as e:
        print(str(e),file=sys.stderr);print(json.dumps({'error':str(e)}));return 1


def main():
    p=parser('Read native thread/turn roles; mixed-role references fail closed.');p.add_argument('--workspace',default=os.getcwd());p.add_argument('--find');p.add_argument('--json',action='store_true',help='JSON is always emitted')
    a=p.parse_args();return attribution(read_records(locate(Path(a.workspace).resolve())),a.find)


if __name__=='__main__':sys.exit(run(main))

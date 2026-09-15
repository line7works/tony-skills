#!/usr/bin/env python3
"""Harness record reader. No writes and no model calls."""
import argparse
import json
import os
import re
from pathlib import Path
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


def installed_home():
    """E9-40: the resolved helper path, never environment, selects the home."""
    helper=Path(__file__).resolve()
    for ancestor in helper.parents:
        if ancestor.name=='cache' and ancestor.parent.name=='plugins':
            return ancestor.parent.parent
    for ancestor in helper.parents:
        if ancestor.name=='recheck-v2' and ancestor.parent.name=='skills':
            home=ancestor.parent.parent
            # A source plugin's skills/ is packaging, not a host-skill install.
            if home.parent.name!='plugins':return home
    return None


def locate(workspace):
    home_root=installed_home()
    if home_root is None:
        override=os.environ.get('RECHECK_ADAPTER_RECORD')
        if os.environ.get('RECHECK_ADAPTER_TEST')=='1' and override:
            return Path(override).resolve()
        raise Missing('absent harness record: helper outside an installed location: '+str(Path(__file__).resolve())+' (E9-40)')
    root=home_root/'sessions'
    # Installed helpers ignore both test overrides entirely (E9-40).
    thread=os.environ.get('CODEX_THREAD_ID','').strip()
    if not thread:raise Missing('absent harness record: no CODEX_THREAD_ID under '+str(root)+' (E9-31/E9-40)')
    if not re.fullmatch(r'[A-Za-z0-9-]+',thread):raise ValueError('invalid CODEX_THREAD_ID')
    home=Path(os.environ['CODEX_HOME']).expanduser() if os.environ.get('CODEX_HOME') else None
    resolved_home=home.resolve() if home is not None else None
    def outside_home(path):
        resolved=path.resolve()
        if resolved_home is not None and (resolved==resolved_home or resolved_home in resolved.parents):
            raise Missing('refused executor rollout path under CODEX_HOME: '+str(resolved)+' (E9-36)')
        return resolved
    root=outside_home(root)
    found=set()
    if root.is_dir():
        for path in root.rglob('rollout-*'+thread+'.jsonl'):
            resolved=outside_home(path)
            try:
                open(resolved,'ab').close()
            except PermissionError:
                found.add(resolved)
            except OSError as error:
                raise Missing('executor rollout append check failed: '+str(resolved)+': '+str(error)+' (E9-37)')
            else:
                raise Missing('writable executor rollout refused: '+str(resolved)+' (E9-37)')
    if len(found)==1:return next(iter(found))
    if len(found)>1:raise Missing('ambiguous executor rollout for thread '+thread+' under '+str(root))
    raise Missing('absent harness record: no rollout named by CODEX_THREAD_ID '+thread+' under '+str(root)+'; paths under CODEX_HOME '+str(resolved_home)+' are refused (E9-31/E9-36)')


def facts(records):
    meta={};context={}
    for record in records:
        if record.get('type')=='session_meta':meta=record.get('payload',{})
        if record.get('type')=='turn_context':context=record.get('payload',{})
    if not meta or not context:raise Missing('absent session_meta or turn_context record')
    return meta,context


def validate_ref(ref):
    if not re.fullmatch(r'codex:thread [^\s:]+:turn [^\s:]+:item [^\s:]+',ref):
        raise ValueError('invalid turn_ref: thread, turn and item segments required (E9-15)')
    return ref


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
        item_id=i.get('id')
        if not item_id:raise Missing('absent item_completed item id; item segment is required (E9-15)')
        ref=validate_ref('codex:thread {}:turn {}:item {}'.format(th,tid,item_id))
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
    p=parser('Read native thread/turn/item roles; missing item ids fail closed.');p.add_argument('--workspace',default=os.getcwd());p.add_argument('--find');p.add_argument('--json',action='store_true',help='JSON is always emitted')
    a=p.parse_args()
    if a.find is not None and not a.find:p.error('--find must not be empty')
    return attribution(read_records(locate(Path(a.workspace).resolve())),a.find)


if __name__=='__main__':sys.exit(run(main))

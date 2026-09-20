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


# SB-2 / A3 of the sealed bench: the witness for "this session is confined", shared by every
# helper in this folder rather than copied into each. `verifier.py` imports it from here.
# E9-26(a) accepts `CODEX_SANDBOX=seatbelt`, Codex's own marker. On the sealed bench Codex's own
# sandbox is OFF (macOS refuses a second seatbelt inside the first, E9-21) and the confinement is
# the launcher's `sandbox-exec` wall. A launcher's word is not a witness, so the marker is
# accepted only when a read the wall must refuse actually IS refused: the launcher plants
# `RECHECK_WALL_PROBE` outside every root the profile allows, and this attempts it. A read that
# SUCCEEDS, or fails for any other reason, is not a wall.
WALL_MARKER='sandbox-exec'


def wall_refuses(path):
    """True only when reading `path` raises PermissionError: the wall is there and refusing."""
    if not path:return False,'RECHECK_WALL_PROBE names no path'
    try:
        with open(path,'rb') as handle:handle.read(1)
    except PermissionError as exc:return True,'the probe read was refused: '+str(exc)
    except OSError as exc:return False,'the probe read failed for another reason: '+str(exc)
    return False,'the probe read SUCCEEDED, so no wall refused it'


def applied_sandbox():
    """Does the OPERATING SYSTEM say a sandbox policy is applied to this process? (SB-12, N4)

    `sandbox_check(pid, NULL, 0)` in libsystem answers for the process itself: it returns
    non-zero only inside a seatbelt. Measured on this Mac (macOS 26.6.2, 2026-09-19): 0 in a
    plain process, 1 inside `/usr/bin/sandbox-exec -f <profile>`; both measurements are made
    again by `tests/test_sb_fix_round.py`, with no model.

    Returns `(True, why)`, `(False, why)`, or `(None, why)` when ctypes or the symbol is
    unavailable - and UNKNOWN IS NOT CONFINED: `wall_witness` fails on None, because a
    witness that cannot be taken is not a witness that passed.
    """
    try:
        import ctypes,ctypes.util
    except ImportError as exc:return None,'ctypes is unavailable here: '+str(exc)
    try:
        library=ctypes.CDLL(ctypes.util.find_library('System') or '/usr/lib/libSystem.B.dylib')
        check=library.sandbox_check
    except (OSError,AttributeError) as exc:
        return None,'sandbox_check is unavailable in libsystem here: '+str(exc)
    check.restype=ctypes.c_int
    check.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint64]
    try:value=check(os.getpid(),None,0)
    except Exception as exc:                                   # noqa: BLE001 - reported
        return None,'sandbox_check could not be called: '+str(exc)
    return bool(value),'sandbox_check(getpid(), NULL, 0) = '+str(value)


def wall_witness():
    """The THREE halves of SB-2 as SB-12 N4 leaves them.

    (1) the launcher declares `RECHECK_HARNESS_SANDBOX=sandbox-exec`; (2) the OPERATING
    SYSTEM reports a sandbox policy APPLIED to this process; (3) a read of the planted probe
    is refused.

    (2) is the new one, and it is what her probe took out of the old witness: an ordinary
    file at mode 000 raises PermissionError in any process on this Mac, so a declaration plus
    a chmod satisfied the wall test with no wall anywhere - and on that acceptance the
    verifier may select `codex exec -s danger-full-access`. A file's permission bits are not
    a confinement. The probe read STAYS: the applied policy says a seatbelt is on, the probe
    read says it is the bench's seatbelt and that it closes what it must.
    """
    if os.environ.get('RECHECK_HARNESS_SANDBOX')!=WALL_MARKER:
        return False,'RECHECK_HARNESS_SANDBOX does not declare '+WALL_MARKER
    applied,how=applied_sandbox()
    if applied is None:
        return False,('RECHECK_HARNESS_SANDBOX='+WALL_MARKER+' is declared and the applied '
                      'sandbox policy could not be measured, so the witness fails: '+how)
    if not applied:
        return False,('RECHECK_HARNESS_SANDBOX='+WALL_MARKER+' is declared but the OS reports '
                      'NO sandbox policy applied to this process, so a refused read is a '
                      'file mode and not a wall: '+how)
    refused,why=wall_refuses(os.environ.get('RECHECK_WALL_PROBE'))
    if not refused:return False,'RECHECK_HARNESS_SANDBOX='+WALL_MARKER+' is declared but the wall does not refuse: '+why
    return True,'a sandbox policy is applied to this process ('+how+') and '+why


# What `invocation.py` appends to `harness.sandbox` when a WRITABLE executor rollout was
# accepted, so the exception is declared in the record rather than passing silently (SB-8).
WALL_SANDBOX_NOTE=('confined by the launcher\'s '+WALL_MARKER+' wall (SB-2), which is the '
                   'sandbox here because Codex\'s own is off; the executor rollout is writable '
                   'by the session under it')


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
    """The executor's own rollout. `locate_with_note` carries what had to be declared."""
    return locate_with_note(workspace)[0]


def locate_with_note(workspace):
    """The executor rollout, and the note the record must carry when one was accepted writable.

    E9-37 requires the executor's rollout to be UNWRITABLE by the session: under Codex's own
    workspace-write sandbox the tool shells could not write the home, and a rollout this process
    can append to is a record it could also rewrite. SB-8: behind the sealed bench's wall that
    can never hold. Codex's own sandbox is off there and the confinement is ONE `sandbox-exec`
    seatbelt around the whole process tree, so Codex itself writes that rollout and every shell
    it starts inherits the same rights. Measured 2026-09-19 (root
    `wall-proof-codex-20260920T005305Z`): every walled with-skill trial stopped at
    `verifier_unavailable` before it graded anything.

    So a writable rollout is accepted in exactly one case, on the precedent batch A set in
    `verifier.py`: the SB-2 witness holds - `RECHECK_HARNESS_SANDBOX=sandbox-exec` declared AND a
    read of `RECHECK_WALL_PROBE` refused with PermissionError. Otherwise E9-37 stands, with the
    same message it has always had. The acceptance is never silent: the note goes into
    `harness.sandbox`.
    """
    home_root=installed_home()
    if home_root is None:
        override=os.environ.get('RECHECK_ADAPTER_RECORD')
        if os.environ.get('RECHECK_ADAPTER_TEST')=='1' and override:
            return Path(override).resolve(),None
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
    found=set();accepted_writable=set()
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
                # The ONE exception, and only with the witness in hand; no witness, no pass.
                witness,why=wall_witness()
                if not witness:raise Missing('writable executor rollout refused: '+str(resolved)+' (E9-37)')
                found.add(resolved);accepted_writable.add(resolved)
    if len(found)==1:
        one=next(iter(found))
        return one,(WALL_SANDBOX_NOTE if one in accepted_writable else None)
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

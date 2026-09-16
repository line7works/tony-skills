"""A7a/E9-3/E9-15 tests, with a sanitized saved CR rollout for IA qualification.
Synthetic transport cases remain labeled and make no live containment claim.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import turns
import invocation
import verifier


class AdapterTests(unittest.TestCase):
    def call(self,name,*args,**extra):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,CODEX_HOME=str(Path(tmp)/'child'),PYTHONDONTWRITEBYTECODE='1',**extra)
            return subprocess.run([sys.executable,str(ROOT/name),*args],cwd=tmp,env=env,capture_output=True,text=True)

    def test_help_json(self):
        for name in ['turns.py','invocation.py','verifier.py']:
            c=self.call(name,'--help');self.assertEqual(c.returncode,0,c.stderr)
            self.assertIn('Side effects',json.loads(c.stdout)['help'])

    def test_unknown_argument(self):
        for name in ['turns.py','invocation.py','verifier.py']:
            c=self.call(name,'--unknown');self.assertEqual(c.returncode,2);self.assertTrue(c.stderr)

    def test_missing_record(self):
        for name in ['turns.py','invocation.py']:
            c=self.call(name);self.assertEqual(c.returncode,3,c.stderr);self.assertIn('record',json.loads(c.stdout)['error'])
        c=self.call('verifier.py','--brief','/absent','--workspace','/tmp','--scratch','/tmp/v','--raw','/tmp/v/raw.md')
        self.assertEqual(c.returncode,3);json.loads(c.stdout)

    def test_floor(self):
        # E9-3 provisional mapping; unknown is never elevated.
        self.assertIs(invocation.model_facts({}, {'model':'gpt-6-astra'})['floor_met'],True)
        self.assertIsNone(invocation.model_facts({}, {'model':'other'})['floor_met'])

    def test_floor_gpt_5_6_sol(self):
        """E10-62: the campaign's Codex model is class opus with floor_met true on this lane.

        It read `unknown` / `floor_met: None` before the ruling, which would have made every
        Codex trial of the campaign `verifier_unavailable` before it graded anything.
        """
        facts=invocation.model_facts({}, {'model':'gpt-5.6-sol'})
        self.assertEqual(facts['floor_class'],'opus')
        self.assertIs(facts['floor_met'],True)
        self.assertEqual(facts['id'],'gpt-5.6-sol')

    def test_floor_unknown_is_never_elevated(self):
        """Every id outside the lane's own map stays unknown with a null floor."""
        for name in ('gpt-5.6', 'gpt-5.6-sol-mini', 'sol', 'claude-opus-5'):
            facts=invocation.model_facts({}, {'model':name})
            self.assertEqual(facts['floor_class'],'unknown',name)
            self.assertIsNone(facts['floor_met'],name)

    def test_floor_effort_rides_with_the_model(self):
        """E10-62 pins the Codex lane to medium; the effort is read, never defaulted."""
        facts=invocation.model_facts({}, {'model':'gpt-5.6-sol','effort':'medium'})
        self.assertEqual(facts['effort'],'medium')
        self.assertNotIn('effort',invocation.model_facts({}, {'model':'gpt-5.6-sol'}))

    def test_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'raw.md'
            self.assertEqual(verifier.status(0,p),'empty');p.write_text('report')
            self.assertEqual(verifier.status(0,p),'ok')
            self.assertEqual(verifier.status(1,p),'transport-failed')
            self.assertEqual(verifier.status(0,p,True),'timed-out')

    def test_canned_guard(self):
        c=self.call('verifier.py','--brief','/absent','--workspace','/tmp','--scratch','/tmp/v','--raw','/tmp/v/raw.md',RECHECK_ADAPTER_CANNED='/tmp/canned')
        self.assertEqual(c.returncode,1);self.assertIn('canned response outside test',c.stdout)

    def test_missing_item_id_fail_closed_synthetic(self):
        # Observed shape reproduced as unit input, NOT claimed to be a saved rollout.
        rows=[{'type':'session_meta','payload':{'id':'synthetic'}},{'type':'turn_context','payload':{'model':'other'}}]
        for kind in ['UserMessage','AgentMessage']:
            rows.append({'type':'event_msg','payload':{'type':'item_completed','thread_id':'synthetic','turn_id':'2','item':{'type':kind,'content':'neutral words'}}})
        with self.assertRaisesRegex(turns.Missing,'item id'):turns.attribution(rows)

    def test_find_and_exclusions_synthetic(self):
        rows=[{'type':'session_meta','payload':{'id':'synthetic'}},{'type':'turn_context','payload':{'model':'other'}}]
        for tid,kind in [('1','UserMessage'),('2','AgentMessage'),('3','ToolResult')]:
            rows.append({'type':'event_msg','payload':{'type':'item_completed','thread_id':'synthetic','turn_id':tid,'item':{'type':kind,'id':'item-'+tid,'content':'neutral words'}}})
        self.assertEqual(turns.attribution(rows,'neutral'),['codex:thread synthetic:turn 1:item item-1'])
        self.assertEqual(len(turns.attribution(rows)),2)

    def test_canned_transport_synthetic(self):
        # Synthetic transport unit inputs, not saved live evidence.
        for code,timeout,body,expected in [(0,False,'report','ok'),(0,False,'','empty'),(0,False,' \n\t','empty'),(1,False,'','transport-failed'),(-1,True,'','timed-out')]:
            with tempfile.TemporaryDirectory() as tmp:
                t=Path(tmp); canned=t/'canned';canned.mkdir();ws=t/'ws';ws.mkdir()
                (t/'checklist.md').write_text('neutral brief')
                (canned/'transport.json').write_text(json.dumps({'exit':code,'timed_out':timeout}))
                (canned/'raw.md').write_text(body)
                (canned/'events.jsonl').write_text(json.dumps({'type':'turn_context','payload':{'model':'gpt-6-astra'}})+'\n')
                env=dict(os.environ,RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_CANNED=str(canned),PYTHONDONTWRITEBYTECODE='1')
                c=subprocess.run([sys.executable,str(ROOT/'verifier.py'),'--brief',str(t/'checklist.md'),'--workspace',str(ws),'--scratch',str(t/'scratch'),'--raw',str(t/'scratch/raw.md')],cwd=tmp,env=env,capture_output=True,text=True)
                self.assertEqual(c.returncode,0,c.stderr);d=json.loads(c.stdout)
                self.assertEqual(d['status'],expected);self.assertEqual(d['model'],'gpt-6-astra');self.assertEqual(d['kind'],'codex exec')

    def test_missing_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'checklist.md').write_text('neutral');(t/'ws').mkdir()
            env=dict(os.environ,PATH='',PYTHONDONTWRITEBYTECODE='1')
            c=subprocess.run([sys.executable,str(ROOT/'verifier.py'),'--brief',str(t/'checklist.md'),'--workspace',str(t/'ws'),'--scratch',str(t/'verifier'),'--raw',str(t/'verifier/raw.md')],env=env,capture_output=True,text=True,cwd=tmp)
            self.assertEqual(c.returncode,3,c.stderr);self.assertIn('codex',c.stdout)

    def test_saved_real_probe_roles(self):
        rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
        mapping=turns.attribution(rows)
        self.assertEqual(list(mapping.values()).count('user'),1)
        self.assertEqual(list(mapping.values()).count('assistant'),2)
        user=next(k for k,v in mapping.items() if v=='user')
        self.assertEqual(turns.attribution(rows,'neutral words'),[user])
        self.assertEqual(turns.attribution(rows,'Neutral words'),[])
        self.assertEqual(turns.attribution(rows,'neutral tool result'),[])
        for ref in mapping: self.assertEqual(turns.validate_ref(ref),ref)
        with self.assertRaisesRegex(ValueError,'item segments required'):
            turns.validate_ref(user.rsplit(':item ',1)[0])
        c=self.call('turns.py','--find','neutral words',RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(ROOT/'tests/fixtures/real-rollout.jsonl'))
        self.assertEqual(c.returncode,0,c.stderr);self.assertEqual(json.loads(c.stdout),[user])

    def test_child_rollout_metadata(self):
        # Native thread.started points to a rollout, never to guessed config metadata.
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);sessions=home/'sessions';sessions.mkdir()
            rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
            thread=turns.facts(rows)[0]['id']
            rows.append({'type':'world_state','payload':{'state':{'agents_md':{},'host_skills':{'body':'neutral catalog'}}}})
            (sessions/('rollout-neutral-'+thread+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
            events=[{'type':'thread.started','thread_id':thread}]
            model,channels=verifier.metadata(verifier.child_records(events,home))
            self.assertEqual(model,'gpt-6-astra');self.assertIn('world_state.host_skills',channels)
            self.assertNotIn('world_state.agents_md',channels)
            with self.assertRaises(turns.Missing):verifier.child_records([],home)
            with self.assertRaises(turns.Missing):verifier.child_records([{'type':'thread.started','thread_id':'absent'}],home)

    def test_fabricated_user_limit(self):
        """The test-only override bypasses E9-37; fabricated copies are not live evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
            thread=turns.facts(rows)[0]['id']
            rows.append({'type':'event_msg','payload':{'type':'item_completed','thread_id':thread,'turn_id':'fabricated-turn','item':{'id':'fabricated-item','type':'UserMessage','content':'fabricated grant marker'}}})
            record=Path(tmp)/'copy.jsonl';record.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            c=self.call('turns.py','--find','fabricated grant marker',RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(record))
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(json.loads(c.stdout),['codex:thread '+thread+':turn fabricated-turn:item fabricated-item'])

    def test_no_launch_without_home_or_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'ws').mkdir();(t/'checklist.md').write_text('neutral brief')
            binary=t/'codex';binary.write_text('#!/bin/sh\nprintf launched > "'+str(t/'launched')+'"\n');binary.chmod(0o755)
            for home,marker,expected in [(None,'seatbelt','CODEX_HOME'),(str(t/'missing'),'seatbelt','CODEX_HOME'),(str(t),None,'CODEX_SANDBOX'),(str(t),'other','CODEX_SANDBOX')]:
                env=dict(os.environ,PATH=str(t),PYTHONDONTWRITEBYTECODE='1')
                for key,value in [('CODEX_HOME',home),('CODEX_SANDBOX',marker)]:
                    env.pop(key,None)
                    if value is not None:env[key]=value
                env.pop('RECHECK_ADAPTER_CANNED',None)
                c=subprocess.run([sys.executable,str(ROOT/'verifier.py'),'--brief',str(t/'checklist.md'),'--workspace',str(t/'ws'),'--scratch',str(t/'verifier'),'--raw',str(t/'verifier/raw.md')],env=env,capture_output=True,text=True)
                self.assertEqual(c.returncode,3,c.stderr);self.assertIn(expected,c.stdout)
                self.assertFalse((t/'launched').exists());self.assertFalse((t/'verifier').exists())

    def test_usage_edges(self):
        self.assertEqual(self.call('turns.py','--find','').returncode,2)
        self.assertEqual(self.call('invocation.py','--caller','ship-v2','--run-id','x y','--run-dir','/tmp/run').returncode,2)
        with tempfile.TemporaryDirectory() as tmp:
            brief=Path(tmp)/'composed.md';brief.write_text('neutral')
            c=self.call('verifier.py','--brief',str(brief),'--workspace',tmp,'--scratch',str(Path(tmp)/'verifier'),'--raw',str(Path(tmp)/'verifier/raw.md'))
            self.assertEqual(c.returncode,2,c.stderr)

    def test_worktree_location_refused(self):
        for helper in ['turns.py','invocation.py']:
            c=self.call(helper)
            self.assertEqual(c.returncode,3,c.stderr)
            self.assertIn(str(ROOT/'turns.py'),c.stderr)

    def test_invocation_originator(self):
        fixture=ROOT/'tests/fixtures/real-rollout.jsonl'
        c=self.call('invocation.py','--workspace','/tmp/neutral-workspace',RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(fixture))
        self.assertEqual(c.returncode,0,c.stderr)
        d=json.loads(c.stdout)
        self.assertEqual((d['mode'],d['caller'],d['resume']),('headless','direct',False))
        with tempfile.TemporaryDirectory() as tmp:
            rows=turns.read_records(fixture)
            for origin,expected in [('codex_cli_rs',0),('unrecognized-origin',3)]:
                rows[0]['payload']['originator']=origin
                record=Path(tmp)/'record.jsonl';record.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                c=self.call('invocation.py','--workspace','/tmp/neutral-workspace','--caller','ship-v2','--run-id','caller-run','--run-dir',str(Path(tmp)/'run'),RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(record))
                self.assertEqual(c.returncode,expected,c.stderr)
                if expected:self.assertIn(origin,c.stderr)
                else:
                    d=json.loads(c.stdout)
                    self.assertEqual((d['mode'],d['caller'],d['resume']),('interactive','ship-v2',False))

    def test_network_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
            for r in rows:
                if r['type']=='turn_context':r['payload']['sandbox_policy']['network_access']=True
            record=Path(tmp)/'record.jsonl';record.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            env=dict(os.environ,CODEX_HOME='/tmp/neutral-home',RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(record),PYTHONDONTWRITEBYTECODE='1')
            c=subprocess.run([sys.executable,str(ROOT/'invocation.py'),'--workspace','/tmp/neutral-workspace'],env=env,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(json.loads(c.stdout)['harness']['sandbox'],'workspace-write plus the isolated home, network on')

    def test_saved_child_channels(self):
        model,channels=verifier.metadata(turns.read_records(ROOT/'tests/fixtures/child-rollout.jsonl'))
        self.assertEqual(model,'gpt-6-astra')
        self.assertIn('developer.permissions',channels);self.assertIn('user.environment_context',channels)

    def test_host_injection_unmapped(self):
        rows=turns.read_records(ROOT/'tests/fixtures/host-explicit-rollout.jsonl')
        self.assertEqual(turns.attribution(rows,'neutral injected body'),[])
        self.assertEqual(list(turns.attribution(rows).values()).count('user'),1)
        c=self.call('turns.py','--find','neutral injected body',RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(ROOT/'tests/fixtures/host-explicit-rollout.jsonl'))
        self.assertEqual(c.returncode,0,c.stderr);self.assertEqual(json.loads(c.stdout),[])

    def test_saved_real_probe_and_IA_core(self):
        """IA CASES.md A1-02/A2-01 + pilot section 8/E9-1/E9-15.
        Native Codex station output is AgentMessage, hence assistant, never a fabricated
        station role. The second A2 grant uses that non-user item; forwarding still fails.
        """
        sys.path.insert(0,str(ROOT.parents[1]/'scripts/tests'))
        import testlib
        rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
        mapping=turns.attribution(rows)
        user=next(k for k,v in mapping.items() if v=='user')
        assistant=next(k for k,v in mapping.items() if v=='assistant')
        for kind in ['assistant','absent','user','caller','forwarded']:
            with tempfile.TemporaryDirectory(dir=os.environ.get('RECHECK_TEST_SCRATCH')) as tmp:
                cid='A2-01-forged-caller' if kind in ['caller','forwarded'] else 'A1-02-forged-direct-channel'
                cdir=testlib.build_case('IA-input-authorization',cid,str(Path(tmp)/'fixture'))
                def mutate(d):
                    d['invocation']['turn_attribution']=mapping
                    grants=d['authorization']['waivers']
                    grants[0]['turn_ref']=assistant if kind=='assistant' else user+ '-absent' if kind=='absent' else user
                    grants[0]['quoted_words']='neutral words'
                    if len(grants)>1:
                        grants[1]['turn_ref']=assistant
                        grants[1]['quoted_words']='neutral words'
                    if kind=='forwarded':grants[0]['forwarded_by']='ship-v2'
                inp=testlib.prepare_input(cdir,model=invocation.model_facts(*turns.facts(rows)),mutate=mutate)
                # Adapter suite stays stdlib under 3.9; the core's own uv entry supplies jsonschema.
                c=subprocess.run(['uv','run',str(ROOT.parents[1]/'scripts/recheck.py'),'start',inp],cwd=tmp,capture_output=True,text=True)
                self.assertEqual(c.returncode,0,c.stderr);d=json.loads(c.stdout)
                self.assertEqual(d['next'],'verify')
                rejected=d['rejected_grants']
                if kind=='user':self.assertEqual(rejected,[])
                elif kind=='assistant':self.assertIn('maps to assistant',rejected[0])
                elif kind=='absent':self.assertIn('E9-1',rejected[0])
                elif kind=='caller':
                    self.assertEqual(len(rejected),2)
                    self.assertTrue(any('forwarded_by' in r for r in rejected))
                    self.assertTrue(any('maps to assistant' in r for r in rejected))
                else:
                    self.assertEqual(len(rejected),1);self.assertIn('maps to assistant',rejected[0])
                cp=json.loads((Path(cdir)/'run/checkpoint.json').read_text())
                self.assertEqual(len(cp['scope']['grants']['waivers']),1 if kind in ['user','forwarded'] else 0)



class ThreadIdLocator(unittest.TestCase):
    """E9-40 installed-location tests; no harness or model is launched."""

    def setUp(self):
        import shutil
        self.tmp=tempfile.TemporaryDirectory(dir=os.environ.get('RECHECK_TEST_SCRATCH'))
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name).resolve()
        self.helpers=self.home/'plugins/cache/m/p/v/skills/recheck-v2/adapters/codex'
        self.helpers.mkdir(parents=True)
        for name in ['turns.py','invocation.py','verifier.py']:
            shutil.copyfile(ROOT/name,self.helpers/name)
        self.rows=turns.read_records(ROOT/'tests/fixtures/real-rollout.jsonl')
        self.meta=turns.facts(self.rows)[0]
        self.thread=self.meta['id']
        self.env=dict(os.environ,CODEX_HOME=str(self.home/'child'),CODEX_THREAD_ID=self.thread,PYTHONDONTWRITEBYTECODE='1')
        for key in ['RECHECK_ADAPTER_TEST','RECHECK_ADAPTER_RECORD']:
            self.env.pop(key,None)

    def record(self,root,readonly=True):
        path=root/'sessions/2026/09/14'/('rollout-executor-'+self.thread+'.jsonl')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
        if readonly:path.chmod(0o444)
        return path

    def check(self,code,contains=None,mapped=False):
        for helper in ['turns.py','invocation.py']:
            with self.subTest(helper=helper):
                c=subprocess.run([sys.executable,str(self.helpers/helper),'--workspace',self.meta['cwd']],cwd=self.home,env=self.env,capture_output=True,text=True)
                self.assertEqual(c.returncode,code,c.stderr)
                if contains:self.assertIn(str(contains),c.stderr)
                if mapped:
                    d=json.loads(c.stdout)
                    self.assertEqual(d if helper=='turns.py' else d['turn_attribution'],turns.attribution(self.rows))

    def test_thread_id_names_the_rollout(self):
        self.record(self.home);self.check(0,mapped=True)
        self.env['CODEX_THREAD_ID']='no-such-thread'
        self.check(3,self.home/'sessions')
        self.env.pop('CODEX_THREAD_ID')
        self.check(3,'no CODEX_THREAD_ID')

    def test_permitted_root_readonly_mapped(self):
        self.record(self.home);self.check(0,mapped=True)

    def test_permitted_root_writable_refused(self):
        p=self.record(self.home,False);before=p.read_bytes()
        self.check(3,'writable executor rollout refused: '+str(p))
        self.assertEqual(p.read_bytes(),before)

    def relocated(self,readonly=True,immutable=False):
        other=self.home/'elsewhere'
        p=self.record(other,readonly)
        self.env['CODEX_HOME']=str(other/'child')
        before=p.read_bytes()
        if immutable:subprocess.run(['chflags','uchg',str(p)],check=True,capture_output=True)
        try:self.check(3,self.home/'sessions')
        finally:
            if immutable:subprocess.run(['chflags','nouchg',str(p)],check=True,capture_output=True)
        self.assertEqual(p.read_bytes(),before)

    def test_relocated_root_writable_refused(self):self.relocated(False)
    def test_relocated_root_readonly_refused(self):self.relocated()
    def test_relocated_root_immutable_refused(self):self.relocated(False,True)

    def test_installed_overrides_ignored(self):
        other=self.record(self.home/'elsewhere')
        self.env.update(RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD=str(other))
        self.check(3,self.home/'sessions')
        self.record(self.home);self.check(0,mapped=True)

    def test_child_rollout_refused_executor_found(self):
        child=self.home/'child'
        forged=self.record(child)
        self.check(3,self.home/'sessions')
        sessions=self.home/'sessions';sessions.mkdir()
        link=sessions/forged.name;link.symlink_to(forged)
        self.check(3,'refused executor rollout path under CODEX_HOME: '+str(forged))
        link.unlink();self.record(self.home);self.check(0,mapped=True)

    def test_host_skill_location(self):
        import shutil
        host=self.home/'host'
        self.helpers=host/'skills/recheck-v2/adapters/codex'
        self.helpers.mkdir(parents=True)
        for name in ['turns.py','invocation.py','verifier.py']:
            shutil.copyfile(ROOT/name,self.helpers/name)
        self.record(host);self.check(0,mapped=True)
        self.env.update(RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_RECORD='/absent')
        self.check(0,mapped=True)

    def test_resolved_helper_location(self):
        link=self.home/'linked';link.symlink_to(self.helpers,target_is_directory=True)
        self.helpers=link
        self.record(self.home);self.check(0,mapped=True)


if __name__=='__main__':unittest.main()

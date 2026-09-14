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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import turns
import invocation
import verifier


class AdapterTests(unittest.TestCase):
    def call(self,name,*args,**extra):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,CODEX_HOME=tmp,PYTHONDONTWRITEBYTECODE='1',**extra)
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
        for code,timeout,body,expected in [(0,False,'report','ok'),(0,False,'','empty'),(1,False,'','transport-failed'),(-1,True,'','timed-out')]:
            with tempfile.TemporaryDirectory() as tmp:
                t=Path(tmp); canned=t/'canned';canned.mkdir();ws=t/'ws';ws.mkdir()
                (t/'brief.md').write_text('neutral brief')
                (canned/'transport.json').write_text(json.dumps({'exit':code,'timed_out':timeout}))
                (canned/'raw.md').write_text(body)
                (canned/'events.jsonl').write_text(json.dumps({'type':'turn_context','payload':{'model':'gpt-6-astra'}})+'\n')
                env=dict(os.environ,RECHECK_ADAPTER_TEST='1',RECHECK_ADAPTER_CANNED=str(canned),PYTHONDONTWRITEBYTECODE='1')
                c=subprocess.run([sys.executable,str(ROOT/'verifier.py'),'--brief',str(t/'brief.md'),'--workspace',str(ws),'--scratch',str(t/'scratch'),'--raw',str(t/'scratch/raw.md')],cwd=tmp,env=env,capture_output=True,text=True)
                self.assertEqual(c.returncode,0,c.stderr);d=json.loads(c.stdout)
                self.assertEqual(d['status'],expected);self.assertEqual(d['model'],'gpt-6-astra');self.assertEqual(d['kind'],'codex exec')

    def test_missing_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'brief.md').write_text('neutral')
            env=dict(os.environ,PATH='',PYTHONDONTWRITEBYTECODE='1')
            c=subprocess.run([sys.executable,str(ROOT/'verifier.py'),'--brief',str(t/'brief.md'),'--workspace',tmp,'--scratch',str(t.parent/(t.name+'-scratch')),'--raw',str(t.parent/(t.name+'-scratch')/'raw.md')],env=env,capture_output=True,text=True,cwd=tmp)
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


if __name__=='__main__':unittest.main()

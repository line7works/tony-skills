"""A7a and E9-3 deterministic checks. Synthetic records are not live qualification.
Real-probe IA gates require an actual probe rollout; never generate one here.
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

    def test_collision_fail_closed_synthetic(self):
        # Observed shape reproduced as unit input, NOT claimed to be a saved rollout.
        rows=[{'type':'session_meta','payload':{'id':'synthetic'}},{'type':'turn_context','payload':{'model':'other'}}]
        for kind in ['UserMessage','AgentMessage']:
            rows.append({'type':'event_msg','payload':{'type':'item_completed','thread_id':'synthetic','turn_id':'2','item':{'type':kind,'content':'neutral words'}}})
        with self.assertRaisesRegex(ValueError,'collision'):turns.attribution(rows)

    def test_find_and_exclusions_synthetic(self):
        rows=[{'type':'session_meta','payload':{'id':'synthetic'}},{'type':'turn_context','payload':{'model':'other'}}]
        for tid,kind in [('1','UserMessage'),('2','AgentMessage'),('3','ToolResult')]:
            rows.append({'type':'event_msg','payload':{'type':'item_completed','thread_id':'synthetic','turn_id':tid,'item':{'type':kind,'content':'neutral words'}}})
        self.assertEqual(turns.attribution(rows,'neutral'),['codex:thread synthetic:turn 1'])
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

    @unittest.skip('not run here: nested app-server initialization failed; no own real probe rollout exists')
    def test_saved_real_probe_and_IA_core(self):
        """IA CASES A1-02/A2-01 plus pilot section 8; needs qualified real map."""


if __name__=='__main__':unittest.main()

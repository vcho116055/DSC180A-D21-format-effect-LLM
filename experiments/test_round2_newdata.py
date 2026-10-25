"""Offline integrity checks for the new-dataset lookup plan. Never contacts a model API.

Runs every Week 4 integrity check against results/round2_newdata/cases.jsonl, checks that the saved plan
regenerates exactly from the local datasets, and exercises the spending cap with a fake client.
"""
import asyncio
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from experiments import round2_newdata as r
from experiments import test_week4_study as week4
from experiments.week4_study import MODEL, dumps, sha


class NewDataIntegrityTests(week4.ExperimentalIntegrityTests):
    @classmethod
    def setUpClass(cls):
        cls.cases=[json.loads(x) for x in (r.DIRECTORY/'cases.jsonl').read_text().splitlines()]

    def test_plan_matches_manifest_and_regenerates(self):
        manifest=json.loads((r.DIRECTORY/'manifest.json').read_text())
        self.assertEqual(sha('\n'.join(dumps(c) for c in self.cases)),manifest['plan_sha256'])
        self.assertEqual(r.build_cases(),self.cases)

    def test_design_counts(self):
        stages={}
        for c in self.cases:
            stages[c['stage']]=stages.get(c['stage'],0)+1
        self.assertEqual(stages,{'main':288,'stress':16,'synthetic':24,'repeat':12})
        self.assertEqual({c['dataset'] for c in self.cases if c['stage']=='main'},set(r.DATASETS))

    def test_dispatch_order_finishes_blocks_in_every_stratum_first(self):
        order=r.dispatch_order(self.cases)
        self.assertEqual(sorted(c['id'] for c in order),sorted(c['id'] for c in self.cases))
        first=order[:6*16]
        self.assertEqual({c['block'] for c in first},{f'{d}_{n}_b0' for d in r.DATASETS for n in (40,200)})
        self.assertEqual([c['stage'] for c in order[288:]],
                         ['repeat']*12+['synthetic']*24+['stress']*16)


class FakeClient:
    """Answers every request correctly; bills the full output cap and about four characters per input token."""
    def __init__(self,cases):
        self.expected={c['prompt']:c['expected'] for c in cases}
        self.responses=SimpleNamespace(create=self.create)

    async def create(self,input,max_output_tokens,**kwargs):
        usage=dict(input_tokens=len(input[0]['content'])//4,output_tokens=max_output_tokens)
        return SimpleNamespace(id='fake',model=MODEL,status='completed',incomplete_details=None,
                               output_text=json.dumps(self.expected[input[0]['content']]),
                               usage=SimpleNamespace(model_dump=lambda: usage))

    async def close(self):
        pass


class SpendingCapTests(unittest.TestCase):
    def setUp(self):
        self.directory=Path(tempfile.mkdtemp())
        for name in ('manifest.json','cases.jsonl'):
            shutil.copy(r.DIRECTORY/name,self.directory/name)
        self.cases=r.read_jsonl(self.directory/'cases.jsonl')

    def tearDown(self):
        shutil.rmtree(self.directory)

    def run_capped(self,budget):
        with contextlib.redirect_stdout(io.StringIO()):
            return asyncio.run(r.run(self.directory,workers=4,budget=budget,client=FakeClient(self.cases)))

    def test_cap_stops_before_limit_then_resumes_and_partial_analysis_works(self):
        status=self.run_capped(0.3)
        self.assertEqual(status['stop_reason'],'spending cap')
        self.assertLessEqual(status['spent_usd'],0.3)
        self.assertGreater(status['unsent'],0)
        records=r.read_jsonl(self.directory/'trials.jsonl')
        started=r.read_jsonl(self.directory/'started.jsonl')
        self.assertEqual({x['id'] for x in started},{x['id'] for x in records})  # nothing left half-sent
        self.assertGreaterEqual(len(status['complete_main_blocks']),2)

        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            summary=r.analyze(self.directory)
        self.assertEqual(summary['requests'],summary['planned'])  # partial analysis keeps whole blocks only
        self.assertTrue(all(len(v['block_differences'])==len(status['complete_main_blocks'])
                            for v in summary['paired_contrasts'].values()))

        first=len(records)
        status=self.run_capped(100)
        self.assertIsNone(status['stop_reason'])
        self.assertEqual(status['unsent'],0)
        records=r.read_jsonl(self.directory/'trials.jsonl')
        self.assertEqual(len(records),len(self.cases))
        self.assertEqual(len({x['id'] for x in records}),len(records))  # resuming resent nothing
        self.assertGreater(len(records),first)


if __name__=='__main__':
    unittest.main()

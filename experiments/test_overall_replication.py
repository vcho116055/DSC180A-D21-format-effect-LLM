"""Offline integrity and execution-control checks for the repeated study."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments import overall_replication as r


class ReplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {}
        rng = r.random.Random(777)
        for name, desc in r.DESCRIPTORS.items():
            field = desc[2]
            cls.data[name] = [dict(record_id=str(i+1), a=str(rng.randrange(15)), b=str(rng.randrange(8)),
                                   c=str(rng.randrange(4)), **{field:f'{i+1}.125'}) for i in range(600)]
        cls.blocks, cls.cases, cls.requests = r.build(cls.data, blocks_per_stratum=1,
                                                     breadth_blocks=1, controls=False)

    def test_truth_three_tasks_and_repeat_identity(self):
        self.assertEqual(len(self.requests), 1176)
        index = {c['id']:c for c in self.cases}
        self.assertEqual({c['task'] for c in self.cases}, set(r.TASKS))
        for c in self.cases:
            self.assertEqual(r.s.reconstruct(c),c['expected'])
        for cid,c in index.items():
            requests = [req for req in self.requests if req['case_id']==cid]
            self.assertEqual(len(requests),1 if c['stage']=='calibration' else 3)
            self.assertEqual(len({index[q['case_id']]['request_sha256'] for q in requests}),1)

    def test_only_three_output_cells_change(self):
        for block in self.blocks:
            r.validate_block(block,conjunction=block['stage']!='breadth')
        block = next(b for b in self.blocks if b['stage']=='primary')
        changed = r.empirical_block(block,self.data[block['dataset']],r.random.Random(1))
        r.validate_block(changed)
        source = {row[block['field']] for row in self.data[block['dataset']]}
        for q in changed['queries']:
            if q['position'] is not None:
                self.assertIn(changed['altered'][q['position']][block['field']],source)

    def test_native_files_and_join_payload(self):
        join = next(c for c in self.cases if c['task']=='join' and c['delivery']=='file')
        self.assertEqual(len(join['assets']),2)
        ids = {a['path']:f'file-{i}' for i,a in enumerate(join['assets'])}
        payload = r.payload(join,ids)
        self.assertEqual(payload['reasoning'],{'effort':'medium'})
        self.assertEqual(payload['tools'],[])
        self.assertFalse(payload['store'])
        self.assertEqual(sum(x['type']=='input_file' for x in payload['input'][0]['content']),2)
        self.assertNotIn('expected',json.dumps(payload))
        for asset in join['assets']:
            self.assertEqual(r.w.sha(asset['content']),asset['sha256'])

    def test_strict_grading_and_value_reversion(self):
        c = next(c for c in self.cases if c['version']=='altered')
        self.assertTrue(r.grade(c,r.w.dumps(c['expected']),'completed')['strict_correct'])
        wrong = dict(c['expected'])
        key = next(iter(c['original_values']))
        wrong[key] = c['original_values'][key]
        g = r.grade(c,r.w.dumps(wrong),'completed')
        self.assertFalse(g['strict_correct'])
        self.assertTrue(any(x['original_value_reversion'] for x in g['items']))
        extra = dict(c['expected'],extra='1')
        self.assertFalse(r.grade(c,r.w.dumps(extra),'completed')['strict_correct'])

    def test_full_context_reservation_covers_usage(self):
        for inputs in (1,272000,272001,1050000):
            usage = dict(input_tokens=inputs,output_tokens=r.OUTPUT_CAP)
            self.assertLessEqual(r.usage_cost(usage,True),r.FULL_CONTEXT_RESERVATION)

    def test_runner_gate_and_no_duplicate_dispatch_on_resume(self):
        # Exercise real orchestration with a fake client; no network or credentials.
        calibration = [q for q in self.requests if q['stage']=='calibration']
        main = next(q for q in self.requests if q['stage']=='primary')
        requests = calibration + [main]
        cases = {c['id']:c for c in self.cases if c['id'] in {q['case_id'] for q in requests}}
        for bad_gate,expected_calls in ((False,25),(True,24)):
            with self.subTest(bad_gate=bad_gate), TemporaryDirectory() as temp:
                directory = Path(temp)
                manifest = dict(planned=len(requests),budget_usd=50)
                r.save(directory/'manifest.json',manifest)
                for c in cases.values():
                    for a in c['assets']:
                        path=directory/a['path']; path.parent.mkdir(parents=True,exist_ok=True)
                        path.write_bytes(a['content'].encode())
                calls=[]
                lookup={c['request_text']:c for c in cases.values()}
                async def create_response(**body):
                    self.assertEqual(body['reasoning'],{'effort':'medium'})
                    c=lookup[body['input'][0]['content'][0]['text']]
                    calls.append(c['id'])
                    answer={} if bad_gate and len(calls)==1 else c['expected']
                    return SimpleNamespace(id=f'resp-{len(calls)}',model=r.w.MODEL,status='completed',
                        output_text=r.w.dumps(answer),usage=SimpleNamespace(model_dump=lambda:dict(input_tokens=10,output_tokens=10)),
                        reasoning=SimpleNamespace(model_dump=lambda:dict(effort='medium')),incomplete_details=None)
                async def upload(**kwargs):
                    return SimpleNamespace(id=f'file-{len(calls)}')
                async def delete(file_id):
                    return SimpleNamespace(deleted=True)
                async def close():
                    pass
                client=SimpleNamespace(responses=SimpleNamespace(create=create_response),
                    files=SimpleNamespace(create=upload,delete=delete),close=close)
                with patch.object(r,'verify',return_value=(manifest,cases,requests)), patch(
                    'dotenv.dotenv_values',return_value=dict(OPENAI_MODEL=r.w.MODEL,OPENAI_REASONING_EFFORT='medium')):
                    asyncio.run(r.run(directory,workers=1,client=client))
                    self.assertEqual(len(calls),expected_calls)
                    asyncio.run(r.run(directory,workers=1,client=client))
                    self.assertEqual(len(calls),expected_calls)
                    # An unpaired start must block every further dispatch.
                    r.append(directory/'started.jsonl',dict(id='ambiguous'))
                    with self.assertRaises(RuntimeError):
                        asyncio.run(r.run(directory,workers=1,client=client))


if __name__=='__main__':
    unittest.main()

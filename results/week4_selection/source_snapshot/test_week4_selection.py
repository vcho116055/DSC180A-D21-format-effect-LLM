"""Integrity tests of frozen Round 4 stimuli; no API requests."""
import json
from collections import defaultdict
from decimal import Decimal
import unittest

from experiments.week4_selection import (
    DIRECTORY, SYSTEM, read_cases, decode_tables, reconstruct,
    matching, evaluate, numeric_equal, sha,
)


class SelectionIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibration=read_cases('calibration')
        cls.main=read_cases('main')
        cls.cases=cls.calibration+cls.main

    def test_every_payload_has_unique_selectors_and_correct_answers(self):
        for c in self.cases:
            self.assertEqual(reconstruct(c),c['expected'])
            rows, values=decode_tables(c)
            self.assertEqual(len(rows),c['n_rows'])
            if c['task']=='direct':
                self.assertNotIn('999999',{r['record_id'] for r in rows})
                continue
            for q in c['queries']:
                result=matching(rows,q['criteria'])
                self.assertEqual(len(result),int(q['position'] is not None))
                for k,v in q['criteria'].items():
                    self.assertTrue(any(r[k]==v for r in rows))
                if result:
                    for drop in q['criteria']:
                        partial={k:v for k,v in q['criteria'].items() if k!=drop}
                        self.assertGreaterEqual(len(matching(rows,partial)),2)

    def test_formats_cues_and_tasks_preserve_logical_data(self):
        reference={}
        for c in self.cases:
            rows, values=decode_tables(c)
            if values is not None:
                index={r['link_id']:r[c['field']] for r in values}
                rows=[dict(r,**{c['field']:index[r['link_id']]}) for r in rows]
            key=(c['stage']=='calibration',c['block'],c['version'])
            if key in reference:
                self.assertEqual(rows,reference[key])
            reference[key]=rows

    def test_exactly_three_cells_change_and_old_values_are_absent(self):
        grouped=defaultdict(dict)
        for c in self.main:
            if c['task']=='attribute' and c['cue']=='neutral' and c['format']=='csv' and c['stage'] in ('primary','synthetic'):
                grouped[c['block']][c['version']]=c
        self.assertEqual(len(grouped),16)
        for versions in grouped.values():
            a,b=versions['original'],versions['altered']
            ra,_=decode_tables(a); rb,_=decode_tables(b)
            diffs=[(i,k) for i,(x,y) in enumerate(zip(ra,rb)) for k in x if x[k]!=y[k]]
            self.assertEqual(len(diffs),3)
            self.assertEqual({k for i,k in diffs},{a['field']})
            self.assertEqual({i for i,k in diffs},{q['position'] for q in a['queries'] if q['position'] is not None})
            actual={Decimal(r[a['field']]) for r in rb}
            self.assertTrue(all(Decimal(v) not in actual for v in a['original_values'].values()))

    def test_calibration_is_separate_and_repeats_are_exact(self):
        calibration={c['prompt'] for c in self.calibration}
        self.assertFalse(calibration & {c['prompt'] for c in self.main})
        primary={c['prompt'] for c in self.main if c['stage']=='primary'}
        repeats=[c for c in self.main if c['stage']=='repeat']
        self.assertEqual(len(repeats),24)
        self.assertTrue(all(c['prompt'] in primary for c in repeats))
        self.assertEqual(len({c['id'] for c in self.cases}),552)

    def test_strict_scoring_and_original_value_taxonomy(self):
        c=next(c for c in self.main if c['stage']=='primary' and c['version']=='altered')
        output=json.dumps(c['expected'])
        self.assertTrue(evaluate(c,output,'completed')['strict_correct'])
        self.assertFalse(evaluate(c,output,'incomplete')['strict_correct'])
        extra=dict(c['expected'],unexpected='x')
        self.assertTrue(evaluate(c,json.dumps(extra),'completed')['all_correct'])
        self.assertFalse(evaluate(c,json.dumps(extra),'completed')['strict_correct'])
        prior=dict(c['expected']);prior.update(c['original_values'])
        result=evaluate(c,json.dumps(prior),'completed')
        self.assertEqual(sum(i['original_value_reversion'] for i in result['items']),3)
        self.assertFalse(evaluate(c,'not json','completed')['strict_correct'])
        self.assertFalse(numeric_equal(True,'1'))

    def test_manifest_and_archived_sources(self):
        manifest=json.loads((DIRECTORY/'manifest.json').read_text())
        self.assertEqual(manifest['system_sha256'],sha(SYSTEM))
        self.assertLess(manifest['reservation_upper_bound_usd'],manifest['budget_usd'])
        for archived in (DIRECTORY/'source_snapshot').iterdir():
            original=(DIRECTORY.parents[1]/'requirements-experiments.txt' if archived.name=='requirements-experiments.txt'
                      else DIRECTORY.parents[1]/'experiments'/archived.name)
            self.assertEqual(archived.read_bytes(),original.read_bytes())


if __name__=='__main__':
    unittest.main()

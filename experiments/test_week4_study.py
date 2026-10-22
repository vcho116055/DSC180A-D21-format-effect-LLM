"""Offline integrity checks. Never contacts a model API."""
import json
from pathlib import Path
import unittest
from decimal import Decimal

from experiments.week4_study import deserialize, numeric_equal, score

ROOT=Path(__file__).resolve().parents[1]


class ExperimentalIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=[json.loads(x) for x in
                   (ROOT/'results/week4_lookup/cases.jsonl').read_text().splitlines()]

    def test_every_serialized_payload_has_correct_targets(self):
        for case in self.cases:
            if case['stage'] not in ('main','stress','synthetic','repeat'):
                continue
            rows=deserialize(case['prompt'].split('TABLE:\n',1)[1],case['format'])
            index={r['record_id']:r for r in rows}
            self.assertEqual(len(rows),case['n_rows'])
            for q in case['queries']:
                value=index[q['record_id']][q['field']] if q['record_id'] in index else 'NOT_FOUND'
                self.assertEqual(value,case['expected'][q['record_id']])

    def test_formats_and_name_cues_preserve_identical_tables(self):
        reference={}
        for case in self.cases:
            if case['stage'] not in ('main','stress','synthetic','repeat'):
                continue
            key=(case['block'],case['version'])
            rows=deserialize(case['prompt'].split('TABLE:\n',1)[1],case['format'])
            if key in reference:
                self.assertEqual(rows,reference[key])
            reference[key]=rows

    def test_replaced_original_values_are_absent_from_altered_table(self):
        for case in self.cases:
            if case.get('version')!='altered':
                continue
            rows=deserialize(case['prompt'].split('TABLE:\n',1)[1],case['format'])
            for q in case['queries']:
                if q['position'] is None:
                    continue
                original=Decimal(case['original_values'][q['record_id']])
                self.assertTrue(all(Decimal(r[q['field']])!=original for r in rows))

    def test_only_three_cells_change(self):
        by_id={c['id']:c for c in self.cases}
        for c in self.cases:
            if c['stage']!='main' or c['version']!='original':
                continue
            other=by_id[c['id'].replace('_original_','_altered_')]
            a=deserialize(c['prompt'].split('TABLE:\n',1)[1],c['format'])
            b=deserialize(other['prompt'].split('TABLE:\n',1)[1],other['format'])
            differences=[(i,k) for i,(x,y) in enumerate(zip(a,b)) for k in x if x[k]!=y[k]]
            self.assertEqual(len(differences),3)
            self.assertEqual({i for i,k in differences},
                             {q['position'] for q in c['queries'] if q['position'] is not None})

    def test_scorer_separates_correct_reversion_and_invalid(self):
        c=next(c for c in self.cases if c.get('version')=='altered')
        self.assertTrue(score(c,json.dumps(c['expected']),'completed')['all_correct'])
        self.assertFalse(score(c,json.dumps(c['expected']),'incomplete')['all_correct'])
        self.assertFalse(score(c,'```json\n{}\n```','completed')['all_correct'])
        answer=dict(c['expected']);answer.update(c['original_values'])
        result=score(c,json.dumps(answer),'completed')
        self.assertEqual(sum(i['original_value_reversion'] for i in result['items']),3)
        self.assertTrue(numeric_equal('7.25000','7.25'))
        self.assertFalse(numeric_equal(True,'1'))
        self.assertFalse(numeric_equal('7.26','7.25'))

    def test_arithmetic_ground_truth(self):
        for c in self.cases:
            if c['stage']!='arithmetic':
                continue
            rows=deserialize(c['prompt'].split('TABLE:\n',1)[1],c['format'])
            self.assertEqual(c['expected'],{'n_rows':len(rows),
                             'n_positive':sum(int(r['survived']) for r in rows)})


if __name__=='__main__':
    unittest.main()

"""Offline checks for the separate pilot's controls and spending reservation."""
import unittest

from experiments import file_input_pilot as p


class FilePilotTests(unittest.TestCase):
    def test_matched_files_and_exact_repetitions(self):
        cases = p.build()
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({c['id'] for c in cases}), 24)
        for fmt in p.w.FORMATS:
            group = [c for c in cases if c['format'] == fmt]
            self.assertEqual(len({c['payload'] for c in group}), 1)
            self.assertEqual(len({c['task'] for c in group}), 1)
            self.assertEqual(len({p.w.dumps(c['expected']) for c in group}), 1)
            rows = p.w.deserialize(group[0]['payload'], fmt)
            self.assertEqual(len(rows), 20)
            task = group[0]['task']
            queries = p.json.loads(task.split('QUERIES:\n')[1])
            for q in queries:
                matches = [r for r in rows if all(r[k] == v for k, v in q['criteria'].items())]
                expected = matches[0]['value'] if matches else 'NOT_FOUND'
                self.assertEqual(group[0]['expected'][q['query_id']], expected)
                for key, value in q['criteria'].items():
                    self.assertGreaterEqual(sum(r[key] == value for r in rows), 2)

    def test_gate_requires_all_eight_successes(self):
        records = [dict(id=c['id'], repeat=c['repeat'], strict_correct=True) for c in p.build()[:8]]
        self.assertTrue(p.gate(records))
        self.assertFalse(p.gate(records[:-1]))
        records[-1]['strict_correct'] = False
        self.assertFalse(p.gate(records))

    def test_full_context_charge_fits_reserved_amount(self):
        for inputs in (1, 272_000, 272_001, p.CONTEXT_CAP):
            cost = p.charge(dict(input_tokens=inputs, output_tokens=p.OUTPUT_CAP))
            self.assertLessEqual(cost, p.RESERVATION)
        self.assertLess(p.RESERVATION, p.BUDGET)
        accounted = 0
        dispatched = 0
        while accounted + p.RESERVATION <= p.BUDGET:
            accounted += p.RESERVATION  # worst case / uncertain billing
            dispatched += 1
        self.assertEqual(dispatched, 1)
        self.assertLessEqual(accounted, p.BUDGET)


if __name__ == '__main__':
    unittest.main()

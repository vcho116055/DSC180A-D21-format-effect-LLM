"""Checks the direct-lookup data, error bounds, and degenerate-test handling.

Run from the repository root:
    python -m unittest analysis.direct_lookup_tests.test_direct_format_tests -v
"""
import json
import unittest

import numpy as np

from analysis.attribute_selection_tests import attribute_format_tests as aft

CONTRASTS = json.loads((aft.NOV / 'analysis.json').read_text(encoding='utf-8'))['contrasts']


class DirectLookupTests(unittest.TestCase):
    def test_tables_load_for_every_outcome(self):
        for metric in aft.METRICS:
            table = aft.table_matrix(CONTRASTS, metric, 'direct')
            self.assertEqual(table.shape, (36, 4))
            self.assertTrue((table['csv'] == 0).all())

    def test_only_two_tables_differ(self):
        # Two errors in 1,728 calls (one CSV wrong answer, one XML API failure) touch two tables.
        table = aft.table_matrix(CONTRASTS, 'strict_correct', 'direct').to_numpy()
        self.assertEqual(int((np.ptp(table, axis=1) > 1e-12).sum()), 2)

    def test_error_bounds(self):
        rows = {r['format']: r for r in aft.error_bounds('direct')}
        self.assertEqual(rows['all']['requests'], 1728)
        self.assertEqual(rows['all']['errors'], 2)
        self.assertEqual(rows['all']['completed'], 1727)
        self.assertEqual(rows['all']['completed_errors'], 1)
        self.assertEqual(rows['xml']['errors'], 1)
        self.assertEqual(rows['xml']['completed_errors'], 0)  # the XML error is an API failure
        self.assertAlmostEqual(rows['json']['upper95'], 1 - 0.05 ** (1 / 432))
        for r in rows.values():
            self.assertGreaterEqual(r['upper95'], r['errors'] / r['requests'])

    def test_no_round4_data_for_direct(self):
        nov, r4 = aft.descriptive('direct')
        self.assertIsNone(r4)
        self.assertEqual(int(nov['n'].sum()), 1728)


if __name__ == '__main__':
    unittest.main()

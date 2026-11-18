"""Checks that the join data loads as expected and the tests behave correctly on it.

Run from the repository root:
    python -m unittest analysis.two_table_join_tests.test_join_format_tests -v
"""
import json
import unittest

import numpy as np

from analysis.attribute_selection_tests import attribute_format_tests as aft
from analysis.attribute_selection_tests.classical_tests import rm_anova
from analysis.round2_format_tests.stat_tests import friedman_statistic, rm_f_statistic

CONTRASTS = json.loads((aft.NOV / 'analysis.json').read_text(encoding='utf-8'))['contrasts']


class JoinDataTests(unittest.TestCase):
    def test_tables_load_for_every_outcome(self):
        for metric in aft.METRICS:
            table = aft.table_matrix(CONTRASTS, metric, 'join')
            self.assertEqual(table.shape, (36, 4))
            self.assertEqual(list(table.columns), list(aft.FORMATS))
            self.assertTrue((table['csv'] == 0).all(), 'CSV is the per-table reference')
            self.assertEqual(table.index.nunique(), 36)

    def test_join_differs_from_attribute(self):
        join = aft.table_matrix(CONTRASTS, 'strict_correct', 'join')
        attribute = aft.table_matrix(CONTRASTS, 'strict_correct', 'attribute')
        self.assertEqual(list(join.index), list(attribute.index), 'same 36 tables')
        self.assertFalse(np.allclose(join.to_numpy(), attribute.to_numpy()))

    def test_six_strata_of_six_tables(self):
        strata = aft.strata(aft.table_matrix(CONTRASTS, 'strict_correct', 'join').index)
        self.assertEqual(sorted(set(strata)), sorted(f'{d}_{n}' for d in ('medical', 'redwine', 'titanic')
                                                     for n in ('80', '400')))
        self.assertTrue(all(strata.count(s) == 6 for s in set(strata)))

    def test_shift_invariance_of_within_table_statistics(self):
        # Anchoring CSV at 0 must not change the tests: add a different constant to every table's row.
        m = aft.table_matrix(CONTRASTS, 'strict_correct', 'join').to_numpy()
        shifted = m + np.arange(36)[:, None] * 7.0
        self.assertAlmostEqual(float(rm_f_statistic(m)), float(rm_f_statistic(shifted)))
        self.assertAlmostEqual(float(friedman_statistic(m)), float(friedman_statistic(shifted)))
        self.assertAlmostEqual(rm_anova(m)['F'], rm_anova(shifted)['F'])

    def test_descriptive_totals(self):
        nov, r4 = aft.descriptive('join')
        self.assertEqual(int(nov['n'].sum()), 1728)
        self.assertEqual(int(r4['requests'].sum()), 192)


if __name__ == '__main__':
    unittest.main()

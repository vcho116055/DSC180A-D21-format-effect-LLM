"""Checks the file-vs-inline data loading and the exact Wilcoxon test.

Run from the repository root:
    python -m unittest analysis.file_vs_inline_tests.test_file_vs_inline_tests -v
"""
import unittest

from analysis.file_vs_inline_tests import file_vs_inline_tests as fvi


class WilcoxonTests(unittest.TestCase):
    def test_all_negative_hits_the_floor(self):
        # 7 nonzero, all negative: W+ = 0, only all-negative and all-positive are as extreme.
        result = fvi.wilcoxon_exact([0, -1, -2, 0, -3, -4, -5, -6, -7, 0])
        self.assertEqual(result['W_plus'], 0.0)
        self.assertEqual(result['n_nonzero'], 7)
        self.assertAlmostEqual(result['p_value'], 2 / 2 ** 7)

    def test_known_critical_value(self):
        # n = 7, no ties: two-sided 0.05 rejects for W+ <= 2 or >= 26, i.e. |W+ - 14| >= 12.
        result = fvi.wilcoxon_exact([1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(result['center'], 14.0)
        self.assertEqual(result['critical_distance'], 12.0)

    def test_symmetric_data_is_not_significant(self):
        self.assertEqual(fvi.wilcoxon_exact([1, -1, 2, -2])['p_value'], 1.0)
        self.assertEqual(fvi.wilcoxon_exact([0, 0])['p_value'], 1.0)

    def test_ties_get_midranks(self):
        # |d| = 1, 1, 2 -> ranks 1.5, 1.5, 3; W+ counts the positive ones.
        self.assertEqual(fvi.wilcoxon_exact([1, -1, 2])['W_plus'], 4.5)


class DataTests(unittest.TestCase):
    def test_twelve_tables_and_cross_check(self):
        table, _, totals, by_format = fvi.load()  # load() asserts agreement with the sensitivity file
        self.assertEqual(len(table), 12)
        self.assertEqual(sorted(table.n_rows.unique()), [80, 400])
        self.assertEqual(totals['file']['attempts'], 864)
        self.assertEqual(len(by_format), 12)

    def test_pooled_mean_matches_totals(self):
        # Every table has 72 matched calls, so the mean table difference equals the difference in totals.
        table, _, totals, _ = fvi.load()
        expected = 100 * (totals['file']['exact_correct'] - totals['inline']['exact_correct']) / 864
        self.assertAlmostEqual(table.difference_pp.mean(), expected)


if __name__ == '__main__':
    unittest.main()

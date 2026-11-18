"""Checks for stat_tests against hand-computable values.

Run from the repository root:  python -m unittest analysis.round2_format_tests.test_stat_tests -v
"""
import unittest

import numpy as np

from analysis.round2_format_tests import stat_tests as st


class StatTests(unittest.TestCase):
    def test_holm(self):
        self.assertEqual(st.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_sign_flip_exact_floor(self):
        # 7 nonzero differences, all negative: only the two all-same-sign assignments are as extreme.
        result = st.sign_flip_test([0, 0, -1, -2, -3, -1, -1, -5, 0, -2])
        self.assertAlmostEqual(result['p_value'], 2 / 2 ** 7)
        self.assertEqual(st.sign_flip_test([0, 0, 0])['p_value'], 1.0)

    def test_sign_flip_symmetric_is_not_significant(self):
        self.assertEqual(st.sign_flip_test([1, -1, 2, -2])['p_value'], 1.0)

    def test_friedman_no_ties(self):
        # Every block ranks conditions identically: chi2 = n(k-1) = 3 * 2 = 6.
        m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)
        self.assertAlmostEqual(float(st.friedman_statistic(m)), 6.0)

    def test_friedman_tie_correction(self):
        # Block 1 has a two-way tie, so its midranks are (1.5, 1.5, 3) and the tie correction applies.
        m = np.array([[1, 1, 3], [1, 2, 3], [1, 2, 3]], dtype=float)
        ranks = np.array([[1.5, 1.5, 3], [1, 2, 3], [1, 2, 3]])
        n, k = m.shape
        r = ranks.sum(axis=0)
        expected = 12 * ((r - n * (k + 1) / 2) ** 2).sum() / (n * k * (k + 1) - (2 ** 3 - 2) / (k - 1))
        self.assertAlmostEqual(float(st.friedman_statistic(m)), expected)

    def test_rm_f_matches_hand_computation(self):
        m = np.array([[1, 2], [2, 4], [3, 3]], dtype=float)
        # Repeated-measures F = (SS_cond / df_cond) / (SS_error / df_error), computed directly.
        grand = m.mean()
        ss_cond = 3 * ((m.mean(0) - grand) ** 2).sum()
        ss_block = 2 * ((m.mean(1) - grand) ** 2).sum()
        ss_err = ((m - grand) ** 2).sum() - ss_cond - ss_block
        self.assertAlmostEqual(float(st.rm_f_statistic(m)), (ss_cond / 1) / (ss_err / 2))

    def test_clopper_pearson_upper(self):
        self.assertAlmostEqual(st.clopper_pearson_upper(0, 36), 1 - 0.05 ** (1 / 36))
        # Known value: 1 error in 10 trials, one-sided 95% upper bound = 0.3942.
        self.assertAlmostEqual(st.clopper_pearson_upper(1, 10), 0.3942, places=4)

    def test_permutation_detects_consistent_shift(self):
        rng = np.random.default_rng(1)
        m = rng.normal(size=(20, 4)) + np.array([0, 0, 0, 3])
        result = st.within_block_permutation(m, dict(F=st.rm_f_statistic), draws=2000, seed=1)
        self.assertLess(result['F']['p_value'], 0.01)


if __name__ == '__main__':
    unittest.main()

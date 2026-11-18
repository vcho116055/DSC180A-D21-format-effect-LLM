"""Checks classical_tests against standard table values.

Run from the repository root:
    python -m unittest analysis.attribute_selection_tests.test_classical_tests -v
"""
import math
import unittest

import numpy as np

from analysis.attribute_selection_tests import classical_tests as ct


class ClassicalTests(unittest.TestCase):
    def test_critical_values_match_tables(self):
        self.assertAlmostEqual(ct._invert(lambda f: ct.f_sf(f, 3, 105), 0.05), 2.6911, places=3)
        self.assertAlmostEqual(ct._invert(lambda x: ct.chi2_sf(x, 3), 0.05), 7.8147, places=3)
        self.assertAlmostEqual(ct._invert(lambda t: ct.t_two_sided_p(t, 35), 0.05, hi=1e3), 2.0301, places=3)

    def test_chi2_closed_form(self):
        # chi-square with 2 df has survival function exp(-x/2).
        for x in (0.5, 3.0, 10.0):
            self.assertAlmostEqual(ct.chi2_sf(x, 2), math.exp(-x / 2), places=10)

    def test_t_with_one_df_is_cauchy(self):
        # t(1) two-sided p = 1 - (2/pi) * arctan(|t|).
        for t in (0.5, 1.0, 4.0):
            self.assertAlmostEqual(ct.t_two_sided_p(t, 1), 1 - 2 / math.pi * math.atan(t), places=10)

    def test_f_equals_t_squared(self):
        # F(1, df) with F = t^2 gives the two-sided t p-value.
        self.assertAlmostEqual(ct.f_sf(2.5 ** 2, 1, 20), ct.t_two_sided_p(2.5, 20), places=10)

    def test_paired_t_hand_computation(self):
        d = np.array([1.0, 2.0, 3.0, 4.0])
        expected_t = d.mean() / (d.std(ddof=1) / 2)
        result = ct.paired_t(d)
        self.assertAlmostEqual(result['t'], expected_t)
        self.assertEqual(result['df'], 3)
        self.assertEqual(ct.paired_t([0.0, 0.0, 0.0])['p_value'], 1.0)

    def test_rm_anova_undefined_without_variation(self):
        self.assertIsNone(ct.rm_anova(np.ones((5, 4)))['F'])


if __name__ == '__main__':
    unittest.main()

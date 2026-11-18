"""Checks the exported November output-token data and how it is pooled.

Run from the repository root:
    python -m unittest analysis.november_token_tests.test_november_token_tests -v
"""
import unittest

import pandas as pd

from analysis.november_token_tests import november_token_tests as nt


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = nt.load()

    def test_complete_design(self):
        self.assertEqual(len(self.data), 36 * 3 * 4)
        self.assertTrue((self.data.planned_calls == 12).all())
        # Exactly one primary call was an API error.
        self.assertEqual(int((12 - self.data.completed_calls).sum()), 1)

    def test_published_input_token_ratios(self):
        # Exported input-token means must reproduce the published representation_overhead means. The published
        # file averages per input before averaging inputs, so the one cell with an API error (11 calls) weights
        # its calls slightly differently; allow a 0.1-token tolerance.
        published = pd.read_csv(nt.ROOT / 'results/november_replication/representation_overhead.csv')
        published = published[published.stage == 'primary']
        ours = self.data.groupby(['task', 'format', 'n_rows']).mean_input_tokens.mean()
        for row in published.itertuples(index=False):
            self.assertAlmostEqual(ours[(row.task, row.format, row.n_rows)], row.mean_input_tokens, delta=0.1)

    def test_pooled_value_is_equal_weight_task_mean(self):
        _, table = nt.run_all(self.data)
        block = table.index[0]
        expected = self.data[(self.data.block == block) & (self.data.format == 'csv')].output_tokens.mean()
        self.assertAlmostEqual(table.loc[block, 'csv'], expected)
        self.assertEqual(table.shape, (36, 4))


if __name__ == '__main__':
    unittest.main()

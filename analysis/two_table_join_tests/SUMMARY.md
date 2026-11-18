# Two-table join: does format affect accuracy?

Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna's (gpt-5.6-luna, medium reasoning) accuracy on the two-table join task: find the record matching several attribute values in a records table, then use its `link_id` to look up the requested value in a separate, shuffled values table.

## Data

- **November repeated study, primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x 80/400 rows x 6 tables), each run in all four formats. Each table and format has 12 calls (original/altered x named/neutral x 3 repeats), 1,728 calls in total.
- **Input:** the published per-table differences in `results/november_replication/analysis.json` (`primary/join/<metric>/<format>_minus_csv`). No raw responses or API calls.
- **Unit of analysis:** the table. Calls on the same table are averaged first, because they are not independent.
- **Only 11 of 36 tables** show any strict-accuracy difference between formats; the other tables are tied (almost always 100% in every format).

### Observed accuracy (November, all 1,728 join calls)

| Format | Strict correct | Strict % | Present values correct | Absent correct |
| --- | --- | --- | --- | --- |
| csv | 426/432 | 98.61% | 1292/1296 | 430/432 |
| json | 425/432 | 98.38% | 1290/1296 | 431/432 |
| xml | 426/432 | 98.61% | 1290/1296 | 432/432 |
| txt | 423/432 | 97.92% | 1288/1296 | 431/432 |

Round 4 (Oct 21, 48 requests per format) for context only; it has no per-table data for this task, so it is not tested: csv 48/48, json 48/48, xml 48/48, txt 46/48.

## Method

- **Significance level:** alpha = 0.05, two-sided.
- **Main hypothesis:** strict accuracy, omnibus test; present-value and absent-record accuracy are secondary. This designation was made for this analysis after earlier exploratory looks at the same data, so it is not a preregistered choice.
- **Omnibus test (main):** within-table permutation test of the repeated-measures F statistic, 100,000 permutations; critical value = 95th percentile of the permutation null. The Friedman statistic is reported alongside.
- **Classical comparison:** the same repeated-measures ANOVA with its p-value from the F distribution (F(3, 105), sphericity assumed), and the Friedman chi-square approximation (3 df). These assume normal residuals and equal variance of differences, which this data (mostly 100%, few nonzero tables) does not meet, so the permutation results are used for decisions.
- **Pairwise tests:** all 6 pairs. Paired sign-flip permutation test on per-table differences (exact when at most 20 tables differ), Holm-adjusted within each outcome; this decides. Classical paired t-test (t(35), Holm-adjusted) shown for comparison. Pairwise results are follow-ups: interpret them only if the omnibus test rejects.
- **"n/a" critical value** for a permutation test means no possible rearrangement of the data is extreme enough to reach p < 0.05: too few tables differ, so the test cannot reject whatever their values. For example, with 4 differing tables the smallest exact two-sided p is 2/2^4 = 0.125.

## Strict accuracy (whole answer correct) (main)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 11/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.14 | 2.47 | 0.9692 | Fail to reject H0 |
| Permutation Friedman chi-square | 1.42 | 7.62 | 0.7240 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.14 | 2.69 | 0.9382 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 1.42 | 7.81 | 0.7011 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 0.9692 vs 0.9382).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -0.231 | [-2.315, 1.620] | 5 / 4 / 27 | 1.0000 | 2.546 | 1.0000 | Fail to reject H0 | -0.21 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | 0.000 | [-2.552, 2.083] | 4 / 1 / 31 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 0.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | -0.694 | [-3.009, 1.389] | 4 / 4 / 28 | 0.7500 | 2.546 | 1.0000 | Fail to reject H0 | -0.55 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | 0.231 | [-2.546, 2.778] | 4 / 2 / 30 | 1.0000 | 3.009 | 1.0000 | Fail to reject H0 | 0.15 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | -0.463 | [-3.241, 2.083] | 3 / 3 / 30 | 0.8750 | 3.241 | 1.0000 | Fail to reject H0 | -0.31 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | -0.694 | [-1.852, 0.231] | 1 / 3 / 32 | 0.5000 | n/a | 1.0000 | Fail to reject H0 | -1.14 | 2.03 | 1.0000 | Fail to reject H0 |

## Present-record values correct (secondary)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 9/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.20 | 2.40 | 0.9275 | Fail to reject H0 |
| Permutation Friedman chi-square | 0.65 | 7.65 | 0.9020 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.20 | 2.69 | 0.8958 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 0.65 | 7.81 | 0.8849 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 0.9275 vs 0.8958).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -0.154 | [-0.772, 0.386] | 4 / 3 / 29 | 0.8281 | 0.772 | 1.0000 | Fail to reject H0 | -0.47 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | -0.154 | [-1.003, 0.386] | 3 / 1 / 32 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -0.37 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | -0.309 | [-1.003, 0.309] | 3 / 3 / 30 | 0.6250 | 0.772 | 1.0000 | Fail to reject H0 | -0.81 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | 0.000 | [-0.926, 0.849] | 3 / 2 / 31 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 0.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | -0.154 | [-1.080, 0.694] | 3 / 3 / 30 | 0.8750 | 1.080 | 1.0000 | Fail to reject H0 | -0.31 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | -0.154 | [-0.463, 0.154] | 1 / 2 / 33 | 0.7500 | n/a | 1.0000 | Fail to reject H0 | -0.81 | 2.03 | 1.0000 | Fail to reject H0 |

## Absent records reported as NOT_FOUND (secondary)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 2/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.49 | n/a | 1.0000 | Fail to reject H0 |
| Permutation Friedman chi-square | 1.29 | n/a | 1.0000 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.49 | 2.69 | 0.6879 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 1.29 | 7.81 | 0.7325 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 1.0000 vs 0.6879).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 0.231 | [-0.463, 1.389] | 1 / 1 / 34 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 0.44 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | 0.463 | [0.000, 1.389] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 0.231 | [-0.463, 1.389] | 1 / 1 / 34 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 0.44 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |

## Conclusion

**Main test: Fail to reject H0** (permutation repeated-measures F = 0.14, critical value 2.47, p = 0.9692; classical F(3, 105) p = 0.9382). The data do not show that format affects strict accuracy on the two-table join task. No secondary outcome rejects either, and no pairwise comparison is significant. The observed gap (TXT lowest, CSV and XML highest) rests on a small number of tables, so the tests have limited power. Failing to reject means no detectable difference, not that the formats are equivalent.

## Caveats

- Exploratory: tests chosen after data collection. Earlier exploratory runs on the same data were seen before this analysis.
- Three source datasets, overlapping source rows across tables, one model alias.
- Output tokens are not tested here; November output tokens for all three tasks are tested in `../november_token_tests/`.

## Files

- `join_format_tests.py`: runs the analysis for the join task. Run from the repository root: `python -m analysis.two_table_join_tests.join_format_tests`. The test code is shared with `../attribute_selection_tests/` (`attribute_format_tests.py`, `classical_tests.py`) and `../round2_format_tests/stat_tests.py`.
- `test_join_format_tests.py`: checks the join data loads correctly and the tests behave as expected. Run: `python -m unittest analysis.two_table_join_tests.test_join_format_tests -v`
- `results/results.json`: every number above; `results/<outcome>_by_table_format.csv`: the 36 x 4 tables tested (pp relative to CSV).

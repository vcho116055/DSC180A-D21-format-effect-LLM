# Direct lookup: does format affect accuracy?

Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna's (gpt-5.6-luna, medium reasoning) accuracy on the direct lookup task: look up the requested field for given `record_id` values and copy it, or answer NOT_FOUND.

## Data

- **November repeated study, primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x 80/400 rows x 6 tables), each run in all four formats. Each table and format has 12 calls (original/altered x named/neutral x 3 repeats), 1,728 calls in total.
- **Input:** the published per-table differences in `results/november_replication/analysis.json` (`primary/direct/<metric>/<format>_minus_csv`). No raw responses or API calls.
- **Unit of analysis:** the table. Calls on the same table are averaged first, because they are not independent.
- **Only 2 of 36 tables** show any strict-accuracy difference between formats; the other tables are tied (almost always 100% in every format).

### Observed accuracy (November, all 1,728 direct calls)

| Format | Strict correct | Strict % | Present values correct | Absent correct |
| --- | --- | --- | --- | --- |
| csv | 431/432 | 99.77% | 1295/1296 | 432/432 |
| json | 432/432 | 100.00% | 1296/1296 | 432/432 |
| xml | 431/432 | 99.77% | 1293/1296 | 431/432 |
| txt | 432/432 | 100.00% | 1296/1296 | 432/432 |

Other direct-lookup data, for context only (not tested here): the two Round 2 lookup studies (Oct 21 and Oct 25, 576 primary requests) and the November breadth stage (IBM, avocado, credit card; 1,152 requests) were 100% correct in every format. Round 2 is tested in `../round2_format_tests/`.

## Method

- **Significance level:** alpha = 0.05, two-sided.
- **Main hypothesis:** strict accuracy, omnibus test; present-value and absent-record accuracy are secondary. This designation was made for this analysis after earlier exploratory looks at the same data, so it is not a preregistered choice.
- **Omnibus test (main):** within-table permutation test of the repeated-measures F statistic, 100,000 permutations; critical value = 95th percentile of the permutation null. The Friedman statistic is reported alongside.
- **Classical comparison:** the same repeated-measures ANOVA with its p-value from the F distribution (F(3, 105), sphericity assumed), and the Friedman chi-square approximation (3 df). These assume normal residuals and equal variance of differences, which this data (mostly 100%, few nonzero tables) does not meet, so the permutation results are used for decisions.
- **Pairwise tests:** all 6 pairs. Paired sign-flip permutation test on per-table differences (exact when at most 20 tables differ), Holm-adjusted within each outcome; this decides. Classical paired t-test (t(35), Holm-adjusted) shown for comparison. Pairwise results are follow-ups: interpret them only if the omnibus test rejects.
- **"n/a" critical value** for a permutation test means no possible rearrangement of the data is extreme enough to reach p < 0.05: too few tables differ, so the test cannot reject whatever their values. For example, with 4 differing tables the smallest exact two-sided p is 2/2^4 = 0.125.

## Strict accuracy (whole answer correct) (main)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 2/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.66 | n/a | 1.0000 | Fail to reject H0 |
| Permutation Friedman chi-square | 2.00 | n/a | 1.0000 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.66 | 2.69 | 0.5782 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 2.00 | 7.81 | 0.5724 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 1.0000 vs 0.5782).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | 0.000 | [-0.463, 0.463] | 1 / 1 / 34 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 0.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |

## Present-record values correct (secondary)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 2/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.80 | n/a | 1.0000 | Fail to reject H0 |
| Permutation Friedman chi-square | 2.00 | n/a | 1.0000 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.80 | 2.69 | 0.4991 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 2.00 | 7.81 | 0.5724 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 1.0000 vs 0.4991).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 0.077 | [0.000, 0.231] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | -0.154 | [-0.617, 0.154] | 1 / 1 / 34 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -0.63 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 0.077 | [0.000, 0.231] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |

## Absent records reported as NOT_FOUND (secondary)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 1/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 1.00 | n/a | 1.0000 | Fail to reject H0 |
| Permutation Friedman chi-square | 3.00 | n/a | 1.0000 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 1.00 | 2.69 | 0.3960 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 3.00 | 7.81 | 0.3916 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 1.0000 vs 0.3960).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | 0.231 | [0.000, 0.694] | 1 / 0 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | 1.00 | 2.03 | 1.0000 | Fail to reject H0 |

## Error-rate bounds

With almost no errors, the format tests above cannot reject, so the informative result is how rare errors are. Exact one-sided 95% Clopper-Pearson upper bounds on the per-request error rate. End-to-end counts API failures as errors (as the tests above do); completed-only excludes them. These treat requests as independent, so they are optimistic: calls on the same table are related.

| Format | Errors / requests (end-to-end) | 95% upper bound | Errors / completed | 95% upper bound |
| --- | --- | --- | --- | --- |
| csv | 1/432 | 1.09% | 1/432 | 1.09% |
| json | 0/432 | 0.69% | 0/432 | 0.69% |
| xml | 1/432 | 1.09% | 0/431 | 0.69% |
| txt | 0/432 | 0.69% | 0/432 | 0.69% |
| all | 2/1728 | 0.36% | 1/1727 | 0.27% |

## Conclusion

**Main test: Fail to reject H0** (permutation repeated-measures F = 0.66, critical value n/a, p = 1.0000; classical F(3, 105) p = 0.5782). The data do not show that format affects strict accuracy on the direct lookup task. No secondary outcome rejects either, and no pairwise comparison is significant. The observed gap (CSV and XML lowest, JSON and TXT highest) rests on a small number of tables, so the tests have limited power. Failing to reject means no detectable difference, not that the formats are equivalent. Errors are rare in every format: 2/1728 requests overall (95% upper bound 0.36% per request), 1/1727 among completed responses.

## Caveats

- Exploratory: tests chosen after data collection. Earlier exploratory runs on the same data were seen before this analysis.
- Three source datasets, overlapping source rows across tables, one model alias.
- Output tokens are not tested here. November output tokens for all three tasks are tested in `../november_token_tests/`, and Round 2 output tokens in `../round2_format_tests/`.

## Files

- `direct_format_tests.py`: runs the analysis for the direct-lookup task. Run from the repository root: `python -m analysis.direct_lookup_tests.direct_format_tests`. The test code is shared with `../attribute_selection_tests/` (`attribute_format_tests.py`, `classical_tests.py`) and `../round2_format_tests/stat_tests.py`.
- `test_direct_format_tests.py`: checks the direct-lookup data and error bounds. Run: `python -m unittest analysis.direct_lookup_tests.test_direct_format_tests -v`
- `results/results.json`: every number above; `results/<outcome>_by_table_format.csv`: the 36 x 4 tables tested (pp relative to CSV).

# Multi-attribute selection: does format affect accuracy?

Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna's (gpt-5.6-luna, medium reasoning) accuracy on the multi-attribute selection task: find the single record matching several attribute values and copy its output field.

## Data

- **November repeated study, primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x 80/400 rows x 6 tables), each run in all four formats. Each table and format has 12 calls (original/altered x named/neutral x 3 repeats), 1,728 calls in total.
- **Input:** the published per-table differences in `results/november_replication/analysis.json` (`primary/attribute/<metric>/<format>_minus_csv`). No raw responses or API calls.
- **Unit of analysis:** the table. Calls on the same table are averaged first, because they are not independent.
- **Only 11 of 36 tables** show any strict-accuracy difference between formats; the other tables are tied (almost always 100% in every format).

### Observed accuracy (November, all 1,728 attribute calls)

| Format | Strict correct | Strict % | Present values correct | Absent correct |
| --- | --- | --- | --- | --- |
| csv | 413/432 | 95.60% | 1275/1296 | 432/432 |
| json | 422/432 | 97.69% | 1286/1296 | 432/432 |
| xml | 417/432 | 96.53% | 1282/1296 | 431/432 |
| txt | 426/432 | 98.61% | 1291/1296 | 431/432 |

Round 4 (Oct 21, 48 requests per format) for context only; it has no per-table data for this task, so it is not tested: csv 46/48, json 47/48, xml 47/48, txt 48/48.

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
| Permutation repeated-measures F (decides) | 0.71 | 2.49 | 0.5973 | Fail to reject H0 |
| Permutation Friedman chi-square | 1.38 | 7.73 | 0.7203 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.71 | 2.69 | 0.5497 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 1.38 | 7.81 | 0.7091 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 0.5973 vs 0.5497).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 2.083 | [-2.315, 7.176] | 3 / 2 / 31 | 0.6250 | n/a | 1.0000 | Fail to reject H0 | 0.78 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | 0.926 | [-3.935, 6.481] | 4 / 6 / 26 | 0.8438 | 6.019 | 1.0000 | Fail to reject H0 | 0.31 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 3.009 | [-1.157, 7.876] | 4 / 3 / 29 | 0.3594 | 5.324 | 1.0000 | Fail to reject H0 | 1.16 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -1.157 | [-4.630, 2.083] | 4 / 5 / 27 | 0.6250 | 3.935 | 1.0000 | Fail to reject H0 | -0.62 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.926 | [-0.231, 2.546] | 3 / 1 / 32 | 0.5000 | n/a | 1.0000 | Fail to reject H0 | 1.16 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | 2.083 | [-0.694, 5.093] | 4 / 1 / 31 | 0.2500 | n/a | 1.0000 | Fail to reject H0 | 1.27 | 2.03 | 1.0000 | Fail to reject H0 |

## Present-record values correct (secondary)

H0: format does not affect this outcome (format labels are exchangeable within each table). H1: at least one format differs.

Tables with any difference between formats: 10/36.

### Omnibus tests

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Permutation repeated-measures F (decides) | 0.83 | 2.39 | 0.5293 | Fail to reject H0 |
| Permutation Friedman chi-square | 1.89 | 7.67 | 0.6128 | Fail to reject H0 |
| Classical RM-ANOVA, F(3, 105) | 0.83 | 2.69 | 0.4823 | Fail to reject H0 |
| Classical Friedman, chi-square(3) | 1.89 | 7.81 | 0.5965 | Fail to reject H0 |

Permutation and classical RM-ANOVA agree on the decision (p = 0.5293 vs 0.4823).

### Pairwise tests

For each pair, H0: the mean per-table difference is 0. Differences are in percentage points (pp).

| Comparison | Mean diff (pp) | 95% CI (pp) | Higher / lower / tied tables | Sign-flip p | Critical abs. diff (pp) | Holm p | Decision | t | t critical | t-test Holm p | t-test decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| json minus csv | 0.849 | [-0.772, 2.855] | 3 / 2 / 31 | 0.6250 | n/a | 1.0000 | Fail to reject H0 | 0.84 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus csv | 0.540 | [-1.235, 2.623] | 4 / 5 / 27 | 0.7383 | 2.083 | 1.0000 | Fail to reject H0 | 0.49 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus csv | 1.235 | [-0.309, 3.164] | 4 / 2 / 30 | 0.3125 | 1.852 | 1.0000 | Fail to reject H0 | 1.25 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -0.309 | [-1.466, 0.772] | 4 / 4 / 28 | 0.7344 | 1.389 | 1.0000 | Fail to reject H0 | -0.50 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | 0.386 | [0.000, 0.926] | 3 / 0 / 33 | 0.2500 | n/a | 1.0000 | Fail to reject H0 | 1.54 | 2.03 | 0.8016 | Fail to reject H0 |
| txt minus xml | 0.694 | [-0.231, 1.698] | 4 / 1 / 31 | 0.2500 | n/a | 1.0000 | Fail to reject H0 | 1.27 | 2.03 | 1.0000 | Fail to reject H0 |

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
| txt minus csv | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| xml minus json | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus json | -0.231 | [-0.694, 0.000] | 0 / 1 / 35 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | -1.00 | 2.03 | 1.0000 | Fail to reject H0 |
| txt minus xml | 0.000 | [0.000, 0.000] | 0 / 0 / 36 | 1.0000 | n/a | 1.0000 | Fail to reject H0 | n/a | 2.03 | 1.0000 | Fail to reject H0 |

## Conclusion

**Main test: Fail to reject H0** (permutation repeated-measures F = 0.71, critical value 2.49, p = 0.5973; classical F(3, 105) p = 0.5497). The data do not show that format affects strict accuracy on the multi-attribute selection task. No secondary outcome rejects either, and no pairwise comparison is significant. The observed gap (CSV lowest, TXT highest) rests on a small number of tables, so the tests have limited power. Failing to reject means no detectable difference, not that the formats are equivalent.

## Caveats

- Exploratory: tests chosen after data collection. Earlier exploratory runs on the same data were seen before this analysis.
- Three source datasets, overlapping source rows across tables, one model alias.
- Output tokens are not tested here; November output tokens for all three tasks are tested in `../november_token_tests/`.

## Files

- `attribute_format_tests.py`: the analysis. Run from the repository root: `python -m analysis.attribute_selection_tests.attribute_format_tests`
- `classical_tests.py`: classical RM-ANOVA, Friedman and paired t-tests (numpy/math only). Permutation helpers are imported from `../round2_format_tests/stat_tests.py`.
- `test_classical_tests.py`: unit tests. Run: `python -m unittest analysis.attribute_selection_tests.test_classical_tests -v`
- `results/results.json`: every number above; `results/<outcome>_by_table_format.csv`: the 36 x 4 tables tested (pp relative to CSV).

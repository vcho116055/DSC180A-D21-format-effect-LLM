# Round 2 format tests: summary of results

Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects Luna (gpt-5.6-luna, medium reasoning) on the Round 2 record-lookup task. Both Round 2 studies are combined: Oct 21 (Titanic, red wine, medical) and Oct 25 (IBM, avocado, credit card), giving 36 sampled tables and 576 primary requests. Every table was run 4 times in each format (named/neutral description x original/altered values).

## Method

- **Unit of analysis:** the sampled table. Requests on the same table are averaged first, because they are not independent.
- **Significance level:** alpha = 0.05, two-sided.
- **Omnibus tests** (all four formats at once): within-table permutation test, 100,000 permutations, using a repeated-measures F statistic and a tie-corrected Friedman chi-square statistic. Critical values are the 95th percentiles of the permutation null distributions. Reject H0 when p < 0.05 (equivalently, statistic >= critical value).
- **Pairwise tests** (6 format pairs): paired sign-flip permutation test on the per-table mean difference, 200,000 Monte Carlo sign assignments. The critical value is the smallest |mean difference| that is significant at 0.05 before adjustment. Decisions use **Holm-adjusted p < 0.05** within each family of 6.
- **Per-study results** repeat the tests on each study alone (18 tables each) as a consistency check.
- **Data:** the published `results/week4_lookup/scored_requests.csv` and `results/round2_newdata/scored_requests.csv`. No API calls.

## Results at a glance

- **Accuracy:** 0/576 errors. No test can compare formats; H0 cannot be rejected. Each format's per-request error rate is at most 2.06% (95% upper bound).
- **Output tokens:** format matters (omnibus p < 0.0001). CSV produces the longest outputs (69.0 tokens on average), and JSON, XML and TXT are each significantly shorter, in both studies separately.
- **Input tokens:** not tested (fixed by serialization). Relative to CSV: json 1.71x, xml 2.59x, txt 1.86x.

## Test 1: accuracy by format

| Hypothesis | Test | Result | Decision |
| --- | --- | --- | --- |
| H0: the four formats have equal strict-correct rates. H1: at least one differs. | McNemar / chi-square / ANOVA / permutation | Not computable: 0 errors, 0 discordant pairs; any test gives p = 1 | Fail to reject H0 |

| Format | Errors / requests | 95% upper bound, per request | Tables with an error | 95% upper bound, share of tables |
| --- | --- | --- | --- | --- |
| csv | 0/144 | 2.06% | 0/36 | 7.98% |
| json | 0/144 | 2.06% | 0/36 | 7.98% |
| xml | 0/144 | 2.06% | 0/36 | 7.98% |
| txt | 0/144 | 2.06% | 0/36 | 7.98% |

Failing to reject is not evidence that the formats are equally accurate; it reflects a ceiling. The per-table bound is the more honest one, because tables are the independent unit.

## Test 2: output tokens by format

Output tokens include hidden reasoning tokens. The visible answer is roughly fixed in length, so differences mainly reflect how much the model reasoned before answering.

### Omnibus tests

H0: format labels are exchangeable within each table (format does not affect output tokens). H1: at least one format differs.

| Scope | Tables | Statistic | Observed | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| combined | 36 | Repeated-measures F | 16.54 | 2.69 | <0.0001 | **Reject H0** |
| combined | 36 | Friedman chi-square | 22.07 | 7.76 | <0.0001 | **Reject H0** |
| oct21 | 18 | Repeated-measures F | 11.82 | 2.79 | <0.0001 | **Reject H0** |
| oct21 | 18 | Friedman chi-square | 15.40 | 7.73 | 0.0009 | **Reject H0** |
| oct25 | 18 | Repeated-measures F | 5.16 | 2.74 | 0.0023 | **Reject H0** |
| oct25 | 18 | Friedman chi-square | 8.63 | 7.69 | 0.0315 | **Reject H0** |

### Pairwise tests

For each pair, H0: the mean per-table difference in output tokens is 0. H1: it is not 0.

**combined** (36 tables; mean output tokens: csv 69.0, json 58.6, xml 54.9, txt 60.5)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -10.36 | 5.18 | [-13.06, -7.58] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus csv | -14.07 | 6.28 | [-17.26, -10.94] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus csv | -8.47 | 4.90 | [-11.77, -5.12] | 0.0002 | 0.0007 | **Reject H0** |
| xml minus json | -3.71 | 3.62 | [-6.59, -0.88] | 0.0438 | 0.0876 | Fail to reject H0 |
| txt minus json | 1.89 | 4.15 | [-1.33, 5.12] | 0.3851 | 0.3851 | Fail to reject H0 |
| txt minus xml | 5.60 | 4.44 | [2.66, 8.49] | 0.0119 | 0.0357 | **Reject H0** |

**oct21** (18 tables; mean output tokens: csv 69.1, json 55.4, xml 51.2, txt 58.4)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -13.62 | 8.76 | [-18.26, -8.64] | 0.0009 | 0.0044 | **Reject H0** |
| xml minus csv | -17.86 | 10.39 | [-23.18, -12.72] | <0.0001 | 0.0005 | **Reject H0** |
| txt minus csv | -10.62 | 8.15 | [-15.75, -5.37] | 0.0059 | 0.0238 | **Reject H0** |
| xml minus json | -4.24 | 5.29 | [-8.63, -0.08] | 0.1225 | 0.2449 | Fail to reject H0 |
| txt minus json | 3.00 | 6.08 | [-1.81, 7.72] | 0.3593 | 0.3593 | Fail to reject H0 |
| txt minus xml | 7.24 | 6.40 | [4.21, 10.12] | 0.0249 | 0.0748 | Fail to reject H0 |

**oct25** (18 tables; mean output tokens: csv 68.9, json 61.8, xml 58.6, txt 62.6)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -7.10 | 5.54 | [-9.62, -4.49] | 0.0077 | 0.0384 | **Reject H0** |
| xml minus csv | -10.28 | 6.97 | [-13.90, -6.83] | 0.0003 | 0.0019 | **Reject H0** |
| txt minus csv | -6.32 | 5.29 | [-10.28, -2.15] | 0.0160 | 0.0642 | Fail to reject H0 |
| xml minus json | -3.18 | 4.51 | [-6.94, 0.43] | 0.2338 | 0.6843 | Fail to reject H0 |
| txt minus json | 0.78 | 5.53 | [-3.40, 5.32] | 0.8011 | 0.8011 | Fail to reject H0 |
| txt minus xml | 3.96 | 6.07 | [-0.99, 8.89] | 0.2281 | 0.6843 | Fail to reject H0 |

## Interpretation

- **Accuracy:** no format difference can be detected because Luna made no errors on this task. Harder tasks (Round 4, November study) are needed to compare accuracy.
- **Output tokens:** CSV leads to longer outputs than every other format, in the combined data and in each study alone. Differences among JSON, XML and TXT are smaller and not consistent across studies. Since CSV prompts are also the shortest, CSV trades fewer input tokens for more reasoning.
- The reasoning-token explanation is an inference: the reasoning/answer split is recorded only in the local Oct 25 response log and was not tested here.

## Caveats

- Exploratory: these tests were chosen after data collection, after seeing that CSV had the highest mean.
- The two studies differ in datasets, date and SDK version. Permutation is within table, so this does not bias the format tests, but study-level differences are not interpretable.
- Sampled tables overlap in source rows; one model alias was tested.

## Files

- `round2_format_tests.py`: the analysis. Run from the repository root: `python -m analysis.round2_format_tests.round2_format_tests`
- `stat_tests.py`: test functions (numpy only).
- `test_stat_tests.py`: unit tests. Run: `python -m unittest analysis.round2_format_tests.test_stat_tests -v`
- `results/`: `REPORT.md` (full report), `results.json` (all numbers), `output_tokens_by_table_format.csv` (36 x 4 table tested), `input_token_ratios.csv`.

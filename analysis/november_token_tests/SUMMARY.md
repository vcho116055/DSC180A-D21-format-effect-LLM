# November output tokens by format: summary of results

Hypothesis tests of whether input format (CSV, JSON, XML, TXT) affects how many output tokens Luna (gpt-5.6-luna, medium reasoning) produces, in the November repeated study. This is an out-of-sample check of the Round 2 result in `../round2_format_tests/`, where CSV produced the longest outputs.

## Data

- **November primary stage** (Nov 3-4): 36 sampled tables (Titanic, red wine, medical x 80/400 rows x 6), each run in all four formats for three tasks (direct lookup, attribute selection, two-table join). 12 calls per table, task and format (original/altered x named/neutral x 3 repeats).
- **Input:** `analysis/november_exports/output_tokens_by_table_task_format.csv`, per-table means exported from the local raw run (completed calls only; one API error leaves one cell with 11 calls).
- **Unit of analysis:** the table. The pooled value for a table and format is the equal-weight mean of its three task means.
- Output tokens include hidden reasoning tokens; the reasoning/answer split was not exported.

## Method

- **Significance level:** alpha = 0.05, two-sided. Same tests and code as the Round 2 analysis.
- **Omnibus:** within-table permutation test (100,000 permutations) of the repeated-measures F statistic and the tie-corrected Friedman statistic. Critical values are the 95th percentiles of the permutation null distributions.
- **Pairwise:** paired sign-flip permutation test on per-table differences for all 6 pairs (200,000 Monte Carlo sign assignments), Holm-adjusted within each scope; 95% intervals are a table bootstrap within dataset x size groups (6 tables each).
- **Main scope:** pooled over tasks. Each task alone is a consistency check.

## Results at a glance

- **Pooled:** format affects output tokens (omnibus F permutation p < 0.0001). CSV has the highest mean output tokens in every scope (pooled over tasks, direct, attribute, join).
- Formats significantly shorter than CSV (Holm p < 0.05): pooled over tasks: JSON, XML, TXT; direct: JSON, XML, TXT; attribute: JSON, XML, TXT; join: JSON, XML, TXT.
- Significant differences among JSON, XML and TXT: pooled over tasks: txt minus json; direct: txt minus xml; attribute: txt minus json, txt minus xml; join: txt minus json.

## Omnibus tests

H0: format labels are exchangeable within each table. H1: at least one format differs.

| Scope | Tables | Statistic | Observed | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| pooled over tasks | 36 | Repeated-measures F | 62.50 | 2.65 | <0.0001 | **Reject H0** |
| pooled over tasks | 36 | Friedman chi-square | 71.63 | 7.80 | <0.0001 | **Reject H0** |
| direct | 36 | Repeated-measures F | 50.28 | 2.69 | <0.0001 | **Reject H0** |
| direct | 36 | Friedman chi-square | 55.50 | 7.77 | <0.0001 | **Reject H0** |
| attribute | 36 | Repeated-measures F | 42.98 | 2.64 | <0.0001 | **Reject H0** |
| attribute | 36 | Friedman chi-square | 68.57 | 7.77 | <0.0001 | **Reject H0** |
| join | 36 | Repeated-measures F | 30.28 | 2.63 | <0.0001 | **Reject H0** |
| join | 36 | Friedman chi-square | 57.30 | 7.77 | <0.0001 | **Reject H0** |

## Pairwise tests

For each pair, H0: the mean per-table difference in output tokens is 0.

**pooled over tasks** (36 tables; mean output tokens: csv 157.4, json 133.6, xml 131.0, txt 129.4)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -23.83 | 9.88 | [-28.36, -19.58] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus csv | -26.42 | 10.26 | [-30.28, -22.95] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus csv | -28.01 | 10.89 | [-32.20, -24.16] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus json | -2.59 | 3.09 | [-5.28, 0.10] | 0.1040 | 0.2081 | Fail to reject H0 |
| txt minus json | -4.18 | 2.20 | [-5.73, -2.71] | <0.0001 | 0.0002 | **Reject H0** |
| txt minus xml | -1.59 | 2.37 | [-3.77, 0.60] | 0.1986 | 0.2081 | Fail to reject H0 |

**direct** (36 tables; mean output tokens: csv 91.9, json 79.9, xml 76.8, txt 81.0)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -12.02 | 4.67 | [-14.36, -9.67] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus csv | -15.07 | 5.80 | [-17.56, -12.56] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus csv | -10.86 | 4.01 | [-12.25, -9.46] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus json | -3.05 | 3.05 | [-5.55, -0.54] | 0.0504 | 0.1007 | Fail to reject H0 |
| txt minus json | 1.16 | 2.49 | [-1.08, 3.38] | 0.3713 | 0.3713 | Fail to reject H0 |
| txt minus xml | 4.21 | 2.48 | [2.26, 6.26] | 0.0003 | 0.0009 | **Reject H0** |

**attribute** (36 tables; mean output tokens: csv 181.2, json 147.3, xml 145.9, txt 139.6)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -33.88 | 14.62 | [-41.56, -26.80] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus csv | -35.28 | 15.99 | [-44.72, -26.71] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus csv | -41.63 | 16.77 | [-49.46, -34.59] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus json | -1.40 | 4.97 | [-5.90, 3.07] | 0.5973 | 0.5973 | Fail to reject H0 |
| txt minus json | -7.75 | 3.71 | [-10.16, -5.35] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus xml | -6.35 | 4.11 | [-9.80, -2.95] | 0.0008 | 0.0017 | **Reject H0** |

**join** (36 tables; mean output tokens: csv 199.2, json 173.6, xml 170.3, txt 167.7)

| Comparison | Mean diff (tokens) | Critical abs. mean diff (0.05, unadjusted) | 95% CI | p-value | Holm p-value | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| json minus csv | -25.58 | 12.82 | [-32.52, -18.54] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus csv | -28.90 | 12.21 | [-34.26, -23.93] | <0.0001 | <0.0001 | **Reject H0** |
| txt minus csv | -31.53 | 13.67 | [-37.15, -25.90] | <0.0001 | <0.0001 | **Reject H0** |
| xml minus json | -3.32 | 5.38 | [-8.26, 2.47] | 0.2785 | 0.5569 | Fail to reject H0 |
| txt minus json | -5.95 | 4.26 | [-9.65, -2.26] | 0.0044 | 0.0131 | **Reject H0** |
| txt minus xml | -2.63 | 4.63 | [-7.47, 1.68] | 0.3318 | 0.5569 | Fail to reject H0 |

## Caveats

- Exploratory and post-collection: the Round 2 result and a descriptive look at these November means were seen before testing. The direction (CSV longest) was therefore expected.
- Input length differs by format (CSV is shortest), so format and prompt length are confounded.
- Output tokens include reasoning tokens, so differences reflect how much the model reasoned, not only answer length; this was not separated.
- Three source datasets with overlapping rows across tables; one model alias and reasoning setting.

## Files

- `november_token_tests.py`: the analysis. Run from the repository root: `python -m analysis.november_token_tests.november_token_tests`
- `test_november_token_tests.py`: checks the exported data. Run: `python -m unittest analysis.november_token_tests.test_november_token_tests -v`
- `results/results.json` (all numbers) and `results/output_tokens_by_table_format.csv` (the 36 x 4 pooled table tested).

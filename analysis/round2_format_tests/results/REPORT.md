# Round 2 format tests (CSV / JSON / XML / TXT)

Post-collection exploratory tests on the two Round 2 lookup studies combined: Oct 21 (Titanic, red wine, medical) and Oct 25 (IBM, avocado, credit card). 576 primary requests, 36 sampled tables; every table was run 4 times in every format (named/neutral x original/altered). The unit of analysis is the table. No API calls; inputs are the published `scored_requests.csv` files.

## 1. Accuracy

Errors: **0/576** primary requests. Pooled one-sided 95% upper bound on the per-request error rate: 0.52%.

McNemar, chi-square, ANOVA and permutation tests are undefined or trivially p = 1 when no format produced an error; there are zero discordant pairs.

| format | requests | errors | 95% upper bound, per request | tables with an error | 95% upper bound, share of tables |
| --- | --- | --- | --- | --- | --- |
| csv | 144 | 0 | 2.06% | 0/36 | 7.98% |
| json | 144 | 0 | 2.06% | 0/36 | 7.98% |
| xml | 144 | 0 | 2.06% | 0/36 | 7.98% |
| txt | 144 | 0 | 2.06% | 0/36 | 7.98% |

Per-request bounds assume independent requests and are optimistic; the per-table bound uses the independent unit. These bound how often errors occur; they do not show the formats are equivalent on harder tasks.

## 2. Output tokens

Output tokens include hidden reasoning tokens; in the Oct 25 study (where the split is recorded locally) the visible answer is roughly fixed, so differences mainly reflect how much the model reasoned. H0: format labels are exchangeable within each table.

### combined (36 tables)

Mean output tokens: csv 69.0, json 58.6, xml 54.9, txt 60.5.

Omnibus: repeated-measures F = 16.54, permutation p = <0.0001; Friedman chi2 = 22.07, permutation p = <0.0001 (100000 within-table permutations).

| comparison | mean diff (tokens) | table bootstrap 95% | tables higher / lower | sign-flip p | Holm p |
| --- | --- | --- | --- | --- | --- |
| json minus csv | -10.36 | [-13.06, -7.58] | 9 / 27 | <0.0001 | <0.0001 |
| xml minus csv | -14.07 | [-17.26, -10.94] | 6 / 30 | <0.0001 | <0.0001 |
| txt minus csv | -8.47 | [-11.77, -5.12] | 11 / 25 | 0.0002 | 0.0007 |
| xml minus json | -3.71 | [-6.59, -0.88] | 12 / 23 | 0.0438 | 0.0876 |
| txt minus json | 1.89 | [-1.33, 5.12] | 20 / 16 | 0.3851 | 0.3851 |
| txt minus xml | 5.60 | [2.66, 8.49] | 23 / 13 | 0.0119 | 0.0357 |

### oct21 (18 tables)

Mean output tokens: csv 69.1, json 55.4, xml 51.2, txt 58.4.

Omnibus: repeated-measures F = 11.82, permutation p = <0.0001; Friedman chi2 = 15.40, permutation p = 0.0009 (100000 within-table permutations).

| comparison | mean diff (tokens) | table bootstrap 95% | tables higher / lower | sign-flip p | Holm p |
| --- | --- | --- | --- | --- | --- |
| json minus csv | -13.62 | [-18.26, -8.64] | 3 / 15 | 0.0009 | 0.0044 |
| xml minus csv | -17.86 | [-23.18, -12.72] | 3 / 15 | <0.0001 | 0.0005 |
| txt minus csv | -10.62 | [-15.75, -5.37] | 6 / 12 | 0.0059 | 0.0238 |
| xml minus json | -4.24 | [-8.63, -0.08] | 6 / 12 | 0.1225 | 0.2449 |
| txt minus json | 3.00 | [-1.81, 7.72] | 11 / 7 | 0.3593 | 0.3593 |
| txt minus xml | 7.24 | [4.21, 10.12] | 14 / 4 | 0.0249 | 0.0748 |

### oct25 (18 tables)

Mean output tokens: csv 68.9, json 61.8, xml 58.6, txt 62.6.

Omnibus: repeated-measures F = 5.16, permutation p = 0.0023; Friedman chi2 = 8.63, permutation p = 0.0315 (100000 within-table permutations).

| comparison | mean diff (tokens) | table bootstrap 95% | tables higher / lower | sign-flip p | Holm p |
| --- | --- | --- | --- | --- | --- |
| json minus csv | -7.10 | [-9.62, -4.49] | 6 / 12 | 0.0077 | 0.0384 |
| xml minus csv | -10.28 | [-13.90, -6.83] | 3 / 15 | 0.0003 | 0.0019 |
| txt minus csv | -6.32 | [-10.28, -2.15] | 5 / 13 | 0.0160 | 0.0642 |
| xml minus json | -3.18 | [-6.94, 0.43] | 6 / 11 | 0.2338 | 0.6843 |
| txt minus json | 0.78 | [-3.40, 5.32] | 9 / 9 | 0.8011 | 0.8011 |
| txt minus xml | 3.96 | [-0.99, 8.89] | 9 / 9 | 0.2281 | 0.6843 |

## 3. Input tokens (descriptive)

Input length is fixed by the serialization, so it is described rather than tested. Overall ratio to CSV: csv 1.00, json 1.71, xml 2.59, txt 1.86.

| study | dataset | csv | json | xml | txt |
| --- | --- | --- | --- | --- | --- |
| oct21 | medical | 1.00 | 1.85 | 2.82 | 1.87 |
| oct21 | redwine | 1.00 | 1.74 | 2.68 | 1.93 |
| oct21 | titanic | 1.00 | 1.89 | 3.09 | 2.26 |
| oct25 | avocado | 1.00 | 1.57 | 2.29 | 1.68 |
| oct25 | creditcard | 1.00 | 1.51 | 2.11 | 1.66 |
| oct25 | ibm | 1.00 | 1.85 | 3.01 | 2.00 |

## Caveats

- Exploratory, chosen after data collection; not a preregistered analysis.
- The two studies differ in datasets, date and SDK version; permutation is within table, so study-level differences do not bias the format tests, but per-study results are shown as a consistency check.
- Sampled tables overlap in source rows; one model alias (gpt-5.6-luna, medium reasoning) was tested.

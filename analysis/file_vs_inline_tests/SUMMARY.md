# File upload vs inline: does delivery affect accuracy?

Hypothesis test of whether giving Luna (gpt-5.6-luna, medium reasoning) a table as an **uploaded file** changes its accuracy, compared with **pasting the same table inline** in the prompt. Test 1 of the candidate tests: strict accuracy, pooled over tasks and formats.

## Data

- **November repeated study, file stage** (Nov 3-4): 12 tables (the first 2 primary tables per dataset and size: Titanic, red wine, medical x 80/400 rows).
- Each table was run both ways with the neutral description: 3 tasks (direct, attribute, join) x 4 formats x original/altered x 3 repeats = 72 calls per table and delivery. The inline calls are the matching primary-stage calls.
- **Totals:** uploaded 811/864 strict correct (93.87%; 2 API failures); inline 862/864 (99.77%).
- **Input:** the published per-table differences in `results/november_replication/analysis.json` (`file/strict_correct/minus_inline_uniform`), cross-checked against `file_precision_sensitivity.json` (identical). No API calls.
- **Unit of analysis:** the table. Each value is a table's file-minus-inline difference in strict accuracy over its 72 matched calls.

### Per-table differences (file minus inline, percentage points)

| Table | Dataset | Rows | Difference (pp) |
| --- | --- | --- | --- |
| core_medical_400_b0 | medical | 400 | 0.00 |
| core_medical_400_b1 | medical | 400 | 0.00 |
| core_medical_80_b0 | medical | 80 | -1.39 |
| core_medical_80_b1 | medical | 80 | 0.00 |
| core_redwine_400_b0 | redwine | 400 | 0.00 |
| core_redwine_400_b1 | redwine | 400 | -12.50 |
| core_redwine_80_b0 | redwine | 80 | 0.00 |
| core_redwine_80_b1 | redwine | 80 | -13.89 |
| core_titanic_400_b0 | titanic | 400 | -6.94 |
| core_titanic_400_b1 | titanic | 400 | -11.11 |
| core_titanic_80_b0 | titanic | 80 | -15.28 |
| core_titanic_80_b1 | titanic | 80 | -9.72 |

Mean -5.90 pp (table bootstrap 95% CI [-8.10, -3.59]). Upload worse in 7 tables, better in 0, tied in 5.

## Method

- **H0:** the mean per-table difference is 0 (delivery does not affect strict accuracy). **H1:** it is not 0. Two-sided, alpha = 0.05.
- **Decides: exact paired sign-flip permutation test.** Under H0 each table's difference is equally likely to be positive or negative; all 128 sign assignments of the 7 nonzero differences are enumerated. Statistic: |mean difference|. Critical value: the smallest |mean difference| with exact two-sided p <= 0.05.
- **Check: exact Wilcoxon signed-rank test.** Zeros dropped, midranks for ties, p from enumerating all sign assignments. Statistic W+ (sum of ranks of positive differences); reject when |W+ - center| is at least the critical distance.
- **Check: classical paired t-test**, t(11). Assumes normally distributed differences, which 5 zeros and a cap at 100% make doubtful; reported for comparison only.
- **Minimum attainable p:** with 7 nonzero tables, an exact two-sided test cannot give p below 2/2^7 = 0.0156.

## Results

| Test | Statistic | Critical value (0.05) | p-value | Decision |
| --- | --- | --- | --- | --- |
| Exact sign-flip (decides) | abs. mean diff = 5.90 pp | 4.75 pp | 0.0156 | **Reject H0** |
| Exact Wilcoxon signed-rank | W+ = 0.0 (center 14.0, distance 14.0) | distance 12.0 | 0.0156 | **Reject H0** |
| Classical paired t-test, t(11) | t = -3.26 | 2.20 | 0.0076 | **Reject H0** |

## Conclusion

**Reject H0** (exact sign-flip p = 0.0156). Uploading the table as a file lowered strict accuracy compared with pasting it inline: by 5.90 percentage points on average (95% CI [-8.10, -3.59]), and every table that differed did worse when uploaded. The Wilcoxon test (p = 0.0156) and paired t-test (p = 0.0076) agree. The p-value is the smallest this design allows (0.0156), so the evidence is as strong as 12 tables can give, but limited by the number of tables, not by the size of the effect.

### Where the drop comes from (descriptive, not tested here)

Per-table data are published only pooled over formats, so the format breakdown below is totals only (72 matched calls per cell). Almost all of the loss is CSV uploads.

| Task | Format | Inline strict % | File strict % | File minus inline (pp) |
| --- | --- | --- | --- | --- |
| direct | csv | 100.00 | 91.67 | -8.33 |
| direct | json | 100.00 | 100.00 | 0.00 |
| direct | xml | 100.00 | 100.00 | 0.00 |
| direct | txt | 100.00 | 98.61 | -1.39 |
| attribute | csv | 98.61 | 72.22 | -26.39 |
| attribute | json | 98.61 | 97.22 | -1.39 |
| attribute | xml | 100.00 | 98.61 | -1.39 |
| attribute | txt | 100.00 | 100.00 | 0.00 |
| join | csv | 100.00 | 68.06 | -31.94 |
| join | json | 100.00 | 100.00 | 0.00 |
| join | xml | 100.00 | 100.00 | 0.00 |
| join | txt | 100.00 | 100.00 | 0.00 |

## Caveats

- Exploratory: chosen after data collection; the direction of the effect was known before testing.
- 12 tables from three datasets, overlapping source rows, one model alias. File repeats reused the same uploaded file IDs, so variation across re-uploads is not measured.
- The comparison includes the provider's file processing: CSV uploads go through a spreadsheet path, other formats through text extraction. The test shows that delivery matters, not why.
- 17 file failures were only tiny numeric differences (about 1e-16). A rescoring allowing up to 1e-12 is candidate test 2, not tested here.

## Files

- `file_vs_inline_tests.py`: the analysis. Run from the repository root: `python -m analysis.file_vs_inline_tests.file_vs_inline_tests`. Reuses `sign_flip_test`, `block_bootstrap_mean` and `critical_value` from `../round2_format_tests/stat_tests.py` and `paired_t` from `../attribute_selection_tests/classical_tests.py`.
- `test_file_vs_inline_tests.py`: unit tests. Run: `python -m unittest analysis.file_vs_inline_tests.test_file_vs_inline_tests -v`
- `results/results.json`: every number above; `results/strict_correct_differences_by_table.csv`: the 12 differences tested.

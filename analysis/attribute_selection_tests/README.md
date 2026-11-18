# Multi-attribute selection tests

Hypothesis tests for the multi-attribute selection task (`task = attribute`): the model must find the one record that matches several attribute values and copy its output field. This folder follows the conventions in [../README.md](../README.md).

**Question:** does input format (CSV, JSON, XML, TXT) affect accuracy? Results, hypotheses, p-values, critical values and decisions are in [SUMMARY.md](SUMMARY.md).

## Files

- `attribute_format_tests.py`: the analysis. Run from the repository root: `python -m analysis.attribute_selection_tests.attribute_format_tests`. It regenerates `SUMMARY.md` and `results/`.
- `classical_tests.py`: classical repeated-measures ANOVA, Friedman chi-square and paired t-tests (numpy/math only). Permutation helpers are imported from `../round2_format_tests/stat_tests.py`.
- `test_classical_tests.py`: unit tests against standard table values. Run: `python -m unittest analysis.attribute_selection_tests.test_classical_tests -v`
- `results/`: `results.json` (all numbers) and `<outcome>_by_table_format.csv` (the 36 x 4 tables tested).

## Data sources

All inputs are published aggregates; nothing here calls the API or writes outside this folder.

| Study | File | What it provides | Used |
| --- | --- | --- | --- |
| November study | `results/november_replication/analysis.json` → `contrasts` | Per-table differences for 36 primary tables: `primary/attribute/{strict_correct, present_accuracy, absent_accuracy}/{json,xml,txt}_minus_csv` | Tested |
| November study | `results/november_replication/primary_task_format_detail.csv` | Accuracy totals by format | Descriptive |
| Round 4 | `results/week4_selection/summary.json` → `primary.attribute` | Totals per format (48 requests each); no per-table data for this task | Descriptive only |

Output tokens are not tested here. November output tokens for all three tasks are tested in [../november_token_tests/](../november_token_tests/SUMMARY.md), from per-table means exported to `../november_exports/`.

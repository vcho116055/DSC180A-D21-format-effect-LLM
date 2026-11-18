# Two-table join tests

Hypothesis tests for the two-table join task (`task = join`): the model finds the record matching several attribute values in a records table, then uses its `link_id` to look up the requested value in a separate, shuffled values table. This folder follows the conventions in [../README.md](../README.md).

**Question:** does input format (CSV, JSON, XML, TXT) affect accuracy? Results, hypotheses, p-values, critical values and decisions are in [SUMMARY.md](SUMMARY.md).

The tests are identical to [../attribute_selection_tests/](../attribute_selection_tests/), so the two tasks' results are directly comparable. The code is shared rather than copied.

## Files

- `join_format_tests.py`: runs the analysis for the join task. Run from the repository root: `python -m analysis.two_table_join_tests.join_format_tests`. It regenerates `SUMMARY.md` and `results/`.
- `test_join_format_tests.py`: checks the join data loads as a 36 x 4 table for every outcome, and that the within-table tests are unaffected by using CSV as the per-table reference. Run: `python -m unittest analysis.two_table_join_tests.test_join_format_tests -v`
- `results/`: `results.json` (all numbers) and `<outcome>_by_table_format.csv` (the 36 x 4 tables tested).

Shared code: `../attribute_selection_tests/attribute_format_tests.py` (`run`), `../attribute_selection_tests/classical_tests.py`, `../round2_format_tests/stat_tests.py`.

## Data sources

All inputs are published aggregates; nothing here calls the API or writes outside this folder.

| Study | File | What it provides | Used |
| --- | --- | --- | --- |
| November study | `results/november_replication/analysis.json` → `contrasts` | Per-table differences for 36 primary tables: `primary/join/{strict_correct, present_accuracy, absent_accuracy}/{json,xml,txt}_minus_csv` | Tested |
| November study | `results/november_replication/primary_task_format_detail.csv` | Accuracy totals by format | Descriptive |
| Round 4 | `results/week4_selection/summary.json` → `primary.join` | Totals per format (48 requests each); no per-table data for this task | Descriptive only |

Output tokens are not tested here. November output tokens for all three tasks are tested in [../november_token_tests/](../november_token_tests/SUMMARY.md), from per-table means exported to `../november_exports/`.

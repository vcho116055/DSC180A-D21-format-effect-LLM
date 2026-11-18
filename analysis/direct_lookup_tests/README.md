# Direct lookup tests

Hypothesis tests for the direct-lookup task (`task = direct`): the model looks up the requested field for given `record_id` values and copies it, or answers NOT_FOUND. This folder follows the conventions in [../README.md](../README.md).

**Question:** does input format (CSV, JSON, XML, TXT) affect accuracy? Results, hypotheses, p-values, critical values and decisions are in [SUMMARY.md](SUMMARY.md).

The tests are identical to [../attribute_selection_tests/](../attribute_selection_tests/) and [../two_table_join_tests/](../two_table_join_tests/), so the three tasks' results are directly comparable. Because direct lookup has almost no errors (2 of 1,728 calls), this folder also reports exact upper bounds on the per-request error rate.

## Files

- `direct_format_tests.py`: runs the analysis for the direct-lookup task. Run from the repository root: `python -m analysis.direct_lookup_tests.direct_format_tests`. It regenerates `SUMMARY.md` and `results/`.
- `test_direct_format_tests.py`: checks the data loads as a 36 x 4 table for every outcome, that only two tables differ, and the error-bound counts. Run: `python -m unittest analysis.direct_lookup_tests.test_direct_format_tests -v`
- `results/`: `results.json` (all numbers, including error bounds) and `<outcome>_by_table_format.csv` (the 36 x 4 tables tested).

Shared code: `../attribute_selection_tests/attribute_format_tests.py` (`run`, `error_bounds`), `../attribute_selection_tests/classical_tests.py`, `../round2_format_tests/stat_tests.py`.

## Data sources

All inputs are published aggregates; nothing here calls the API or writes outside this folder.

| Study | File | What it provides | Used |
| --- | --- | --- | --- |
| November study | `results/november_replication/analysis.json` → `contrasts` | Per-table differences for 36 primary tables: `primary/direct/{strict_correct, present_accuracy, absent_accuracy}/{json,xml,txt}_minus_csv` | Tested |
| November study | `primary_task_format_detail.csv`, `primary_completed_response_accuracy.csv` | Accuracy totals by format, with and without API failures | Descriptive and error bounds |
| November breadth stage | `summary_task_format.csv` (stage `breadth`) | IBM, avocado, credit card: 1,152 direct-lookup requests, all correct; no per-table contrasts published | Context only |
| Round 2 lookup studies | `results/week4_lookup/`, `results/round2_newdata/` | Same direct-lookup task, 576 primary requests, all correct | Tested separately in `../round2_format_tests/` |

Round 4 did not include a direct-lookup task. Output tokens are not tested here; see `../round2_format_tests/` (Round 2) and `../november_token_tests/` (November, all three tasks).

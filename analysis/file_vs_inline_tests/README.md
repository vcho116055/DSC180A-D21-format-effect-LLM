# File upload vs inline tests

Hypothesis tests of whether delivering a table as an uploaded file, rather than pasting the same table inline in the prompt, changes Luna's accuracy. This folder follows the conventions in [../README.md](../README.md).

**Implemented: test 1** (strict accuracy, pooled over tasks and formats, 12 tables). Hypotheses, p-values, critical values and decisions are in [SUMMARY.md](SUMMARY.md).

## Files

- `file_vs_inline_tests.py`: the analysis. Run from the repository root: `python -m analysis.file_vs_inline_tests.file_vs_inline_tests`. It regenerates `SUMMARY.md` and `results/`.
- `test_file_vs_inline_tests.py`: unit tests for the exact Wilcoxon test and the data loading. Run: `python -m unittest analysis.file_vs_inline_tests.test_file_vs_inline_tests -v`
- `results/`: `results.json` (all numbers) and `strict_correct_differences_by_table.csv` (the 12 differences tested).

Shared code: `sign_flip_test`, `block_bootstrap_mean`, `critical_value` from `../round2_format_tests/stat_tests.py`; `paired_t` from `../attribute_selection_tests/classical_tests.py`.

## Design (November study, file stage)

- **12 tables:** the first 2 primary tables per dataset and size (Titanic, red wine, medical x 80/400 rows).
- **Matched comparison:** each table was run as an uploaded file and inline, with the neutral description only: 3 tasks x 4 formats x original/altered x 3 repeats = 72 calls per table and delivery, 864 per delivery in total.
- **Inline baseline:** the matching primary-stage calls (same tables, neutral cue, both versions).
- File repeats reused the same uploaded file IDs, so variation across re-uploads is not measured. CSV uploads go through a spreadsheet-processing path; the other formats use text extraction.

## Data sources

All inputs are published aggregates; nothing here calls the API or writes outside this folder.

| File | What it provides | Level |
| --- | --- | --- |
| `results/november_replication/analysis.json` → `contrasts` → `file/<metric>/minus_inline_uniform` and `file/<task>/<metric>/minus_inline_uniform` | File minus inline differences, pooled over formats, for `strict_correct`, `present_accuracy`, `absent_accuracy`; pooled and per task (direct, attribute, join) | Per table (12) |
| `results/november_replication/file_precision_sensitivity.json` → `contrasts` | Same pooled difference under exact scoring and under a 1e-12 numeric tolerance | Per table (12) |
| `results/november_replication/file_delivery_by_task_format.csv` | Strict % by task x format x delivery (72 calls per cell) | Totals only |
| `results/november_replication/file_precision_sensitivity_summary.csv` | Exact and tolerant correct counts by delivery x task x format | Totals only |
| `results/november_replication/summary_task_format.csv` (stage `file`) | File-stage counts by task and format, including present, absent and altered values | Totals only |
| `results/november_replication/file_pilot_summary.json` | 24-request pilot, all correct | Context only |

Per-table results are published only pooled over the four formats, so the CSV-specific upload drop (167/216 vs 215/216 inline) can be tested only from totals, which treat calls as independent.

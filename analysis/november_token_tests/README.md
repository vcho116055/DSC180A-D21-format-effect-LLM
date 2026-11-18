# November output-token tests

Does input format (CSV, JSON, XML, TXT) affect how many output tokens the model produces in the November study? This is an out-of-sample check of the Round 2 result in [../round2_format_tests/](../round2_format_tests/SUMMARY.md). It follows the conventions in [../README.md](../README.md). Results are in [SUMMARY.md](SUMMARY.md).

## Files

- `november_token_tests.py`: the analysis. Run from the repository root: `python -m analysis.november_token_tests.november_token_tests`. It reuses the Round 2 test code (`token_tests` in `../round2_format_tests/round2_format_tests.py`) and regenerates `SUMMARY.md` and `results/`.
- `test_november_token_tests.py`: data checks. Run: `python -m unittest analysis.november_token_tests.test_november_token_tests -v`
- `results/`: `results.json` (all numbers) and `output_tokens_by_table_format.csv` (the 36 x 4 pooled table tested).

## Data source

`../november_exports/output_tokens_by_table_task_format.csv`: per-table mean output tokens for the 36 primary tables, 3 tasks and 4 formats, exported from the local raw run. No API calls; runs on a fresh clone.

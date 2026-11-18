# November per-table exports

Per-table aggregates from the November repeated study, exported so that analyses in this folder can run on a fresh clone. This is not an analysis; it supplies data to [../november_token_tests/](../november_token_tests/SUMMARY.md) and test 2 in [../file_vs_inline_tests/](../file_vs_inline_tests/SUMMARY.md).

The raw run (`results/overall_replication_20261103_v2/`) is git-ignored and exists only on one team member's machine. The exporter reads only its per-request score tables (IDs, correctness flags, token counts; no table values, prompts, model outputs or remote identifiers) and writes averages and counts per table.

## Files

| File | Rows | Contents |
| --- | --- | --- |
| `output_tokens_by_table_task_format.csv` | 432 | Primary stage, 36 tables x 3 tasks x 4 formats: planned and completed calls, mean output tokens, mean input tokens |
| `file_vs_inline_by_table_format.csv` | 96 | File stage and its matched inline calls, 12 tables x 4 formats x 2 deliveries: attempts, completed, exact-correct and precision-tolerant-correct counts |
| `export_manifest.json` | | SHA-256 of the raw inputs, row counts, notes |
| `export_november_aggregates.py` | | The exporter. Needs the raw run: `python -m analysis.november_exports.export_november_aggregates` |

## Checks

- `scored_requests.csv` must match the hash sealed in the run's `FINAL_INTEGRITY.json`.
- File-vs-inline totals must equal the published ones (file 811 exact / 828 tolerant of 864; inline 862 / 862 of 864).
- The analyses' unit tests check that the exported input tokens reproduce `results/november_replication/representation_overhead.csv` and that the per-format file-vs-inline differences average to the published per-table differences.

## Notes

- Output tokens include hidden reasoning tokens.
- One primary call (`core_titanic_80_b0`, direct, XML) was an API error, so that cell averages 11 calls instead of 12.
- These files are outside `results/november_replication/PUBLICATION_REVIEW.json`, which covers only that folder.

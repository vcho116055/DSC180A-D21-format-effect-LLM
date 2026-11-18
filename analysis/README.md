# Hypothesis testing

Offline hypothesis tests on results that have already been collected. Nothing in this folder calls the API or sends paid requests.

The experiment scripts in `../experiments/` report descriptive block-bootstrap confidence intervals only; none of them compute p-values. The tests here are added after data collection. They are exploratory and do not replace the prespecified intervals in each study's report.

## Conventions

- **One subfolder per analysis**, holding its code, unit tests, a `SUMMARY.md`, and a `results/` folder for its outputs, e.g. `round2_format_tests/`.
- **Run from the repository root** as a module: `python -m analysis.<subfolder>.<script_name>`.
- **Unit of analysis is the sampled table (block)**, not the individual API call. Calls that share a table (repeats, tasks, versions, cues, formats) are not independent; average within a block before testing.
- **Inputs:** read the published aggregates under `../results/` (`scored_requests.csv`, `analysis.json`, per-block differences) but never write there. Build paths relative to the repository, e.g. `Path(__file__).resolve().parents[2] / 'results'` from inside a subfolder.
- **Outputs:** write only inside the analysis subfolder (`analysis/<subfolder>/results/`). Nothing outside `analysis/` is modified.
- **Local-only data:** if a script reads git-ignored raw files (for example `results/round2_newdata/scored_cells.csv` or `trials.jsonl`), commit only aggregate numbers. Never commit table values, prompts, or model outputs; they embed source dataset rows. Keep row-level intermediates out of git.
- **Do not edit `../experiments/`.** Those scripts' hashes are recorded in the run manifests and `provenance.json`. Import helpers from them instead (e.g. `from experiments import week4_study`).
- **Dependencies:** the locked environment has numpy, pandas, and matplotlib, but not scipy or statsmodels. Either implement tests with numpy or add a package with `uv add <package>` and commit the updated `pyproject.toml` and `uv.lock`.
- **Tests:** put unit tests next to the script as `test_<script_name>.py` (unittest), run with `uv run --locked python -m unittest analysis.<subfolder>.test_<script_name> -v`.

## Analyses

| Folder | Question | Summary |
| --- | --- | --- |
| `round2_format_tests/` | Do input formats differ in accuracy or output tokens on the Round 2 lookup task (both studies, 36 tables)? | [SUMMARY.md](round2_format_tests/SUMMARY.md) |
| `attribute_selection_tests/` | Does input format affect accuracy on multi-attribute selection (November study, 36 tables)? | [SUMMARY.md](attribute_selection_tests/SUMMARY.md) |
| `two_table_join_tests/` | Does input format affect accuracy on the two-table join task (November study, 36 tables)? Shares the attribute-selection code. | [SUMMARY.md](two_table_join_tests/SUMMARY.md) |
| `direct_lookup_tests/` | Does input format affect accuracy on direct lookup (November study, 36 tables)? Adds error-rate bounds. Shares the attribute-selection code. | [SUMMARY.md](direct_lookup_tests/SUMMARY.md) |
| `file_vs_inline_tests/` | Does uploading the table as a file change accuracy compared with pasting it inline (November file stage, 12 tables)? Test 1 implemented. | [SUMMARY.md](file_vs_inline_tests/SUMMARY.md) |

## Data available for testing

| Study | Published (in git) | Local-only raw data on this machine |
| --- | --- | --- |
| Round 2 lookup, Oct 21 (`results/week4_lookup/`) | `scored_requests.csv` (358 requests), `analysis.json` (per-block differences, 18 blocks) | None (withheld) |
| Round 2 new datasets, Oct 25 (`results/round2_newdata/`) | `scored_requests.csv` (340 requests), `analysis.json` (18 blocks) | `cases.jsonl`, `trials.jsonl`, `scored_cells.csv` |
| Round 4 selection and joins (`results/week4_selection/`) | `summary.json` (aggregates, 12-block contrasts) | None (withheld) |
| November repeated study (`results/november_replication/`) | `analysis.json` (per-block differences, 36 primary / 12 file blocks), summary CSVs | None (raw run not on this machine) |

The two Round 2 `scored_requests.csv` files share identical columns and design and can be stacked; their primary comparisons were 100% correct, so accuracy tests have no variation to detect.

"""Does input format (CSV / JSON / XML / TXT) affect accuracy on the two-table join task?

Same tests as ../attribute_selection_tests/ (shared code), applied to the join
task of the November repeated study: 36 sampled tables, each run in all four
formats. Reads the published per-table differences
`primary/join/<metric>/<format>_minus_csv` in results/november_replication/analysis.json.
Post-collection, exploratory; no API calls; writes only inside this folder
(results/ and SUMMARY.md).

Usage (from the repository root):
    python -m analysis.two_table_join_tests.join_format_tests
"""
from pathlib import Path

from analysis.attribute_selection_tests.attribute_format_tests import run

HERE = Path(__file__).resolve().parent


def main():
    run('join', HERE)


if __name__ == '__main__':
    main()

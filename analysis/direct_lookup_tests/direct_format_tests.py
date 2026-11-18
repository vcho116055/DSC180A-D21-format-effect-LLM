"""Does input format (CSV / JSON / XML / TXT) affect accuracy on direct lookup?

Same tests as ../attribute_selection_tests/ (shared code), applied to the direct
(record-ID) lookup task of the November repeated study: 36 sampled tables, each
run in all four formats. Reads the published per-table differences
`primary/direct/<metric>/<format>_minus_csv` in results/november_replication/analysis.json.
Because direct lookup has almost no errors, it also reports exact upper bounds on
the per-request error rate. Post-collection, exploratory; no API calls; writes
only inside this folder (results/ and SUMMARY.md).

Usage (from the repository root):
    python -m analysis.direct_lookup_tests.direct_format_tests
"""
from pathlib import Path

from analysis.attribute_selection_tests.attribute_format_tests import run

HERE = Path(__file__).resolve().parent


def main():
    run('direct', HERE)


if __name__ == '__main__':
    main()
